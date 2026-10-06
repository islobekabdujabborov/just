from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import Follow, User
from .serializers import EmailTokenSerializer, PrivateUserSerializer, RegisterSerializer, UserSerializer
from apps.notifications.models import Notification

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
            if user: response.data["user"] = UserSerializer(user, context={"request": request}).data
        return response

class CurrentUserView(generics.RetrieveUpdateAPIView):
    serializer_class = PrivateUserSerializer
    permission_classes = [IsAuthenticated]
    def get_object(self): return self.request.user

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
        if not request.user.is_authenticated: return Response(status=status.HTTP_401_UNAUTHORIZED)
        target = get_object_or_404(User, username=username)
        if target == request.user: return Response({"detail": "You cannot follow yourself."}, status=400)
        _, created = Follow.objects.get_or_create(follower=request.user, followed=target)
        if created and Notification.should_send(target, "follow"):
            Notification.objects.create(recipient=target, actor=request.user, type="follow", text=f"@{request.user.username} started following you")
        return Response({"is_following": True, "followers_count": target.followers.count()})
    def delete(self, request, username):
        if not request.user.is_authenticated: return Response(status=status.HTTP_401_UNAUTHORIZED)
        target = get_object_or_404(User, username=username)
        Follow.objects.filter(follower=request.user, followed=target).delete()
        return Response({"is_following": False, "followers_count": target.followers.count()})