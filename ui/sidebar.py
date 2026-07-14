import customtkinter as ctk
from services.theme_service import ThemeManager
from services.translation_service import TranslationService

class SidebarFrame(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_note_select,
        on_restore_deleted,
        on_permanently_delete,
        on_search,
        initial_settings=None
    ):
        super().__init__(master, width=280, corner_radius=0, fg_color=ThemeManager.get("popup_bg"))
        self.grid_propagate(False)
        self.grid_rowconfigure(2, weight=2)
        self.grid_rowconfigure(3, weight=1)

        self.on_note_select = on_note_select
        self.on_restore_deleted = on_restore_deleted
        self.on_permanently_delete = on_permanently_delete
        initial_settings = initial_settings or {}

        # Logo
        ctk.CTkLabel(
            self, text=TranslationService.get("sidebar.logo"), font=ctk.CTkFont(size=24, weight="bold"),
            text_color=ThemeManager.get("text_primary")
        ).grid(row=0, column=0, padx=20, pady=(20, 10))

        # Search
        self.search_entry = ctk.CTkEntry(
            self, placeholder_text=TranslationService.get("sidebar.search_placeholder"),
            fg_color=ThemeManager.get("cell_bg"),
            text_color=ThemeManager.get("text_primary"),
            border_color=ThemeManager.get("grid_border"),
            border_width=3
        )
        self.search_entry.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.search_entry.bind("<KeyRelease>", on_search)

        # Note list
        self.scroll_list = ctk.CTkScrollableFrame(
            self, label_text=TranslationService.get("sidebar.note_list"),
            fg_color=ThemeManager.get("cell_bg"),
            label_fg_color="transparent",
            label_text_color=ThemeManager.get("text_primary")
        )
        self.scroll_list.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        self.deleted_scroll_list = ctk.CTkScrollableFrame(
            self, label_text=TranslationService.get("sidebar.deleted_list"),
            fg_color=ThemeManager.get("cell_bg"),
            label_fg_color="transparent",
            label_text_color=ThemeManager.get("text_primary")
        )
        self.deleted_scroll_list.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="nsew")

    def update_list(self, notes_list):
        """Vẽ lại danh sách Note."""
        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        for note in notes_list:
            title = note.get('title', TranslationService.get("sidebar.no_title"))
            icon = "☑" if str(note.get('type', '')).lower() == 'checklist' else "📄"
            lock_icon = " 🔒" if note.get('is_locked') else ""
            reminder_icon = " 🔔" if note.get('reminder_at') else ""
            deadline_icon = " 📌" if note.get('deadline_at') else ""

            btn = ctk.CTkButton(
                self.scroll_list,
                text=f"{icon} {title}{lock_icon}{reminder_icon}{deadline_icon}",
                fg_color="transparent",
                hover_color=ThemeManager.get("cell_bg_muted"),
                text_color=ThemeManager.get("text_primary"),
                anchor="w",
                command=lambda id=note['id']: self.on_note_select(id)
            )
            btn.pack(fill="x", pady=2, padx=5)

    def update_deleted_list(self, deleted_notes):
        for widget in self.deleted_scroll_list.winfo_children():
            widget.destroy()

        if not deleted_notes:
            ctk.CTkLabel(
                self.deleted_scroll_list, text=TranslationService.get("sidebar.no_deleted"),
                text_color=ThemeManager.get("text_primary")
            ).pack(padx=10, pady=10)
            return

        for note in deleted_notes:
            title = note.get('title', TranslationService.get("sidebar.no_title"))
            deleted_at = note.get('deleted_at', '')
            icon = "☑" if str(note.get('type', '')).lower() == 'checklist' else "📄"
            label = f"{icon} {title}"
            if deleted_at:
                label += f" • {deleted_at[:16].replace('T', ' ')}"

            row_frame = ctk.CTkFrame(self.deleted_scroll_list, fg_color="transparent")
            row_frame.pack(fill="x", pady=2, padx=5)

            btn = ctk.CTkButton(
                row_frame,
                text=f"↩ {label}",
                fg_color="transparent",
                hover_color=ThemeManager.get("cell_bg_muted"),
                text_color=ThemeManager.get("text_primary"),
                anchor="w",
                command=lambda id=note['id']: self.on_restore_deleted(id)
            )
            btn.pack(side="left", fill="x", expand=True)

            del_btn = ctk.CTkButton(
                row_frame,
                text="❌",
                width=28,
                height=28,
                fg_color="transparent",
                hover_color=ThemeManager.get("accent_danger_hover"),
                text_color=ThemeManager.get("accent_danger"),
                command=lambda id=note['id']: self.on_permanently_delete(id)
            )
            del_btn.pack(side="right", padx=(5, 0))
