import re
import tkinter as tk
import tkinter.font as tkfont
import uuid
from collections import OrderedDict
from urllib.parse import quote, unquote

import customtkinter as ctk
from tkinter import ttk, messagebox, colorchooser, filedialog
from PIL import Image, UnidentifiedImageError
from datetime import datetime
from ui.date_picker import CTkDatePicker
from ui.color_picker import CTkColorPicker
from services.media_service import MediaService
from services.theme_service import ThemeManager
from services.translation_service import TranslationService

class EditorFrame(ctk.CTkFrame):
    _thumbnail_cache = OrderedDict()
    _thumbnail_cache_limit = 32

    def __init__(
        self,
        master
    ):
        # Anchor the component into a unified obsidian foundation frame
        super().__init__(master, fg_color=ThemeManager.get("popup_bg"))
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_propagate(False)

        self.current_note_type = "Text"
        self.checklist_vars = []
        self._editor_default_height = 420
        self._font_cache = {}
        self._font_base_sizes = {}
        self._font_cache_initialized = set()
        self._zoom_after_id = None
        self._zoom_restore_after_id = None
        self._pending_zoom_value = 100.0
        self.default_font_family = self._customtkinter_default_font_family()
        self.available_font_families = self._available_font_families()
        self.zoom_factor = 1.0
        self._content_search_matches = []
        self._content_search_index = -1
        self.media_service = MediaService()
        self._media_attachments = []
        self._media_widgets = {}
        self._media_image_refs = {}

        self._reminder_placeholder = TranslationService.get("editor.reminder_placeholder")
        self._deadline_placeholder = TranslationService.get("editor.deadline_placeholder")

        # --- Toolbar Section ---
        # Breathing room top padding layout shift to naturally guide focus downward
        self.toolbar = ctk.CTkFrame(self, fg_color="transparent", height=45)
        self.toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(25, 10))

        # Tactile actions setup with refined geometric formatting properties
        btn_kwargs = dict(
            fg_color=ThemeManager.get("btn_note"),
            hover_color=ThemeManager.get("btn_note_hover"),
            text_color=ThemeManager.get("text_primary"),
            border_color=ThemeManager.get("grid_border"),
            border_width=1,
            corner_radius=6
        )
        
        self.btn_bold = ctk.CTkButton(
            self.toolbar, text="B", width=38, height=32,
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.apply_text_style("bold"), **btn_kwargs
        )
        self.btn_bold.pack(side="left", padx=(20, 3))

        self.btn_italic = ctk.CTkButton(
            self.toolbar, text="I", width=38, height=32,
            font=ctk.CTkFont(slant="italic"),
            command=lambda: self.apply_text_style("italic"), **btn_kwargs
        )
        self.btn_italic.pack(side="left", padx=3)

        self.btn_underline = ctk.CTkButton(
            self.toolbar, text="U", width=38, height=32,
            font=ctk.CTkFont(underline=True),
            command=lambda: self.apply_text_style("underline"), **btn_kwargs
        )
        self.btn_underline.pack(side="left", padx=3)

        self.btn_media = ctk.CTkButton(
            self.toolbar,
            text="＋ " + TranslationService.get("editor.insert_media"),
            width=110, height=32,
            command=self.insert_media,
            **btn_kwargs
        )
        self.btn_media.pack(side="left", padx=(8, 3))

        # Content Search bar framed beautifully using card design elements
        self.content_search_entry = ctk.CTkEntry(
            self.toolbar,
            placeholder_text=TranslationService.get("editor.content_search_placeholder"),
            width=320,
            height=32,
            fg_color=ThemeManager.get("cell_bg"),
            text_color=ThemeManager.get("text_primary"),
            border_color=ThemeManager.get("grid_border"),
            border_width=1,
            corner_radius=6
        )
        self.content_search_entry.pack(side="left", padx=(16, 5))
        self.content_search_entry.bind("<KeyRelease>", self.search_current_note)
        self.content_search_entry.bind("<Escape>", self.clear_content_search)

        self.btn_search_previous = ctk.CTkButton(
            self.toolbar, text="‹", width=32, height=32,
            command=lambda: self.navigate_content_search(-1), **btn_kwargs
        )
        self.btn_search_previous.pack(side="left", padx=(0, 3))

        self.btn_search_next = ctk.CTkButton(
            self.toolbar, text="›", width=32, height=32,
            command=lambda: self.navigate_content_search(1), **btn_kwargs
        )
        self.btn_search_next.pack(side="left", padx=(0, 5))

        self.content_search_status = ctk.CTkLabel(
            self.toolbar, text="", width=48,
            text_color=ThemeManager.get("text_secondary"),
            font=ctk.CTkFont(size=12)
        )
        self.content_search_status.pack(side="left")

        # --- Format Bar Section ---
        self.format_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.format_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15), padx=20)
        self.format_bar.grid_columnconfigure(7, weight=0)
        self.format_bar.grid_columnconfigure(8, weight=1)

        menu_kwargs = dict(
            fg_color=ThemeManager.get("cell_bg"),
            button_color=ThemeManager.get("btn_note"),
            button_hover_color=ThemeManager.get("btn_note_hover"),
            text_color=ThemeManager.get("text_primary"),
            dropdown_fg_color=ThemeManager.get("popup_bg"),
            dropdown_text_color=ThemeManager.get("text_primary"),
            dropdown_hover_color=ThemeManager.get("btn_note_hover"),
            corner_radius=6
        )

        ctk.CTkLabel(
            self.format_bar, 
            text=TranslationService.get("editor.font").upper(), 
            text_color=ThemeManager.get("text_primary"),
            font=ctk.CTkFont(size=11, weight="bold")
        ).grid(row=0, column=0, padx=(0, 6), sticky="w")
        
        self.font_family_menu = ctk.CTkOptionMenu(
            self.format_bar, values=self.available_font_families,
            width=140, height=30, command=self.apply_font_family, **menu_kwargs
        )
        self.font_family_menu.set(self.default_font_family)
        self.font_family_menu.grid(row=0, column=1, padx=(0, 15), sticky="w")

        ctk.CTkLabel(
            self.format_bar, 
            text=TranslationService.get("editor.size").upper(), 
            text_color=ThemeManager.get("text_primary"),
            font=ctk.CTkFont(size=11, weight="bold")
        ).grid(row=0, column=2, padx=(0, 6), sticky="w")
        
        self.font_size_menu = ctk.CTkOptionMenu(
            self.format_bar, values=["10", "11", "12", "14", "15", "16", "18", "20", "24", "28", "32"],
            width=72, height=30, command=self.apply_font_size, **menu_kwargs
        )
        self.font_size_menu.set("15")
        self.font_size_menu.grid(row=0, column=3, padx=(0, 15), sticky="w")

        # Re-introducing tactical border items explicitly for the buttons where they are native
        btn_format_kwargs = btn_kwargs.copy()
        
        ctk.CTkButton(self.format_bar, text=TranslationService.get("editor.text_color"), width=90, height=30, command=self.pick_text_color, **btn_format_kwargs).grid(row=0, column=4, padx=(0, 8), sticky="w")
        ctk.CTkButton(self.format_bar, text=TranslationService.get("editor.highlight"), width=90, height=30, command=self.pick_highlight_color, **btn_format_kwargs).grid(row=0, column=5, padx=(0, 15), sticky="w")

        ctk.CTkLabel(
            self.format_bar, 
            text=TranslationService.get("editor.zoom").upper(), 
            text_color=ThemeManager.get("text_primary"),
            font=ctk.CTkFont(size=11, weight="bold")
        ).grid(row=0, column=6, padx=(0, 6), sticky="w")
        
        self.document_zoom_slider = ctk.CTkSlider(
            self.format_bar, from_=50, to=200, number_of_steps=30, width=130,
            button_color=ThemeManager.get("btn_note_hover"),
            button_hover_color=ThemeManager.get("accent_primary")
        )
        self.document_zoom_slider.set(100)
        self.document_zoom_slider.grid(row=0, column=7, padx=(0, 8), sticky="w")
        self.document_zoom_slider.bind("<ButtonRelease-1>", self.on_zoom_release)
        self.document_zoom_slider.configure(command=self._queue_zoom)

        # --- Primary Title Header ---
        self.entry_title = ctk.CTkEntry(
            self, placeholder_text=TranslationService.get("editor.title_placeholder"),
            font=ctk.CTkFont(size=24, weight="bold"),
            border_width=0, fg_color="transparent",
            text_color=ThemeManager.get("text_primary")
        )
        self.entry_title.grid(row=2, column=0, columnspan=2, pady=(0, 15), padx=20, sticky="ew")

        # --- Content Box Layer (Dedicated Card Structs) ---
        self.content_container = ctk.CTkFrame(
            self, 
            fg_color=ThemeManager.get("cell_bg"),
            border_color=ThemeManager.get("grid_border"),
            border_width=1,
            corner_radius=8
        )
        self.content_container.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, 15), padx=20)
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_propagate(False)

        self._create_textbox_widget()
        self.checklist_frame = ctk.CTkScrollableFrame(
            self.content_container, 
            fg_color="transparent"
        )

        # --- Metadata & Micro-Dressing Tags Bar ---
        self.meta_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.meta_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 10), padx=20)
        self.meta_frame.grid_columnconfigure(0, weight=1)

        entry_kwargs = dict(
            fg_color=ThemeManager.get("cell_bg"),
            text_color=ThemeManager.get("text_primary"),
            border_color=ThemeManager.get("grid_border"),
            border_width=1,
            corner_radius=6
        )

        ctk.CTkLabel(
            self.meta_frame, 
            text=TranslationService.get("editor.reminder_label").upper(), 
            text_color=ThemeManager.get("text_secondary"),
            font=ctk.CTkFont(size=11, weight="bold")
        ).grid(row=0, column=1, padx=(0, 8), sticky="e")
        
        self.entry_reminder = ctk.CTkEntry(self.meta_frame, placeholder_text=self._reminder_placeholder, width=140, height=30, **entry_kwargs)
        self.entry_reminder.grid(row=0, column=2, padx=(0, 5), sticky="e")
        
        # Meta Indicators aligned cleanly at the absolute tail-end with minimal shapes
        ctk.CTkButton(self.meta_frame, text="📅", width=34, height=30, command=lambda: self.open_datetime_picker(self.entry_reminder, TranslationService.get("editor.date_picker_reminder")), **btn_kwargs).grid(row=0, column=3, padx=(0, 15), sticky="e")

        ctk.CTkLabel(
            self.meta_frame, 
            text=TranslationService.get("editor.deadline_label").upper(), 
            text_color=ThemeManager.get("text_secondary"),
            font=ctk.CTkFont(size=11, weight="bold")
        ).grid(row=0, column=4, padx=(0, 8), sticky="e")
        
        self.entry_deadline = ctk.CTkEntry(self.meta_frame, placeholder_text=self._deadline_placeholder, width=140, height=30, **entry_kwargs)
        self.entry_deadline.grid(row=0, column=5, padx=(0, 5), sticky="e")
        
        # Deadline calendar action button
        ctk.CTkButton(self.meta_frame, text="📅", width=34, height=30, command=lambda: self.open_datetime_picker(self.entry_deadline, TranslationService.get("editor.date_picker_deadline")), **btn_kwargs).grid(row=0, column=6, padx=(0, 0), sticky="e")
        self.meta_frame.grid_columnconfigure((1, 6), weight=0)

        # --- Checklist Add-Item Interface ---
        self.add_item_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.new_item_entry = ctk.CTkEntry(self.add_item_frame, placeholder_text=TranslationService.get("editor.checklist_placeholder"), height=32, **entry_kwargs)
        self.new_item_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ctk.CTkButton(
            self.add_item_frame, text="＋ " + TranslationService.get("editor.checklist_add"), 
            width=90, height=32, command=self.add_checklist_item,
            fg_color=ThemeManager.get("accent_primary"),
            hover_color=ThemeManager.get("accent_primary_hover"),
            text_color=ThemeManager.get("text_on_accent"),
            corner_radius=6
        ).pack(side="right")
        self.new_item_entry.bind("<Return>", lambda event: self._add_checklist_item_from_enter(event))

    @staticmethod
    def _tk_theme_color(key):
        value = ThemeManager.get(key)
        if isinstance(value, (list, tuple)):
            return value[1] if ctk.get_appearance_mode() == "Dark" else value[0]
        return value

    def _configure_search_tags(self):
        widget = self._text_widget()
        widget.tag_configure(
            "content_search_match",
            background=self._tk_theme_color("search_match_bg"),
            foreground=self._tk_theme_color("search_match_fg")
        )
        widget.tag_configure(
            "content_search_current",
            background=self._tk_theme_color("search_current_bg"),
            foreground=self._tk_theme_color("search_current_fg")
        )
        widget.tag_raise("content_search_match")
        widget.tag_raise("content_search_current")

    def apply_theme(self, previous_palette=None):
        """Apply palette changes without replacing editor state or media."""
        if previous_palette:
            ThemeManager.apply_to_widget_tree(self, previous_palette)

        widget = self._text_widget()
        widget.tag_configure("sel", background=ThemeManager.get("selection_bg"))
        self._configure_search_tags()

        for item in self.checklist_vars:
            item["search_default_text_color"] = ThemeManager.get("text_primary")
            item["search_default_border_color"] = ThemeManager.get("grid_border")

        keyword = self.content_search_entry.get().strip()
        if keyword:
            selected_index = self._content_search_index
            self.search_current_note()
            if self._content_search_matches and selected_index >= 0:
                self._content_search_index = min(selected_index, len(self._content_search_matches) - 1)
                self._activate_content_search_match()

    @classmethod
    def _cached_thumbnail(cls, path, size=(420, 260)):
        """Decode each unchanged image once and retain a small LRU cache."""
        stat = path.stat()
        resolved_path = str(path.resolve())
        key = (resolved_path, stat.st_mtime_ns, stat.st_size, tuple(size))
        cached = cls._thumbnail_cache.get(key)
        if cached is not None:
            cls._thumbnail_cache.move_to_end(key)
            return cached

        with Image.open(path) as source_image:
            preview = source_image.convert("RGBA")
            preview.thumbnail(size)

        for stale_key in list(cls._thumbnail_cache):
            if stale_key[0] == resolved_path and stale_key != key:
                del cls._thumbnail_cache[stale_key]
        cls._thumbnail_cache[key] = preview
        cls._thumbnail_cache.move_to_end(key)
        while len(cls._thumbnail_cache) > cls._thumbnail_cache_limit:
            cls._thumbnail_cache.popitem(last=False)
        return preview

    def _customtkinter_default_font_family(self):
        """Read CustomTkinter's platform default instead of hardcoding Arial."""
        font = ctk.CTkFont()
        return str(font.cget("family"))

    def _available_font_families(self):
        """Expose every font family that CTkFont can use through Tk."""
        families = {
            str(family).strip()
            for family in tkfont.families(self)
            if str(family).strip()
        }
        families.add(self.default_font_family)
        return sorted(families, key=str.casefold)

    def _create_textbox_widget(self):
        self.textbox_content = ctk.CTkTextbox(
            self.content_container,
            font=ctk.CTkFont(size=15),
            wrap="word", undo=True, autoseparators=True, maxundo=-1,
            fg_color="transparent",
            text_color=ThemeManager.get("text_primary"),
            border_width=0
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

        widget = self._text_widget()
        widget.bind("<<Selection>>", self._on_cursor_moved)
        widget.bind("<KeyRelease>", self._on_cursor_moved)
        widget.bind("<ButtonRelease-1>", self._on_cursor_moved)

        self._configure_search_tags()

    @staticmethod
    def _find_content_occurrences(content, keyword):
        if not keyword:
            return []
        return [
            (match.start(), match.end())
            for match in re.finditer(re.escape(keyword), content, re.IGNORECASE)
        ]

    def _reset_checklist_search_style(self):
        for item in self.checklist_vars:
            try:
                item["checkbox"].configure(
                    text_color=item.get("search_default_text_color", ThemeManager.get("text_primary")),
                    border_color=item.get("search_default_border_color", ThemeManager.get("text_primary"))
                )
            except tk.TclError:
                pass

    def _clear_content_search_highlights(self):
        try:
            widget = self._text_widget()
            widget.tag_remove("content_search_match", "1.0", "end")
            widget.tag_remove("content_search_current", "1.0", "end")
        except (AttributeError, tk.TclError):
            pass
        self._reset_checklist_search_style()
        self._content_search_matches = []
        self._content_search_index = -1
        self.content_search_status.configure(text="")

    def clear_content_search(self, event=None):
        self.content_search_entry.delete(0, "end")
        self._clear_content_search_highlights()
        return "break" if event is not None else None

    def search_current_note(self, event=None):
        if event is not None and event.keysym in ("Return", "KP_Enter"):
            direction = -1 if event.state & 0x0001 else 1
            self.navigate_content_search(direction)
            return "break"

        keyword = self.content_search_entry.get().strip()
        self._clear_content_search_highlights()
        if not keyword:
            return

        if self.current_note_type == "Checklist":
            for item in self.checklist_vars:
                checkbox = item["checkbox"]
                if self._find_content_occurrences(str(checkbox.cget("text")), keyword):
                    checkbox.configure(
                        text_color=ThemeManager.get("accent_primary"),
                        border_color=ThemeManager.get("accent_primary")
                    )
                    self._content_search_matches.append(item)
        else:
            widget = self._text_widget()
            content = widget.get("1.0", "end-1c")
            for start_offset, end_offset in self._find_content_occurrences(content, keyword):
                start = self._widget_index_from_plain_offset(start_offset)
                end = self._widget_index_from_plain_offset(end_offset)
                widget.tag_add("content_search_match", start, end)
                self._content_search_matches.append((start, end))
            widget.tag_raise("content_search_match")
            widget.tag_raise("content_search_current")

        if self._content_search_matches:
            self._content_search_index = 0
            self._activate_content_search_match()
        else:
            self.content_search_status.configure(text="0/0")
    ####
    def _activate_content_search_match(self):
        total = len(self._content_search_matches)
        if not total:
            self.content_search_status.configure(text="0/0")
            return

        self._content_search_index %= total
        self.content_search_status.configure(
            text=f"{self._content_search_index + 1}/{total}"
        )

        if self.current_note_type == "Checklist":
            self._reset_checklist_search_style()
            for item in self._content_search_matches:
                item["checkbox"].configure(
                    text_color=ThemeManager.get("accent_primary"),
                    border_color=ThemeManager.get("accent_primary")
                )
            current = self._content_search_matches[self._content_search_index]
            current["checkbox"].configure(
                text_color=self._tk_theme_color("search_current_fg"),
                border_color=self._tk_theme_color("search_current_bg")
            )
            return

        widget = self._text_widget()
        widget.tag_remove("content_search_current", "1.0", "end")
        start, end = self._content_search_matches[self._content_search_index]
        widget.tag_add("content_search_current", start, end)
        widget.tag_raise("content_search_current")
        widget.see(start)

    def navigate_content_search(self, direction=1):
        if not self._content_search_matches:
            self.search_current_note()
            if not self._content_search_matches:
                return
        else:
            self._content_search_index += direction
        self._activate_content_search_match()

    def _on_cursor_moved(self, event=None):
        if self.current_note_type != "Text":
            return
        try:
            widget = self._text_widget()
            cursor = widget.index("insert")
            style = self._style_at_index(cursor)
            family = style.get("family", self.default_font_family)
            if family != self.font_family_menu.get():
                self.font_family_menu.set(family)
            size = str(style.get("size", 15))
            if size != self.font_size_menu.get():
                self.font_size_menu.set(size)
        except Exception:
            pass

    def _text_widget(self):
        return getattr(self.textbox_content, "_textbox", self.textbox_content)

    def _configure_text_tags(self):
        self._base_style = {
            "family": self.font_family_menu.get() if hasattr(self, "font_family_menu") else self.default_font_family,
            "size": int(self.font_size_menu.get()) if hasattr(self, "font_size_menu") else 15,
            "bold": False, "italic": False, "underline": False,
            "foreground": "", "highlight": ""
        }
        zoom_mult = getattr(self, "zoom_factor", 1.0)
        self._text_font = tkfont.Font(
            family=self._base_style["family"],
            size=int(self._base_style["size"] * zoom_mult),
        )
        widget = self._text_widget()
        widget.configure(font=self._text_font)
        widget.tag_configure("sel", background=ThemeManager.get("selection_bg"))

    def _default_style(self):
        return dict(self._base_style)

    def _normalize_style(self, style):
        normalized = self._default_style()
        normalized.update(style or {})
        normalized["family"] = str(normalized.get("family") or self.default_font_family)
        normalized["size"] = max(8, int(normalized.get("size") or 15))
        normalized["bold"] = bool(normalized.get("bold"))
        normalized["italic"] = bool(normalized.get("italic"))
        normalized["underline"] = bool(normalized.get("underline"))
        normalized["foreground"] = str(normalized.get("foreground") or "")
        normalized["highlight"] = str(normalized.get("highlight") or "")
        return normalized

    def _sanitize_tag_part(self, value):
        return quote(str(value), safe="")

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
            "family": unquote(family),
            "size": int(size),
            "bold": bool(int(bold)),
            "italic": bool(int(italic)),
            "underline": bool(int(underline)),
            "foreground": "" if foreground == "none" else unquote(foreground),
            "highlight": "" if highlight == "none" else unquote(highlight),
        }

    def _ensure_style_tag(self, tag_name, style):
        widget = self._text_widget()
        normalized = self._normalize_style(style)
        zoom_mult = getattr(self, "zoom_factor", 1.0)

        if tag_name in self._font_cache_initialized:
            font = self._font_cache.get(tag_name)
            if font:
                new_size = int(normalized["size"] * zoom_mult)
                if int(font.cget("size")) != new_size:
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
        self._font_base_sizes[tag_name] = normalized["size"]
        self._font_cache_initialized.add(tag_name)
        widget.tag_configure(tag_name, **kwargs)

    def _style_at_index(self, index):
        widget = self._text_widget()
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
        widget = self._text_widget()
        index = start
        runs = []
        while widget.compare(index, "<", end):
            style = self._normalize_style(self._style_at_index(index))
            style.update(updates)
            target_tag = self._style_tag_name(style)
            run_start = index
            while widget.compare(index, "<", end):
                next_style = self._normalize_style(self._style_at_index(index))
                next_style.update(updates)
                if self._style_tag_name(next_style) != target_tag:
                    break
                index = widget.index(f"{index}+1c")
            run_end = index
            runs.append((run_start, run_end, style))

        for run_start, run_end, style in runs:
            self._remove_style_tags(run_start, run_end)
            self._apply_style_tag_to_range(run_start, run_end, style)

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
            self._text_widget().tag_remove("sel", "1.0", "end")
            self._text_widget().focus_set()

    def apply_font_size(self, size_value):
        if self.current_note_type != "Text":
            return
        start, end = self._get_selected_or_current_word_range()
        if start and end:
            self._apply_style_updates(start, end, {"size": int(size_value)})
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
            title=TranslationService.get("editor.text_color"),
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
            title=TranslationService.get("editor.highlight"),
        )
        self.wait_window(picker)
        color = picker.result
        if not color:
            return
        self._apply_style_updates(start, end, {"highlight": color})
        self._text_widget().tag_remove("sel", "1.0", "end")
        self._text_widget().focus_set()

    def _queue_zoom(self, value):
        """Keep slider dragging cheap and commit wheel/click zoom after idle."""
        self._pending_zoom_value = float(value)
        if self._zoom_after_id is not None:
            self.after_cancel(self._zoom_after_id)
        self._zoom_after_id = self.after(120, self._commit_pending_zoom)

    def on_zoom_release(self, event=None):
        self._pending_zoom_value = float(self.document_zoom_slider.get())
        self._commit_pending_zoom()

    def _commit_pending_zoom(self):
        if self._zoom_after_id is not None:
            self.after_cancel(self._zoom_after_id)
            self._zoom_after_id = None
        self._apply_zoom(self._pending_zoom_value)

    @staticmethod
    def _scaled_font_size(base_size, zoom_factor):
        return max(1, int(base_size * zoom_factor))

    def _apply_zoom(self, value):
        zoom_factor = max(0.5, min(2.0, float(value) / 100.0))
        if abs(zoom_factor - self.zoom_factor) < 0.0001:
            return

        widget = self._text_widget()
        cursor_pos = widget.index("insert")
        yview = widget.yview()
        self.zoom_factor = zoom_factor

        new_base_size = self._scaled_font_size(self._base_style["size"], zoom_factor)
        if int(self._text_font.cget("size")) != new_base_size:
            self._text_font.configure(size=new_base_size)

        for tag_name, font in list(self._font_cache.items()):
            base_size = self._font_base_sizes.get(tag_name)
            if base_size is not None:
                new_size = self._scaled_font_size(base_size, zoom_factor)
                if int(font.cget("size")) == new_size:
                    continue
                font.configure(size=new_size)

        if self._zoom_restore_after_id is not None:
            self.after_cancel(self._zoom_restore_after_id)
        self._zoom_restore_after_id = self.after_idle(
            lambda: self._restore_view_after_zoom(cursor_pos, yview[0])
        )

    def _restore_view_after_zoom(self, cursor_pos, yview_fraction):
        self._zoom_restore_after_id = None
        try:
            widget = self._text_widget()
            widget.mark_set("insert", cursor_pos)
            widget.yview_moveto(yview_fraction)
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
        for font in self._font_cache.values():
            try:
                font.destroy()
            except Exception:
                pass
        self._font_cache.clear()
        self._font_base_sizes.clear()
        self._font_cache_initialized.clear()

    @staticmethod
    def _format_file_size(size):
        size = int(size or 0)
        if size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        if size >= 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size} B"

    def insert_media(self):
        if self.current_note_type == "Checklist":
            return
        paths = filedialog.askopenfilenames(
            title=TranslationService.get("editor.choose_media"),
            filetypes=self.media_service.supported_filetypes()
        )
        if not paths:
            return

        widget = self._text_widget()
        insert_index = widget.index("insert")
        errors = []
        for path in paths:
            try:
                attachment = self.media_service.import_file(path)
                attachment["position"] = len(widget.get("1.0", insert_index))
                self._media_attachments.append(attachment)
                media_widget = self._create_inline_media_widget(attachment, insert_index)
                insert_index = widget.index(f"{str(media_widget)} + 1c")
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
        widget.mark_set("insert", insert_index)
        widget.see(insert_index)
        widget.focus_set()
        try:
            widget.edit_separator()
        except Exception:
            pass
        if errors:
            messagebox.showwarning(
                TranslationService.get("msg.media_error"),
                "\n".join(errors),
                parent=self
            )

    def _open_media(self, attachment):
        try:
            self.media_service.open_file(attachment.get("path"))
        except (OSError, ValueError) as exc:
            messagebox.showerror(
                TranslationService.get("msg.media_error"),
                str(exc),
                parent=self
            )
