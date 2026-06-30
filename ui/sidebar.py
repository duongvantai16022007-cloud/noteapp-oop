import customtkinter as ctk

class SidebarFrame(ctk.CTkFrame):
    def __init__(self, master, on_note_select, on_new_text_note, on_new_checklist, on_search):
        super().__init__(master, width=280, corner_radius=0)
        self.grid_rowconfigure(4, weight=1)

        self.on_note_select = on_note_select
        
        # Logo
        ctk.CTkLabel(self, text="📝 Engraver", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))

        # Khung Tìm kiếm
        self.search_entry = ctk.CTkEntry(self, placeholder_text="🔍 Tìm kiếm...")
        self.search_entry.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.search_entry.bind("<KeyRelease>", on_search)

        # Nút tạo Text Note
        ctk.CTkButton(self, text="📄 Tạo Text Note", command=on_new_text_note).grid(row=2, column=0, padx=20, pady=(10, 5), sticky="ew")
        
        # Nút tạo Checklist Note
        ctk.CTkButton(self, text="☑ Tạo Checklist", fg_color="#10b981", hover_color="#059669", command=on_new_checklist).grid(row=3, column=0, padx=20, pady=(5, 10), sticky="ew")

        # Danh sách Ghi chú
        self.scroll_list = ctk.CTkScrollableFrame(self, label_text="Danh sách Ghi chú")
        self.scroll_list.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")

    def update_list(self, notes_list):
        """Vẽ lại danh sách Note"""
        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        for note in notes_list:
            title = note.get('title', 'Không có tiêu đề')
            icon = "☑" if note.get('type') == 'Checklist' else "📄"
            
            btn = ctk.CTkButton(
                self.scroll_list, text=f"{icon} {title}",
                fg_color="transparent", text_color=("gray10", "gray90"), anchor="w",
                command=lambda id=note['id']: self.on_note_select(id)
            )
            btn.pack(fill="x", pady=2, padx=5)