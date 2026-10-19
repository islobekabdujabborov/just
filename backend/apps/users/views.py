from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.notifications.models import Notification
from apps.users.services import (
    cancel_verification,
    create_telegram_verification,
    get_verification_status,
    resend_verification_code,
    validate_verification_token,
    verify_registration_code,
)
from .models import Follow, Subscription, User
from .serializers import EmailTokenSerializer, PrivateUserSerializer, RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            username = request.data.get("username", "")
            user = User.objects.filter(email__iexact=username).first() if "@" in username else User.objects.filter(username=username).first()
            if user:
                response.data["user"] = UserSerializer(user, context={"request": request}).data
        return response


class CurrentUserView(generics.RetrieveUpdateAPIView):
    serializer_class = PrivateUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class SubscriptionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        active = Subscription.objects.active_for(request.user).first()
        subscription = active or Subscription.objects.filter(user=request.user).first()
        data = None
        if subscription:
            data = {
                "plan": subscription.plan,
                "status": subscription.status,
                "started_at": subscription.started_at,
                "expires_at": subscription.expires_at,
                "canceled_at": subscription.canceled_at,
                "provider": subscription.provider,
            }
        return Response({"subscription": data, "has_access": bool(active)})


class CancelSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        subscription = Subscription.objects.active_for(request.user).filter(
            status__in=[Subscription.STATUS_ACTIVE, Subscription.STATUS_CANCELED]
        ).first()
        if not subscription:
            return Response({"detail": "Faol obuna topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        if subscription.status == Subscription.STATUS_ACTIVE:
            subscription.status = Subscription.STATUS_CANCELED
            subscription.canceled_at = timezone.now()
            subscription.save(update_fields=["status", "canceled_at"])
        return Response({
            "status": subscription.status,
            "expires_at": subscription.expires_at,
            "canceled_at": subscription.canceled_at,
            "has_access": subscription.grants_access,
        })


class CheckoutStubView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(
            {"detail": "To'lov provayderi ulanmagan. Checkout hozircha mavjud emas."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class PaymentWebhookStubView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, provider):
        return Response(
            {"detail": f"{provider} webhook integratsiyasi hali ulanmagan."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class TelegramVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        action = request.path.rstrip("/").split("/")[-1]
        if action == "start":
            username = request.data.get("username", "")
            email = request.data.get("email", "")
            password = request.data.get("password", "")
            confirmation = request.data.get("confirmPassword") or request.data.get("password_confirmation")
            try:
                result = create_telegram_verification(request, username, email, password, confirmation)
                return Response(result, status=status.HTTP_200_OK)
            except Exception as exc:
                detail = str(exc)
                return Response({"detail": detail if detail else "Telegram verification could not be started."}, status=status.HTTP_400_BAD_REQUEST)

        if action == "verify":
            token = request.data.get("verification_token")
            code = request.data.get("code")
            try:
                result = verify_registration_code(request, token, code)
                return Response(result, status=status.HTTP_200_OK)
            except Exception as exc:
                detail = str(exc)
                return Response({"detail": detail if detail else "Code verification failed."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Method not supported."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class TelegramStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.GET.get("token") or request.session.get("telegram_verification_token")
        try:
            result = get_verification_status(request, token)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as exc:
            return Response({"detail": str(exc) or "Unable to load verification status."}, status=status.HTTP_400_BAD_REQUEST)


class ResendTelegramVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("verification_token") or request.session.get("telegram_verification_token")
        try:
            result = resend_verification_code(request, token)
            return Response({"status": result.get("status"), "detail": "Yangi kod yuborildi."}, status=status.HTTP_200_OK)
        except Exception as exc:
            return Response({"detail": str(exc) or "Unable to resend code."}, status=status.HTTP_400_BAD_REQUEST)


class CancelTelegramVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("verification_token") or request.session.get("telegram_verification_token")
        try:
            result = cancel_verification(request, token)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as exc:
            return Response({"detail": str(exc) or "Unable to cancel verification."}, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(APIView):
    def get(self, request, username):
        user = get_object_or_404(User, username=username)
        can_view = user.can_view_profile(request.user)
        data = UserSerializer(user, context={"request": request}).data
        data.pop("email", None)
        data["is_following"] = request.user.is_authenticated and Follow.objects.filter(follower=request.user, followed=user).exists()
        if not can_view:
            data["reels"] = []
            data["private_account"] = True
            return Response(data, status=status.HTTP_403)
        from apps.reels.serializers import ReelSerializer
        reels = user.reels.select_related("book", "book__author", "book__genre", "author").order_by("-created_at")[:12]
        data["reels"] = ReelSerializer(reels, many=True, context={"request": request}).data
        return Response(data)

    def post(self, request, username):
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        target = get_object_or_404(User, username=username)
        if target == request.user:
            return Response({"detail": "You cannot follow yourself."}, status=400)
        _, created = Follow.objects.get_or_create(follower=request.user, followed=target)
        if created and Notification.should_send(target, "follow"):
            Notification.objects.create(recipient=target, actor=request.user, type="follow", text=f"@{request.user.username} started following you")
        return Response({"is_following": True, "followers_count": target.followers.count()})

    def delete(self, request, username):
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        target = get_object_or_404(User, username=username)
        Follow.objects.filter(follower=request.user, followed=target).delete()
        return Response({"is_following": False, "followers_count": target.followers.count()})