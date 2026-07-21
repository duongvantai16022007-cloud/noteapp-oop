import sqlite3
import tempfile
import unittest
import datetime
from pathlib import Path

from data.DatabaseManager import DatabaseManager, _default_db_path
from data.NoteRepository import NoteRepository


class FolderRepositoryTests(unittest.TestCase):
    def _repository(self, root):
        database = DatabaseManager(str(Path(root) / "notes.db"))
        self.addCleanup(database.close)
        return NoteRepository(database)

    def test_database_migrates_parent_id_for_legacy_folder_table(self):
        temp_dir = self.enterContext(tempfile.TemporaryDirectory())
        db_path = Path(temp_dir) / "notes.db"
        connection = sqlite3.connect(db_path)
        connection.execute(
            "CREATE TABLE folders (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        connection.commit()
        connection.close()

        repository = self._repository(temp_dir)
        columns = repository.db.fetch_all("PRAGMA table_info(folders)")

        self.assertIn("parent_id", {row["name"] for row in columns})

    def test_default_database_path_is_absolute(self):
        self.assertTrue(Path(_default_db_path()).is_absolute())

    def test_create_nested_folders_and_reject_cycle(self):
        temp_dir = self.enterContext(tempfile.TemporaryDirectory())
        repository = self._repository(temp_dir)
        root_id = repository.create_folder("Root")
        child_id = repository.create_folder("Child", parent_id=root_id)
        grandchild_id = repository.create_folder("Grandchild", parent_id=child_id)

        self.assertEqual(repository.get_folder(child_id)["parent_id"], root_id)
        self.assertEqual(
            set(repository.get_descendant_folder_ids(root_id)),
            {child_id, grandchild_id},
        )
        with self.assertRaises(ValueError):
            repository.move_folder(root_id, grandchild_id)

    def test_delete_folder_promotes_children_and_moves_notes_to_root(self):
        temp_dir = self.enterContext(tempfile.TemporaryDirectory())
        repository = self._repository(temp_dir)
        parent_id = repository.create_folder("Parent")
        target_id = repository.create_folder("Target", parent_id=parent_id)
        child_id = repository.create_folder("Child", parent_id=target_id)
        repository.db.execute_query(
            "INSERT INTO notes (id, type, title, folder_id) VALUES (?, ?, ?, ?)",
            ("note-1", "Text", "Note", target_id),
        )

        repository.delete_folder(target_id)

        self.assertIsNone(repository.get_folder(target_id))
        self.assertEqual(repository.get_folder(child_id)["parent_id"], parent_id)
        self.assertIsNone(repository.get_note("note-1")["folder_id"])

    def test_purge_returns_expired_note_ids_for_media_cleanup(self):
        temp_dir = self.enterContext(tempfile.TemporaryDirectory())
        repository = self._repository(temp_dir)
        expired = (datetime.datetime.now() - datetime.timedelta(days=31)).isoformat()
        repository.db.execute_query(
            "INSERT INTO notes (id, type, title, deleted_at) VALUES (?, ?, ?, ?)",
            ("expired-note", "Text", "Old", expired),
        )

        purged_ids = repository.purge_expired_deleted_notes(days=30)

        self.assertEqual(purged_ids, ["expired-note"])
        self.assertIsNone(repository.get_note("expired-note"))
