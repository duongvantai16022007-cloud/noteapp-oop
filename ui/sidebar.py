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
        self.grid_rowconfigure(3, weight=3)
        self.grid_rowconfigure(5, weight=2)

        self.on_note_select = on_note_select
        self.on_restore_deleted = on_restore_deleted
        self.on_permanently_delete = on_permanently_delete
        initial_settings = initial_settings or {}

        _ = TranslationService.get

        # Logo / App Header
        self.logo_label = ctk.CTkLabel(
            self, text="Engraver", 
            font=ctk.CTkFont(family="Inter", size=22, weight="bold"),
            text_color=ThemeManager.get("text_primary")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(25, 15), sticky="w")

        # Search Block
        self.search_entry = ctk.CTkEntry(
            self, 
            placeholder_text=f"  {_('sidebar.search_placeholder')}",
            fg_color=ThemeManager.get("cell_bg"),
            text_color=ThemeManager.get("text_primary"),
            border_color=ThemeManager.get("grid_border"),
            border_width=1,
            corner_radius=8,
            height=36
        )
        self.search_entry.grid(row=1, column=0, padx=16, pady=(0, 10), sticky="ew")
        self.search_entry.bind("<KeyRelease>", on_search)

        # Action Button Block
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, padx=16, pady=(0, 10), sticky="ew")
        self.action_frame.grid_columnconfigure(0, weight=1)

        self.btn_new_folder = ctk.CTkButton(
            self.action_frame, 
            text=f"＋  {_('sidebar.new_folder')}", 
            font=ctk.CTkFont(weight="bold", size=13),
            fg_color=ThemeManager.get("btn_secondary"),
            hover_color=ThemeManager.get("btn_secondary_hover"),
            text_color=ThemeManager.get("text_primary"),
            corner_radius=6,
            height=32,
            command=self._on_new_folder_click
        )
        self.btn_new_folder.grid(row=0, column=0, sticky="ew")

        # 4. Restored Solid Container Context for Active Tree View
        self.scroll_list = ctk.CTkScrollableFrame(
            self, 
            label_text=_("sidebar.all_notes").upper(),
            fg_color=ThemeManager.get("cell_bg"),
            label_fg_color="transparent",
            label_text_color=ThemeManager.get("text_primary"),
            label_font=ctk.CTkFont(size=10, weight="bold"),
            border_color=ThemeManager.get("grid_border"),
            border_width=1,
            corner_radius=8
        )
        self.scroll_list.grid(row=3, column=0, padx=16, pady=5, sticky="nsew")

        # Separator Frame
        self.separator = ctk.CTkFrame(self, height=1, fg_color=ThemeManager.get("grid_border"))
        self.separator.grid(row=4, column=0, padx=16, pady=10, sticky="ew")

        # 5. Restored Solid Container Context for Trash Area
        self.deleted_scroll_list = ctk.CTkScrollableFrame(
            self, 
            label_text=_("sidebar.deleted_list").upper(),
            fg_color=ThemeManager.get("cell_bg"),
            label_fg_color="transparent",
            label_text_color=ThemeManager.get("text_primary"),
            label_font=ctk.CTkFont(size=10, weight="bold"),
            border_color=ThemeManager.get("grid_border"),
            border_width=1,
            corner_radius=8
        )
        self.deleted_scroll_list.grid(row=5, column=0, padx=16, pady=(0, 20), sticky="nsew")

    def update_tree_list(self, folders, notes_by_folder):
        """Redraws the folder tree with solid nested list backing structures."""
        for widget in self.scroll_list.winfo_children():
            widget.destroy()
            
        _ = TranslationService.get

        for folder in folders:
            f_id = folder["id"]
            f_name = folder["name"]
            
            folder_container_frame = ctk.CTkFrame(self.scroll_list, fg_color="transparent")
            folder_container_frame.pack(fill="x", pady=2, padx=4)
            
            header_frame = ctk.CTkFrame(folder_container_frame, fg_color="transparent")
            header_frame.pack(fill="x")
            
            sub_notes_frame = ctk.CTkFrame(folder_container_frame, fg_color="transparent")
            
            def toggle(frame=sub_notes_frame):
                if frame.winfo_manager(): 
                    frame.pack_forget()
                else: 
                    frame.pack(fill="x", padx=(14, 0))

            btn_folder = ctk.CTkButton(
                header_frame, text=f"{f_name}", anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color=ThemeManager.get("cell_bg_muted"), 
                hover_color=ThemeManager.get("popup_bg"),
                text_color=ThemeManager.get("text_primary"),
                corner_radius=6,
                height=32,
                command=toggle
            )
            btn_folder.pack(side="left", fill="x", expand=True, padx=(0, 2))

            btn_delete_folder = ctk.CTkButton(
                header_frame, text="✕", width=26, height=32,
                font=ctk.CTkFont(size=11),
                fg_color="transparent",
                hover_color=ThemeManager.get("accent_danger_hover"),
                text_color=ThemeManager.get("accent_danger"),
                corner_radius=4,
                command=lambda fid=f_id, fname=f_name: self._on_delete_folder_click(fid, fname)
            )
            btn_delete_folder.pack(side="right")

            btn_add_note = ctk.CTkButton(
                header_frame, text="＋", width=26, height=32,
                font=ctk.CTkFont(size=12),
                fg_color="transparent",
                hover_color=ThemeManager.get("popup_bg"),
                text_color=ThemeManager.get("text_primary"),
                corner_radius=4,
                command=lambda fid=f_id, fname=f_name: self._on_add_note_to_folder_click(fid, fname)
            )
            btn_add_note.pack(side="right", padx=(0, 2))
            
            sub_notes_frame.pack(fill="x", padx=(14, 0)) 
            
            for note in notes_by_folder.get(f_id, []):
                self._draw_single_note(sub_notes_frame, note)

        if folders and notes_by_folder.get("root"):
            lbl_divider = ctk.CTkLabel(
                self.scroll_list, text=f"— {_('sidebar.all_notes')} —", 
                text_color=ThemeManager.get("text_muted") if ThemeManager.get("text_muted") else "#888888",
                font=ctk.CTkFont(size=10, weight="bold")
            )
            lbl_divider.pack(pady=(12, 4))

        for note in notes_by_folder.get("root", []):
            self._draw_single_note(self.scroll_list, note)

    def update_list(self, notes_list):
        for widget in self.scroll_list.winfo_children():
            widget.destroy()
        for note in notes_list:
            self._draw_single_note(self.scroll_list, note)

    def _draw_single_note(self, parent_frame, note):
        _ = TranslationService.get
        title = note.get('title', _('sidebar.no_title'))
        icon = "◼" if str(note.get('type', '')).lower() == 'checklist' else "📄"
        
        meta_str = ""
        if note.get('is_locked'): meta_str += " 🔒"
        if note.get('reminder_at'): meta_str += " 🔔"
        if note.get('deadline_at'): meta_str += " 📌"

        btn = ctk.CTkButton(
            parent_frame,
            text=f"{icon}  {title}{meta_str}",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=ThemeManager.get("btn_note"),
            hover_color=ThemeManager.get("btn_note_hover"),
            text_color=ThemeManager.get("text_primary"),
            anchor="w",
            corner_radius=4,
            height=28,
            command=lambda id=note['id']: self.on_note_select(id)
        )
        btn.pack(fill="x", pady=1, padx=4)

    def update_deleted_list(self, deleted_notes):
        for widget in self.deleted_scroll_list.winfo_children():
            widget.destroy()
            
        _ = TranslationService.get

        if not deleted_notes:
            lbl_empty = ctk.CTkLabel(
                self.deleted_scroll_list, text=_("sidebar.no_deleted"),
                text_color=ThemeManager.get("text_muted") if ThemeManager.get("text_muted") else "#888888",
                font=ctk.CTkFont(size=12, slant="italic")
            )
            lbl_empty.pack(padx=10, pady=15)
            return

        for note in deleted_notes:
            title = note.get('title', _('sidebar.no_title'))
            deleted_at = note.get('deleted_at', '')
            icon = "◼" if str(note.get('type', '')).lower() == 'checklist' else "📄"
            
            label_text = f"{icon} {title}"
            if deleted_at:
                label_text += f"  ({deleted_at[:10]})"

            row_frame = ctk.CTkFrame(self.deleted_scroll_list, fg_color="transparent")
            row_frame.pack(fill="x", pady=1, padx=4)

            btn = ctk.CTkButton(
                row_frame,
                text=f"↺  {label_text}",
                font=ctk.CTkFont(size=12),
                fg_color="transparent",
                hover_color=ThemeManager.get("cell_bg_muted"),
                text_color=ThemeManager.get("text_primary"),
                anchor="w",
                corner_radius=4,
                height=28,
                command=lambda id=note['id']: self.on_restore_deleted(id)
            )
            btn.pack(side="left", fill="x", expand=True)

            del_btn = ctk.CTkButton(
                row_frame,
                text="✕",
                width=24,
                height=28,
                font=ctk.CTkFont(size=10),
                fg_color="transparent",
                hover_color=ThemeManager.get("accent_danger_hover"),
                text_color=ThemeManager.get("accent_danger"),
                corner_radius=4,
                command=lambda id=note['id']: self.on_permanently_delete(id)
            )
            del_btn.pack(side="right", padx=(4, 0))

    def _on_new_folder_click(self):
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
        if hasattr(self.master, "delete_folder_by_id"):
            self.master.delete_folder_by_id(folder_id, folder_name)

    def _on_add_note_to_folder_click(self, folder_id, folder_name):
        if hasattr(self.master, "prepare_new_in_folder"):
            self.master.prepare_new_in_folder(folder_id, folder_name)