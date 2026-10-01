from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.books.models import Book
from apps.books.serializers import BookSerializer
from apps.interactions.models import Like, Save
from .models import ListeningProgress

class LikedBooksView(generics.ListAPIView):
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self): return Book.objects.filter(likes__user=self.request.user).select_related("author", "genre").distinct()
class SavedBooksView(generics.ListAPIView):
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self): return Book.objects.filter(saves__user=self.request.user).select_related("author", "genre").distinct()
class HistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        rows = ListeningProgress.objects.filter(user=request.user).select_related("audiobook__book", "audiobook__book__author", "audiobook__book__genre")
        return Response([{"audiobook_id": row.audiobook_id, "book": BookSerializer(row.audiobook.book, context={"request": request}).data,
                          "position": row.position, "percentage": row.percentage, "updated_at": row.updated_at} for row in rows])
class LibraryView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        liked = Book.objects.filter(likes__user=request.user).select_related("author", "genre").distinct()
        saved = Book.objects.filter(saves__user=request.user).select_related("author", "genre").distinct()
        history = ListeningProgress.objects.filter(user=request.user).select_related("audiobook__book", "audiobook__book__author", "audiobook__book__genre")
        uploaded = Book.objects.filter(owner=request.user).select_related("author", "genre")
        context = {"request": request}
        return Response({"liked": BookSerializer(liked, many=True, context=context).data,
                         "saved": BookSerializer(saved, many=True, context=context).data,
                         "history": [{"book": BookSerializer(p.audiobook.book, context=context).data, "position": p.position, "percentage": p.percentage} for p in history],
                         "my_books": BookSerializer(uploaded, many=True, context=context).data})