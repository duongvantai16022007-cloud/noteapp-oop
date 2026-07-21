import threading
import time
import datetime
from queue import PriorityQueue
from services.notification_service import DesktopNotificationService
from services.translation_service import TranslationService

class ReminderService:
    """
    Service chạy nền để kiểm tra reminder.

    Vẫn giữ PriorityQueue cũ để tương thích, đồng thời bổ sung chế độ kiểm tra SQLite
    thông qua NoteRepository để reminder không mất sau khi tắt/mở app.
    """

    def __init__(self, repo=None, callback=None, interval=10, notifier=None, autostart=True):
        self.repo = repo
        self.callback = callback
        self.interval = interval
        self.notifier = notifier or DesktopNotificationService()
        self.reminders = PriorityQueue()
        self.running = True
        self._stop_event = threading.Event()

        self.thread = threading.Thread(target=self._run, name="engraver-reminders")
        self.thread.daemon = True
        if autostart:
            self.thread.start()

    def add_reminder(self, remind_time, message):
        self.reminders.put((remind_time.timestamp(), message))

    def _run(self):
        while self.running:
            try:
                self._check_memory_queue()
                self._check_database_reminders()
            except Exception as exc:
                print(f"ReminderService error: {exc}")
            self._stop_event.wait(self.interval)

    def _check_memory_queue(self):
        if not self.reminders.empty():
            remind_time, message = self.reminders.queue[0]
            current_time = time.time()

            if current_time >= remind_time:
                self.reminders.get()
                self.notify(message)

    def _check_database_reminders(self):
        if not self.repo:
            return

        now_iso = datetime.datetime.now().replace(microsecond=0).isoformat()
        
        # Check reminders
        due_notes = self.repo.get_due_reminders(now_iso)
        for note in due_notes:
            self.repo.mark_reminder_notified(note["id"])
            self._dispatch_note(note, is_deadline=False)

        # Check deadlines
        due_deadlines = self.repo.get_due_deadlines(now_iso)
        for note in due_deadlines:
            self.repo.mark_deadline_notified(note["id"])
            self._dispatch_note(note, is_deadline=True)

    def _dispatch_note(self, note, is_deadline=False):
        note_title = note.get("title") or TranslationService.get("sidebar.no_title")
        title_key = "deadline.title" if is_deadline else "reminder.title"
        text_key = "deadline.text" if is_deadline else "reminder.text"
        self.notify(
            TranslationService.get(text_key, title=note_title),
            title=TranslationService.get(title_key),
        )
        if self.callback:
            try:
                self.callback(note, is_deadline=is_deadline)
            except TypeError:
                self.callback(note)

    def notify(self, message, title="Engraver"):
        if not self.notifier.notify(title=title, message=message):
            print(f"🔔 {title}: {message}")

    def stop(self):
        self.running = False
        self._stop_event.set()
        if self.thread.is_alive() and threading.current_thread() is not self.thread:
            self.thread.join(timeout=max(1, min(self.interval + 1, 5)))
