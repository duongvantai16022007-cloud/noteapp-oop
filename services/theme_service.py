import json
import os
import logging

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
    def get(cls, key, default="transparent"):
        instance = cls()
        val = instance._colors.get(key, default)
        
        # If the value is a list of exactly 2 strings, convert it to a tuple for CustomTkinter
        if isinstance(val, list) and len(val) == 2:
            return (val[0], val[1])
        return val

# Global instance for easy imports
theme = ThemeManager()
