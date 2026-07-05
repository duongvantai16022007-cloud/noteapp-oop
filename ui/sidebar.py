import customtkinter as ctk
from services.theme_service import ThemeManager

class SidebarFrame(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_note_select,
        on_restore_deleted,
        on_permanently_delete,
        on_new_text_note,
        on_new_checklist,
        on_search,
        on_open_calendar,
        on_theme_change,
        initial_settings=None
    ):
        super().__init__(master, width=280, corner_radius=0)
        self.grid_propagate(False)
        self.grid_rowconfigure(6, weight=2)
        self.grid_rowconfigure(7, weight=1)

        self.on_note_select = on_note_select
        self.on_restore_deleted = on_restore_deleted
        self.on_permanently_delete = on_permanently_delete
        self.on_theme_change = on_theme_change
        initial_settings = initial_settings or {}

        # Logo
        ctk.CTkLabel(self, text="📝 Engraver", font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(20, 10)
        )

        # Khung Tìm kiếm
        self.search_entry = ctk.CTkEntry(self, placeholder_text="🔍 Tìm kiếm...")
        self.search_entry.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.search_entry.bind("<KeyRelease>", on_search)

        # Nút tạo Text Note
        ctk.CTkButton(self, text="📄 Tạo Text Note", command=on_new_text_note).grid(
            row=2, column=0, padx=20, pady=(10, 5), sticky="ew"
        )

        # Nút tạo Checklist Note
        ctk.CTkButton(self, text="☑ Tạo Checklist", fg_color=ThemeManager.get("accent_success"), hover_color=ThemeManager.get("accent_success_hover"), command=on_new_checklist).grid(
            row=3, column=0, padx=20, pady=(5, 5), sticky="ew"
        )

        # Lịch biểu
        ctk.CTkButton(self, text="📅 Lịch biểu", command=on_open_calendar).grid(
            row=4, column=0, padx=20, pady=(5, 10), sticky="ew"
        )

        # Theme UI
        self.theme_frame = ctk.CTkFrame(self)
        self.theme_frame.grid(row=5, column=0, padx=10, pady=5, sticky="ew")
        self.theme_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.theme_frame, text="🎨 Giao diện", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=10, pady=(8, 3), sticky="w"
        )

        self.appearance_menu = ctk.CTkOptionMenu(
            self.theme_frame,
            values=["System", "Light", "Dark"],
            command=lambda value: self.on_theme_change("appearance_mode", value)
        )
        self.appearance_menu.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.appearance_menu.set(initial_settings.get("appearance_mode", "System"))

        self.color_menu = ctk.CTkOptionMenu(
            self.theme_frame,
            values=["blue", "green", "dark blue"],
            command=lambda value: self.on_theme_change("color_theme", value)
        )
        self.color_menu.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.color_menu.set(initial_settings.get("color_theme", "blue"))

        # Danh sách Ghi chú
        self.scroll_list = ctk.CTkScrollableFrame(self, label_text="Danh sách Ghi chú")
        self.scroll_list.grid(row=6, column=0, padx=10, pady=10, sticky="nsew")

        self.deleted_scroll_list = ctk.CTkScrollableFrame(self, label_text="Bị xoá gần đây")
        self.deleted_scroll_list.grid(row=7, column=0, padx=10, pady=(0, 10), sticky="nsew")

    def update_list(self, notes_list):
        """Vẽ lại danh sách Note."""
        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        for note in notes_list:
            title = note.get('title', 'Không có tiêu đề')
            icon = "☑" if str(note.get('type', '')).lower() == 'checklist' else "📄"
            lock_icon = " 🔒" if note.get('is_locked') else ""
            reminder_icon = " 🔔" if note.get('reminder_at') else ""
            deadline_icon = " 📌" if note.get('deadline_at') else ""

            btn = ctk.CTkButton(
                self.scroll_list,
                text=f"{icon} {title}{lock_icon}{reminder_icon}{deadline_icon}",
                fg_color="transparent",
                text_color=ThemeManager.get("text_primary"),
                anchor="w",
                command=lambda id=note['id']: self.on_note_select(id)
            )
            btn.pack(fill="x", pady=2, padx=5)

    def update_deleted_list(self, deleted_notes):
        for widget in self.deleted_scroll_list.winfo_children():
            widget.destroy()

        if not deleted_notes:
            ctk.CTkLabel(self.deleted_scroll_list, text="Không có mục đã xóa").pack(padx=10, pady=10)
            return

        for note in deleted_notes:
            title = note.get('title', 'Không có tiêu đề')
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
