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
        self.grid_rowconfigure(3, weight=2)
        self.grid_rowconfigure(4, weight=1)

        self.on_note_select = on_note_select
        self.on_restore_deleted = on_restore_deleted
        self.on_permanently_delete = on_permanently_delete
        initial_settings = initial_settings or {}

        _ = TranslationService.get

        # Logo
        ctk.CTkLabel(
            self, text="📝 Engraver", font=ctk.CTkFont(size=24, weight="bold"),
            text_color=ThemeManager.get("text_primary")
        ).grid(row=0, column=0, padx=20, pady=(20, 10))

        # Khung Tìm kiếm
        self.search_entry = ctk.CTkEntry(
            self, 
            placeholder_text=f"🔍 {_('sidebar.search_placeholder')}",
            fg_color=ThemeManager.get("cell_bg"),
            text_color=ThemeManager.get("text_primary"),
            border_color=ThemeManager.get("grid_border"),
            border_width=3
        )
        self.search_entry.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.search_entry.bind("<KeyRelease>", on_search)

        # Khung chứa nút tác vụ (Thư mục mới)
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.action_frame.grid_columnconfigure(0, weight=1)

        self.btn_new_folder = ctk.CTkButton(
            self.action_frame, 
            text=f"📁 {_('sidebar.new_folder')}", 
            fg_color=ThemeManager.get("btn_secondary"),
            hover_color=ThemeManager.get("btn_secondary_hover"),
            text_color=ThemeManager.get("text_primary"),
            command=self._on_new_folder_click
        )
        self.btn_new_folder.grid(row=0, column=0, sticky="ew")

        # Danh sách Ghi chú chính
        self.scroll_list = ctk.CTkScrollableFrame(
            self, 
            label_text=_("sidebar.all_notes"),
            fg_color=ThemeManager.get("cell_bg"),
            label_fg_color="transparent",
            label_text_color=ThemeManager.get("text_primary")
        )
        self.scroll_list.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")

        # Danh sách thùng rác
        self.deleted_scroll_list = ctk.CTkScrollableFrame(
            self, 
            label_text=_("sidebar.deleted_list"),
            fg_color=ThemeManager.get("cell_bg"),
            label_fg_color="transparent",
            label_text_color=ThemeManager.get("text_primary")
        )
        self.deleted_scroll_list.grid(row=4, column=0, padx=10, pady=5, sticky="nsew")

    def update_tree_list(self, folders, notes_by_folder):
        """Vẽ lại danh sách Sidebar dạng cây thư mục gập mở được kèm nút xóa."""
        for widget in self.scroll_list.winfo_children():
            widget.destroy()
            
        _ = TranslationService.get

        # 1. Vẽ các Folder trước
        for folder in folders:
            f_id = folder["id"]
            f_name = folder["name"]
            
            folder_container_frame = ctk.CTkFrame(self.scroll_list, fg_color="transparent")
            folder_container_frame.pack(fill="x", pady=2)
            
            header_frame = ctk.CTkFrame(folder_container_frame, fg_color="transparent")
            header_frame.pack(fill="x")
            
            sub_notes_frame = ctk.CTkFrame(folder_container_frame, fg_color="transparent")
            
            def toggle(frame=sub_notes_frame):
                if frame.winfo_manager(): 
                    frame.pack_forget()
                else: 
                    frame.pack(fill="x", padx=(15, 0))

            btn_folder = ctk.CTkButton(
                header_frame, text=f"📂 {f_name}", anchor="w",
                fg_color=ThemeManager.get("cell_bg_muted"), 
                text_color=ThemeManager.get("text_primary"),
                command=toggle
            )
            btn_folder.pack(side="left", fill="x", expand=True, padx=(0, 2))

            btn_delete_folder = ctk.CTkButton(
                header_frame, text="❌", width=28, height=28,
                fg_color="transparent",
                hover_color=ThemeManager.get("accent_danger_hover"),
                text_color=ThemeManager.get("accent_danger"),
                command=lambda fid=f_id, fname=f_name: self._on_delete_folder_click(fid, fname)
            )
            btn_delete_folder.pack(side="right")
            btn_add_note = ctk.CTkButton(
                header_frame, text="➕", width=28, height=28,
                fg_color="transparent",
                hover_color=ThemeManager.get("cell_bg_muted"),
                text_color=ThemeManager.get("text_primary"),
                command=lambda fid=f_id, fname=f_name: self._on_add_note_to_folder_click(fid, fname)
            )
            btn_add_note.pack(side="right", padx=(0, 2))
            sub_notes_frame.pack(fill="x", padx=(15, 0)) 
            
            for note in notes_by_folder.get(f_id, []):
                self._draw_single_note(sub_notes_frame, note)

        # 2. Vẽ dải phân cách nếu có Note ở ngoài
        if folders and notes_by_folder.get("root"):
            ctk.CTkLabel(
                self.scroll_list, text="--- Ngoài thư mục ---", 
                text_color=ThemeManager.get("text_muted"), font=ctk.CTkFont(size=11)
            ).pack(pady=(10, 2))

        # 3. Vẽ các Note nằm ngoài không thuộc folder nào (Root)
        for note in notes_by_folder.get("root", []):
            self._draw_single_note(self.scroll_list, note)

    # Backup hỗ trợ cơ chế search cũ
    def update_list(self, notes_list):
        """Vẽ lại danh sách phẳng (sử dụng khi tìm kiếm)."""
        for widget in self.scroll_list.winfo_children():
            widget.destroy()
        for note in notes_list:
            self._draw_single_note(self.scroll_list, note)

    def _draw_single_note(self, parent_frame, note):
        _ = TranslationService.get
        title = note.get('title', _('sidebar.no_title'))
        icon = "☑" if str(note.get('type', '')).lower() == 'checklist' else "📄"
        lock_icon = " 🔒" if note.get('is_locked') else ""
        reminder_icon = " 🔔" if note.get('reminder_at') else ""
        deadline_icon = " 📌" if note.get('deadline_at') else ""

        btn = ctk.CTkButton(
            parent_frame,
            text=f"{icon} {title}{lock_icon}{reminder_icon}{deadline_icon}",
            fg_color="transparent",
            hover_color=ThemeManager.get("cell_bg_muted"),
            text_color=ThemeManager.get("text_primary"),
            anchor="w",
            command=lambda id=note['id']: self.on_note_select(id)
        )
        btn.pack(fill="x", pady=1, padx=2)

    def update_deleted_list(self, deleted_notes):
        for widget in self.deleted_scroll_list.winfo_children():
            widget.destroy()
            
        _ = TranslationService.get

        if not deleted_notes:
            ctk.CTkLabel(
                self.deleted_scroll_list, text=_("sidebar.no_deleted"),
                text_color=ThemeManager.get("text_primary")
            ).pack(padx=10, pady=10)
            return

        for note in deleted_notes:
            title = note.get('title', _('sidebar.no_title'))
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

    def _on_new_folder_click(self):
        """Kích hoạt hộp thoại yêu cầu nhập tên thư mục mới"""
        from tkinter import simpledialog, messagebox
        _ = TranslationService.get
        folder_name = simpledialog.askstring(_("msg.new_folder_title"), _("msg.new_folder_prompt"))
        
        if folder_name:
            if folder_name.strip() == "":
                messagebox.showwarning(_("msg.save_error"), _("msg.folder_empty"))
                return
            
            if hasattr(self.master, "create_new_folder"):
                self.master.create_new_folder(folder_name.strip())

    def _on_delete_folder_click(self, folder_id, folder_name):
        """Truyền sự kiện yêu cầu xóa thư mục lên MainWindow"""
        if hasattr(self.master, "delete_folder_by_id"):
            self.master.delete_folder_by_id(folder_id, folder_name)
    def _on_add_note_to_folder_click(self, folder_id, folder_name):
        """Kích hoạt lệnh tạo ghi chú mới nằm trong thư mục"""
        if hasattr(self.master, "prepare_new_in_folder"):
            self.master.prepare_new_in_folder(folder_id, folder_name)