####
    def _remove_media(self, attachment):
        attachment_id = str(attachment.get("id", ""))
        media_widget = self._media_widgets.get(attachment_id)
        widget = self._text_widget()
        if media_widget is not None:
            try:
                index = widget.index(str(media_widget))
                widget.delete(index, f"{index} + 1c")
            except tk.TclError:
                pass
            try:
                media_widget.destroy()
            except Exception:
                pass
        self._media_widgets.pop(attachment_id, None)
        self._media_image_refs.pop(attachment_id, None)
        self._media_attachments = [
            item for item in self._media_attachments
            if str(item.get("id", "")) != attachment_id
        ]
        widget.focus_set()

    def _clear_inline_media(self):
        for media_widget in list(self._media_widgets.values()):
            try:
                media_widget.destroy()
            except Exception:
                pass
        self._media_widgets.clear()
        self._media_image_refs.clear()

    def _create_inline_media_widget(self, attachment, index):
        widget = self._text_widget()
        attachment_id = str(attachment.get("id") or uuid.uuid4().hex)
        attachment["id"] = attachment_id
        path = self.media_service.resolve_path(attachment.get("path"))
        kind = attachment.get("kind") or self.media_service.media_kind(path) or "media"

        # Embedded media wrapper stylized using cell background properties
        card = ctk.CTkFrame(
            widget,
            fg_color=ThemeManager.get("cell_bg"),
            border_width=1,
            border_color=ThemeManager.get("grid_border"),
            corner_radius=6
        )
        name = str(attachment.get("name") or path.name)

        if kind == "image" and path.is_file():
            try:
                preview = self._cached_thumbnail(path)
                ctk_image = ctk.CTkImage(
                    light_image=preview,
                    dark_image=preview,
                    size=preview.size
                )
                self._media_image_refs[attachment_id] = ctk_image
                ctk.CTkLabel(card, text="", image=ctk_image).pack(
                    padx=8, pady=(8, 3)
                )
            except (OSError, UnidentifiedImageError):
                ctk.CTkLabel(card, text="🖼", font=ctk.CTkFont(size=34)).pack(
                    padx=12, pady=(8, 3)
                )
        else:
            icon = "🔊" if kind == "audio" else "🎬" if kind == "video" else "📕" if kind == "document" else "📎"
            ctk.CTkLabel(
                card,
                text=f"{icon}  {name}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=ThemeManager.get("text_primary")
            ).pack(padx=14, pady=(10, 4))

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.pack(fill="x", padx=8, pady=(2, 8))
        if kind == "image":
            ctk.CTkLabel(
                footer,
                text=f"{name} · {self._format_file_size(attachment.get('size'))}",
                anchor="w",
                font=ctk.CTkFont(size=11),
                text_color=ThemeManager.get("text_secondary")
            ).pack(side="left", padx=(0, 8))
            
        # Action tags mapped into high-contrast secondary glaze buttons
        ctk.CTkButton(
            footer,
            text=TranslationService.get("editor.open_media"),
            width=58,
            height=26,
            fg_color=ThemeManager.get("btn_note"),
            hover_color=ThemeManager.get("btn_note_hover"),
            text_color=ThemeManager.get("text_primary"),
            border_color=ThemeManager.get("grid_border"),
            border_width=1,
            corner_radius=4,
            command=lambda item=attachment: self._open_media(item)
        ).pack(side="left", padx=(0, 4))
        
        ctk.CTkButton(
            footer,
            text="✕",
            width=28,
            height=26,
            fg_color=ThemeManager.get("accent_danger"),
            hover_color=ThemeManager.get("accent_danger_hover"),
            text_color=ThemeManager.get("text_on_accent"),
            corner_radius=4,
            command=lambda item=attachment: self._remove_media(item)
        ).pack(side="left")

        widget.window_create(index, window=card, align="center", padx=6, pady=6)
        self._media_widgets[attachment_id] = card
        return card

    def _render_inline_media(self):
        self._clear_inline_media()
        if self.current_note_type == "Checklist":
            return
        text_length = len(self._text_widget().get("1.0", "end-1c"))

        def sort_key(indexed_attachment):
            original_index, item = indexed_attachment
            try:
                position = int(item.get("position", text_length))
            except (TypeError, ValueError):
                position = text_length
            return position, original_index

        indexed_attachments = list(enumerate(self._media_attachments))
        for _original_index, attachment in sorted(
            indexed_attachments, key=sort_key, reverse=True
        ):
            try:
                position = max(0, min(int(attachment.get("position", text_length)), text_length))
            except (TypeError, ValueError):
                position = text_length
            attachment["position"] = position
            self._create_inline_media_widget(attachment, f"1.0+{position}c")

    def _serialized_media(self):
        widget = self._text_widget()
        serialized = []
        for attachment in self._media_attachments:
            attachment_id = str(attachment.get("id", ""))
            media_widget = self._media_widgets.get(attachment_id)
            if media_widget is None:
                continue
            try:
                position = len(widget.get("1.0", str(media_widget)))
            except tk.TclError:
                continue
            item = dict(attachment)
            item["position"] = position
            serialized.append(item)
        serialized.sort(key=lambda item: int(item.get("position", 0)))
        self._media_attachments = serialized
        return [dict(item) for item in serialized]

    def _current_media_positions(self):
        widget = self._text_widget()
        positions = []
        for media_widget in self._media_widgets.values():
            try:
                positions.append(len(widget.get("1.0", str(media_widget))))
            except tk.TclError:
                continue
        return sorted(positions)

    def _widget_index_from_plain_offset(self, offset, positions=None):
        offset = max(0, int(offset))
        if positions is None:
            positions = self._current_media_positions()
        embedded_before = sum(1 for position in positions if position <= offset)
        return self._text_widget().index(f"1.0+{offset + embedded_before}c")

    def _render_content(self, content):
        widget = self._text_widget()
        self._clear_font_cache()
        self._clear_inline_media()
        widget.delete("1.0", "end")
        self._remove_style_tags("1.0", "end")
        self._media_attachments = []

        if isinstance(content, dict):
            for attachment in content.get("media", []):
                if isinstance(attachment, dict) and attachment.get("path"):
                    item = dict(attachment)
                    item["id"] = str(item.get("id") or uuid.uuid4().hex)
                    item.setdefault("position", len(str(content.get("text", ""))))
                    self._media_attachments.append(item)

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
            self._render_inline_media()
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
        self._render_inline_media()

    def _serialize_content(self):
        widget = self._text_widget()
        text = widget.get("1.0", "end-1c")
        media = self._serialized_media()
        if not text:
            return {"text": "", "spans": [], "media": media}
        media_positions = [int(item.get("position", 0)) for item in media]
        spans = []
        current_style = self._normalize_style(
            self._style_at_index(self._widget_index_from_plain_offset(0, media_positions))
        )
        span_start = 0
        for index, _char in enumerate(text):
            widget_index = self._widget_index_from_plain_offset(index, media_positions)
            style = self._normalize_style(self._style_at_index(widget_index))
            if style != current_style:
                spans.append({"start": span_start, "end": index, "style": current_style})
                span_start = index
                current_style = style
        spans.append({"start": span_start, "end": len(text), "style": current_style})
        return {"text": text, "spans": spans, "media": media}

    def apply_markdown_format(self, marker):
        if marker == "**":
            self.apply_text_style("bold")
        else:
            self.apply_text_style("italic")

    def setup_ui_mode(self, note_type):
        note_type = "Checklist" if str(note_type).lower() == "checklist" else note_type
        self.current_note_type = note_type

        self.textbox_content.grid_forget()
        self.checklist_frame.grid_forget()
        self.add_item_frame.grid_forget()

        if note_type == "Checklist":
            self._clear_inline_media()
            self._media_attachments = []
            self.checklist_frame.grid(row=0, column=0, sticky="nsew")
            
            # Breathing layout splits applied to the active checklist fields
            self.add_item_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(15, 10), padx=20)
            self.btn_bold.configure(state="disabled")
            self.btn_italic.configure(state="disabled")
            self.font_family_menu.configure(state="disabled")
            self.font_size_menu.configure(state="disabled")
            self.document_zoom_slider.configure(state="disabled")
            self.btn_media.configure(state="disabled")
        else:
            self.textbox_content.grid(row=0, column=0, sticky="nsew")
            self.btn_bold.configure(state="normal")
            self.btn_italic.configure(state="normal")
            self.font_family_menu.configure(state="normal")
            self.font_size_menu.configure(state="normal")
            self.document_zoom_slider.configure(state="normal")
            self.btn_media.configure(state="normal")

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
        if not text:
            text = self.new_item_entry.get().strip()
            self.new_item_entry.delete(0, 'end')
        if not text:
            return
        var = ctk.BooleanVar(value=is_done)
        
        # Micro-dressing applied to individual items, using punchy base states
        cb = ctk.CTkCheckBox(
            self.checklist_frame, text=text, variable=var,
            fg_color=ThemeManager.get("accent_primary"),
            hover_color=ThemeManager.get("btn_note_hover"),
            text_color=ThemeManager.get("text_primary"),
            border_color=ThemeManager.get("grid_border"),
            border_width=1,
            corner_radius=4,
            font=ctk.CTkFont(size=14)
        )
        cb.pack(anchor="w", pady=6, padx=15)
        self.checklist_vars.append({
            "checkbox": cb,
            "var": var,
            "search_default_text_color": cb.cget("text_color"),
            "search_default_border_color": cb.cget("border_color")
        })

    def clear_checklist_items(self):
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

        CTkDatePicker(self, initial_dt=initial_dt, title=title, on_select=on_date_selected)

    def prepare_new(self, note_type):
        self.current_note = None
        self.set_data("", "", note_type, reminder_at=None, deadline_at=None, is_locked=False)

    def set_data(self, title, content_data, note_type, reminder_at=None, deadline_at=None, is_locked=False):
        self.clear_content_search()
        self.setup_ui_mode(note_type)
        self.entry_title.delete(0, 'end')
        if title:
            self.entry_title.insert(0, title)
        elif hasattr(self.entry_title, '_activate_placeholder'):
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
            if isinstance(content_data, list):
                for item in content_data:
                    text = item.get("content") if isinstance(item, dict) else getattr(item, 'content', str(item))
                    done = item.get("is_done") if isinstance(item, dict) else getattr(item, 'is_done', False)
                    self.add_checklist_item(text, done)
            self.new_item_entry.focus_set()
        else:
            self._render_content(content_data)
            self.textbox_content.focus_set()

        if note_type == "Text":
            try:
                self._text_widget().edit_reset()
            except Exception:
                pass

    def _is_placeholder(self, entry, placeholder_text):
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
