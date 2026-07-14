import datetime
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from data.DatabaseManager import DatabaseManager
from data.FileSystemManager import FileSystemManager
from model.tag import Tag
from model.textnote import TextNote
from services.reminder_service import ReminderService
from services.search_service import SearchEngine
from services.security_service import SecurityManager
from services.settings_service import SettingsService
from services.theme_service import ThemeManager
from services.translation_service import TranslationService
from ui.calendar_view import CTkCalendarView
from ui.color_picker import CTkColorPicker


class SecurityServiceTests(unittest.TestCase):
    def test_password_hash_verify_and_reuse_salt(self):
        manager = SecurityManager()
        password_hash, salt = manager.hash_password("secret")
        repeated_hash, repeated_salt = manager.hash_password("secret", salt)

        self.assertEqual((password_hash, salt), (repeated_hash, repeated_salt))
        self.assertTrue(manager.verify_password("secret", password_hash, salt))
        self.assertFalse(manager.verify_password("wrong", password_hash, salt))
        self.assertFalse(manager.verify_password("", password_hash, salt))
        with self.assertRaises(ValueError):
            manager.hash_password("")

    def test_encrypt_decrypt_roundtrip(self):
        manager = SecurityManager()
        if manager.cipher is None:
            self.skipTest("cryptography is not installed")
        encrypted = manager.encrypt("Nội dung bí mật")
        self.assertNotEqual(encrypted, "Nội dung bí mật".encode("utf-8"))
        self.assertEqual(manager.decrypt(encrypted), "Nội dung bí mật")


class TranslationAndThemeTests(unittest.TestCase):
    def tearDown(self):
        TranslationService.set_language("en")
        ThemeManager.set_active_theme("blue")

    def test_translation_switch_format_calendar_names_and_fallback(self):
        TranslationService.set_language("vi")
        self.assertEqual(TranslationService.get_language(), "vi")
        self.assertEqual(TranslationService.get("menu.file"), "Tệp")
        self.assertIn("Tháng", TranslationService.month_name(7))
        self.assertEqual(len(TranslationService.weekdays()), 7)
        self.assertIn("Folder", TranslationService.get("msg.create_in_folder_prompt", "Folder"))
        self.assertEqual(TranslationService.get("missing.translation.key"), "missing.translation.key")

        languages = TranslationService.get_available_languages()
        self.assertEqual({item["code"] for item in languages}, {"en", "vi"})

    def test_theme_discovery_switch_and_color_tuple(self):
        themes = ThemeManager.get_available_themes()
        self.assertIn("blue", themes)
        ThemeManager.set_active_theme("blue")
        self.assertIsInstance(ThemeManager.get("text_primary"), tuple)
        self.assertEqual(len(ThemeManager.get("text_primary")), 2)
        self.assertEqual(ThemeManager.get("missing-key", "fallback"), "fallback")

        ThemeManager.set_active_theme("theme-does-not-exist")
        self.assertIsInstance(ThemeManager.get("grid_bg"), tuple)


class SettingsServiceTests(unittest.TestCase):
    def test_defaults_persistence_and_unknown_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db = DatabaseManager(str(Path(temp_dir) / "settings.db"))
            with patch("services.settings_service.DatabaseManager", return_value=db):
                settings = SettingsService()
                self.assertEqual(settings.get_all(), SettingsService.DEFAULTS)
                self.assertEqual(settings.get_setting("unknown", "fallback"), "fallback")
                settings.set_setting("language", "vi")
                settings.set_setting("custom", "value")
                self.assertEqual(settings.get_setting("language"), "vi")
                self.assertEqual(settings.get_setting("custom"), "value")
            db.close()


class SearchServiceTests(unittest.TestCase):
    def setUp(self):
        self.first = TextNote("Project Alpha", "Meeting notes", tags=[Tag("work")])
        self.second = TextNote("Shopping", "Milk and bread", tags=["personal"])
        self.third = TextNote(
            "Rich",
            {"text": "Embedded searchable content", "spans": [], "media": []},
            tags=["work"],
        )
        self.first._created = datetime.datetime(2026, 7, 10)
        self.second._created = datetime.datetime(2026, 7, 15)
        self.third._created = datetime.datetime(2026, 7, 20)
        self.engine = SearchEngine([self.first, self.second, self.third])

    def test_keyword_search_supports_title_plain_and_rich_content(self):
        self.assertEqual(self.engine.search_by_keyword("alpha"), [self.first])
        self.assertEqual(self.engine.search_by_keyword("bread"), [self.second])
        self.assertEqual(self.engine.search_by_keyword("searchable"), [self.third])

    def test_tag_date_and_advanced_filters(self):
        self.assertEqual(self.engine.filter_by_tag("work"), [self.first, self.third])
        self.assertEqual(
            self.engine.filter_by_date(
                datetime.datetime(2026, 7, 11),
                datetime.datetime(2026, 7, 20),
            ),
            [self.second, self.third],
        )
        self.assertEqual(
            self.engine.advanced_search(
                keyword="rich",
                tag="work",
                start_date=datetime.datetime(2026, 7, 1),
                end_date=datetime.datetime(2026, 7, 31),
            ),
            [self.third],
        )


