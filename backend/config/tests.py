import tempfile
from pathlib import Path

from django.test import TestCase, override_settings


class MediaServingTests(TestCase):
    def test_missing_media_does_not_fall_through_to_the_spa(self):
        with tempfile.TemporaryDirectory() as media_dir, override_settings(MEDIA_ROOT=media_dir, DEBUG=False):
            response = self.client.get("/media/missing-file.mp3")

        self.assertEqual(response.status_code, 404)
        self.assertNotIn(b"<div id=\"root\">", response.content)

    def test_uploaded_media_is_served_from_media_root(self):
        with tempfile.TemporaryDirectory() as media_dir, override_settings(MEDIA_ROOT=media_dir, DEBUG=False):
            Path(media_dir, "sample.mp3").write_bytes(b"audio-data")
            response = self.client.get("/media/sample.mp3")
            try:
                content = b"".join(response.streaming_content)
            finally:
                response.close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(content, b"audio-data")

    def test_media_supports_byte_range_requests(self):
        with tempfile.TemporaryDirectory() as media_dir, override_settings(MEDIA_ROOT=media_dir, DEBUG=False):
            Path(media_dir, "sample.mp3").write_bytes(b"audio-data")
            response = self.client.get("/media/sample.mp3", HTTP_RANGE="bytes=2-5")
            try:
                content = b"".join(response.streaming_content)
            finally:
                response.close()

        self.assertEqual(response.status_code, 206)
        self.assertEqual(content, b"dio-")
        self.assertEqual(response["Content-Range"], "bytes 2-5/10")