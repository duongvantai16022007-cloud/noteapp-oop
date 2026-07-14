import customtkinter as ctk
from services.settings_service import SettingsService
from services.translation_service import TranslationService
from ui.main_window import MainWindow

if __name__ == "__main__":
    settings = SettingsService().get_all()
    ctk.set_appearance_mode(settings.get("appearance_mode", "System"))
    color_theme = settings.get("color_theme", "blue").lower().replace(" ", "-")
    try:
        ctk.set_default_color_theme(color_theme)
    except Exception:
        ctk.set_default_color_theme("blue")

    # Initialize language
    TranslationService.set_language(settings.get("language", "en"))

    app = MainWindow()
    app.mainloop()