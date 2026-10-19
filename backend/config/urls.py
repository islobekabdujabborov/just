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
from django.core import signing
from django.shortcuts import get_object_or_404
from django.utils._os import safe_join
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.users.views import (
    CancelTelegramVerificationView,
    CurrentUserView,
    LoginView,
    RegisterView,
    ResendTelegramVerificationView,
    TelegramStatusView,
    TelegramStartVerificationView,
    TelegramVerifyVerificationView,
    UserDetailView,
    CancelSubscriptionView,
    CheckoutStubView,
    PaymentWebhookStubView,
    SubscriptionStatusView,
)
from apps.books.views import BookReviewListView, BookViewSet, RecommendationsView, ReviewDetailView, search_view, explore_view
from apps.audiobooks.models import Audiobook, Chapter
from apps.audiobooks.views import AudiobookBookmarkListView, AudiobookStreamView, AudiobookViewSet, BookmarkDetailView, ChapterDetailView, ChapterListView, ChapterStreamView, ProgressView
from apps.reels.views import FollowingReelFeedView, ReelViewSet
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


def _serve_media_file(request, path):
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


def media_serve(request, path):
    if request.method not in {"GET", "HEAD"}:
        return HttpResponseNotAllowed(["GET", "HEAD"])
    locked_chapter = Chapter.objects.filter(
        audio_file=path,
        audiobook__access=Audiobook.ACCESS_PREMIUM,
        is_free_preview=False,
    ).exists()
    premium_audiobook = Audiobook.objects.filter(
        audio_file=path,
        access=Audiobook.ACCESS_PREMIUM,
    ).exists()
    if locked_chapter or premium_audiobook:
        return HttpResponse("Premium audio must be requested through its signed stream URL.", status=403)
    return _serve_media_file(request, path)


def protected_chapter_media(request, pk, token):
    try:
        payload = signing.TimestampSigner(salt="avobook.protected_audio").unsign_object(token, max_age=600)
    except signing.BadSignature:
        return HttpResponse("Signed audio URL is invalid or expired.", status=403)
    chapter = get_object_or_404(Chapter, pk=pk)
    if payload != {"type": "chapter", "id": chapter.id, "path": chapter.audio_file.name} or not chapter.audio_file:
        raise Http404
    return _serve_media_file(request, chapter.audio_file.name)


def protected_audiobook_media(request, pk, token):
    try:
        payload = signing.TimestampSigner(salt="avobook.protected_audio").unsign_object(token, max_age=600)
    except signing.BadSignature:
        return HttpResponse("Signed audio URL is invalid or expired.", status=403)
    audiobook = get_object_or_404(Audiobook, pk=pk)
    if payload != {"type": "audiobook", "id": audiobook.id, "path": audiobook.audio_file.name} or not audiobook.audio_file:
        raise Http404
    return _serve_media_file(request, audiobook.audio_file.name)


urlpatterns = [
    path("health/", health_check, name="health"),
    path("api/health/", health_check, name="api-health"),
    path("service-worker.js", service_worker, name="service-worker"),
    path("admin/", admin.site.urls),
    path("api/auth/login/", LoginView.as_view()),
    path("api/auth/refresh/", TokenRefreshView.as_view()),
    path("api/auth/me/", CurrentUserView.as_view()),
    path("api/subscription/", SubscriptionStatusView.as_view()),
    path("api/subscription/cancel/", CancelSubscriptionView.as_view()),
    path("api/payments/checkout/", CheckoutStubView.as_view()),
    path("api/payments/<str:provider>/webhook/", PaymentWebhookStubView.as_view()),
    path("api/auth/telegram/start/", TelegramStartVerificationView.as_view()),
    path("api/auth/telegram/status/", TelegramStatusView.as_view()),
    path("api/auth/telegram/verify/", TelegramVerifyVerificationView.as_view()),
    path("api/auth/telegram/resend/", ResendTelegramVerificationView.as_view()),
    path("api/auth/telegram/cancel/", CancelTelegramVerificationView.as_view()),
    path("api/users/<str:username>/", UserDetailView.as_view()),
    path("api/users/<str:username>/follow/", UserDetailView.as_view()),
    path("api/search/", search_view), path("api/explore/", explore_view),
    path("api/audiobooks/<int:pk>/chapters/", ChapterListView.as_view()),
    path("api/audiobooks/<int:pk>/stream/", AudiobookStreamView.as_view()),
    path("api/chapters/<int:pk>/", ChapterDetailView.as_view()),
    path("api/chapters/<int:pk>/stream/", ChapterStreamView.as_view()),
    path("api/audiobooks/<int:pk>/progress/", ProgressView.as_view()),
    path("api/audiobooks/<int:pk>/bookmarks/", AudiobookBookmarkListView.as_view()),
    path("api/bookmarks/<int:pk>/", BookmarkDetailView.as_view()),
    path("api/reels/feed/", FollowingReelFeedView.as_view()),
    path("api/reels/<int:pk>/like/", ReelLikeView.as_view()),
    path("api/reels/<int:pk>/save/", ReelSaveView.as_view()),
    path("api/books/<int:pk>/like/", BookLikeView.as_view()),
    path("api/books/<int:pk>/save/", BookSaveView.as_view()),
    path("api/books/<int:pk>/reviews/", BookReviewListView.as_view()),
    path("api/reviews/<int:pk>/", ReviewDetailView.as_view()),
    path("api/recommendations/", RecommendationsView.as_view()),
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
    re_path(r"^media-protected/chapters/(?P<pk>\d+)/(?P<token>[^/]+)/$", protected_chapter_media, name="protected-chapter-audio"),
    re_path(r"^media-protected/audiobooks/(?P<pk>\d+)/(?P<token>[^/]+)/$", protected_audiobook_media, name="protected-audiobook-audio"),
    re_path(r"^media/(?P<path>.*)$", media_serve),
]

urlpatterns += [
    path("", TemplateView.as_view(template_name="index.html"), name="frontend"),
    re_path(r"^(?!api/|admin/|static/).+$", TemplateView.as_view(template_name="index.html")),
]