from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Notification
from .serializers import NotificationSerializer

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self): return Notification.objects.filter(recipient=self.request.user).select_related("actor")
class ReadNotificationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        ids = request.data.get("ids", [])
        Notification.objects.filter(recipient=request.user, id__in=ids).update(is_read=True)
        return Response({"updated": len(ids)})
class ReadAllNotificationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        updated, _ = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"updated": updated})