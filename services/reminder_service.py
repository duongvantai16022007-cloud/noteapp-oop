import threading
import time
import datetime
from queue import PriorityQueue

class ReminderService:
    """
    Service chạy nền để kiểm tra reminder.

    Vẫn giữ PriorityQueue cũ để tương thích, đồng thời bổ sung chế độ kiểm tra SQLite
    thông qua NoteRepository để reminder không mất sau khi tắt/mở app.
    """

    def __init__(self, repo=None, callback=None, interval=10):
        self.repo = repo
        self.callback = callback
        self.interval = interval
        self.reminders = PriorityQueue()
        self.running = True

        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
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
            time.sleep(self.interval)

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
            if self.callback:
                try:
                    self.callback(note, is_deadline=False)
                except TypeError:
                    self.callback(note)
            else:
                self.notify(f"{note.get('title', 'Ghi chú')} đã đến giờ nhắc!")

        # Check deadlines
        due_deadlines = self.repo.get_due_deadlines(now_iso)
        for note in due_deadlines:
            self.repo.mark_deadline_notified(note["id"])
            if self.callback:
                try:
                    self.callback(note, is_deadline=True)
                except TypeError:
                    self.callback(note)
            else:
                self.notify(f"{note.get('title', 'Ghi chú')} đã đến deadline!")

    def notify(self, message):
        print(f"🔔 Reminder: {message}")

    def stop(self):
        self.running = False
