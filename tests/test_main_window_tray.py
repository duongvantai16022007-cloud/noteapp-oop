import unittest

from ui.main_window import MainWindow


class _FakeTrayIcon:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


class _FakeReminderService:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


class _FakeWindow:
    def __init__(self):
        self.tray_icon = None
        self.reminder_service = _FakeReminderService()
        self.calls = []

    def after(self, delay, callback):
        self.calls.append(("after", delay))
        callback()

    def deiconify(self):
        self.calls.append("deiconify")

    def state(self, value):
        self.calls.append(("state", value))

    def lift(self):
        self.calls.append("lift")

    def focus_force(self):
        self.calls.append("focus_force")

    def quit(self):
        self.calls.append("quit")

    def destroy(self):
        self.calls.append("destroy")


class MainWindowTrayTests(unittest.TestCase):
    def test_show_window_from_tray_stops_icon_and_restores_window(self):
        window = _FakeWindow()
        icon = _FakeTrayIcon()

        MainWindow.show_window_from_tray(window, icon, object())

        self.assertTrue(icon.stopped)
        self.assertIsNone(window.tray_icon)
        self.assertIn("deiconify", window.calls)
        self.assertIn(("state", "normal"), window.calls)
        self.assertIn("focus_force", window.calls)

    def test_quit_app_completely_stops_services_and_destroys_window(self):
        window = _FakeWindow()
        icon = _FakeTrayIcon()

        MainWindow.quit_app_completely(window, icon, object())

        self.assertTrue(icon.stopped)
        self.assertTrue(window.reminder_service.stopped)
        self.assertIn("quit", window.calls)
        self.assertIn("destroy", window.calls)


if __name__ == "__main__":
    unittest.main()
