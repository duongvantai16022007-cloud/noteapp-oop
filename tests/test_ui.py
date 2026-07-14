import datetime
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

import customtkinter as ctk
import tkinter as tk

from ui.calendar_view import CTkCalendarView
from ui.date_picker import CTkDatePicker
from ui.editor import EditorFrame
from ui.main_window import MainWindow
from ui.sidebar import SidebarFrame


class TkTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = ctk.CTk()
            cls.root.withdraw()
        except tk.TclError as exc:
            raise unittest.SkipTest(f"Tk display is unavailable: {exc}")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "root", None) is not None:
            try:
                for callback_id in cls.root.tk.call("after", "info"):
                    cls.root.after_cancel(callback_id)
            except (tk.TclError, TypeError):
                pass
            cls.root.destroy()


class EditorFrameTests(TkTestCase):
    def setUp(self):
        self.editor = EditorFrame(self.root)
        self.editor.pack(fill="both", expand=True)
        self.root.update_idletasks()

    def tearDown(self):
        self.editor.destroy()
        self.root.update_idletasks()

    def test_rich_text_media_position_search_and_reload(self):
        payload = {
            "text": "AB searchable",
            "spans": [
                {"start": 0, "end": 1, "style": {}},
                {"start": 1, "end": 2, "style": {"bold": True}},
            ],
            "media": [{
                "id": "audio-1",
                "name": "clip.mp3",
                "path": "data/media/missing.mp3",
                "kind": "audio",
                "size": 12,
                "position": 1,
            }],
        }
        self.editor.set_data(
            "Demo", payload, "Text",
            reminder_at="2026-07-14T09:00:00",
            deadline_at="2026-07-15T10:00:00",
        )
        self.root.update_idletasks()
        widget = self.editor._text_widget()
        self.assertEqual(widget.index(str(self.editor._media_widgets["audio-1"])), "1.1")

        widget.insert("1.0", "X")
        self.editor.content_search_entry.insert(0, "searchable")
        self.editor.search_current_note()
        self.assertEqual(len(self.editor._content_search_matches), 1)

        saved = self.editor.get_data()
        self.assertEqual(saved["content"]["text"], "XAB searchable")
        self.assertEqual(saved["content"]["media"][0]["position"], 2)
        self.assertEqual(saved["reminder_at"], "2026-07-14 09:00")
        self.assertEqual(saved["deadline_at"], "2026-07-15 10:00")

        self.editor.set_data("Demo", saved["content"], "Text")
        self.root.update_idletasks()
        self.assertIn("audio-1", self.editor._media_widgets)

    def test_text_formatting_undo_redo_and_zoom(self):
        self.editor.set_data("Format", "hello", "Text")
        widget = self.editor._text_widget()
        widget.tag_add("sel", "1.0", "1.5")
        self.editor.apply_text_style("bold")
        serialized = self.editor._serialize_content()
        self.assertTrue(any(span["style"].get("bold") for span in serialized["spans"]))

        widget.insert("end-1c", "!")
        self.editor.undo_text()
        self.assertEqual(widget.get("1.0", "end-1c"), "hello")
        self.editor.redo_text()
        self.assertEqual(widget.get("1.0", "end-1c"), "hello!")

        self.editor.document_zoom_slider.set(125)
        self.editor.on_zoom_release(None)
        self.assertAlmostEqual(self.editor.zoom_factor, 1.25)

    def test_checklist_roundtrip_add_and_clear(self):
        self.editor.set_data(
            "Tasks",
            [
                {"content": "Done", "is_done": True},
                {"content": "Todo", "is_done": False},
            ],
            "Checklist",
        )
        self.assertEqual(len(self.editor.checklist_vars), 2)
        self.editor.add_checklist_item("Third", True)
        data = self.editor.get_data()
        self.assertEqual(len(data["content"]), 3)
        self.assertEqual(data["content"][0], {"content": "Done", "is_done": True})
        self.assertEqual(data["content"][2], {"content": "Third", "is_done": True})
        self.assertEqual(self.editor.btn_media.cget("state"), "disabled")
        self.editor.clear_checklist_items()
        self.assertEqual(self.editor.checklist_vars, [])

    def test_editor_datetime_and_file_size_helpers(self):
        self.assertEqual(
            self.editor._format_datetime_for_entry("2026-07-14T09:30:00"),
            "2026-07-14 09:30",
        )
        self.assertEqual(
            self.editor._parse_datetime_value("2026-07-14 09:30"),
            datetime.datetime(2026, 7, 14, 9, 30),
        )
        self.assertIsNone(self.editor._parse_datetime_value("invalid"))
        self.assertEqual(self.editor._format_file_size(1024), "1.0 KB")
        self.assertEqual(self.editor._format_file_size(2 * 1024 * 1024), "2.0 MB")


