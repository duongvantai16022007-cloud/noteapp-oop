import json
import os
import logging
from copy import deepcopy

class ThemeManager:
    _instance = None
    _colors = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThemeManager, cls).__new__(cls)
            cls._instance._colors = {}
            cls._instance.active_theme = "blue"
            cls._instance.load_theme("blue")
        return cls._instance

    def load_theme(self, theme_name):
        try:
            # Clean up the theme name to match file format (e.g., "dark blue" -> "dark-blue")
            formatted_name = theme_name.lower().replace(" ", "-")
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            theme_path = os.path.join(base_dir, "config", "themes", f"{formatted_name}.json")
            
            if not os.path.exists(theme_path):
                # Fallback to blue.json
                theme_path = os.path.join(base_dir, "config", "themes", "blue.json")
                
            if os.path.exists(theme_path):
                with open(theme_path, "r", encoding="utf-8") as f:
                    self._colors = json.load(f)
                    self.active_theme = formatted_name
            else:
                logging.warning(f"Theme file not found at {theme_path}. Falling back to transparent.")
                self._colors = {}
        except Exception as e:
            logging.error(f"Failed to load theme file: {e}")
            self._colors = {}

    @classmethod
    def set_active_theme(cls, theme_name):
        instance = cls()
        instance.load_theme(theme_name)

    @classmethod
    def get_available_themes(cls):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            themes_dir = os.path.join(base_dir, "config", "themes")
            if not os.path.exists(themes_dir):
                return ["FALLBACK_NO_DIR"]
            
            themes = []
            for file in os.listdir(themes_dir):
                if file.endswith(".json"):
                    # Convert filename to dropdown display name: e.g. "dark-blue.json" -> "dark blue"
                    theme_name = file[:-5].replace("-", " ")
                    themes.append(theme_name)
            
            themes.sort()
            if not themes:
                themes = ["FALLBACK_EMPTY"]
            return themes
        except Exception as e:
            logging.error(f"Error getting available themes: {e}")
            return ["FALLBACK_EXCEPTION"]

    @classmethod
    def get(cls, key, default="transparent"):
        instance = cls()
        val = instance._colors.get(key, default)
        
        # If the value is a list of exactly 2 strings, convert it to a tuple for CustomTkinter
        if isinstance(val, list) and len(val) == 2:
            return (val[0], val[1])
        return val

    @classmethod
    def get_palette(cls):
        """Return an isolated palette snapshot for in-place theme transitions."""
        return deepcopy(cls()._colors)

    @staticmethod
    def _color_token(value):
        if isinstance(value, (list, tuple)):
            return tuple(value)
        return value

    @classmethod
    def apply_to_widget_tree(cls, root, previous_palette):
        """Replace old palette values on existing CustomTkinter widgets.

        Widgets are updated in-place, so changing a color theme does not need to
        destroy the editor/sidebar or reload notes from the database.
        """
        if root is None or not previous_palette:
            return

        current_palette = cls.get_palette()
        replacements = {}
        replacement_priorities = {}
        # Search-current colors are reapplied explicitly by EditorFrame. When
        # their old value matches a persistent widget color (commonly white),
        # prefer the semantic color used by those persistent widgets.
        semantic_priorities = {"text_on_accent": 10}
        for key, old_value in previous_palette.items():
            if key not in current_palette:
                continue
            token = cls._color_token(old_value)
            new_value = cls.get(key)
            priority = semantic_priorities.get(key, 0)
            if token not in replacements or priority > replacement_priorities[token]:
                replacements[token] = new_value
                replacement_priorities[token] = priority

        color_options = (
            "fg_color", "bg_color", "hover_color", "border_color",
            "text_color", "button_color", "button_hover_color",
            "progress_color", "dropdown_fg_color", "dropdown_hover_color",
            "dropdown_text_color", "label_fg_color", "label_text_color",
            "scrollbar_button_color", "scrollbar_button_hover_color",
        )

        pending = [root]
        while pending:
            widget = pending.pop()
            try:
                pending.extend(widget.winfo_children())
            except Exception:
                pass

            updates = {}
            for option in color_options:
                try:
                    old_value = widget.cget(option)
                except Exception:
                    continue
                replacement = replacements.get(cls._color_token(old_value))
                if replacement is not None and replacement != old_value:
                    updates[option] = replacement
            if updates:
                try:
                    widget.configure(**updates)
                except Exception:
                    # Internal Tk widgets may expose similarly named options with
                    # incompatible value formats; their CTk parent redraws them.
                    pass

# Global instance for easy imports
theme = ThemeManager()
