import copy
import unittest

from commands.command import Command, NoteModelAdapter
from commands.command_history import CommandHistory
from commands.note_commands import AddCommand, DeleteCommand, EditCommand
from model.textnote import TextNote


class FakeRepository:
    def __init__(self):
        self.records = {}
        self.deleted = set()
        self.updated = []

    def create_note(self, note):
        note_id = note.get("id") or "generated-id"
        stored = copy.deepcopy(note)
        stored["id"] = note_id
        self.records[note_id] = stored
        self.deleted.discard(note_id)
        return note_id

    def update_note(self, note):
        self.records[note["id"]] = copy.deepcopy(note)
        self.updated.append(copy.deepcopy(note))

    def get_note(self, note_id):
        return copy.deepcopy(self.records.get(note_id))

    def delete_note(self, note_id):
        if note_id in self.records:
            self.deleted.add(note_id)

    def restore_deleted_note(self, note_id):
        self.deleted.discard(note_id)


class CounterCommand(Command):
    def __init__(self, state):
        self.state = state

    def execute(self):
        self.state["value"] += 1

    def undo(self):
        self.state["value"] -= 1


class CommandTests(unittest.TestCase):
    def test_command_history_execute_undo_redo_and_clear_redo(self):
        state = {"value": 0}
        history = CommandHistory()
        first = CounterCommand(state)
        second = CounterCommand(state)

        history.execute_command(first)
        self.assertEqual(state["value"], 1)
        self.assertTrue(history.can_undo())
        self.assertFalse(history.can_redo())

        history.undo()
        self.assertEqual(state["value"], 0)
        self.assertTrue(history.can_redo())
        history.redo()
        self.assertEqual(state["value"], 1)

        history.undo()
        history.pushExecutedCommand(second)
        self.assertEqual(state["value"], 1)
        self.assertFalse(history.can_redo())

    def test_empty_history_is_safe(self):
        history = CommandHistory()
        history.undo()
        history.redo()
        self.assertFalse(history.can_undo())
        self.assertFalse(history.can_redo())

    def test_add_command_syncs_generated_id_and_soft_deletes_on_undo(self):
        repo = FakeRepository()
        note = TextNote("New", "Content")
        note._id = ""
        command = AddCommand(note, repo)

        command.execute()
        self.assertEqual(note.id, "generated-id")
        self.assertIn("generated-id", repo.records)
        command.undo()
        self.assertIn("generated-id", repo.deleted)

    def test_edit_command_updates_and_restores_full_state(self):
        repo = FakeRepository()
        note = TextNote(
            "Old",
            {"text": "Before", "spans": []},
            reminder_at="2026-07-14T09:00:00",
        )
        repo.create_note(note.to_dict())
        original_state = copy.deepcopy(note.__dict__)
        command = EditCommand(
            note,
            repo,
            new_title="New",
            new_content={"text": "After", "spans": []},
            new_extra={"reminder_at": "2026-07-14T10:00:00", "reminder_notified": 0},
        )

        command.execute()
        self.assertEqual(note.title, "New")
        self.assertEqual(note.content["text"], "After")
        self.assertEqual(note.reminder_at, "2026-07-14T10:00:00")
        command.undo()
        self.assertEqual(note.__dict__, original_state)
        self.assertEqual(repo.records[note.id]["title"], "Old")

    def test_delete_command_backup_and_restore(self):
        repo = FakeRepository()
        note = TextNote("Delete", "Content")
        repo.create_note(note.to_dict())
        command = DeleteCommand(note.id, repo)

        command.execute()
        self.assertIn(note.id, repo.deleted)
        command.undo()
        self.assertNotIn(note.id, repo.deleted)

    def test_delete_missing_note_is_safe(self):
        repo = FakeRepository()
        command = DeleteCommand("missing", repo)
        command.execute()
        command.undo()
        self.assertEqual(repo.deleted, set())

    def test_note_model_adapter_snapshot_restore_and_fallback_fields(self):
        class LegacyNote:
            def __init__(self):
                self._id = "legacy"
                self._title = "Old"
                self._content = "Before"

        note = LegacyNote()
        snapshot = NoteModelAdapter.snapshot(note)
        self.assertEqual(NoteModelAdapter.get_id(note), "legacy")
        NoteModelAdapter.set_title(note, "New")
        NoteModelAdapter.set_content(note, "After")
        self.assertEqual((note._title, note._content), ("New", "After"))
        NoteModelAdapter.restore(note, snapshot)
        self.assertEqual((note._title, note._content), ("Old", "Before"))


if __name__ == "__main__":
    unittest.main()
