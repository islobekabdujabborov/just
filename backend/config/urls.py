import mimetypes
import re
from pathlib import Path
from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.http import FileResponse, Http404, HttpResponse, HttpResponseNotAllowed, JsonResponse, StreamingHttpResponse
from django.utils._os import safe_join
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


def service_worker(request):
    worker_path = settings.PROJECT_ROOT / "dist" / "service-worker.js"
    response = FileResponse(worker_path.open("rb"), content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response


def media_serve(request, path):
    if request.method not in {"GET", "HEAD"}:
        return HttpResponseNotAllowed(["GET", "HEAD"])
    try:
        full_path = safe_join(str(settings.MEDIA_ROOT), path)
        file_path = Path(full_path)
        file_size = file_path.stat().st_size
    except (FileNotFoundError, ValueError, SuspiciousFileOperation):
        raise Http404
    if not file_path.is_file():
        raise Http404

    content_type = mimetypes.guess_type(full_path)[0] or "application/octet-stream"
    range_header = request.headers.get("Range")
    if range_header:
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
        if not match or (not match.group(1) and not match.group(2)) or file_size == 0:
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{file_size}"
            response["Accept-Ranges"] = "bytes"
            return response
        try:
            if match.group(1):
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else file_size - 1
            else:
                suffix_length = int(match.group(2))
                start = max(file_size - suffix_length, 0)
                end = file_size - 1
        except ValueError:
            start, end = file_size, file_size
        end = min(end, file_size - 1)
        if start >= file_size or start > end:
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{file_size}"
            response["Accept-Ranges"] = "bytes"
            return response

        media_file = file_path.open("rb")
        media_file.seek(start)
        remaining = end - start + 1

        def stream_range():
            nonlocal remaining
            while remaining:
                chunk = media_file.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

        response = StreamingHttpResponse(stream_range(), status=206, content_type=content_type)
        response._resource_closers.append(media_file.close)
        response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        response["Content-Length"] = str(end - start + 1)
    elif request.method == "HEAD":
        response = HttpResponse(content_type=content_type)
        response["Content-Length"] = str(file_size)
    else:
        response = FileResponse(file_path.open("rb"), content_type=content_type)
    response["Accept-Ranges"] = "bytes"
    return response


urlpatterns = [
    path("health/", health_check, name="health"),
    path("api/health/", health_check, name="api-health"),
    path("service-worker.js", service_worker, name="service-worker"),
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
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", media_serve),
]

urlpatterns += [
    path("", TemplateView.as_view(template_name="index.html"), name="frontend"),
    re_path(r"^(?!api/|admin/|static/).+$", TemplateView.as_view(template_name="index.html")),
]