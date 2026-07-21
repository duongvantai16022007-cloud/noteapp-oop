import unittest
from types import SimpleNamespace
from unittest.mock import patch

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

    def test_export_note_zip_does_not_prompt_for_password(self):
        calls = []

        class _FakeExportService:
            def export_media_archive(self, note, path):
                calls.append((note, path))
                return 2

        note = object()
        window = SimpleNamespace(
            current_note=note,
            export_service=_FakeExportService(),
            _current_editor_note_for_export=lambda: note,
        )

        with patch(
            "ui.main_window.filedialog.asksaveasfilename",
            return_value="note-package.zip",
        ), patch(
            "ui.main_window.simpledialog.askstring",
            side_effect=AssertionError("ZIP export must not request a password"),
        ), patch("ui.main_window.messagebox.showinfo"):
            MainWindow.export_media_zip(window)

        self.assertEqual(calls, [(note, "note-package.zip")])

    def test_export_encrypted_note_zip_confirms_and_passes_password(self):
        calls = []

        class _FakeExportService:
            def export_encrypted_media_archive(self, note, path, password):
                calls.append((note, path, password))
                return 2

        note = object()
        window = SimpleNamespace(
            current_note=note,
            export_service=_FakeExportService(),
            _current_editor_note_for_export=lambda: note,
        )

        with patch(
            "ui.main_window.simpledialog.askstring",
            side_effect=["secret-123", "secret-123"],
        ) as ask_password, patch(
            "ui.main_window.filedialog.asksaveasfilename",
            return_value="encrypted-note.zip",
        ), patch("ui.main_window.messagebox.showinfo"):
            MainWindow.export_media_zip_with_password(window)

        self.assertEqual(ask_password.call_count, 2)
        self.assertEqual(
            calls,
            [(note, "encrypted-note.zip", "secret-123")],
        )

    def test_open_plain_note_zip_does_not_prompt_for_password(self):
        calls = []

        class _FakeExportService:
            def archive_requires_password(self, path):
                return False

            def extract_media_archive(self, path, destination, password=None):
                calls.append((path, destination, password))
                return 3

        window = SimpleNamespace(export_service=_FakeExportService())

        with patch(
            "ui.main_window.filedialog.askopenfilename",
            return_value="plain.zip",
        ), patch(
            "ui.main_window.filedialog.askdirectory",
            return_value="extracted",
        ), patch(
            "ui.main_window.simpledialog.askstring",
            side_effect=AssertionError("Plain ZIP must not request a password"),
        ), patch("ui.main_window.messagebox.showinfo"):
            MainWindow.open_media_zip(window)

        self.assertEqual(calls, [("plain.zip", "extracted", None)])

    def test_open_encrypted_note_zip_prompts_for_password(self):
        calls = []

        class _FakeExportService:
            def archive_requires_password(self, path):
                return True

            def extract_media_archive(self, path, destination, password=None):
                calls.append((path, destination, password))
                return 3

        window = SimpleNamespace(export_service=_FakeExportService())

        with patch(
            "ui.main_window.filedialog.askopenfilename",
            return_value="encrypted.zip",
        ), patch(
            "ui.main_window.filedialog.askdirectory",
            return_value="extracted",
        ), patch(
            "ui.main_window.simpledialog.askstring",
            return_value="secret-123",
        ) as ask_password, patch("ui.main_window.messagebox.showinfo"):
            MainWindow.open_media_zip(window)

        ask_password.assert_called_once()
        self.assertEqual(
            calls,
            [("encrypted.zip", "extracted", "secret-123")],
        )


if __name__ == "__main__":
    unittest.main()
