import customtkinter as ctk
from services.settings_service import SettingsService
from ui.main_window import MainWindow

if __name__ == "__main__":
    settings = SettingsService().get_all()
    ctk.set_appearance_mode(settings.get("appearance_mode", "System"))
    color_theme = settings.get("color_theme", "blue").lower().replace(" ", "-")
    ctk.set_default_color_theme(color_theme)

    app = MainWindow()
    app.mainloop()
