import tempfile
import unittest
from pathlib import Path

from PIL import Image

from services.export_service import ExportService
from services.media_service import MediaService


class DummyNote:
    def __init__(self, content):
        self.title = "Media note"
        self.content = content
        self.deadline_at = None
        self.reminder_at = None


class MediaServiceTests(unittest.TestCase):
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
