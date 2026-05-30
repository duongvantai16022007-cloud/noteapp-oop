import threading
import time
from queue import PriorityQueue

class ReminderService:
    def __init__(self):
        self.reminders = PriorityQueue()
        self.running = True

        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True  
        self.thread.start()

    def add_reminder(self, remind_time, message):
        self.reminders.put((remind_time.timestamp(), message))

    def _run(self):
        while self.running:
            if not self.reminders.empty():
                remind_time, message = self.reminders.queue[0]
                current_time = time.time()

                if current_time >= remind_time:
                    self.reminders.get()  
                    self.notify(message)

            time.sleep(1)  

    def notify(self, message):
        print(f"🔔 Reminder: {message}")

    def stop(self):
        self.running = False