import unittest

from model.note_factory import NoteFactory


class NoteFactoryTests(unittest.TestCase):
    def test_checklist_preserves_folder_and_notification_state(self):
        note = NoteFactory.from_dict({
            "id": "check-1",
            "type": "Checklist",
            "title": "Tasks",
            "content": [{"content": "Done", "is_done": True}],
            "folder_id": "child-folder",
            "reminder_notified": 1,
            "deadline_notified": 1,
        })

        self.assertEqual(note.folder_id, "child-folder")
        self.assertEqual(note.reminder_notified, 1)
        self.assertEqual(note.deadline_notified, 1)
        self.assertTrue(note.content[0].is_done)


if __name__ == "__main__":
    unittest.main()
