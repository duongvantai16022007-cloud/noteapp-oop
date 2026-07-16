import tempfile
import unittest
import os
import sys
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from services.export_service import ExportService
from services.media_service import MediaService

try:
    import pyzipper
except ImportError:
    pyzipper = None


class DummyNote:
    def __init__(self, content):
        self.title = "Media note"
        self.content = content
        self.deadline_at = None
        self.reminder_at = None


class MediaServiceTests(unittest.TestCase):
    def test_export_resolves_legacy_media_path_from_user_storage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            user_root = Path(temp_dir) / "Engraver"
            source = user_root / "media" / "photo.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"legacy image")

            with patch.dict(os.environ, {"LOCALAPPDATA": temp_dir}), patch.object(
                sys, "frozen", False, create=True
            ):
                resolved = ExportService._resolve_media_path("media/photo.png")

            self.assertEqual(resolved, source.resolve())

    def test_export_resolves_current_media_path_in_packaged_storage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "Engraver" / "data" / "media" / "photo.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"current image")

            with patch.dict(os.environ, {"LOCALAPPDATA": temp_dir}), patch.object(
                sys, "frozen", True, create=True
            ):
                resolved = ExportService._resolve_media_path("data/media/photo.png")

            self.assertEqual(resolved, source.resolve())

    def test_import_file_copies_media_into_managed_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "recording.mp3"
            source.write_bytes(b"example audio")
            service = MediaService(
                project_root=root,
                media_dir=root / "data" / "media"
            )

            attachment = service.import_file(source)
            copied_file = service.resolve_path(attachment["path"])

            self.assertEqual(attachment["kind"], "audio")
            self.assertEqual(attachment["name"], "recording.mp3")
            self.assertEqual(copied_file.read_bytes(), b"example audio")
            self.assertNotEqual(copied_file, source)

    def test_media_service_resolves_legacy_path_in_current_project(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "data" / "media" / "legacy.mp4"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"video")
            service = MediaService(project_root=root, media_dir=root / "data" / "media")

            self.assertEqual(service.resolve_path("media/legacy.mp4"), source.resolve())

    def test_import_file_rejects_unsupported_extension(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "document.txt"
            source.write_text("not media", encoding="utf-8")
            service = MediaService(project_root=root, media_dir=root / "media")

            with self.assertRaises(ValueError):
                service.import_file(source)

    def test_markdown_export_copies_and_links_media_inline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "photo.png"
            source.write_bytes(b"fake png data")
            output = root / "exports" / "note.md"
            output.parent.mkdir()
            note = DummyNote({
                "text": "Hello media",
                "spans": [],
                "media": [{
                    "id": "image-1",
                    "name": "photo.png",
                    "path": str(source),
                    "kind": "image",
                    "size": source.stat().st_size,
                    "position": 5,
                }]
            })

            ExportService().export_to_markdown(note, output)

            markdown = output.read_text(encoding="utf-8")
            self.assertIn("Hello![photo.png](note_media/photo.png) media", markdown)
            self.assertEqual(
                (output.parent / "note_media" / "photo.png").read_bytes(),
                source.read_bytes()
            )

    def test_markdown_export_url_encodes_special_media_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "ảnh #1.png"
            source.write_bytes(b"fake png data")
            output = root / "note.md"
            note = DummyNote({
                "text": "Ảnh",
                "media": [{
                    "name": source.name,
                    "path": str(source),
                    "kind": "image",
                    "position": 3,
                }],
            })

            ExportService().export_to_markdown(note, output)

            markdown = output.read_text(encoding="utf-8")
            self.assertIn("note_media/%E1%BA%A3nh%20%231.png", markdown)

    @unittest.skipIf(pyzipper is None, "pyzipper is not installed")
    def test_media_archive_creates_aes_encrypted_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "clip.mp4"
            source.write_bytes(b"example video bytes")
            output = root / "protected.zip"
            note = DummyNote({
                "text": "Video",
                "media": [{
                    "name": source.name,
                    "path": str(source),
                    "kind": "video",
                    "position": 5,
                }],
            })

            count = ExportService().export_media_archive(note, output, "secret-123")

            self.assertEqual(count, 1)
            with pyzipper.AESZipFile(output) as archive:
                names = archive.namelist()
                media_name = next(name for name in names if name.endswith("/clip.mp4"))
                archive.setpassword(b"wrong-password")
                with self.assertRaises(RuntimeError):
                    archive.read(media_name)
                archive.setpassword(b"secret-123")
                self.assertEqual(archive.read(media_name), source.read_bytes())

            extracted = root / "extracted"
            extracted_count = ExportService().extract_media_archive(
                output,
                extracted,
                "secret-123",
            )
            self.assertEqual(extracted_count, 2)
            self.assertEqual(
                next(extracted.rglob("clip.mp4")).read_bytes(),
                source.read_bytes(),
            )

            with self.assertRaises(RuntimeError):
                ExportService().extract_media_archive(
                    output,
                    root / "wrong-password",
                    "incorrect",
                )

    @unittest.skipIf(pyzipper is None, "pyzipper is not installed")
    def test_media_archive_rejects_parent_path_during_extraction(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "unsafe.zip"
            with pyzipper.AESZipFile(
                archive_path,
                "w",
                compression=pyzipper.ZIP_DEFLATED,
                encryption=pyzipper.WZ_AES,
            ) as archive:
                archive.setpassword(b"secret-123")
                archive.setencryption(pyzipper.WZ_AES, nbits=256)
                archive.writestr("../outside.txt", b"unsafe")

            with self.assertRaises(ValueError):
                ExportService().extract_media_archive(
                    archive_path,
                    root / "destination",
                    "secret-123",
                )
            self.assertFalse((root / "outside.txt").exists())

    def test_pdf_export_uses_unicode_font_without_project_pickle_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "ghi-chu.pdf"
            note = DummyNote({
                "text": "Nội dung tiếng Việt: Nguyễn Quyền, trường học, nhắc nhở.",
                "spans": [],
                "media": [],
            })

            ExportService().export_to_pdf(note, output)

            self.assertTrue(output.read_bytes().startswith(b"%PDF"))
            project_font_dir = Path(__file__).resolve().parent.parent / "assets" / "fonts"
            self.assertFalse((project_font_dir / "ArialUnicode.pkl").exists())
            self.assertFalse((project_font_dir / "ArialUnicode.cw127.pkl").exists())

    def test_pdf_export_embeds_inline_image(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "photo.png"
            Image.new("RGB", (640, 360), "#2563eb").save(source)
            output = root / "media-note.pdf"
            note = DummyNote({
                "text": "Trước ảnh, sau ảnh.",
                "spans": [],
                "media": [{
                    "id": "image-1",
                    "name": "photo.png",
                    "path": str(source),
                    "kind": "image",
                    "size": source.stat().st_size,
                    "position": 10,
                }],
            })

            ExportService().export_to_pdf(note, output)

            pdf_data = output.read_bytes()
            self.assertTrue(pdf_data.startswith(b"%PDF"))
            self.assertIn(b"/Subtype /Image", pdf_data)


if __name__ == "__main__":
    unittest.main()
