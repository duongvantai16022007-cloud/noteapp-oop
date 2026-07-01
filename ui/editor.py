import customtkinter as ctk
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime

class EditorFrame(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_save,
        on_delete,
        on_undo,
        on_redo,
        on_export_md,
        on_export_pdf,
        on_lock_toggle
    ):
        super().__init__(master, fg_color="transparent")
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.current_note_type = "Text"  # Mặc định là Text
        self.checklist_vars = []  # Lưu trạng thái các ô tick

        # Toolbar: Chứa Export, Undo/Redo, định dạng cơ bản, khóa ghi chú.
        self.toolbar = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self.toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ctk.CTkButton(self.toolbar, text="⟲ Undo", width=70, command=on_undo).pack(side="left", padx=5)
        ctk.CTkButton(self.toolbar, text="⟳ Redo", width=70, command=on_redo).pack(side="left", padx=5)

        self.btn_bold = ctk.CTkButton(
            self.toolbar,
            text="B",
            width=38,
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.apply_text_style("bold")
        )
        self.btn_bold.pack(side="left", padx=(20, 3))

        self.btn_italic = ctk.CTkButton(
            self.toolbar,
            text="I",
            width=38,
            font=ctk.CTkFont(slant="italic"),
            command=lambda: self.apply_text_style("italic")
        )
        self.btn_italic.pack(side="left", padx=3)

        self.btn_lock = ctk.CTkButton(self.toolbar, text="🔒 Khóa", width=95, command=on_lock_toggle)
        self.btn_lock.pack(side="left", padx=(20, 5))

        ctk.CTkButton(self.toolbar, text="⬇ Xuất Markdown", width=120, command=on_export_md).pack(side="right", padx=5)
        ctk.CTkButton(self.toolbar, text="⬇ Xuất PDF", width=100, command=on_export_pdf).pack(side="right", padx=5)

        # Tiêu đề
        self.entry_title = ctk.CTkEntry(
            self,
            placeholder_text="Nhập tiêu đề...",
            font=ctk.CTkFont(size=24, weight="bold"),
            border_width=0,
            fg_color="transparent"
        )
        self.entry_title.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="ew")

        # Khung chứa nội dung động (swap giữa Textbox và Checklist)
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

        # 1. UI cho Text Note
        self.textbox_content = ctk.CTkTextbox(self.content_container, font=ctk.CTkFont(size=15), wrap="word")
        self._configure_text_tags()
        self.textbox_content.bind("<Control-b>", lambda event: self._shortcut_format(event, "bold"))
        self.textbox_content.bind("<Control-i>", lambda event: self._shortcut_format(event, "italic"))
        self._text_widget().bind("<Control-b>", lambda event: self._shortcut_format(event, "bold"))
        self._text_widget().bind("<Control-i>", lambda event: self._shortcut_format(event, "italic"))

        # 2. UI cho Checklist Note - GIỮ NGUYÊN các ô checkbox như bản cũ
        self.checklist_frame = ctk.CTkScrollableFrame(self.content_container)

        # Metadata: reminder/deadline
        self.meta_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.meta_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.meta_frame.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(self.meta_frame, text="🔔 Nhắc lúc").grid(row=0, column=0, padx=(0, 8), sticky="w")
        self.entry_reminder = ctk.CTkEntry(self.meta_frame, placeholder_text="YYYY-MM-DD HH:MM")
        self.entry_reminder.grid(row=0, column=1, padx=(0, 15), sticky="ew")

        ctk.CTkLabel(self.meta_frame, text="📌 Deadline").grid(row=0, column=2, padx=(0, 8), sticky="w")
        self.entry_deadline = ctk.CTkEntry(self.meta_frame, placeholder_text="YYYY-MM-DD HH:MM")
        self.entry_deadline.grid(row=0, column=3, sticky="ew")

        # Khung thêm item cho Checklist
        self.add_item_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.new_item_entry = ctk.CTkEntry(self.add_item_frame, placeholder_text="Thêm công việc mới...")
        self.new_item_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(self.add_item_frame, text="Thêm", width=80, command=self.add_checklist_item).pack(side="right")
        self.new_item_entry.bind("<Return>", lambda event: self._add_checklist_item_from_enter(event))

        # Nút chức năng cuối
        self.btn_delete = ctk.CTkButton(self, text="🗑 Xóa", fg_color="#ef4444", hover_color="#dc2626", command=on_delete)
        self.btn_delete.grid(row=5, column=0, sticky="w")

        self.btn_save = ctk.CTkButton(self, text="💾 Lưu Ghi Chú", command=lambda: on_save(self.get_data(), self.current_note_type))
        self.btn_save.grid(row=5, column=1, sticky="e")

    # =========================
    # Rich text cơ bản B/I
    # =========================
    def _text_widget(self):
        """Lấy widget Text thật bên trong CTkTextbox để dùng tag bôi đậm/in nghiêng."""
        return getattr(self.textbox_content, "_textbox", self.textbox_content)

    def _configure_text_tags(self):
        """Cấu hình tag hiển thị thật, không chỉ chèn ký tự ** hoặc *."""
        widget = self._text_widget()
        self._text_font = tkfont.Font(family="Arial", size=15)
        self._bold_font = tkfont.Font(family="Arial", size=15, weight="bold")
        self._italic_font = tkfont.Font(family="Arial", size=15, slant="italic")
        self._bold_italic_font = tkfont.Font(family="Arial", size=15, weight="bold", slant="italic")

        widget.tag_configure("bold", font=self._bold_font)
        widget.tag_configure("italic", font=self._italic_font)
        widget.tag_configure("bold_italic", font=self._bold_italic_font)

    def _shortcut_format(self, event, style_name):
        self.apply_text_style(style_name)
        return "break"

    def _style_at_index(self, index):
        widget = self._text_widget()
        tags = set(widget.tag_names(index))
        if "bold_italic" in tags:
            return True, True
        return "bold" in tags, "italic" in tags

    def _apply_style_tag_to_range(self, start, end, style):
        widget = self._text_widget()
        bold, italic = style
        if bold and italic:
            widget.tag_add("bold_italic", start, end)
        elif bold:
            widget.tag_add("bold", start, end)
        elif italic:
            widget.tag_add("italic", start, end)

    def _remove_style_tags(self, start, end):
        widget = self._text_widget()
        for tag_name in ("bold", "italic", "bold_italic"):
            widget.tag_remove(tag_name, start, end)

    def _get_selected_or_current_word_range(self):
        """Ưu tiên vùng đang bôi chọn; nếu không có thì áp dụng cho từ tại con trỏ."""
        widget = self._text_widget()
        try:
            start = widget.index("sel.first")
            end = widget.index("sel.last")
            return start, end
        except tk.TclError:
            start = widget.index("insert wordstart")
            end = widget.index("insert wordend")
            if widget.compare(start, "==", end):
                return None, None
            return start, end

    def _iterate_char_ranges(self, start, end):
        widget = self._text_widget()
        index = start
        while widget.compare(index, "<", end):
            next_index = widget.index(f"{index}+1c")
            yield index, next_index
            index = next_index

    def apply_text_style(self, style_name):
        """
        Bôi đậm/in nghiêng bằng tag của Tkinter Text.
        - Trên màn hình: chữ được in đậm/in nghiêng thật.
        - Khi lưu: convert tag về Markdown để dữ liệu content cũ vẫn dùng được.
        """
        if self.current_note_type != "Text":
            return

        widget = self._text_widget()
        start, end = self._get_selected_or_current_word_range()
        if not start or not end:
            return

        # Nếu toàn bộ vùng chọn đã có style này thì bấm lại để tắt; ngược lại thì bật.
        should_enable = False
        for char_start, _ in self._iterate_char_ranges(start, end):
            bold, italic = self._style_at_index(char_start)
            has_style = bold if style_name == "bold" else italic
            if not has_style:
                should_enable = True
                break

        styled_segments = []
        segment_start = start
        current_style = None

        for char_start, char_end in self._iterate_char_ranges(start, end):
            bold, italic = self._style_at_index(char_start)
            if style_name == "bold":
                bold = should_enable
            else:
                italic = should_enable
            new_style = (bold, italic)

            if current_style is None:
                current_style = new_style
                segment_start = char_start
            elif new_style != current_style:
                styled_segments.append((segment_start, char_start, current_style))
                segment_start = char_start
                current_style = new_style

        if current_style is not None:
            styled_segments.append((segment_start, end, current_style))

        self._remove_style_tags(start, end)
        for seg_start, seg_end, style in styled_segments:
            self._apply_style_tag_to_range(seg_start, seg_end, style)

        widget.tag_remove("sel", "1.0", "end")
        widget.focus_set()

    def _insert_segment_with_style(self, text, style):
        if not text:
            return
        widget = self._text_widget()
        start = widget.index("insert")
        widget.insert("insert", text)
        end = widget.index("insert")
        self._apply_style_tag_to_range(start, end, style)

    def _markdown_to_rich_text(self, content):
        """Render Markdown cơ bản (**bold**, *italic*, ***bold italic***) thành tag hiển thị."""
        widget = self._text_widget()
        widget.delete("1.0", "end")
        self._remove_style_tags("1.0", "end")

        text = str(content or "")
        bold = False
        italic = False
        buffer = []
        i = 0

        def flush_buffer():
            if buffer:
                self._insert_segment_with_style("".join(buffer), (bold, italic))
                buffer.clear()

        while i < len(text):
            # Ưu tiên *** để hỗ trợ cả đậm + nghiêng.
            if text.startswith("***", i):
                flush_buffer()
                bold = not bold
                italic = not italic
                i += 3
            elif text.startswith("**", i):
                flush_buffer()
                bold = not bold
                i += 2
            elif text[i] == "*":
                flush_buffer()
                italic = not italic
                i += 1
            else:
                buffer.append(text[i])
                i += 1

        flush_buffer()

    def _rich_text_to_markdown(self):
        """Convert nội dung đang hiển thị cùng tag B/I về Markdown để lưu vào content TEXT cũ."""
        widget = self._text_widget()
        end = widget.index("end-1c")
        result = []
        current_style = (False, False)

        def close_style(style):
            bold, italic = style
            if italic:
                result.append("*")
            if bold:
                result.append("**")

        def open_style(style):
            bold, italic = style
            if bold:
                result.append("**")
            if italic:
                result.append("*")

        index = "1.0"
        while widget.compare(index, "<", end):
            style = self._style_at_index(index)
            if style != current_style:
                close_style(current_style)
                open_style(style)
                current_style = style
            result.append(widget.get(index, f"{index}+1c"))
            index = widget.index(f"{index}+1c")

        close_style(current_style)
        return "".join(result).strip()

    # Giữ alias cũ để không làm lỗi nếu nơi khác còn gọi apply_markdown_format.
    def apply_markdown_format(self, marker):
        if marker == "**":
            self.apply_text_style("bold")
        else:
            self.apply_text_style("italic")

    # =========================
    # Checklist + dữ liệu form
    # =========================
    def setup_ui_mode(self, note_type):
        """Chuyển đổi giao diện dựa theo loại Note."""
        note_type = "Checklist" if str(note_type).lower() == "checklist" else note_type
        self.current_note_type = note_type

        # Ẩn tất cả đi trước
        self.textbox_content.grid_forget()
        self.checklist_frame.grid_forget()
        self.add_item_frame.grid_forget()

        if note_type == "Checklist":
            self.checklist_frame.grid(row=0, column=0, sticky="nsew")
            self.add_item_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 10))
            self.btn_bold.configure(state="disabled")
            self.btn_italic.configure(state="disabled")
        else:  # Text Note
            self.textbox_content.grid(row=0, column=0, sticky="nsew")
            self.btn_bold.configure(state="normal")
            self.btn_italic.configure(state="normal")

    def _add_checklist_item_from_enter(self, event):
        self.add_checklist_item()
        return "break"

    def add_checklist_item(self, text="", is_done=False):
        """Thêm một dòng checkbox vào khung Checklist - khôi phục đúng kiểu bản noteapp-oop gốc."""
        if not text:
            text = self.new_item_entry.get().strip()
            self.new_item_entry.delete(0, 'end')

        if not text:
            return

        var = ctk.BooleanVar(value=is_done)
        cb = ctk.CTkCheckBox(self.checklist_frame, text=text, variable=var)
        cb.pack(anchor="w", pady=5, padx=10)
        self.checklist_vars.append({"checkbox": cb, "var": var})

    def clear_checklist_items(self):
        """Xóa các checkbox cũ giống cơ chế của bản noteapp-oop gốc."""
        for item in self.checklist_vars:
            item["checkbox"].destroy()
        self.checklist_vars.clear()

    def set_lock_state(self, is_locked=False, enabled=True):
        if not enabled:
            self.btn_lock.configure(text="🔒 Khóa", state="disabled")
            return
        self.btn_lock.configure(
            text="🔓 Gỡ khóa" if is_locked else "🔒 Khóa",
            state="normal"
        )

    def _format_datetime_for_entry(self, value):
        if not value:
            return ""
        try:
            dt = datetime.fromisoformat(str(value))
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return str(value)

    def set_data(self, title, content_data, note_type, reminder_at=None, deadline_at=None, is_locked=False):
        self.setup_ui_mode(note_type)
        self.entry_title.delete(0, 'end')
        self.entry_title.insert(0, title)

        self.entry_reminder.delete(0, 'end')
        self.entry_reminder.insert(0, self._format_datetime_for_entry(reminder_at))
        self.entry_deadline.delete(0, 'end')
        self.entry_deadline.insert(0, self._format_datetime_for_entry(deadline_at))
        self.set_lock_state(is_locked=is_locked, enabled=bool(title))

        if note_type == "Checklist":
            self.clear_checklist_items()

            # Khởi tạo lại danh sách checkbox từ dữ liệu cũ: list[dict] hoặc list[TodoItem]
            if isinstance(content_data, list):
                for item in content_data:
                    text = item.get("content") if isinstance(item, dict) else getattr(item, 'content', str(item))
                    done = item.get("is_done") if isinstance(item, dict) else getattr(item, 'is_done', False)
                    self.add_checklist_item(text, done)
        else:
            self._markdown_to_rich_text(content_data)

    def get_data(self):
        title = self.entry_title.get().strip()
        if self.current_note_type == "Checklist":
            content = [
                {"content": item["checkbox"].cget("text"), "is_done": item["var"].get()}
                for item in self.checklist_vars
            ]
        else:
            content = self._rich_text_to_markdown()

        return {
            "title": title,
            "content": content,
            "reminder_at": self.entry_reminder.get().strip(),
            "deadline_at": self.entry_deadline.get().strip()
        }