class ReminderServiceTests(unittest.TestCase):
    def make_service(self, repo=None, callback=None):
        thread_patch = patch("services.reminder_service.threading.Thread")
        mocked_thread = thread_patch.start()
        self.addCleanup(thread_patch.stop)
        service = ReminderService(repo=repo, callback=callback, interval=0.01)
        mocked_thread.return_value.start.assert_called_once()
        return service

    def test_memory_queue_notifies_due_item(self):
        service = self.make_service()
        service.notify = MagicMock()
        now = datetime.datetime.now()
        service.add_reminder(now - datetime.timedelta(seconds=1), "Wake up")

        with patch("services.reminder_service.time.time", return_value=now.timestamp()):
            service._check_memory_queue()

        service.notify.assert_called_once_with("Wake up")
        self.assertTrue(service.reminders.empty())

    def test_database_reminders_callbacks_and_marking(self):
        class Repo:
            def __init__(self):
                self.marked_reminders = []
                self.marked_deadlines = []

            def get_due_reminders(self, _now):
                return [{"id": "r1", "title": "Reminder"}]

            def get_due_deadlines(self, _now):
                return [{"id": "d1", "title": "Deadline"}]

            def mark_reminder_notified(self, note_id):
                self.marked_reminders.append(note_id)

            def mark_deadline_notified(self, note_id):
                self.marked_deadlines.append(note_id)

        repo = Repo()
        callbacks = []
        service = self.make_service(
            repo=repo,
            callback=lambda note, is_deadline=False: callbacks.append((note["id"], is_deadline)),
        )

        service._check_database_reminders()

        self.assertEqual(repo.marked_reminders, ["r1"])
        self.assertEqual(repo.marked_deadlines, ["d1"])
        self.assertEqual(callbacks, [("r1", False), ("d1", True)])
        service.thread.is_alive.return_value = True
        service.stop()
        self.assertFalse(service.running)
        self.assertTrue(service._stop_event.is_set())
        service.thread.join.assert_called_once_with(timeout=1)

    def test_legacy_callback_and_console_notification_fallback(self):
        repo = SimpleNamespace(
            get_due_reminders=lambda _now: [{"id": "r1", "title": "Old callback"}],
            get_due_deadlines=lambda _now: [],
            mark_reminder_notified=MagicMock(),
            mark_deadline_notified=MagicMock(),
        )
        received = []
        service = self.make_service(repo=repo, callback=lambda note: received.append(note["id"]))
        service._check_database_reminders()
        self.assertEqual(received, ["r1"])


class FileSystemAndHelperTests(unittest.TestCase):
    def test_file_system_copy_resolve_and_traversal_protection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.txt"
            source.write_text("content", encoding="utf-8")
            app_dir = root / "app"
            with patch.object(FileSystemManager, "_get_app_storage_path", return_value=str(app_dir)):
                manager = FileSystemManager()
            relative = manager.copy_to_internal_storage(str(source), "document")
            absolute = Path(manager.get_absolute_path(relative))
            self.assertTrue(absolute.is_file())
            self.assertEqual(absolute.read_text(encoding="utf-8"), "content")
            with self.assertRaises(ValueError):
                manager.get_absolute_path("../outside.txt")

    def test_color_and_calendar_helpers(self):
        self.assertTrue(CTkColorPicker._is_valid_hex("#aB12fF"))
        self.assertFalse(CTkColorPicker._is_valid_hex("red"))
        calendar_view = object.__new__(CTkCalendarView)
        self.assertEqual(
            CTkCalendarView._date_from_iso(calendar_view, "2026-07-14T12:30:00"),
            datetime.date(2026, 7, 14),
        )
        self.assertIsNone(CTkCalendarView._date_from_iso(calendar_view, "invalid"))


if __name__ == "__main__":
    unittest.main()
