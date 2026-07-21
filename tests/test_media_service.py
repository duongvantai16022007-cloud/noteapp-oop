import tempfile
import unittest
import os
import sys
import zipfile
import pyzipper
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from services.export_service import ExportService
from services.media_service import MediaService
from data.FileSystemManager import FileSystemManager

class DummyNote:
    def __init__(self, content):
        self.title = "Media note"
        self.content = content
        self.deadline_at = None
        self.reminder_at = None


class MediaServiceTests(unittest.TestCase):
    def test_filesystem_manager_returns_note_scoped_absolute_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.png"
            source.write_bytes(b"image")
            manager = FileSystemManager(app_dir=root / "app")

            stored_path = Path(manager.copy_to_internal_storage(source, note_id="note-01"))

            self.assertTrue(stored_path.is_absolute())
            self.assertTrue(os.path.samefile(stored_path.parent, root / "app" / "media" / "note_note-01"))

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
                media_dir=root / "media"
            )

            attachment = service.import_file(source, note_id="abc123")
            copied_file = service.resolve_path(attachment["path"])

            self.assertEqual(attachment["kind"], "audio")
            self.assertEqual(attachment["name"], "recording.mp3")
            self.assertEqual(copied_file.read_bytes(), b"example audio")
            self.assertNotEqual(copied_file, source)
            self.assertTrue(Path(attachment["path"]).is_absolute())
            self.assertEqual(copied_file.parent.name, "note_abc123")

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
                service.import_file(source, note_id="abc123")

    def test_import_file_requires_note_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "photo.png"
            source.write_bytes(b"image")
            service = MediaService(project_root=temp_dir)

            with self.assertRaises(ValueError):
                service.import_file(source)

    def test_organize_media_copies_legacy_file_into_note_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            legacy = root / "data" / "media" / "legacy.mp4"
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"video")
            service = MediaService(project_root=root)

            content = service.organize_content_media("note-id", {
                "text": "video",
                "media": [{"id": "media-id", "path": "data/media/legacy.mp4"}],
            })

            stored = Path(content["media"][0]["path"])
            self.assertTrue(stored.is_absolute())
            self.assertTrue(
                os.path.samefile(stored.parent, root / "media" / "note_note-id")
            )
            self.assertEqual(stored.read_bytes(), b"video")

    def test_absolute_path_from_another_machine_rebases_to_local_note_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            local = root / "media" / "note_abc" / "image.png"
            local.parent.mkdir(parents=True)
            local.write_bytes(b"portable")

            resolved = MediaService.resolve_stored_path(
                r"C:\old-machine\noteapp-oop\media\note_abc\image.png",
                project_root=root,
            )

            self.assertEqual(resolved, local.resolve())

    def test_missing_foreign_absolute_path_rebases_to_current_media_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            resolved = MediaService.resolve_stored_path(
                r"C:\old-machine\noteapp-oop\media\note_abc\missing.png",
                project_root=root,
            )

            self.assertTrue(resolved.is_absolute())
            self.assertEqual(
                resolved,
                (root / "media" / "note_abc" / "missing.png").resolve(),
            )

    def test_legacy_media_path_is_migrated_with_an_absolute_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "old" / "recording.mp3"
            source.parent.mkdir()
            source.write_bytes(b"audio")
            service = MediaService(project_root=root)

            stored_path = service.organize_legacy_media("legacy-note", source)
            stored = Path(stored_path)

            self.assertTrue(stored.is_absolute())
            self.assertTrue(os.path.samefile(stored.parent, root / "media" / "note_legacy-note"))
            self.assertEqual(stored.read_bytes(), b"audio")

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

            exported_path = ExportService().export_to_markdown(note, output)

            markdown = output.read_text(encoding="utf-8")
            self.assertTrue(Path(exported_path).is_absolute())
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

    def test_media_archive_creates_note_package_without_password(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "clip.mp4"
            source.write_bytes(b"example video bytes")
            output = root / "note-package.zip"
            note = DummyNote({
                "text": "Video",
                "media": [{
                    "name": source.name,
                    "path": str(source),
                    "kind": "video",
                    "position": 5,
                }],
            })

            count = ExportService().export_media_archive(note, output)

            self.assertEqual(count, 1)
            self.assertFalse(ExportService().archive_requires_password(output))
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
                media_name = next(name for name in names if name.endswith("/media/clip.mp4"))
                note_name = next(name for name in names if name.endswith("/note.md"))
                manifest_name = next(name for name in names if name.endswith("/manifest.json"))
                self.assertEqual(archive.read(media_name), source.read_bytes())
                markdown = archive.read(note_name).decode("utf-8")
                self.assertIn("# Media note", markdown)
                self.assertIn("Video[clip.mp4](media/clip.mp4)", markdown)
                manifest = archive.read(manifest_name).decode("utf-8")
                self.assertIn('"note_file": "note.md"', manifest)
                self.assertIn('"path": "media/clip.mp4"', manifest)

            extracted = root / "extracted"
            extracted_count = ExportService().extract_media_archive(
                output,
                extracted,
            )
            self.assertEqual(extracted_count, 3)
            self.assertEqual(
                next(extracted.rglob("clip.mp4")).read_bytes(),
                source.read_bytes(),
            )
            self.assertIn(
                "Video[clip.mp4](media/clip.mp4)",
                next(extracted.rglob("note.md")).read_text(encoding="utf-8"),
            )

    def test_encrypted_media_archive_requires_password_and_extracts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "voice.mp3"
            source.write_bytes(b"example audio bytes")
            output = root / "encrypted-note.zip"
            note = DummyNote({
                "text": "Audio",
                "media": [{
                    "name": source.name,
                    "path": str(source),
                    "kind": "audio",
                    "position": 5,
                }],
            })
            service = ExportService()

            count = service.export_encrypted_media_archive(
                note,
                output,
                "secret-123",
            )

            self.assertEqual(count, 1)
            self.assertTrue(service.archive_requires_password(output))
            with pyzipper.AESZipFile(output) as archive:
                media_name = next(
                    name for name in archive.namelist()
                    if name.endswith("/media/voice.mp3")
                )
                with self.assertRaises(RuntimeError):
                    archive.read(media_name, pwd=b"wrong-password")
                self.assertEqual(
                    archive.read(media_name, pwd=b"secret-123"),
                    source.read_bytes(),
                )

            with self.assertRaises(ValueError):
                service.extract_media_archive(output, root / "missing-password")
            with self.assertRaises(RuntimeError):
                service.extract_media_archive(
                    output,
                    root / "wrong-password",
                    password="wrong-password",
                )

            extracted = root / "extracted-encrypted"
            extracted_count = service.extract_media_archive(
                output,
                extracted,
                password="secret-123",
            )
            self.assertEqual(extracted_count, 3)
            self.assertEqual(
                next(extracted.rglob("voice.mp3")).read_bytes(),
                source.read_bytes(),
            )

    def test_media_archive_rejects_parent_path_during_extraction(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "unsafe.zip"
            with zipfile.ZipFile(
                archive_path,
                "w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:
                archive.writestr("../outside.txt", b"unsafe")

            with self.assertRaises(ValueError):
                ExportService().extract_media_archive(
                    archive_path,
                    root / "destination",
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
