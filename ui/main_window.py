import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog, Menu
import datetime
import calendar
from types import SimpleNamespace
import os
import sys
import uuid
from pathlib import Path

from data.NoteRepository import NoteRepository
from model.note_factory import NoteFactory
from commands.note_commands import AddCommand, EditCommand
from services.export_service import ExportService
from services.security_service import SecurityManager
from services.reminder_service import ReminderService
from services.settings_service import SettingsService
from services.theme_service import ThemeManager
from services.translation_service import TranslationService

from ui.sidebar import SidebarFrame
from ui.editor import EditorFrame
from ui.calendar_view import CTkCalendarView

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.repo = NoteRepository()
        self.export_service = ExportService()
        self.security_manager = SecurityManager()
        self.settings_service = SettingsService()
        self.settings = self.settings_service.get_all()
        self.current_note = None
        self.pending_note_id = None
        self.calendar_month = datetime.date.today().replace(day=1)
        self._ui_built = False
        self._last_deleted_purge_date = None
        self._resize_tracking_ready = False
        self._resize_layout_active = False
        self._resize_finish_after_id = None
        self._last_window_size = None

        self.geometry("1200x760")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Apply settings initially
        initial_appearance = self.settings.get("appearance_mode", "System")
        initial_color = self.settings.get("color_theme", "blue")
        initial_language = self.settings.get("language", "vi") 
        TranslationService.set_language(initial_language)
        self.title(TranslationService.get("app.title"))
        ctk.set_appearance_mode(initial_appearance)
        try:
            ctk.set_default_color_theme(initial_color.lower().replace(" ", "-"))
        except Exception:
            ctk.set_default_color_theme("blue")
        from services.theme_service import ThemeManager
        ThemeManager.set_active_theme(initial_color)
        self.configure(fg_color=ThemeManager.get("grid_bg"))

        self._build_ui()
        self.bind("<Configure>", self._on_window_configure, add="+")
        self.after_idle(self._enable_resize_tracking)

        # Reminder chạy nền, callback đưa thông báo về main thread bằng self.after.
        self.reminder_service = ReminderService(self.repo, callback=self.handle_reminder_due, interval=10)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # =========================
    # Helpers
    # =========================
    def _enable_resize_tracking(self):
        if not self.winfo_exists():
            return
        self._last_window_size = (self.winfo_width(), self.winfo_height())
        self._resize_tracking_ready = True

    def _on_window_configure(self, event):
        """Coalesce the event storm generated while the window is resized."""
        if event.widget is not self or not self._resize_tracking_ready:
            return

        size = (event.width, event.height)
        if size == self._last_window_size:
            return
        self._last_window_size = size

        if not self._resize_layout_active:
            self._begin_live_resize()

        if self._resize_finish_after_id is not None:
            self.after_cancel(self._resize_finish_after_id)
        self._resize_finish_after_id = self.after(100, self._finish_live_resize)

    def _begin_live_resize(self):
        """Temporarily decouple heavy child layouts from every pixel change."""
        if not all(hasattr(self, name) for name in ("sidebar", "editor")):
            return
        self._resize_layout_active = True
        self.sidebar.grid_remove()
        self.editor.grid_remove()

    def _finish_live_resize(self):
        self._resize_finish_after_id = None
        if not self._resize_layout_active:
            return
        self._resize_layout_active = False
        self.sidebar.grid()
        self.editor.grid()

    def _build_ui(self, restore_note_id=None):
        if getattr(self, "sidebar", None):
            self.sidebar.destroy()
        if getattr(self, "editor", None):
            self.editor.destroy()

        self.sidebar = SidebarFrame(
            self,
            on_note_select=self.load_note,
            on_restore_deleted=self.restore_deleted_note,
            on_permanently_delete=self.permanently_delete_note,
            on_search=self.handle_search,
            initial_settings=self.settings
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.editor = EditorFrame(
            self,
        )
        self.editor.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        self._ui_built = True
        self.refresh_sidebar()
        if restore_note_id:
            self.load_note(restore_note_id)
        else:
            self.prepare_new("Text")
            
        self._build_menu()

    def _menu_save_note(self):
        if hasattr(self, "editor"):
            self.save_note(self.editor.get_data(), self.editor.current_note_type)

    def _build_menu(self):
        menubar = Menu(self)
        _ = TranslationService.get # Hàm rút gọn để lấy từ khóa dịch
        
        # --- File Menu ---
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label=_("menu.file.new_text"), command=lambda: self.prepare_new("Text"))
        file_menu.add_command(label=_("menu.file.new_checklist"), command=lambda: self.prepare_new("Checklist"))
        file_menu.add_separator()
        file_menu.add_command(label=_("menu.file.save"), command=self._menu_save_note)
        file_menu.add_command(label=_("menu.file.delete"), command=self.delete_note)
        file_menu.add_separator()
        file_menu.add_command(label=_("menu.file.export_md"), command=self.export_md)
        file_menu.add_command(label=_("menu.file.export_pdf"), command=self.export_pdf)
        file_menu.add_command(label=_("menu.file.export_media_zip"), command=self.export_media_zip)
        file_menu.add_command(
            label=_("menu.file.export_media_zip_password"),
            command=self.export_media_zip_with_password,
        )
        file_menu.add_command(label=_("menu.file.open_media_zip"), command=self.open_media_zip)
        menubar.add_cascade(label=_("menu.file"), menu=file_menu)
        file_menu.add_separator()
        file_menu.add_command(label=_("menu.file.import"), command=self.import_from_file)
        
        # --- Edit Menu ---
        edit_menu = Menu(menubar, tearoff=0)
        edit_menu.add_command(label=_("menu.edit.undo"), command=self.handle_undo)
        edit_menu.add_command(label=_("menu.edit.redo"), command=self.handle_redo)
        menubar.add_cascade(label=_("menu.edit"), menu=edit_menu)
        
        # --- View Menu ---
        view_menu = Menu(menubar, tearoff=0)
        view_menu.add_command(label=_("menu.view.calendar"), command=self.open_calendar_view)
        menubar.add_cascade(label=_("menu.view"), menu=view_menu)
        
        # --- Options Menu ---
        options_menu = Menu(menubar, tearoff=0)
        options_menu.add_command(label=_("menu.options.lock"), command=self.toggle_note_lock)
        options_menu.add_command(label=_("menu.options.move_folder"), command=self.move_current_note_to_folder)
        options_menu.add_separator()
        
        # Menu Giao diện
        appearance_menu = Menu(options_menu, tearoff=0)
        appearance_modes = (
            ("System", _("appearance.system")),
            ("Light", _("appearance.light")),
            ("Dark", _("appearance.dark")),
        )
        for mode, label in appearance_modes:
            appearance_menu.add_command(label=label, command=lambda m=mode: self.handle_theme_change("appearance_mode", m))
        options_menu.add_cascade(label=_("menu.options.appearance"), menu=appearance_menu)
        
        # Menu Chủ đề màu
        from services.theme_service import ThemeManager
        theme_menu = Menu(options_menu, tearoff=0)
        for t in ThemeManager.get_available_themes():
            theme_menu.add_command(label=t, command=lambda th=t: self.handle_theme_change("color_theme", th))
        options_menu.add_cascade(label=_("menu.options.theme"), menu=theme_menu)

        # ĐOẠN BỔ SUNG: Menu Ngôn ngữ
        lang_menu = Menu(options_menu, tearoff=0)
        for lang in TranslationService.get_available_languages():
            lang_menu.add_command(
                label=lang["name"], 
                command=lambda code=lang["code"]: self.handle_language_change(code)
            )
        options_menu.add_cascade(label=_("menu.options.language"), menu=lang_menu)
        
        menubar.add_cascade(label=_("menu.options"), menu=options_menu)
        self.config(menu=menubar)

    def handle_language_change(self, lang_code):
        """Lưu cấu hình ngôn ngữ và tải lại giao diện"""
        try:
            self.wm_attributes("-alpha", 0) # Tạm làm mờ cửa sổ chống giật chớp
        except Exception:
            pass

        # 1. Lưu tùy chọn vào DB
        self.settings_service.set_setting("language", lang_code)
        self.settings["language"] = lang_code
        
        # 2. Đổi ngôn ngữ trong Service
        TranslationService.set_language(lang_code)

        # Đổi lại tiêu đề app
        self.title(TranslationService.get("app.title"))

        # 3. Tái tạo lại toàn bộ UI với ngôn ngữ mới
        restore_note_id = self.current_note.id if self.current_note else None
        self._build_ui(restore_note_id=restore_note_id)

        self.update_idletasks()
        try:
            self.wm_attributes("-alpha", 1) # Hiện lại cửa sổ
        except Exception:
            pass

    def refresh_sidebar(self):
        today = datetime.date.today()
        if self._last_deleted_purge_date != today:
            for note_id in self.repo.purge_expired_deleted_notes(days=30):
                self.editor.media_service.delete_note_media(note_id)
            self._last_deleted_purge_date = today
        folders = getattr(self.repo, 'get_all_folders', lambda: [])() 
        all_notes = self.repo.get_all_notes()
        notes_by_folder = {"root": []}
        for f in folders:
            notes_by_folder[f["id"]] = []
            
        for note in all_notes:
            f_id = note.get("folder_id")
            if f_id and f_id in notes_by_folder:
                notes_by_folder[f_id].append(note)
            else:
                notes_by_folder["root"].append(note)
        self.sidebar.update_tree_list(folders, notes_by_folder) 
        self.sidebar.update_deleted_list(self.repo.get_deleted_notes())

    def _parse_datetime_input(self, value):
        """Nhận định dạng YYYY-MM-DD HH:MM hoặc ISO; trả ISO string/None."""
        value = (value or "").strip()
        if not value:
            return None

        formats = ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"]
        for fmt in formats:
            try:
                return datetime.datetime.strptime(value, fmt).replace(microsecond=0).isoformat()
            except ValueError:
                pass

        try:
            return datetime.datetime.fromisoformat(value).replace(microsecond=0).isoformat()
        except ValueError:
            raise ValueError(TranslationService.get("msg.time_format_error"))

    def _format_datetime_display(self, value):
        if not value:
            return ""
        try:
            return datetime.datetime.fromisoformat(str(value)).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return str(value)

    def _note_extra_from_form(self, data):
        reminder_at = self._parse_datetime_input(data.get("reminder_at"))
        deadline_at = self._parse_datetime_input(data.get("deadline_at"))

        old_reminder = getattr(self.current_note, "reminder_at", None) if self.current_note else None
        reminder_notified = 0 if reminder_at != old_reminder else getattr(self.current_note, "reminder_notified", 0)

        old_deadline = getattr(self.current_note, "deadline_at", None) if self.current_note else None
        deadline_notified = 0 if deadline_at != old_deadline else getattr(self.current_note, "deadline_notified", 0)

        return {
            "reminder_at": reminder_at,
            "deadline_at": deadline_at,
            "reminder_notified": reminder_notified,
            "deadline_notified": deadline_notified
        }

    def _content_to_plain_text(self, content):
        if isinstance(content, dict):
            return str(content.get("text", ""))
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    parts.append(str(item.get("content", "")))
                else:
                    parts.append(str(getattr(item, "content", item)))
            return " ".join(parts)
        return str(content or "")

    # =========================
    # CRUD Note
    # =========================
    def _discard_pending_media(self, except_note_id=None):
        pending_id = getattr(self, "pending_note_id", None)
        if self.current_note is None and pending_id and pending_id != except_note_id:
            self.editor.media_service.delete_note_media(pending_id)

    def prepare_new(self, note_type, note_id=None):
        draft_note_id = str(note_id or uuid.uuid4())
        self._discard_pending_media(except_note_id=draft_note_id)
        self.current_note = None
        self.pending_folder_id = None
        self.pending_note_id = draft_note_id
        self.editor.set_data(
            "", "", note_type,
            reminder_at=None,
            deadline_at=None,
            is_locked=False,
            note_id=draft_note_id,
        )

    def create_new_folder(self, folder_name, parent_id=None):
        """Hứng tên thư mục từ Sidebar, lưu xuống DB và refresh giao diện"""
        from tkinter import messagebox
        try:
            self.repo.create_folder(folder_name, parent_id=parent_id)
            self.refresh_sidebar() 
        except Exception as e:
            messagebox.showerror(
                TranslationService.get("msg.save_error"),
                TranslationService.get("msg.folder_create_error", error=e),
            )

    def prepare_new_in_folder(self, folder_id, folder_name):
        from services.translation_service import TranslationService
        _ = TranslationService.get
        
        popup = ctk.CTkToplevel(self)
        popup.title(_("msg.create_in_folder_title"))
        popup.geometry("380x150")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()
        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 380) // 2
        y = self.winfo_y() + (self.winfo_height() - 150) // 2
        popup.geometry(f"+{x}+{y}")
        prompt_text = _("msg.create_in_folder_prompt", folder_name)
        ctk.CTkLabel(popup, text=prompt_text, font=ctk.CTkFont(size=14)).pack(pady=(20, 15))
        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20)
        def choose_text():
            self.prepare_new("Text")
            self.pending_folder_id = folder_id
            popup.destroy()
        def choose_checklist():
            self.prepare_new("Checklist")
            self.pending_folder_id = folder_id
            popup.destroy()
        ctk.CTkButton(
            btn_frame, 
            text=_("msg.btn_text_note"), 
            height=35,
            command=choose_text
        ).pack(side="left", expand=True, padx=10)
        ctk.CTkButton(
            btn_frame, 
            text=_("msg.btn_checklist"), 
            height=35,
            command=choose_checklist
        ).pack(side="right", expand=True, padx=10)

    def load_note(self, note_id):
        self._discard_pending_media(except_note_id=note_id)
        self.pending_folder_id = None
        self.pending_note_id = None
        note_data = self.repo.get_note(note_id)
        if not note_data:
            return

        if note_data.get("is_locked"):
            password = simpledialog.askstring(
                TranslationService.get("msg.lock_title"),
                TranslationService.get("msg.lock_prompt"),
                show="*",
                parent=self,
            )
            if password is None:
                return
            if not self.security_manager.verify_password(
                password,
                note_data.get("password_hash"),
                note_data.get("password_salt")
            ):
                messagebox.showerror(
                    TranslationService.get("msg.lock_wrong"),
                    TranslationService.get("msg.lock_wrong_text"),
                )
                return

        self.current_note = NoteFactory.from_dict(note_data)
        organized_content = self.editor.media_service.organize_content_media(
            self.current_note.id,
            self.current_note.content,
        )
        if organized_content != self.current_note.content:
            self.current_note.update_content(organized_content)
            self.repo.update_note_content(self.current_note.id, organized_content)

        legacy_media_path = getattr(self.current_note, "file_path", None)
        if legacy_media_path:
            organized_path = self.editor.media_service.organize_legacy_media(
                self.current_note.id,
                legacy_media_path,
            )
            if organized_path != legacy_media_path:
                self.current_note._file_path = organized_path
                self.repo.update_note_media_path(self.current_note.id, organized_path)

        self.editor.set_data(
            self.current_note.title,
            self.current_note.content,
            self.current_note.get_type(),
            reminder_at=self.current_note.reminder_at,
            deadline_at=self.current_note.deadline_at,
            is_locked=self.current_note.is_locked,
            note_id=self.current_note.id,
        )

    def move_current_note_to_folder(self):
        """Hiển thị hộp thoại danh sách Folder để di chuyển ghi chú hiện tại."""
        if not self.current_note:
            return messagebox.showwarning(
                TranslationService.get("msg.save_error"),
                TranslationService.get("msg.folder_move_no_note"),
            )

        # Lấy tất cả thư mục hiện có
        folders = getattr(self.repo, 'get_all_folders', lambda: [])()
        if not folders:
            return messagebox.showinfo(
                TranslationService.get("msg.info"),
                TranslationService.get("msg.folder_move_no_folders"),
            )

        # Khởi tạo popup phụ
        popup = ctk.CTkToplevel(self)
        popup.title(TranslationService.get("msg.folder_move_title"))
        popup.geometry("380x300")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()

        # Căn giữa popup theo cửa sổ chính
        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 380) // 2
        y = self.winfo_y() + (self.winfo_height() - 300) // 2
        popup.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            popup,
            text=TranslationService.get("msg.folder_move_prompt"),
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=15)

        folder_map = {folder["id"]: dict(folder) for folder in folders}

        def folder_path(folder_id, seen=None):
            seen = set(seen or ())
            if folder_id in seen or folder_id not in folder_map:
                return ""
            seen.add(folder_id)
            folder = folder_map[folder_id]
            parent_path = folder_path(folder.get("parent_id"), seen)
            return f"{parent_path} / {folder['name']}" if parent_path else folder["name"]

        root_label = TranslationService.get("msg.folder_root")
        folder_options = {
            f"{folder_path(folder_id)}  [{folder_id[:6]}]": folder_id
            for folder_id in folder_map
        }
        options = [root_label] + sorted(folder_options, key=str.casefold)
        combo_folder = ctk.CTkComboBox(popup, values=options, width=280)
        combo_folder.pack(pady=10)
        
        # Thiết kế hiển thị mặc định theo thư mục hiện tại của note nếu có
        combo_folder.set(options[0])
        for label, folder_id in folder_options.items():
            if folder_id == self.current_note.folder_id:
                combo_folder.set(label)
                break

        def do_move():
            selected_name = combo_folder.get()
            target_folder_id = folder_options.get(selected_name)
            
            # Thực thi cập nhật xuống Database & Model object
            self.repo.move_note_to_folder(self.current_note.id, target_folder_id)
            self.current_note.folder_id = target_folder_id
            
            popup.destroy()
            self.refresh_sidebar() # Vẽ lại cây thư mục trên Sidebar
            messagebox.showinfo(
                TranslationService.get("msg.export_success"),
                TranslationService.get("msg.folder_move_success"),
            )

        ctk.CTkButton(
            popup, text=TranslationService.get("msg.folder_move_confirm"),
            fg_color=ThemeManager.get("accent_primary"),
            hover_color=ThemeManager.get("accent_primary_hover"),
            text_color=ThemeManager.get("text_on_accent"),
            command=do_move
        ).pack(pady=20)

    def save_note(self, data, note_type):
        if not data["title"]:
            return messagebox.showwarning(
                TranslationService.get("msg.save_error"),
                TranslationService.get("msg.title_empty"),
            )

        try:
            extra = self._note_extra_from_form(data)
        except ValueError as exc:
            return messagebox.showwarning(TranslationService.get("msg.time_error"), str(exc))

        try:
            note_id = self.current_note.id if self.current_note else self.pending_note_id
            if not note_id:
                note_id = str(uuid.uuid4())
                self.pending_note_id = note_id
            data["content"] = self.editor.organize_media(note_id, data["content"])
            if self.current_note is None:
                raw_data = {
                    "id": note_id,
                    "type": note_type,
                    "title": data["title"],
                    "content": data["content"],
                    "folder_id": getattr(self, "pending_folder_id", None),
                    **extra
                }
                new_note_obj = NoteFactory.from_dict(raw_data)

                command = AddCommand(new_note_obj, self.repo)
                command.execute()
                self.current_note = new_note_obj
                self.pending_note_id = None
                self.pending_folder_id = None
            else:
                command = EditCommand(
                    self.current_note,
                    self.repo,
                    new_title=data["title"],
                    new_content=data["content"],
                    new_extra=extra
                )
                command.execute()
        except ValueError as exc:
            return messagebox.showwarning(TranslationService.get("msg.save_error"), str(exc))
        except OSError as exc:
            return messagebox.showerror(
                TranslationService.get("msg.media_error"),
                TranslationService.get("msg.media_save_error", error=exc),
            )

        self.refresh_sidebar()
        messagebox.showinfo(
            TranslationService.get("msg.export_success"),
            TranslationService.get("msg.save_success"),
        )

    def delete_note(self):
        if self.current_note and messagebox.askyesno(
            TranslationService.get("msg.delete_confirm"),
            TranslationService.get("msg.delete_confirm_text"),
        ):
            self.repo.delete_note(self.current_note.id)
            self.prepare_new("Text")
            self.refresh_sidebar()

    def delete_folder_by_id(self, folder_id, folder_name):
        """Yêu cầu Repository xóa thư mục và cập nhật lại giao diện."""
        if messagebox.askyesno(
            TranslationService.get("msg.folder_delete_title"),
            TranslationService.get("msg.folder_delete_confirm", name=folder_name),
        ):
            try:
                self.repo.delete_folder(folder_id)
                messagebox.showinfo(
                    TranslationService.get("msg.export_success"),
                    TranslationService.get("msg.folder_delete_success", name=folder_name),
                )
                self.refresh_sidebar() 
            except Exception as e:
                messagebox.showerror(
                    TranslationService.get("msg.save_error"),
                    TranslationService.get("msg.folder_delete_error", error=e),
                )

    def handle_undo(self):
        self.editor.undo_text()

    def handle_redo(self):
        self.editor.redo_text()

    def restore_deleted_note(self, note_id):
        self.repo.restore_deleted_note(note_id)
        self.refresh_sidebar()
        self.load_note(note_id)

    def permanently_delete_note(self, note_id):
        if messagebox.askyesno(
            TranslationService.get("msg.permanent_delete_confirm"),
            TranslationService.get("msg.permanent_delete_confirm_text"),
        ):
            self.repo.permanently_delete_note(note_id)
            self.editor.media_service.delete_note_media(note_id)
            self.refresh_sidebar()

    def handle_search(self, event=None):
        keyword = self.sidebar.search_entry.get().strip().lower()
        notes = []
        for note in self.repo.get_all_notes():
            title_match = keyword in note.get('title', '').lower()
            # Ghi chú đã khóa không bị search theo content để tránh đọc thuộc tính bên trong khi chưa nhập pass.
            content_match = False if note.get("is_locked") else keyword in self._content_to_plain_text(note.get('content', '')).lower()
            if title_match or content_match:
                notes.append(note)
        self.sidebar.update_list(notes)

    # =========================
    # Bảo mật ghi chú
    # =========================
    def toggle_note_lock(self):
        if not self.current_note:
            return messagebox.showwarning(
                TranslationService.get("msg.lock_first"),
                TranslationService.get("msg.lock_first_text"),
            )

        note_data = self.repo.get_note(self.current_note.id)
        if not note_data:
            return messagebox.showwarning(
                TranslationService.get("msg.lock_not_found"),
                TranslationService.get("msg.lock_not_found_text"),
            )

        if note_data.get("is_locked"):
            password = simpledialog.askstring(
                TranslationService.get("msg.lock_unlock_title"),
                TranslationService.get("msg.lock_enter_current"),
                show="*",
                parent=self,
            )
            if password is None:
                return
            if not self.security_manager.verify_password(password, note_data.get("password_hash"), note_data.get("password_salt")):
                return messagebox.showerror(
                    TranslationService.get("msg.lock_unlock_fail"),
                    TranslationService.get("msg.lock_unlock_fail_text"),
                )

            self.repo.update_note_security(self.current_note.id, False, None, None)
            self.current_note.set_lock_info(False, None, None)
            self.refresh_sidebar()
            return messagebox.showinfo(
                TranslationService.get("msg.lock_unlock_success"),
                TranslationService.get("msg.lock_unlock_success_text"),
            )

        password_1 = simpledialog.askstring(
            TranslationService.get("msg.lock_set_title"),
            TranslationService.get("msg.lock_new_password"),
            show="*",
            parent=self,
        )
        if password_1 is None:
            return
        if len(password_1) < 4:
            return messagebox.showwarning(
                TranslationService.get("msg.lock_weak"),
                TranslationService.get("msg.lock_weak_text"),
            )
        password_2 = simpledialog.askstring(
            TranslationService.get("msg.lock_confirm"),
            TranslationService.get("msg.lock_confirm_text"),
            show="*",
            parent=self,
        )
        if password_2 is None:
            return
        if password_1 != password_2:
            return messagebox.showwarning(
                TranslationService.get("msg.lock_mismatch"),
                TranslationService.get("msg.lock_mismatch_text"),
            )

        password_hash, password_salt = self.security_manager.hash_password(password_1)
        self.repo.update_note_security(self.current_note.id, True, password_hash, password_salt)
        self.current_note.set_lock_info(True, password_hash, password_salt)
        self.refresh_sidebar()
        messagebox.showinfo(
            TranslationService.get("msg.lock_success"),
            TranslationService.get("msg.lock_success_text"),
        )

    # =========================
    # Reminder + Calendar
    # =========================
    def handle_reminder_due(self, note_dict, is_deadline=False):
        def refresh_after_notification():
            self.refresh_sidebar()
        self.after(0, refresh_after_notification)

    def _date_from_iso(self, value):
        if not value:
            return None
        try:
            return datetime.datetime.fromisoformat(str(value)).date()
        except ValueError:
            return None

    def open_calendar_view(self):
        CTkCalendarView(self, repo=self.repo, on_open_note=self.load_note)

    # =========================
    # Theme
    # =========================
    def apply_theme(self, previous_palette):
        """Recolor existing UI while preserving editor and sidebar state."""
        self.configure(fg_color=ThemeManager.get("grid_bg"))
        self.sidebar.apply_theme(previous_palette)
        self.editor.apply_theme(previous_palette)
        for child in self.winfo_children():
            if child not in (self.sidebar, self.editor):
                ThemeManager.apply_to_widget_tree(child, previous_palette)

    def handle_theme_change(self, key, value):
        if self.settings.get(key) == value:
            return

        self.settings_service.set_setting(key, value)
        self.settings[key] = value

        if key == "appearance_mode":
            ctk.set_appearance_mode(value)
            # CustomTkinter redraws tuple colors automatically; native Text tags
            # need a small explicit refresh for their resolved light/dark color.
            self.editor.apply_theme()
        elif key == "color_theme":
            previous_palette = ThemeManager.get_palette()
            try:
                ctk.set_default_color_theme(value.lower().replace(" ", "-"))
            except Exception:
                ctk.set_default_color_theme("blue")
            ThemeManager.set_active_theme(value)
            self.apply_theme(previous_palette)

    # =========================
    # Export
    # =========================
    def _current_editor_note_for_export(self):
        data = self.editor.get_data()
        return SimpleNamespace(
            title=data.get("title") or self.current_note.title,
            content=data.get("content", self.current_note.content),
            reminder_at=data.get("reminder_at"),
            deadline_at=data.get("deadline_at"),
        )

    def export_md(self):
        if not self.current_note:
            return messagebox.showwarning(
                TranslationService.get("msg.export_no_note"),
                TranslationService.get("msg.export_no_note_text"),
            )
        path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown", "*.md")])
        if path:
            try:
                self.export_service.export_to_markdown(self._current_editor_note_for_export(), path)
                messagebox.showinfo(
                    TranslationService.get("msg.export_success"),
                    TranslationService.get("msg.export_success_text", path=path),
                )
            except Exception as exc:
                messagebox.showerror(
                    TranslationService.get("msg.export_markdown_error"),
                    TranslationService.get("msg.export_markdown_error_text", error=exc),
                )

    def export_pdf(self):
        if not self.current_note:
            return messagebox.showwarning(
                TranslationService.get("msg.export_no_note"),
                TranslationService.get("msg.export_no_note_text"),
            )
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if path:
            try:
                self.export_service.export_to_pdf(self._current_editor_note_for_export(), path)
                messagebox.showinfo(
                    TranslationService.get("msg.export_success"),
                    TranslationService.get("msg.export_success_text", path=path),
                )
            except Exception as e:
                messagebox.showerror(
                    TranslationService.get("msg.export_pdf_error"),
                    TranslationService.get("msg.export_pdf_error_text", error=e),
                )

    def export_media_zip(self):
        if not self.current_note:
            return messagebox.showwarning(
                TranslationService.get("msg.export_no_note"),
                TranslationService.get("msg.export_no_note_text")
            )

        path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP", "*.zip")]
        )
        if not path:
            return

        try:
            count = self.export_service.export_media_archive(
                self._current_editor_note_for_export(),
                path,
            )
            messagebox.showinfo(
                TranslationService.get("msg.export_success"),
                TranslationService.get("msg.media_zip_success", count=count, path=path)
            )
        except Exception as exc:
            messagebox.showerror(
                TranslationService.get("msg.media_zip_error"),
                str(exc)
            )

    def export_media_zip_with_password(self):
        if not self.current_note:
            return messagebox.showwarning(
                TranslationService.get("msg.export_no_note"),
                TranslationService.get("msg.export_no_note_text")
            )

        password = simpledialog.askstring(
            TranslationService.get("msg.media_zip_password_title"),
            TranslationService.get("msg.media_zip_password_prompt"),
            show="*",
            parent=self,
        )
        if password is None:
            return
        if len(password) < 4:
            return messagebox.showwarning(
                TranslationService.get("msg.media_zip_password_title"),
                TranslationService.get("msg.media_zip_password_short"),
            )

        confirmation = simpledialog.askstring(
            TranslationService.get("msg.media_zip_password_title"),
            TranslationService.get("msg.media_zip_password_confirm"),
            show="*",
            parent=self,
        )
        if confirmation is None:
            return
        if confirmation != password:
            return messagebox.showwarning(
                TranslationService.get("msg.media_zip_password_title"),
                TranslationService.get("msg.media_zip_password_mismatch"),
            )

        path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP", "*.zip")]
        )
        if not path:
            return

        try:
            count = self.export_service.export_encrypted_media_archive(
                self._current_editor_note_for_export(),
                path,
                password,
            )
            messagebox.showinfo(
                TranslationService.get("msg.export_success"),
                TranslationService.get(
                    "msg.media_zip_password_success",
                    count=count,
                    path=path,
                )
            )
        except Exception as exc:
            messagebox.showerror(
                TranslationService.get("msg.media_zip_error"),
                str(exc)
            )

    def open_media_zip(self):
        path = filedialog.askopenfilename(
            title=TranslationService.get("msg.media_zip_open_title"),
            filetypes=[
                ("ZIP", "*.zip"),
                (TranslationService.get("filetype.all_files"), "*.*"),
            ]
        )
        if not path:
            return

        password = None
        try:
            if self.export_service.archive_requires_password(path):
                password = simpledialog.askstring(
                    TranslationService.get("msg.media_zip_password_title"),
                    TranslationService.get("msg.media_zip_open_password"),
                    show="*",
                    parent=self,
                )
                if password is None:
                    return
        except Exception as exc:
            return messagebox.showerror(
                TranslationService.get("msg.media_zip_error"),
                str(exc),
            )

        destination = filedialog.askdirectory(
            title=TranslationService.get("msg.media_zip_destination")
        )
        if not destination:
            return

        try:
            count = self.export_service.extract_media_archive(
                path,
                destination,
                password=password,
            )
            messagebox.showinfo(
                TranslationService.get("msg.export_success"),
                TranslationService.get(
                    "msg.media_zip_extract_success",
                    count=count,
                    path=destination,
                )
            )
        except RuntimeError:
            messagebox.showerror(
                TranslationService.get("msg.media_zip_error"),
                TranslationService.get("msg.media_zip_wrong_password"),
            )
        except Exception as exc:
            messagebox.showerror(
                TranslationService.get("msg.media_zip_error"),
                str(exc)
            )

    def on_close(self):
        from tkinter import messagebox
        answer = messagebox.askyesnocancel(
            TranslationService.get("msg.close_title"),
            TranslationService.get("msg.close_prompt"),
        )
        if answer is True: 
            self.quit_app_completely()
            
        elif answer is False:  
            self._minimize_to_tray()
            
        else:  
            pass

    def _minimize_to_tray(self):
        import pystray
        from PIL import Image
        import threading
        self.withdraw()
        try:
            bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
            icon_path = (bundle_root / "icon.png").resolve()
            image = Image.open(icon_path)
        except Exception:
            image = Image.new('RGB', (64, 64), color=(0, 0, 0))
        menu = pystray.Menu(
            pystray.MenuItem(TranslationService.get("tray.open"), self.show_window_from_tray),
            pystray.MenuItem(TranslationService.get("tray.quit"), self.quit_app_completely)
        )
        self.tray_icon = pystray.Icon(
            "Engraver",
            image,
            TranslationService.get("tray.tooltip"),
            menu,
        )
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window_from_tray(self, icon=None, item=None):
        """Restore the Tk window from a pystray callback."""
        tray_icon = icon or getattr(self, "tray_icon", None)
        if tray_icon is not None:
            try:
                tray_icon.stop()
            except Exception:
                pass

        def restore_window():
            self.tray_icon = None
            self.deiconify()
            self.state("normal")
            self.lift()
            self.focus_force()

        # pystray invokes menu callbacks on its own worker thread. All Tk calls
        # must be marshalled back to the UI thread.
        self.after(0, restore_window)

    def quit_app_completely(self, icon=None, item=None):
        """Stop background services and close the application completely."""
        import threading

        tray_icon = icon or getattr(self, "tray_icon", None)
        if tray_icon is not None:
            try:
                tray_icon.stop()
            except Exception:
                pass

        def shutdown():
            self.tray_icon = None
            reminder_service = getattr(self, "reminder_service", None)
            if reminder_service is not None:
                reminder_service.stop()
            database = getattr(getattr(self, "repo", None), "db", None)
            if database is not None:
                database.close()
            self.quit()
            self.destroy()

        if threading.current_thread() is threading.main_thread():
            shutdown()
        else:
            self.after(0, shutdown)

    def import_from_file(self):
        """Mở file txt, md, docx hoặc pdf, bóc toàn bộ văn bản và ảnh đính kèm."""
        import os
        import tempfile
        from pathlib import Path
        file_path = filedialog.askopenfilename(
            title=TranslationService.get("import.title"),
            filetypes=[
                (TranslationService.get("import.supported_documents"), "*.txt *.md *.docx *.pdf"),
                (TranslationService.get("filetype.word_document"), "*.docx"),
                (TranslationService.get("filetype.pdf_files"), "*.pdf"),
                (TranslationService.get("filetype.text_markdown"), "*.txt *.md"),
                (TranslationService.get("filetype.all_files"), "*.*"),
            ]
        )
        
        if not file_path:
            return
        import_note_id = str(uuid.uuid4())
        try:
            ext = os.path.splitext(file_path)[1].lower()
            content_text = ""
            extracted_media_list = []
            with tempfile.TemporaryDirectory() as temp_dir:
                if ext == ".docx":
                    import docx2txt
                    content_text = docx2txt.process(file_path, temp_dir)
                    for img_name in os.listdir(temp_dir):
                        img_path = os.path.join(temp_dir, img_name)
                        try:
                            attachment = self.editor.media_service.import_file(
                                Path(img_path), note_id=import_note_id
                            )
                            attachment["position"] = len(content_text)
                            extracted_media_list.append(attachment)
                        except Exception:
                            pass

                elif ext == ".pdf":
                    try:
                        import fitz 
                        doc = fitz.open(file_path)
                        
                        for page_index in range(len(doc)):
                            page = doc[page_index]
                            content_text += page.get_text() + "\n"
                            
                            image_list = page.get_images(full=True)
                            for img_idx, img in enumerate(image_list):
                                xref = img[0]
                                base_image = doc.extract_image(xref)
                                image_bytes = base_image["image"]
                                image_ext = base_image["ext"]
                                
                                temp_img_name = f"pdf_extracted_p{page_index}_{img_idx}.{image_ext}"
                                temp_img_path = os.path.join(temp_dir, temp_img_name)
                                with open(temp_img_path, "wb") as img_f:
                                    img_f.write(image_bytes)
                                
                                attachment = self.editor.media_service.import_file(
                                    Path(temp_img_path), note_id=import_note_id
                                )
                                attachment["position"] = len(content_text)
                                extracted_media_list.append(attachment)
                    except ImportError:
                        messagebox.showerror(
                            TranslationService.get("import.missing_pymupdf_title"),
                            TranslationService.get("import.missing_pymupdf_text"),
                        )
                        return
                else:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content_text = f.read()
                file_name = os.path.basename(file_path).split('.')[0]
                self.prepare_new("Text", note_id=import_note_id)
                self.editor.entry_title.delete(0, 'end')
                self.editor.entry_title.insert(0, file_name)
                full_note_content = {
                    "text": content_text,
                    "spans": [],
                    "media": extracted_media_list
                }
                self.editor._render_content(full_note_content)
                self.editor._media_attachments = extracted_media_list
                messagebox.showinfo(
                    TranslationService.get("msg.export_success"),
                    TranslationService.get("import.success", count=len(extracted_media_list)),
                )
        except Exception as e:
            self.editor.media_service.delete_note_media(import_note_id)
            messagebox.showerror(
                TranslationService.get("import.error_title"),
                TranslationService.get("import.error_text", error=e),
            )
