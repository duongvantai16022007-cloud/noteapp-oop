import unittest

from services.reminder_service import ReminderService


class _FakeNotifier:
    def __init__(self):
        self.calls = []

    def notify(self, **kwargs):
        self.calls.append(kwargs)
        return True


class _FakeRepository:
    def __init__(self):
        self.reminder_marks = []
        self.deadline_marks = []

    def get_due_reminders(self, current_iso):
        return [{"id": "r1", "title": "Reminder note"}]

    def get_due_deadlines(self, current_iso):
        return [{"id": "d1", "title": "Deadline note"}]

    def mark_reminder_notified(self, note_id):
        self.reminder_marks.append(note_id)

    def mark_deadline_notified(self, note_id):
        self.deadline_marks.append(note_id)


class ReminderServiceTests(unittest.TestCase):
    def test_due_items_emit_desktop_notifications_and_callbacks(self):
        repository = _FakeRepository()
        notifier = _FakeNotifier()
        callbacks = []
        service = ReminderService(
            repo=repository,
            callback=lambda note, is_deadline=False: callbacks.append((note["id"], is_deadline)),
            notifier=notifier,
            autostart=False,
        )

        service._check_database_reminders()

        self.assertEqual(repository.reminder_marks, ["r1"])
        self.assertEqual(repository.deadline_marks, ["d1"])
        self.assertEqual(len(notifier.calls), 2)
        self.assertEqual(callbacks, [("r1", False), ("d1", True)])

    def test_stop_wakes_background_thread(self):
        service = ReminderService(repo=None, notifier=_FakeNotifier(), interval=30)
        service.stop()

        self.assertFalse(service.running)
        self.assertFalse(service.thread.is_alive())
