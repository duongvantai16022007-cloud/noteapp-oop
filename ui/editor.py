import customtkinter as ctk
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, colorchooser
from datetime import datetime
from ui.date_picker import CTkDatePicker
from ui.color_picker import CTkColorPicker
from services.theme_service import ThemeManager

class EditorFrame(ctk.CTkFrame):
    def __init__(
        self,
        master
    ):
        super().__init__(master, fg_color="transparent")
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_propagate(False)

        self.current_note_type = "Text"  # Mặc định là Text
        self.checklist_vars = []  # Lưu trạng thái các ô tick
        self._editor_default_height = 420
        self._font_cache = {}
        self._font_cache_initialized = set()  # Track which tags have had Font objects created
        self.zoom_factor = 1.0
        self._zoom_job = None

        # Placeholder text constants for Fix 8
        self._reminder_placeholder = "YYYY-MM-DD HH:MM"
        self._deadline_placeholder = "YYYY-MM-DD HH:MM"

        # Toolbar: Chứa định dạng cơ bản
        self.toolbar = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self.toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        btn_kwargs = dict(
            fg_color=ThemeManager.get("btn_secondary"),
            hover_color=ThemeManager.get("btn_secondary_hover"),
            text_color=ThemeManager.get("text_primary")
        )
        self.btn_bold = ctk.CTkButton(
            self.toolbar,
            text="B",
            width=38,
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.apply_text_style("bold"),
            **btn_kwargs
        )
        self.btn_bold.pack(side="left", padx=(20, 3))

        self.btn_italic = ctk.CTkButton(
            self.toolbar,
            text="I",
            width=38,
            font=ctk.CTkFont(slant="italic"),
            command=lambda: self.apply_text_style("italic"),
            **btn_kwargs
        )
        self.btn_italic.pack(side="left", padx=3)

        self.btn_underline = ctk.CTkButton(
            self.toolbar,
            text="U",
            width=38,
            font=ctk.CTkFont(underline=True),
            command=lambda: self.apply_text_style("underline"),
            **btn_kwargs
        )
        self.btn_underline.pack(side="left", padx=3)

        self.format_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.format_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.format_bar.grid_columnconfigure(7, weight=0)
        self.format_bar.grid_columnconfigure(8, weight=1) # Empty space to absorb width

        menu_kwargs = dict(
            fg_color=ThemeManager.get("btn_secondary"),
            button_color=ThemeManager.get("btn_secondary"),
            button_hover_color=ThemeManager.get("btn_secondary_hover"),
            text_color=ThemeManager.get("text_primary"),
            dropdown_fg_color=ThemeManager.get("popup_bg"),
            dropdown_text_color=ThemeManager.get("text_primary"),
            dropdown_hover_color=ThemeManager.get("btn_secondary_hover")
        )

        ctk.CTkLabel(self.format_bar, text="Font", text_color=ThemeManager.get("text_primary")).grid(row=0, column=0, padx=(0, 6), sticky="w")
        self.font_family_menu = ctk.CTkOptionMenu(
            self.format_bar,
            values=["Arial", "Helvetica", "Times New Roman", "Georgia", "Verdana", "Courier New"],
            width=140,
            command=self.apply_font_family,
            **menu_kwargs
        )
        self.font_family_menu.set("Arial")
        self.font_family_menu.grid(row=0, column=1, padx=(0, 10), sticky="w")

        ctk.CTkLabel(self.format_bar, text="Size", text_color=ThemeManager.get("text_primary")).grid(row=0, column=2, padx=(0, 6), sticky="w")
        self.font_size_menu = ctk.CTkOptionMenu(
            self.format_bar,
            values=["10", "11", "12", "14", "16", "18", "20", "24", "28", "32"],
            width=72,
            command=self.apply_font_size,
            **menu_kwargs
        )
        self.font_size_menu.set("15")
        self.font_size_menu.grid(row=0, column=3, padx=(0, 10), sticky="w")

        ctk.CTkButton(self.format_bar, text="Màu chữ", width=88, command=self.pick_text_color, **btn_kwargs).grid(row=0, column=4, padx=(0, 8), sticky="w")
        ctk.CTkButton(self.format_bar, text="Highlight", width=90, command=self.pick_highlight_color, **btn_kwargs).grid(row=0, column=5, padx=(0, 8), sticky="w")

        ctk.CTkLabel(self.format_bar, text="Zoom", text_color=ThemeManager.get("text_primary")).grid(row=0, column=6, padx=(0, 6), sticky="w")
        self.document_zoom_slider = ctk.CTkSlider(self.format_bar, from_=50, to=200, number_of_steps=30, width=130)
        self.document_zoom_slider.set(100)
        self.document_zoom_slider.grid(row=0, column=7, padx=(0, 8), sticky="w")
        self.document_zoom_slider.bind("<ButtonRelease-1>", self.on_zoom_release)
        # Fix 7: Keyboard zoom support — also call on_zoom_release via a command
        self.document_zoom_slider.configure(command=lambda value: self.on_zoom_release(None))

        # Tiêu đề
        self.entry_title = ctk.CTkEntry(
            self,
            placeholder_text="Nhập tiêu đề...",
            font=ctk.CTkFont(size=24, weight="bold"),
            border_width=0,
            fg_color="transparent",
            text_color=ThemeManager.get("text_primary")
        )
        self.entry_title.grid(row=2, column=0, columnspan=2, pady=(0, 10), sticky="ew")

        # Khung chứa nội dung động (swap giữa Textbox và Checklist)
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_propagate(False)

        # 1. UI cho Text Note
        self._create_textbox_widget()

        # 2. UI cho Checklist Note - GIỮ NGUYÊN các ô checkbox như bản cũ
        self.checklist_frame = ctk.CTkScrollableFrame(self.content_container, fg_color=ThemeManager.get("cell_bg"))

        # Metadata: reminder/deadline
        self.meta_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.meta_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.meta_frame.grid_columnconfigure(0, weight=1) # Spacer column to push everything right

        entry_kwargs = dict(
            fg_color=ThemeManager.get("cell_bg"),
            text_color=ThemeManager.get("text_primary"),
            border_color=ThemeManager.get("grid_border"),
            border_width=3
        )

        ctk.CTkLabel(self.meta_frame, text="🔔 Nhắc lúc", text_color=ThemeManager.get("text_primary")).grid(row=0, column=1, padx=(0, 8), sticky="e")
        self.entry_reminder = ctk.CTkEntry(self.meta_frame, placeholder_text=self._reminder_placeholder, width=140, **entry_kwargs)
        self.entry_reminder.grid(row=0, column=2, padx=(0, 5), sticky="e")
        ctk.CTkButton(self.meta_frame, text="📅", width=34, command=lambda: self.open_datetime_picker(self.entry_reminder, "Chọn thời gian nhắc"), **btn_kwargs).grid(row=0, column=3, padx=(0, 15), sticky="e")

        ctk.CTkLabel(self.meta_frame, text="📌 Deadline", text_color=ThemeManager.get("text_primary")).grid(row=0, column=4, padx=(0, 8), sticky="e")
        self.entry_deadline = ctk.CTkEntry(self.meta_frame, placeholder_text=self._deadline_placeholder, width=140, **entry_kwargs)
        self.entry_deadline.grid(row=0, column=5, padx=(0, 5), sticky="e")
        ctk.CTkButton(self.meta_frame, text="📅", width=34, command=lambda: self.open_datetime_picker(self.entry_deadline, "Chọn deadline"), **btn_kwargs).grid(row=0, column=6, padx=(0, 0), sticky="e")
        self.meta_frame.grid_columnconfigure((1, 6), weight=0)

        # Khung thêm item cho Checklist
        self.add_item_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.new_item_entry = ctk.CTkEntry(self.add_item_frame, placeholder_text="Thêm công việc mới...", **entry_kwargs)
        self.new_item_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(self.add_item_frame, text="Thêm", width=80, command=self.add_checklist_item, fg_color=ThemeManager.get("accent_primary"), hover_color=ThemeManager.get("accent_primary_hover"), text_color=ThemeManager.get("text_on_accent")).pack(side="right")
        self.new_item_entry.bind("<Return>", lambda event: self._add_checklist_item_from_enter(event))

    def _create_textbox_widget(self):
        self.textbox_content = ctk.CTkTextbox(
            self.content_container,
            font=ctk.CTkFont(size=15),
            wrap="word",
            undo=True,
            autoseparators=True,
            maxundo=-1,
            fg_color=ThemeManager.get("cell_bg"),
            text_color=ThemeManager.get("text_primary"),
            border_color=ThemeManager.get("grid_border"),
            border_width=3
        )
        self.textbox_content.configure(height=self._editor_default_height)
        self._configure_text_tags()
        self.textbox_content.bind("<Control-b>", lambda event=None: self._shortcut_format(event, "bold"))
        self.textbox_content.bind("<Control-i>", lambda event=None: self._shortcut_format(event, "italic"))
        self.textbox_content.bind("<Control-u>", lambda event=None: self._shortcut_format(event, "underline"))
        self.textbox_content.bind("<Control-z>", lambda event=None: self.undo_text())
        self.textbox_content.bind("<Control-y>", lambda event=None: self.redo_text())
        self.textbox_content.bind("<Command-z>", lambda event=None: self.undo_text())
        self.textbox_content.bind("<Command-Shift-z>", lambda event=None: self.redo_text())
        self._text_widget().bind("<Control-b>", lambda event=None: self._shortcut_format(event, "bold"))
        self._text_widget().bind("<Control-i>", lambda event=None: self._shortcut_format(event, "italic"))
        self._text_widget().bind("<Control-u>", lambda event=None: self._shortcut_format(event, "underline"))
        self._text_widget().bind("<Control-z>", lambda event=None: self.undo_text())
        self._text_widget().bind("<Control-y>", lambda event=None: self.redo_text())
        self._text_widget().bind("<Command-z>", lambda event=None: self.undo_text())
        self._text_widget().bind("<Command-Shift-z>", lambda event=None: self.redo_text())

        # Fix 5: Update toolbar state on cursor movement / selection change
        widget = self._text_widget()
        widget.bind("<<Selection>>", self._on_cursor_moved)
        widget.bind("<KeyRelease>", self._on_cursor_moved)
        widget.bind("<ButtonRelease-1>", self._on_cursor_moved)

    # =========================
    # Fix 5: Cursor tracking for toolbar state
    # =========================
    def _on_cursor_moved(self, event=None):
        """Update toolbar controls to reflect the style at the current cursor position."""
        if self.current_note_type != "Text":
            return
        try:
            widget = self._text_widget()
            cursor = widget.index("insert")
            style = self._style_at_index(cursor)

            # Update font family menu
            family = style.get("family", "Arial")
            if family != self.font_family_menu.get():
                self.font_family_menu.set(family)

            # Update font size menu
            size = str(style.get("size", 15))
            if size != self.font_size_menu.get():
                self.font_size_menu.set(size)
        except Exception:
            pass

    # =========================
    # Rich text cơ bản B/I
    # =========================
    def _text_widget(self):
        """Lấy widget Text thật bên trong CTkTextbox để dùng tag bôi đậm/in nghiêng."""
        return getattr(self.textbox_content, "_textbox", self.textbox_content)

    def _configure_text_tags(self):
        self._base_style = {
            "family": self.font_family_menu.get() if hasattr(self, "font_family_menu") else "Arial",
            "size": int(self.font_size_menu.get()) if hasattr(self, "font_size_menu") else 15,
            "bold": False,
            "italic": False,
            "underline": False,
            "foreground": "",
            "highlight": ""
        }
        zoom_mult = getattr(self, "zoom_factor", 1.0)
        self._text_font = tkfont.Font(
            family=self._base_style["family"],
            size=int(self._base_style["size"] * zoom_mult),
        )
        widget = self._text_widget()
        widget.configure(font=self._text_font)
        # Don't set foreground="white" on sel — that would mask any color/highlight
        # applied to selected text. Only set background so the selection is visible.
        widget.tag_configure("sel", background="#2563eb")
        # Don't tag_raise("sel") above fmt| tags — let fmt| tags keep their
        # foreground colors even when selected. The selection background alone
        # is sufficient visual feedback.

    def _default_style(self):
        return dict(self._base_style)

    def _normalize_style(self, style):
        normalized = self._default_style()
        normalized.update(style or {})
        normalized["family"] = str(normalized.get("family") or "Arial")
        normalized["size"] = max(8, int(normalized.get("size") or 15))
        normalized["bold"] = bool(normalized.get("bold"))
        normalized["italic"] = bool(normalized.get("italic"))
        normalized["underline"] = bool(normalized.get("underline"))
        normalized["foreground"] = str(normalized.get("foreground") or "")
        normalized["highlight"] = str(normalized.get("highlight") or "")
        return normalized

    def _sanitize_tag_part(self, value):
        """Sanitize a tag name component by replacing dangerous characters."""
        return str(value).replace("|", "_").replace(" ", "_").replace("\n", "_")

    def _style_tag_name(self, style):
        style = self._normalize_style(style)
        family = self._sanitize_tag_part(style["family"])
        foreground = self._sanitize_tag_part(style["foreground"] or "none")
        highlight = self._sanitize_tag_part(style["highlight"] or "none")
        return f"fmt|{family}|{style['size']}|{int(style['bold'])}|{int(style['italic'])}|{int(style['underline'])}|{foreground}|{highlight}"

    def _style_from_tag_name(self, tag_name):
        if not tag_name.startswith("fmt|"):
            return None
        parts = tag_name.split("|", 7)
        if len(parts) != 8:
            return None
        _, family, size, bold, italic, underline, foreground, highlight = parts
        return {
            "family": family.replace("_", " "),
            "size": int(size),
            "bold": bool(int(bold)),
            "italic": bool(int(italic)),
            "underline": bool(int(underline)),
            "foreground": "" if foreground == "none" else foreground,
            "highlight": "" if highlight == "none" else highlight,
        }

    def _ensure_style_tag(self, tag_name, style):
        widget = self._text_widget()
        normalized = self._normalize_style(style)
        zoom_mult = getattr(self, "zoom_factor", 1.0)

        if tag_name in self._font_cache_initialized:
            # Tag already has a Font; just reconfigure if zoom changed
            font = self._font_cache.get(tag_name)
            if font:
                new_size = int(normalized["size"] * zoom_mult)
                font.configure(size=new_size)
            return

        font = tkfont.Font(
            family=normalized["family"],
            size=int(normalized["size"] * zoom_mult),
            weight="bold" if normalized["bold"] else "normal",
            slant="italic" if normalized["italic"] else "roman",
            underline=normalized["underline"]
        )
        kwargs = {"font": font}
        if normalized["foreground"]:
            kwargs["foreground"] = normalized["foreground"]
        if normalized["highlight"]:
            kwargs["background"] = normalized["highlight"]
        self._font_cache[tag_name] = font
        self._font_cache_initialized.add(tag_name)
        widget.tag_configure(tag_name, **kwargs)

    def _style_at_index(self, index):
        widget = self._text_widget()
        # tag_names(index) returns tags lowest-priority first, but we want the
        # visually-active (highest-priority) fmt tag — so iterate in reverse.
        all_tags = widget.tag_names(index)
        for tag_name in reversed(all_tags):
            style = self._style_from_tag_name(tag_name)
            if style is not None:
                return style
        return self._default_style()

    def _apply_style_tag_to_range(self, start, end, style):
        widget = self._text_widget()
        style = self._normalize_style(style)
        tag_name = self._style_tag_name(style)
        self._ensure_style_tag(tag_name, style)
        widget.tag_add(tag_name, start, end)

    def _remove_style_tags(self, start, end):
        widget = self._text_widget()
        for tag_name in widget.tag_names():
            if tag_name.startswith("fmt|"):
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

    def _apply_style_updates(self, start, end, updates):
        """Apply style updates by batching contiguous runs with the same resulting style."""
        widget = self._text_widget()
        # First pass: determine the target style for each character position
        index = start
        runs = []  # list of (run_start, run_end, target_style)
        while widget.compare(index, "<", end):
            style = self._normalize_style(self._style_at_index(index))
            style.update(updates)
            target_tag = self._style_tag_name(style)
            run_start = index
            # Advance while the target style stays the same
            while widget.compare(index, "<", end):
                next_style = self._normalize_style(self._style_at_index(index))
                next_style.update(updates)
                if self._style_tag_name(next_style) != target_tag:
                    break
                index = widget.index(f"{index}+1c")
            run_end = index
            runs.append((run_start, run_end, style))

        # Second pass: apply each run as a single tag_add
        for run_start, run_end, style in runs:
            self._remove_style_tags(run_start, run_end)
            self._apply_style_tag_to_range(run_start, run_end, style)

        # Push an undo separator so formatting changes are undoable
        try:
            widget.edit_separator()
        except Exception:
            pass

        widget.tag_raise("sel")

    def apply_text_style(self, style_name):
        if self.current_note_type != "Text":
            return

        start, end = self._get_selected_or_current_word_range()
        if not start or not end:
            return

        should_enable = False
        for char_start, _ in self._iterate_char_ranges(start, end):
            style = self._style_at_index(char_start)
            has_style = style.get(style_name, False)
            if not has_style:
                should_enable = True
                break

        self._apply_style_updates(start, end, {style_name: should_enable})
        self._text_widget().tag_remove("sel", "1.0", "end")
        self._text_widget().focus_set()

    def apply_font_family(self, family_name):
        if self.current_note_type != "Text":
            return
        start, end = self._get_selected_or_current_word_range()
        if start and end:
            self._apply_style_updates(start, end, {"family": family_name})
            # Fix 6: Clear selection highlight and refocus after font change
            self._text_widget().tag_remove("sel", "1.0", "end")
            self._text_widget().focus_set()

    def apply_font_size(self, size_value):
        if self.current_note_type != "Text":
            return
        start, end = self._get_selected_or_current_word_range()
        if start and end:
            self._apply_style_updates(start, end, {"size": int(size_value)})
            # Fix 6: Clear selection highlight and refocus after size change
            self._text_widget().tag_remove("sel", "1.0", "end")
            self._text_widget().focus_set()

    def pick_text_color(self):
        if self.current_note_type != "Text":
            return
        start, end = self._get_selected_or_current_word_range()
        if not start or not end:
            return
        from ui.color_picker import CTkColorPicker
        picker = CTkColorPicker(
            self,
            initial_color="#000000" if ctk.get_appearance_mode() == "Light" else "#ffffff",
            title="Chọn màu chữ",
        )
        self.wait_window(picker)
        color = picker.result
        if not color:
            return
        self._apply_style_updates(start, end, {"foreground": color})
        self._text_widget().tag_remove("sel", "1.0", "end")
        self._text_widget().focus_set()

    def pick_highlight_color(self):
        if self.current_note_type != "Text":
            return
        start, end = self._get_selected_or_current_word_range()
        if not start or not end:
            return
        from ui.color_picker import CTkColorPicker
        picker = CTkColorPicker(
            self,
            initial_color="#fcc419",
            title="Chọn màu highlight",
        )
        self.wait_window(picker)
        color = picker.result
        if not color:
            return
        self._apply_style_updates(start, end, {"highlight": color})
        self._text_widget().tag_remove("sel", "1.0", "end")
        self._text_widget().focus_set()

    def on_zoom_release(self, event):
        value = self.document_zoom_slider.get()
        self.zoom_factor = float(value) / 100.0

        widget = self._text_widget()
        cursor_pos = widget.index("insert")
        yview = widget.yview()

        # 1. Update base font size
        new_base_size = int(self._base_style["size"] * self.zoom_factor)
        self._text_font.configure(size=new_base_size)

        # 2. Update all fonts in self._font_cache
        for tag_name, font in list(self._font_cache.items()):
            style = self._style_from_tag_name(tag_name)
            if style:
                new_size = int(style["size"] * self.zoom_factor)
                font.configure(size=new_size)

        # Force a layout pass so scroll coordinates recalculate
        self.update_idletasks()

        # Restore position
        try:
            widget.mark_set("insert", cursor_pos)
            widget.yview_moveto(yview[0])
            widget.see("insert")
        except Exception:
            pass

    def _insert_segment_with_style(self, text, style):
        if not text:
            return
        widget = self._text_widget()
        start = widget.index("insert")
        widget.insert("insert", text)
        end = widget.index("insert")
        if isinstance(style, tuple):
            style = self._normalize_style({
                "bold": style[0] if len(style) > 0 else False,
                "italic": style[1] if len(style) > 1 else False,
            })
        self._apply_style_tag_to_range(start, end, style)

    def _clear_font_cache(self):
        """Destroy all cached Font objects and clear the cache (Fix 3)."""
        for font in self._font_cache.values():
            try:
                font.destroy()
            except Exception:
                pass
        self._font_cache.clear()
        self._font_cache_initialized.clear()

    def _render_content(self, content):
        widget = self._text_widget()

        # Fix 3: Clean up old font handles before rendering new content
        self._clear_font_cache()

        widget.delete("1.0", "end")
        self._remove_style_tags("1.0", "end")

        if isinstance(content, dict) and "text" in content:
            text = str(content.get("text", ""))
            widget.insert("1.0", text)
            for span in content.get("spans", []):
                try:
                    start = f"1.0+{int(span.get('start', 0))}c"
                    end = f"1.0+{int(span.get('end', 0))}c"
                    self._apply_style_tag_to_range(start, end, span.get("style", {}))
                except (TypeError, ValueError):
                    continue
            try:
                widget.edit_reset()
            except Exception:
                pass
            widget.tag_raise("sel")
            return

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
        try:
            widget.edit_reset()
        except Exception:
            pass
        widget.tag_raise("sel")

    def _serialize_content(self):
        widget = self._text_widget()
        text = widget.get("1.0", "end-1c")
        if not text:
            return {"text": "", "spans": []}

        spans = []
        current_style = self._normalize_style(self._style_at_index("1.0"))
        span_start = 0

        for index, _char in enumerate(text):
            style = self._normalize_style(self._style_at_index(f"1.0+{index}c"))
            if style != current_style:
                spans.append({"start": span_start, "end": index, "style": current_style})
                span_start = index
                current_style = style

        spans.append({"start": span_start, "end": len(text), "style": current_style})
        return {"text": text, "spans": spans}

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
            self.add_item_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 10))
            self.btn_bold.configure(state="disabled")
            self.btn_italic.configure(state="disabled")
            self.font_family_menu.configure(state="disabled")
            self.font_size_menu.configure(state="disabled")
            self.document_zoom_slider.configure(state="disabled")
        else:  # Text Note
            self.textbox_content.grid(row=0, column=0, sticky="nsew")
            self.btn_bold.configure(state="normal")
            self.btn_italic.configure(state="normal")
            self.font_family_menu.configure(state="normal")
            self.font_size_menu.configure(state="normal")
            self.document_zoom_slider.configure(state="normal")

    def _add_checklist_item_from_enter(self, event):
        self.add_checklist_item()
        return "break"

    def undo_text(self):
        if self.current_note_type != "Text":
            return "break"
        try:
            self._text_widget().edit_undo()
        except tk.TclError:
            pass
        return "break"

    def redo_text(self):
        if self.current_note_type != "Text":
            return "break"
        try:
            self._text_widget().edit_redo()
        except tk.TclError:
            pass
        return "break"

    def add_checklist_item(self, text="", is_done=False):
        """Thêm một dòng checkbox vào khung Checklist - khôi phục đúng kiểu bản noteapp-oop gốc."""
        if not text:
            text = self.new_item_entry.get().strip()
            self.new_item_entry.delete(0, 'end')

        if not text:
            return

        var = ctk.BooleanVar(value=is_done)
        cb = ctk.CTkCheckBox(self.checklist_frame, text=text, variable=var, fg_color=ThemeManager.get("accent_primary"), text_color=ThemeManager.get("text_primary"))
        cb.pack(anchor="w", pady=5, padx=10)
        self.checklist_vars.append({"checkbox": cb, "var": var})

    def clear_checklist_items(self):
        """Xóa các checkbox cũ giống cơ chế của bản noteapp-oop gốc."""
        for item in self.checklist_vars:
            item["checkbox"].destroy()
        self.checklist_vars.clear()



    def _format_datetime_for_entry(self, value):
        if not value:
            return ""
        try:
            dt = datetime.fromisoformat(str(value))
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return str(value)

    def _parse_datetime_value(self, value):
        value = (value or "").strip()
        if not value:
            return None
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                pass
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _set_datetime_entry(self, entry, value):
        entry.delete(0, "end")
        entry.insert(0, value)

    def open_datetime_picker(self, target_entry, title):
        initial_dt = self._parse_datetime_value(target_entry.get()) or datetime.now().replace(second=0, microsecond=0)

        def on_date_selected(selected_str):
            self._set_datetime_entry(target_entry, selected_str)
            if hasattr(target_entry, '_activate_placeholder') and not selected_str:
                target_entry._activate_placeholder()

        CTkDatePicker(
            self,
            initial_dt=initial_dt,
            title=title,
            on_select=on_date_selected
        )

    def prepare_new(self, note_type):
        self.current_note = None
        self.set_data("", "", note_type, reminder_at=None, deadline_at=None, is_locked=False)

    def set_data(self, title, content_data, note_type, reminder_at=None, deadline_at=None, is_locked=False):
        self.setup_ui_mode(note_type)
        self.entry_title.delete(0, 'end')
        if title:
            self.entry_title.insert(0, title)
        else:
            if hasattr(self.entry_title, '_activate_placeholder'):
                self.entry_title._activate_placeholder()

        self.entry_reminder.delete(0, 'end')
        val_reminder = self._format_datetime_for_entry(reminder_at)
        if val_reminder:
            self.entry_reminder.insert(0, val_reminder)
        elif hasattr(self.entry_reminder, '_activate_placeholder'):
            self.entry_reminder._activate_placeholder()

        self.entry_deadline.delete(0, 'end')
        val_deadline = self._format_datetime_for_entry(deadline_at)
        if val_deadline:
            self.entry_deadline.insert(0, val_deadline)
        elif hasattr(self.entry_deadline, '_activate_placeholder'):
            self.entry_deadline._activate_placeholder()
        self.textbox_content.configure(height=self._editor_default_height)

        if note_type == "Checklist":
            self.clear_checklist_items()

            # Khởi tạo lại danh sách checkbox từ dữ liệu cũ: list[dict] hoặc list[TodoItem]
            if isinstance(content_data, list):
                for item in content_data:
                    text = item.get("content") if isinstance(item, dict) else getattr(item, 'content', str(item))
                    done = item.get("is_done") if isinstance(item, dict) else getattr(item, 'is_done', False)
                    self.add_checklist_item(text, done)
            
            # Focus on the new item entry instead of the title to show the title's placeholder
            self.new_item_entry.focus_set()
        else:
            self._render_content(content_data)
            # Focus on the textbox instead of the title to show the title's placeholder
            self.textbox_content.focus_set()

        if note_type == "Text":
            try:
                self._text_widget().edit_reset()
            except Exception:
                pass

    def _is_placeholder(self, entry, placeholder_text):
        """Check if an entry currently shows its placeholder text (Fix 8)."""
        value = entry.get().strip()
        if not value:
            return True
        if value == placeholder_text:
            return True
        return False

    def get_data(self):
        title = self.entry_title.get().strip()
        if self.current_note_type == "Checklist":
            content = [
                {"content": item["checkbox"].cget("text"), "is_done": item["var"].get()}
                for item in self.checklist_vars
            ]
        else:
            content = self._serialize_content()

        # Fix 8: Guard against placeholder text leaking into saved data
        reminder_raw = self.entry_reminder.get().strip()
        if self._is_placeholder(self.entry_reminder, self._reminder_placeholder):
            reminder_raw = ""

        deadline_raw = self.entry_deadline.get().strip()
        if self._is_placeholder(self.entry_deadline, self._deadline_placeholder):
            deadline_raw = ""

        return {
            "title": title,
            "content": content,
            "reminder_at": reminder_raw,
            "deadline_at": deadline_raw
        }