import datetime
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data.DatabaseManager import DatabaseManager
from data.NoteRepository import NoteRepository
from model.note_factory import NoteFactory


class TemporaryRepositoryTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "notes.db")
        self.db = DatabaseManager(self.db_path)
        self.db_patch = patch("data.NoteRepository.DatabaseManager", return_value=self.db)
        self.db_patch.start()
        self.repo = NoteRepository()

    def tearDown(self):
        self.db_patch.stop()
        self.db.close()
        self.temp_dir.cleanup()

    @staticmethod
    def note_data(note_id="note-1", **overrides):
        data = {
            "id": note_id,
            "type": "Text",
            "title": "Note",
            "content": {"text": "Hello", "spans": [], "media": []},
            "tags": ["work"],
            "folder_id": None,
            "is_locked": False,
            "reminder_at": None,
            "deadline_at": None,
            "reminder_notified": 0,
            "deadline_notified": 0,
        }
        data.update(overrides)
        return data


class DatabaseManagerTests(unittest.TestCase):
    def test_singleton_per_path_and_reopens_after_close(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = str(Path(temp_dir) / "db.sqlite")
            first = DatabaseManager(path)
            second = DatabaseManager(path)
            self.assertIs(first, second)
            first.close()
            third = DatabaseManager(path)
            self.assertIsNot(first, third)
            third.close()

    def test_migrates_legacy_notes_table(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = str(Path(temp_dir) / "legacy.sqlite")
            connection = sqlite3.connect(path)
            connection.execute(
                """
                CREATE TABLE notes (
                    id TEXT PRIMARY KEY, type TEXT NOT NULL, title TEXT,
                    content TEXT, media_path TEXT, tags TEXT,
                    created_at TEXT, updated_at TEXT
                )
                """
            )
            connection.commit()
            connection.close()

            db = DatabaseManager(path)
            columns = {row["name"] for row in db.fetch_all("PRAGMA table_info(notes)")}
            self.assertTrue({
                "folder_id", "deleted_at", "is_locked", "password_hash",
                "password_salt", "reminder_at", "deadline_at",
                "reminder_notified", "deadline_notified"
            }.issubset(columns))
            self.assertIsNotNone(db.fetch_one(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='folders'"
            ))
            db.close()


class NoteRepositoryTests(TemporaryRepositoryTestCase):
    def test_create_get_update_and_factory_roundtrip(self):
        source = self.note_data()
        created_id = self.repo.create_note(source)
        stored = self.repo.get_note(created_id)

        self.assertEqual(created_id, "note-1")
        self.assertEqual(json.loads(stored["content"])["text"], "Hello")
        self.assertEqual(stored["tags"], ["work"])
        self.assertFalse(stored["is_locked"])

        model = NoteFactory.from_dict(stored)
        self.assertEqual(model.content["text"], "Hello")
        updated = model.to_dict()
        updated["title"] = "Updated"
        updated["content"] = {"text": "Changed", "spans": [], "media": []}
        updated["tags"] = ["personal"]
        self.repo.update_note(updated)

        stored = self.repo.get_note(created_id)
        self.assertEqual(stored["title"], "Updated")
        self.assertEqual(json.loads(stored["content"])["text"], "Changed")
        self.assertEqual(stored["tags"], ["personal"])

    def test_generates_id_without_mutating_input(self):
        source = self.note_data(note_id="")
        snapshot = dict(source)
        note_id = self.repo.create_note(source)
        self.assertTrue(note_id)
        self.assertEqual(source, snapshot)

    def test_folder_create_move_query_and_delete(self):
        folder_b = self.repo.create_folder("Beta")
        folder_a = self.repo.create_folder("Alpha")
        self.repo.create_note(self.note_data("root-note"))
        self.repo.create_note(self.note_data("folder-note", folder_id=folder_a))

        self.assertEqual([row["name"] for row in self.repo.get_all_folders()], ["Alpha", "Beta"])
        self.assertEqual([note["id"] for note in self.repo.get_notes_by_folder(None)], ["root-note"])
        self.assertEqual([note["id"] for note in self.repo.get_notes_by_folder(folder_a)], ["folder-note"])

        self.repo.move_note_to_folder("root-note", folder_b)
        self.assertEqual(self.repo.get_note("root-note")["folder_id"], folder_b)
        self.repo.delete_folder(folder_b)
        self.assertIsNone(self.repo.get_note("root-note")["folder_id"])
        self.assertEqual([row["id"] for row in self.repo.get_all_folders()], [folder_a])

    def test_soft_delete_restore_permanent_delete_and_limit(self):
        for index in range(3):
            self.repo.create_note(self.note_data(f"note-{index}"))
            self.repo.delete_note(f"note-{index}")

        self.assertEqual(self.repo.get_all_notes(), [])
        self.assertEqual(len(self.repo.get_deleted_notes(limit=2)), 2)

        self.repo.restore_deleted_note("note-0")
        self.assertEqual([note["id"] for note in self.repo.get_all_notes()], ["note-0"])
        self.repo.permanently_delete_note("note-1")
        self.assertIsNone(self.repo.get_note("note-1"))

    def test_purge_expired_deleted_notes(self):
        self.repo.create_note(self.note_data("old"))
        self.repo.create_note(self.note_data("recent"))
        old = (datetime.datetime.now() - datetime.timedelta(days=40)).isoformat()
        recent = (datetime.datetime.now() - datetime.timedelta(days=2)).isoformat()
        self.db.execute_query("UPDATE notes SET deleted_at = ? WHERE id = ?", (old, "old"))
        self.db.execute_query("UPDATE notes SET deleted_at = ? WHERE id = ?", (recent, "recent"))

        self.repo.purge_expired_deleted_notes(days=30)

        self.assertIsNone(self.repo.get_note("old"))
        self.assertIsNotNone(self.repo.get_note("recent"))

    def test_security_update(self):
        self.repo.create_note(self.note_data())
        self.repo.update_note_security("note-1", True, "hash", "salt")
        stored = self.repo.get_note("note-1")
        self.assertTrue(stored["is_locked"])
        self.assertEqual(stored["password_hash"], "hash")
        self.assertEqual(stored["password_salt"], "salt")

    def test_reminder_deadline_and_timed_queries(self):
        now = datetime.datetime.now().replace(microsecond=0)
        past = (now - datetime.timedelta(minutes=5)).isoformat()
        future = (now + datetime.timedelta(minutes=5)).isoformat()
        self.repo.create_note(self.note_data("reminder", reminder_at=past))
        self.repo.create_note(self.note_data("deadline", deadline_at=past))
        self.repo.create_note(self.note_data("future", reminder_at=future))
        self.repo.create_note(self.note_data("deleted", reminder_at=past))
        self.repo.delete_note("deleted")

        self.assertEqual([n["id"] for n in self.repo.get_due_reminders(now.isoformat())], ["reminder"])
        self.assertEqual([n["id"] for n in self.repo.get_due_deadlines(now.isoformat())], ["deadline"])
        self.assertEqual(
            {n["id"] for n in self.repo.get_timed_notes()},
            {"reminder", "deadline", "future"}
        )

        self.repo.mark_reminder_notified("reminder")
        self.repo.mark_deadline_notified("deadline")
        self.assertEqual(self.repo.get_due_reminders(now.isoformat()), [])
        self.assertEqual(self.repo.get_due_deadlines(now.isoformat()), [])


if __name__ == "__main__":
    unittest.main()
