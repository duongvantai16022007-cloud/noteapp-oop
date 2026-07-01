import customtkinter as ctk

class SidebarFrame(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_note_select,
        on_new_text_note,
        on_new_checklist,
        on_search,
        on_open_calendar,
        on_theme_change,
        initial_settings=None
    ):
        super().__init__(master, width=280, corner_radius=0)
        self.grid_rowconfigure(6, weight=1)

        self.on_note_select = on_note_select
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
        ctk.CTkButton(self, text="☑ Tạo Checklist", fg_color="#10b981", hover_color="#059669", command=on_new_checklist).grid(
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
            values=["blue", "green", "dark-blue"],
            command=lambda value: self.on_theme_change("color_theme", value)
        )
        self.color_menu.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.color_menu.set(initial_settings.get("color_theme", "blue"))

        # Danh sách Ghi chú
        self.scroll_list = ctk.CTkScrollableFrame(self, label_text="Danh sách Ghi chú")
        self.scroll_list.grid(row=6, column=0, padx=10, pady=10, sticky="nsew")

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
                text_color=("gray10", "gray90"),
                anchor="w",
                command=lambda id=note['id']: self.on_note_select(id)
            )
            btn.pack(fill="x", pady=2, padx=5)
