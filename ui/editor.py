import customtkinter as ctk

class EditorFrame(ctk.CTkFrame):
    def __init__(self, master, on_save, on_delete, on_undo, on_redo, on_export_md, on_export_pdf):
        super().__init__(master, fg_color="transparent")
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.current_note_type = "Text" # Mặc định là Text
        self.checklist_vars = [] # Lưu trạng thái các ô tick

        # Toolbar: Chứa Export & Undo/Redo
        self.toolbar = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self.toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        ctk.CTkButton(self.toolbar, text="⟲ Undo", width=70, command=on_undo).pack(side="left", padx=5)
        ctk.CTkButton(self.toolbar, text="⟳ Redo", width=70, command=on_redo).pack(side="left", padx=5)
        
        ctk.CTkButton(self.toolbar, text="⬇ Xuất Markdown", width=120, command=on_export_md).pack(side="right", padx=5)
        ctk.CTkButton(self.toolbar, text="⬇ Xuất PDF", width=100, command=on_export_pdf).pack(side="right", padx=5)

        # Tiêu đề
        self.entry_title = ctk.CTkEntry(self, placeholder_text="Nhập tiêu đề...", font=ctk.CTkFont(size=24, weight="bold"), border_width=0, fg_color="transparent")
        self.entry_title.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="ew")

        # Khung chứa nội dung động (Sẽ swap giữa Textbox và Checklist)
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

        # 1. UI cho Text Note
        self.textbox_content = ctk.CTkTextbox(self.content_container, font=ctk.CTkFont(size=15), wrap="word")
        
        # 2. UI cho Checklist Note
        self.checklist_frame = ctk.CTkScrollableFrame(self.content_container)
        
        # Khung thêm item cho Checklist
        self.add_item_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.new_item_entry = ctk.CTkEntry(self.add_item_frame, placeholder_text="Thêm công việc mới...")
        self.new_item_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(self.add_item_frame, text="Thêm", width=80, command=self.add_checklist_item).pack(side="right")

        # Nút chức năng cuối
        self.btn_delete = ctk.CTkButton(self, text="🗑 Xóa", fg_color="#ef4444", hover_color="#dc2626", command=on_delete)
        self.btn_delete.grid(row=4, column=0, sticky="w")

        self.btn_save = ctk.CTkButton(self, text="💾 Lưu Ghi Chú", command=lambda: on_save(self.get_data(), self.current_note_type))
        self.btn_save.grid(row=4, column=1, sticky="e")

    def setup_ui_mode(self, note_type):
        """Chuyển đổi giao diện dựa theo loại Note"""
        self.current_note_type = note_type
        
        # Ẩn tất cả đi trước
        self.textbox_content.grid_forget()
        self.checklist_frame.grid_forget()
        self.add_item_frame.grid_forget()
        
        if note_type == "Checklist":
            self.checklist_frame.grid(row=0, column=0, sticky="nsew")
            self.add_item_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        else: # Text Note
            self.textbox_content.grid(row=0, column=0, sticky="nsew")

    def add_checklist_item(self, text="", is_done=False):
        """Thêm một dòng checkbox vào khung Checklist"""
        if not text:
            text = self.new_item_entry.get().strip()
            self.new_item_entry.delete(0, 'end')
        
        if not text: return
        
        var = ctk.BooleanVar(value=is_done)
        cb = ctk.CTkCheckBox(self.checklist_frame, text=text, variable=var)
        cb.pack(anchor="w", pady=5, padx=10)
        self.checklist_vars.append({"checkbox": cb, "var": var})

    def set_data(self, title, content_data, note_type):
        self.setup_ui_mode(note_type)
        self.entry_title.delete(0, 'end')
        self.entry_title.insert(0, title)
        
        if note_type == "Checklist":
            # Xóa các checkbox cũ
            for item in self.checklist_vars:
                item["checkbox"].destroy()
            self.checklist_vars.clear()
            
            # Khởi tạo lại danh sách checkbox
            if isinstance(content_data, list):
                for item in content_data:
                    # Hỗ trợ cả dict và TodoItem object
                    text = item.get("content") if isinstance(item, dict) else getattr(item, 'content', str(item))
                    done = item.get("is_done") if isinstance(item, dict) else getattr(item, 'is_done', False)
                    self.add_checklist_item(text, done)
        else:
            self.textbox_content.delete("1.0", 'end')
            if content_data:
                self.textbox_content.insert("1.0", content_data)

    def get_data(self):
        title = self.entry_title.get().strip()
        if self.current_note_type == "Checklist":
            content = [{"content": item["checkbox"].cget("text"), "is_done": item["var"].get()} for item in self.checklist_vars]
        else:
            content = self.textbox_content.get("1.0", 'end-1c').strip()
            
        return {"title": title, "content": content}