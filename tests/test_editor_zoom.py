import unittest

from ui.editor import EditorFrame


class _FakeTextWidget:
    def __init__(self):
        self.yview_calls = []

    def yview_moveto(self, fraction):
        self.yview_calls.append(fraction)

    def see(self, _index):
        raise AssertionError("Zoom must not force a full-document see() pass")


class _FakeEditor:
    def __init__(self):
        self._zoom_restore_after_id = "pending"
        self.widget = _FakeTextWidget()

    def _text_widget(self):
        return self.widget


class _FakeSlider:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class _QueuedZoomEditor:
    def __init__(self):
        self._pending_zoom_value = 100.0
        self.document_zoom_slider = _FakeSlider(145.0)
        self.applied = []

    def _apply_zoom(self, value):
        self.applied.append(value)

    def _commit_pending_zoom(self):
        EditorFrame._commit_pending_zoom(self)


class _FakeFont:
    def __init__(self, size):
        self.size = size
        self.configure_calls = []

    def cget(self, option):
        if option != "size":
            raise AssertionError(option)
        return self.size

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)
        self.size = kwargs["size"]


class _NoLayoutEditor:
    def __init__(self):
        self.zoom_factor = 1.0
        self._base_style = {"size": 10}
        self._text_font = _FakeFont(10)
        self._font_cache = {}
        self._font_base_sizes = {}

    def _text_widget(self):
        raise AssertionError("Identical pixel sizes must not request text layout")

    def _scaled_font_size(self, base_size, zoom_factor):
        return EditorFrame._scaled_font_size(base_size, zoom_factor)


class EditorZoomTests(unittest.TestCase):
    def test_font_signature_ignores_color_only_differences(self):
        first = {
            "family": "Arial",
            "size": 15,
            "bold": False,
            "italic": False,
            "underline": False,
            "foreground": "#111111",
            "highlight": "#ffffff",
        }
        second = dict(first, foreground="#ff0000", highlight="#ffff00")

        self.assertEqual(
            EditorFrame._font_signature(first),
            EditorFrame._font_signature(second),
        )

    def test_restore_zoom_preserves_scroll_without_forcing_cursor_visible(self):
        editor = _FakeEditor()

        EditorFrame._restore_view_after_zoom(editor, 0.375)

        self.assertIsNone(editor._zoom_restore_after_id)
        self.assertEqual(editor.widget.yview_calls, [0.375])

    def test_slider_drag_only_commits_zoom_on_release(self):
        editor = _QueuedZoomEditor()

        EditorFrame._queue_zoom(editor, 135.0)

        self.assertEqual(editor._pending_zoom_value, 135.0)
        self.assertEqual(editor.applied, [])
        EditorFrame.on_zoom_release(editor)

        self.assertEqual(editor.applied, [145.0])

    def test_zoom_skips_layout_when_integer_font_size_is_unchanged(self):
        editor = _NoLayoutEditor()

        EditorFrame._apply_zoom(editor, 104.0)

        self.assertEqual(editor.zoom_factor, 1.04)
        self.assertEqual(editor._text_font.configure_calls, [])


if __name__ == "__main__":
    unittest.main()
