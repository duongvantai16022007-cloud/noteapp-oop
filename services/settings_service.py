from data.DatabaseManager import DatabaseManager

class SettingsService:
    """Lưu/đọc cấu hình giao diện ứng dụng."""

    DEFAULTS = {
        "appearance_mode": "System",
        "color_theme": "blue",
        "language": "en"
    }

    def __init__(self):
        self.db = DatabaseManager()

    def get_setting(self, key, default=None):
        row = self.db.fetch_one("SELECT value FROM app_settings WHERE key = ?", (key,))
        if row:
            return row["value"]
        return self.DEFAULTS.get(key, default)

    def set_setting(self, key, value):
        self.db.execute_query(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
            (key, value)
        )

    def get_all(self):
        return {key: self.get_setting(key, value) for key, value in self.DEFAULTS.items()}