from apps.users.models import Subscription
from django.core import signing
from django.urls import reverse


def has_premium_subscription(user):
    return Subscription.objects.active_for(user).exists()


def can_access_audiobook(user, audiobook):
    if audiobook.access != audiobook.ACCESS_PREMIUM:
        return True
    if user and getattr(user, "is_authenticated", False):
        if user.is_staff or audiobook.created_by_id == user.id:
            return True
    return has_premium_subscription(user)


def can_access_chapter(user, chapter):
    if chapter.audiobook.access != chapter.audiobook.ACCESS_PREMIUM or chapter.is_free_preview:
        return True
    return can_access_audiobook(user, chapter.audiobook)


def signed_audio_url(request, resource_type, instance):
    if resource_type == "chapter":
        path = instance.audio_file.name
        payload = {"type": resource_type, "id": instance.id, "path": path}
        route = reverse("protected-chapter-audio", kwargs={"pk": instance.id, "token": signing.TimestampSigner(salt="avobook.protected_audio").sign_object(payload)})
    else:
        path = instance.audio_file.name
        payload = {"type": resource_type, "id": instance.id, "path": path}
        route = reverse("protected-audiobook-audio", kwargs={"pk": instance.id, "token": signing.TimestampSigner(salt="avobook.protected_audio").sign_object(payload)})
    return request.build_absolute_uri(route)
