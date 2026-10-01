from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.users.views import RegisterView, CurrentUserView, UserDetailView, LoginView
from apps.books.views import BookViewSet, search_view, explore_view
from apps.audiobooks.views import AudiobookViewSet, ChapterListView, ProgressView
from apps.reels.views import ReelViewSet
from apps.interactions.views import ReelLikeView, ReelSaveView, BookLikeView, BookSaveView
from apps.comments.views import ReelCommentsView, CommentDeleteView
from apps.comments.views import CommentLikeView
from apps.library.views import LibraryView, LikedBooksView, SavedBooksView, HistoryView
from apps.notifications.views import NotificationListView, ReadNotificationsView, ReadAllNotificationsView

router = DefaultRouter()
router.register("books", BookViewSet, basename="book")
router.register("audiobooks", AudiobookViewSet, basename="audiobook")
router.register("reels", ReelViewSet, basename="reel")

def health_check(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health_check, name="health"),
    path("api/health/", health_check, name="api-health"),
    path("admin/", admin.site.urls),
    path("api/auth/register/", RegisterView.as_view()),
    path("api/auth/login/", LoginView.as_view()),
    path("api/auth/refresh/", TokenRefreshView.as_view()),
    path("api/auth/me/", CurrentUserView.as_view()),
    path("api/users/<str:username>/", UserDetailView.as_view()),
    path("api/users/<str:username>/follow/", UserDetailView.as_view()),
    path("api/search/", search_view), path("api/explore/", explore_view),
    path("api/audiobooks/<int:pk>/chapters/", ChapterListView.as_view()),
    path("api/audiobooks/<int:pk>/progress/", ProgressView.as_view()),
    path("api/reels/<int:pk>/like/", ReelLikeView.as_view()),
    path("api/reels/<int:pk>/save/", ReelSaveView.as_view()),
    path("api/books/<int:pk>/like/", BookLikeView.as_view()),
    path("api/books/<int:pk>/save/", BookSaveView.as_view()),
    path("api/reels/<int:pk>/comments/", ReelCommentsView.as_view()),
    path("api/comments/<int:pk>/", CommentDeleteView.as_view()),
    path("api/comments/<int:pk>/like/", CommentLikeView.as_view()),
    path("api/library/", LibraryView.as_view()), path("api/library/liked/", LikedBooksView.as_view()),
    path("api/library/saved/", SavedBooksView.as_view()), path("api/library/history/", HistoryView.as_view()),
    path("api/notifications/", NotificationListView.as_view()),
    path("api/notifications/read/", ReadNotificationsView.as_view()),
    path("api/notifications/read-all/", ReadAllNotificationsView.as_view()),
    path("api/", include(router.urls)), path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    path("", TemplateView.as_view(template_name="index.html"), name="frontend"),
    re_path(r"^(?!api/|admin/|static/).+$", TemplateView.as_view(template_name="index.html")),
]