class SidebarFrameTests(TkTestCase):
    def test_sidebar_renders_tree_flat_and_deleted_lists(self):
        selected = []
        sidebar = SidebarFrame(
            self.root,
            on_note_select=selected.append,
            on_restore_deleted=MagicMock(),
            on_permanently_delete=MagicMock(),
            on_search=MagicMock(),
            initial_settings={},
        )
        sidebar.pack()
        folder = {"id": "folder-1", "name": "Work"}
        root_note = {"id": "root", "type": "Text", "title": "Root"}
        folder_note = {
            "id": "inside", "type": "Checklist", "title": "Inside",
            "is_locked": True, "reminder_at": "2026-07-14T09:00:00",
            "deadline_at": "2026-07-15T09:00:00",
        }

        sidebar.update_tree_list([folder], {"folder-1": [folder_note], "root": [root_note]})
        self.root.update_idletasks()
        self.assertGreaterEqual(len(sidebar.scroll_list.winfo_children()), 2)

        sidebar.update_list([root_note])
        self.assertEqual(len(sidebar.scroll_list.winfo_children()), 1)
        sidebar.update_deleted_list([])
        self.assertEqual(len(sidebar.deleted_scroll_list.winfo_children()), 1)
        sidebar.update_deleted_list([{**root_note, "deleted_at": "2026-07-14T10:00:00"}])
        self.assertEqual(len(sidebar.deleted_scroll_list.winfo_children()), 1)
        sidebar.destroy()


class UiHelperTests(unittest.TestCase):
    def test_main_window_datetime_content_and_export_snapshot_helpers(self):
        class Harness:
            _parse_datetime_input = MainWindow._parse_datetime_input
            _format_datetime_display = MainWindow._format_datetime_display
            _content_to_plain_text = MainWindow._content_to_plain_text
            _note_extra_from_form = MainWindow._note_extra_from_form
            _current_editor_note_for_export = MainWindow._current_editor_note_for_export

        harness = Harness()
        harness.current_note = SimpleNamespace(
            title="Saved",
            content="Old",
            reminder_at="2026-07-14T08:00:00",
            deadline_at=None,
            reminder_notified=1,
        )
        harness.editor = SimpleNamespace(get_data=lambda: {
            "title": "Draft",
            "content": {"text": "Current", "spans": [], "media": []},
            "reminder_at": "2026-07-14 09:00",
            "deadline_at": "",
        })

        self.assertEqual(
            harness._parse_datetime_input("2026-07-14 09:30"),
            "2026-07-14T09:30:00",
        )
        with self.assertRaises(ValueError):
            harness._parse_datetime_input("tomorrow")
        self.assertEqual(harness._format_datetime_display("2026-07-14T09:30:00"), "2026-07-14 09:30")
        self.assertEqual(
            harness._content_to_plain_text({"text": "Rich", "spans": []}),
            "Rich",
        )
        self.assertEqual(
            harness._content_to_plain_text([{"content": "One"}, {"content": "Two"}]),
            "One Two",
        )

        extra = harness._note_extra_from_form({
            "reminder_at": "2026-07-14 09:00",
            "deadline_at": "",
        })
        self.assertEqual(extra["reminder_at"], "2026-07-14T09:00:00")
        self.assertEqual(extra["reminder_notified"], 0)
        snapshot = harness._current_editor_note_for_export()
        self.assertEqual(snapshot.title, "Draft")
        self.assertEqual(snapshot.content["text"], "Current")

    def test_calendar_and_date_picker_month_rollover(self):
        calendar_view = SimpleNamespace(
            calendar_month=datetime.date(2026, 12, 1),
            _draw_calendar=MagicMock(),
        )
        CTkCalendarView._change_calendar_month(calendar_view, 1)
        self.assertEqual(calendar_view.calendar_month, datetime.date(2027, 1, 1))
        calendar_view._draw_calendar.assert_called_once()

        picker = SimpleNamespace(
            current_month=datetime.date(2026, 1, 1),
            _draw_calendar=MagicMock(),
        )
        CTkDatePicker._change_month(picker, -1)
        self.assertEqual(picker.current_month, datetime.date(2025, 12, 1))
        picker._draw_calendar.assert_called_once()


if __name__ == "__main__":
    unittest.main()
