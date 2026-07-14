import json
import unittest
from datetime import datetime

from model.checklist_note import ChecklistNote
from model.folder import Folder
from model.media_note import MediaNote
from model.note_factory import NoteFactory
from model.tag import Tag
from model.textnote import TextNote
from model.todo_item import TodoItem


class ModelTests(unittest.TestCase):
    def test_text_note_metadata_tags_and_validation(self):
        note = TextNote(
            title="Daily",
            content={"text": "Hello", "spans": []},
            tags=["work"],
            reminder_at="2026-07-14T09:00:00",
            deadline_at="2026-07-15T09:00:00",
        )

        note.add_tag("work")
        note.add_tag("urgent")
        note.folder_id = "folder-1"
        note.update_content({"text": "Updated", "spans": []})
        note.set_lock_info(True, "hash", "salt")

        data = note.to_dict()
        self.assertEqual(note.get_type(), "Text")
        self.assertEqual(note.tags, ["work", "urgent"])
        self.assertEqual(note.folder_id, "folder-1")
        self.assertEqual(note.content["text"], "Updated")
        self.assertTrue(note.is_locked)
        self.assertEqual(data["password_hash"], "hash")
        self.assertEqual(data["deadline_at"], "2026-07-15T09:00:00")

        with self.assertRaises(ValueError):
            note.title = "   "
        with self.assertRaises(ValueError):
            note.title = "x" * 21

    def test_todo_and_checklist_progress(self):
        first = TodoItem("First")
        first.toggle_status()
        note = ChecklistNote(
            "Tasks",
            content=[first, {"content": "Second", "is_done": False}],
        )
        note.add_todo("Third")

        self.assertTrue(first.is_done)
        self.assertAlmostEqual(note.calculate_progress(), 100 / 3)
        self.assertEqual(note.to_dict()["content"][0], {"content": "First", "is_done": True})
        self.assertEqual(ChecklistNote("Empty").calculate_progress(), 0.0)

    def test_media_note_serialization(self):
        note = MediaNote(
            "Photo",
            content={"text": "Caption", "media": []},
            file_path="media/photo.png",
            tags=["image"],
        )

        data = note.to_dict()
        self.assertEqual(note.get_type(), "Media")
        self.assertEqual(note.file_path, "media/photo.png")
        self.assertEqual(data["media_path"], "media/photo.png")

    def test_note_factory_parses_json_and_preserves_common_fields(self):
        created_at = "2026-07-14T08:00:00"
        updated_at = "2026-07-14T09:00:00"
        note = NoteFactory.from_dict({
            "id": "note-1",
            "type": "Text",
            "title": "Factory",
            "content": json.dumps({"text": "Rich", "spans": []}),
            "tags": json.dumps(["one", "two"]),
            "folder_id": "folder-1",
            "created_at": created_at,
            "updated_at": updated_at,
            "is_locked": 1,
            "password_hash": "hash",
            "password_salt": "salt",
            "reminder_notified": 1,
        })

        self.assertIsInstance(note, TextNote)
        self.assertEqual(note.id, "note-1")
        self.assertEqual(note.content["text"], "Rich")
        self.assertEqual(note.tags, ["one", "two"])
        self.assertEqual(note.folder_id, "folder-1")
        self.assertEqual(note.created_at, datetime.fromisoformat(created_at))
        self.assertEqual(note.updated_at, datetime.fromisoformat(updated_at))
        self.assertTrue(note.is_locked)
        self.assertEqual(note.reminder_notified, 1)

    def test_note_factory_builds_checklist_and_media_in_folder(self):
        checklist = NoteFactory.from_dict({
            "id": "check-1",
            "type": "Checklist",
            "title": "List",
            "content": '[{"content": "Done", "is_done": true}]',
            "folder_id": "folder-2",
        })
        media = NoteFactory.from_dict({
            "id": "media-1",
            "type": "Media",
            "title": "Image",
            "content": "Caption",
            "media_path": "media/image.png",
            "folder_id": "folder-2",
        })

        self.assertIsInstance(checklist, ChecklistNote)
        self.assertTrue(checklist.content[0].is_done)
        self.assertEqual(checklist.folder_id, "folder-2")
        self.assertIsInstance(media, MediaNote)
        self.assertEqual(media.file_path, "media/image.png")
        self.assertEqual(media.folder_id, "folder-2")

    def test_factory_keeps_invalid_json_as_plain_text(self):
        note = NoteFactory.from_dict({
            "type": "Text",
            "title": "Plain",
            "content": "{not-json",
            "tags": "[not-json",
        })
        self.assertEqual(note.content, "{not-json")
        self.assertEqual(note.tags, "[not-json")

    def test_folder_composite_and_name_validation(self):
        root = Folder("Root")
        child = Folder("Child")
        first = TextNote("One", "A")
        second = TextNote("Two", "B")

        root.add_item(first)
        root.add_item(first)
        child.add_item(second)
        root.add_item(child)
        self.assertEqual(root.get_all_notes(), [first, second])

        root.remove_item(first)
        self.assertEqual(root.get_all_notes(), [second])
        with self.assertRaises(ValueError):
            root.name = ""

    def test_tag_exposes_name_and_color(self):
        tag = Tag("urgent", "#ff0000")
        self.assertEqual(tag.name, "urgent")
        self.assertEqual(tag.color, "#ff0000")


if __name__ == "__main__":
    unittest.main()
