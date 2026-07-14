import customtkinter as ctk
from services.theme_service import ThemeManager

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

        # Logo
        ctk.CTkLabel(
            self, text="📝 Engraver", font=ctk.CTkFont(size=24, weight="bold"),
            text_color=ThemeManager.get("text_primary")
        ).grid(row=0, column=0, padx=20, pady=(20, 10))

        # Khung Tìm kiếm
        self.search_entry = ctk.CTkEntry(
            self, placeholder_text="🔍 Tìm kiếm...",
            fg_color=ThemeManager.get("cell_bg"),
            text_color=ThemeManager.get("text_primary"),
            border_color=ThemeManager.get("grid_border"),
            border_width=3
        )
        self.search_entry.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.action_frame.grid_columnconfigure(0, weight=1)
        self.btn_new_folder = ctk.CTkButton(
            self.action_frame, 
            text="📁 Thư mục mới", 
            fg_color=ThemeManager.get("btn_secondary"),
            hover_color=ThemeManager.get("btn_secondary_hover"),
            text_color=ThemeManager.get("text_primary"),
            command=self._on_new_folder_click
        )
        self.btn_new_folder.grid(row=0, column=0, sticky="ew")
        self.scroll_list = ctk.CTkScrollableFrame(
            self, fg_color="transparent", label_text="Tất cả ghi chú",
            label_text_color=ThemeManager.get("text_muted")
        )
        self.scroll_list.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")

        self.deleted_scroll_list = ctk.CTkScrollableFrame(
            self, fg_color="transparent", label_text="Đã xóa gần đây",
            label_text_color=ThemeManager.get("text_muted")
        )
        self.deleted_scroll_list.grid(row=4, column=0, padx=10, pady=5, sticky="nsew")

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
                self.deleted_scroll_list, text="Không có mục đã xóa",
                text_color=ThemeManager.get("text_primary")
            ).pack(padx=10, pady=10)
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
    def refresh_note_tree(self, folders, notes_by_folder, on_note_click, on_move_note):
        """
        folders: list các dict folder từ repo
        notes_by_folder: dict dạng { folder_id: [list_notes], "root": [list_notes_ngoai_thư_mục] }
        """
        # Xóa sạch các widget cũ trong khung cuộn trước khi vẽ lại
        for widget in self.note_scroll_list.winfo_children():
            widget.destroy()

        # 1. Vẽ nút "Thêm Thư Mục Mới" ở trên cùng Sidebar
        btn_add_folder = ctk.CTkButton(
        self.note_scroll_list, text="📁 + Thêm Thư Mục",
        fg_color=ThemeManager.get("btn_secondary"),
        command=self._on_click_create_folder # Hàm callback hiển thị dialog nhập tên
        )
        btn_add_folder.pack(fill="x", padx=10, pady=5)

        # 2. Vẽ các Folder và Note bên trong chúng
        for folder in folders:
            f_id = folder["id"]
            f_name = folder["name"]
        
            # Tạo Container Frame cho mỗi cặp (Tiêu đề Thư mục + Danh sách con)
            folder_container = ctk.CTkFrame(self.note_scroll_list, fg_color="transparent")
            folder_container.pack(fill="x", pady=2)

            # Nút tiêu đề thư mục (Click vào để Ẩn/Hiện các ghi chú bên trong)
            sub_notes_frame = ctk.CTkFrame(folder_container, fg_color="transparent")
        
            btn_folder_title = ctk.CTkButton(
                folder_container, text=f"📂 {f_name}",
                anchor="w", fg_color=ThemeManager.get("cell_bg_muted"),
                text_color=ThemeManager.get("text_primary"),
                command=lambda f=sub_notes_frame: self._toggle_folder(f)
            )
            btn_folder_title.pack(fill="x", padx=5)
        
            # Đổ các note thuộc folder này vào sub_notes_frame
            notes_in_f = notes_by_folder.get(f_id, [])
            for note in notes_in_f:
                self._render_note_row(sub_notes_frame, note, on_note_click, indent=15)
            
            # Mặc định hiển thị danh sách note con
            sub_notes_frame.pack(fill="x", padx=5)

        # 3. Vẽ các Note nằm tự do ở ngoài cùng (Root)
        root_notes = notes_by_folder.get("root", [])
        if root_notes:
            lbl_root = ctk.CTkLabel(self.note_scroll_list, text="Ghi chú ngoài thư mục", font=ctk.CTkFont(size=11, weight="bold"))
            lbl_root.pack(anchor="w", padx=10, pady=(10, 2))
        
            for note in root_notes:
                self._render_note_row(self.note_scroll_list, note, on_note_click, indent=5)

    def _toggle_folder(self, target_frame):
        if target_frame.winfo_manager():
            target_frame.pack_forget()
        else:
            target_frame.pack(fill="x", padx=5)

    def _render_note_row(self, master_frame, note, on_note_click, indent):
    # Hàm này thay thế cho việc vẽ Note cũ, bổ sung tham số indent (nội dịch lề) 
    # để tạo cảm giác Note thụt lề vào trong Folder.
        icon = "☑" if str(note.get('type', '')).lower() == 'checklist' else "📄"
        btn = ctk.CTkButton(
            master_frame, text=f"{icon} {note['title']}",
            anchor="w", fg_color="transparent",
            text_color=ThemeManager.get("text_primary"),
            command=lambda: on_note_click(note['id'])
        )
        btn.pack(fill="x", padx=(indent, 5), pady=1)
    def update_tree_list(self, folders, notes_by_folder):
        """Vẽ lại danh sách Sidebar dạng cây thư mục gập mở được kèm nút xóa."""
        for widget in self.scroll_list.winfo_children():
            widget.destroy()
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
            sub_notes_frame.pack(fill="x", padx=(15, 0)) 
            for note in notes_by_folder.get(f_id, []):
                self._draw_single_note(sub_notes_frame, note)
        if folders and notes_by_folder.get("root"):
            ctk.CTkLabel(
                self.scroll_list, text="--- Ngoài thư mục ---", 
                text_color=ThemeManager.get("text_muted"), font=ctk.CTkFont(size=11)
            ).pack(pady=(10, 2))
        for note in notes_by_folder.get("root", []):
            self._draw_single_note(self.scroll_list, note)

    def _on_delete_folder_click(self, folder_id, folder_name):
        """Truyền sự kiện yêu cầu xóa thư mục lên MainWindow xử lý dữ liệu"""
        if hasattr(self.master, "delete_folder_by_id"):
            self.master.delete_folder_by_id(folder_id, folder_name)
            
    def _draw_single_note(self, parent_frame, note):
        """Hàm phụ trợ để vẽ 1 nút Note."""
        title = note.get('title', 'Không có tiêu đề')
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
    def _on_new_folder_click(self):
        """Kích hoạt hộp thoại yêu cầu nhập tên thư mục mới"""
        from tkinter import simpledialog, messagebox
        folder_name = simpledialog.askstring("Thư mục mới", "Nhập tên thư mục cần tạo:")
        if folder_name:
            if folder_name.strip() == "":
                messagebox.showwarning("Cảnh báo", "Tên thư mục không được để trống!")
                return
            if hasattr(self.master, "create_new_folder"):
                self.master.create_new_folder(folder_name.strip())