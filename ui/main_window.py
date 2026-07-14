import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog, Menu
import datetime
import calendar

from data.NoteRepository import NoteRepository
from model.note_factory import NoteFactory
from commands.note_commands import AddCommand, EditCommand
from services.export_service import ExportService
from services.security_service import SecurityManager
from services.reminder_service import ReminderService
from services.settings_service import SettingsService

from ui.sidebar import SidebarFrame
from ui.editor import EditorFrame
from ui.calendar_view import CTkCalendarView
from services.translation_service import TranslationService
from services.theme_service import ThemeManager

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.repo = NoteRepository()
        self.export_service = ExportService()
        self.security_manager = SecurityManager()
        self.settings_service = SettingsService()
        self.settings = self.settings_service.get_all()
        self.current_note = None
        self.calendar_month = datetime.date.today().replace(day=1)
        self._ui_built = False

        # Init language from settings
        TranslationService.set_language(self.settings.get("language", "en"))

        self._update_title()
        self.geometry("1200x760")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Apply settings initially
        initial_appearance = self.settings.get("appearance_mode", "System")
        initial_color = self.settings.get("color_theme", "blue")
        ctk.set_appearance_mode(initial_appearance)
        try:
            ctk.set_default_color_theme(initial_color.lower().replace(" ", "-"))
        except Exception:
            ctk.set_default_color_theme("blue")
        ThemeManager.set_active_theme(initial_color)
        self.configure(fg_color=ThemeManager.get("grid_bg"))

        self._build_ui()

        # Reminder background service
        self.reminder_service = ReminderService(self.repo, callback=self.handle_reminder_due, interval=10)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.refresh_sidebar()
        self.prepare_new("Text")

    def _update_title(self):
        self.title(TranslationService.get("app.title"))

    # =========================
    # Helpers
    # =========================
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

        self.editor = EditorFrame(self)
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

        # --- File Menu ---
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(
            label=TranslationService.get("menu.file.new_text"),
            command=lambda: self.prepare_new("Text")
        )
        file_menu.add_command(
            label=TranslationService.get("menu.file.new_checklist"),
            command=lambda: self.prepare_new("Checklist")
        )
        file_menu.add_separator()
        file_menu.add_command(
            label=TranslationService.get("menu.file.save"),
            command=self._menu_save_note
        )
        file_menu.add_command(
            label=TranslationService.get("menu.file.delete"),
            command=self.delete_note
        )
        file_menu.add_separator()
        file_menu.add_command(
            label=TranslationService.get("menu.file.export_md"),
            command=self.export_md
        )
        file_menu.add_command(
            label=TranslationService.get("menu.file.export_pdf"),
            command=self.export_pdf
        )
        menubar.add_cascade(label=TranslationService.get("menu.file"), menu=file_menu)

        # --- Edit Menu ---
        edit_menu = Menu(menubar, tearoff=0)
        edit_menu.add_command(
            label=TranslationService.get("menu.edit.undo"),
            command=self.handle_undo
        )
        edit_menu.add_command(
            label=TranslationService.get("menu.edit.redo"),
            command=self.handle_redo
        )
        menubar.add_cascade(label=TranslationService.get("menu.edit"), menu=edit_menu)

        # --- View Menu ---
        view_menu = Menu(menubar, tearoff=0)
        view_menu.add_command(
            label=TranslationService.get("menu.view.calendar"),
            command=self.open_calendar_view
        )
        menubar.add_cascade(label=TranslationService.get("menu.view"), menu=view_menu)

        # --- Options Menu ---
        options_menu = Menu(menubar, tearoff=0)
        options_menu.add_command(
            label=TranslationService.get("menu.options.lock"),
            command=self.toggle_note_lock
        )
        options_menu.add_separator()

        # Appearance submenu
        appearance_menu = Menu(options_menu, tearoff=0)
        for mode in ["System", "Light", "Dark"]:
            appearance_menu.add_command(
                label=mode,
                command=lambda m=mode: self.handle_theme_change("appearance_mode", m)
            )
        options_menu.add_cascade(
            label=TranslationService.get("menu.options.appearance"),
            menu=appearance_menu
        )

        # Theme submenu
        theme_menu = Menu(options_menu, tearoff=0)
        for t in ThemeManager.get_available_themes():
            theme_menu.add_command(
                label=t,
                command=lambda th=t: self.handle_theme_change("color_theme", th)
            )
        options_menu.add_cascade(
            label=TranslationService.get("menu.options.theme"),
            menu=theme_menu
        )

        # Language submenu
        lang_menu = Menu(options_menu, tearoff=0)
        for lang in TranslationService.get_available_languages():
            lang_menu.add_command(
                label=lang["name"],
                command=lambda code=lang["code"]: self.handle_language_change(code)
            )
        options_menu.add_cascade(
            label=TranslationService.get("menu.options.language"),
            menu=lang_menu
        )

        menubar.add_cascade(label=TranslationService.get("menu.options"), menu=options_menu)

        self.config(menu=menubar)

    def refresh_sidebar(self):
        self.repo.purge_expired_deleted_notes(days=30)
        self.sidebar.update_list(self.repo.get_all_notes())
        self.sidebar.update_deleted_list(self.repo.get_deleted_notes())

    def _parse_datetime_input(self, value):
        """Parse YYYY-MM-DD HH:MM or ISO format; return ISO string or None."""
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
    def prepare_new(self, note_type):
        self.current_note = None
        self.editor.set_data("", "", note_type, reminder_at=None, deadline_at=None, is_locked=False)

    def load_note(self, note_id):
        note_data = self.repo.get_note(note_id)
        if not note_data:
            return

        if note_data.get("is_locked"):
            password = simpledialog.askstring(
                TranslationService.get("msg.lock_title"),
                TranslationService.get("msg.lock_prompt"),
                show="*", parent=self
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
                    TranslationService.get("msg.lock_wrong_text")
                )
                return

        self.current_note = NoteFactory.from_dict(note_data)

        self.editor.set_data(
            self.current_note.title,
            self.current_note.content,
            self.current_note.get_type(),
            reminder_at=self.current_note.reminder_at,
            deadline_at=self.current_note.deadline_at,
            is_locked=self.current_note.is_locked
        )

    def save_note(self, data, note_type):
        if not data["title"]:
            return messagebox.showwarning(
                TranslationService.get("msg.save_error"),
                TranslationService.get("msg.title_empty")
            )

        try:
            extra = self._note_extra_from_form(data)
        except ValueError as exc:
            return messagebox.showwarning(
                TranslationService.get("msg.time_error"),
                str(exc)
            )

        try:
            if self.current_note is None:
                raw_data = {
                    "id": "",
                    "type": note_type,
                    "title": data["title"],
                    "content": data["content"],
                    **extra
                }
                new_note_obj = NoteFactory.from_dict(raw_data)
                command = AddCommand(new_note_obj, self.repo)
                command.execute()
                self.current_note = new_note_obj
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
            return messagebox.showwarning(
                TranslationService.get("msg.save_error"),
                str(exc)
            )

        self.refresh_sidebar()
        messagebox.showinfo(
            TranslationService.get("msg.save_success"),
            TranslationService.get("msg.save_success")
        )

    def delete_note(self):
        if self.current_note and messagebox.askyesno(
            TranslationService.get("msg.delete_confirm"),
            TranslationService.get("msg.delete_confirm_text")
        ):
            self.repo.delete_note(self.current_note.id)
            self.prepare_new("Text")
            self.refresh_sidebar()

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
            TranslationService.get("msg.permanent_delete_confirm_text")
        ):
            self.repo.permanently_delete_note(note_id)
            self.refresh_sidebar()

    def handle_search(self, event=None):
        keyword = self.sidebar.search_entry.get().strip().lower()
        notes = []
        for note in self.repo.get_all_notes():
            title_match = keyword in note.get('title', '').lower()
            content_match = False if note.get("is_locked") else keyword in self._content_to_plain_text(note.get('content', '')).lower()
            if title_match or content_match:
                notes.append(note)
        self.sidebar.update_list(notes)

    # =========================
    # Note Security
    # =========================
    def toggle_note_lock(self):
        if not self.current_note:
            return messagebox.showwarning(
                TranslationService.get("msg.lock_first"),
                TranslationService.get("msg.lock_first_text")
            )

        note_data = self.repo.get_note(self.current_note.id)
        if not note_data:
            return messagebox.showwarning(
                TranslationService.get("msg.lock_not_found"),
                TranslationService.get("msg.lock_not_found_text")
            )

        if note_data.get("is_locked"):
            password = simpledialog.askstring(
                TranslationService.get("menu.options.lock"),
                TranslationService.get("msg.lock_enter_current"),
                show="*", parent=self
            )
            if password is None:
                return
            if not self.security_manager.verify_password(
                password, note_data.get("password_hash"), note_data.get("password_salt")
            ):
                return messagebox.showerror(
                    TranslationService.get("msg.lock_unlock_fail"),
                    TranslationService.get("msg.lock_unlock_fail_text")
                )

            self.repo.update_note_security(self.current_note.id, False, None, None)
            self.current_note.set_lock_info(False, None, None)
            self.refresh_sidebar()
            return messagebox.showinfo(
                TranslationService.get("msg.lock_unlock_success"),
                TranslationService.get("msg.lock_unlock_success_text")
            )

        password_1 = simpledialog.askstring(
            TranslationService.get("menu.options.lock"),
            TranslationService.get("msg.lock_new_password"),
            show="*", parent=self
        )
        if password_1 is None:
            return
        if len(password_1) < 4:
            return messagebox.showwarning(
                TranslationService.get("msg.lock_weak"),
                TranslationService.get("msg.lock_weak_text")
            )
        password_2 = simpledialog.askstring(
            TranslationService.get("msg.lock_confirm"),
            TranslationService.get("msg.lock_confirm_text"),
            show="*", parent=self
        )
        if password_2 is None:
            return
        if password_1 != password_2:
            return messagebox.showwarning(
                TranslationService.get("msg.lock_mismatch"),
                TranslationService.get("msg.lock_mismatch_text")
            )

        password_hash, password_salt = self.security_manager.hash_password(password_1)
        self.repo.update_note_security(self.current_note.id, True, password_hash, password_salt)
        self.current_note.set_lock_info(True, password_hash, password_salt)
        self.refresh_sidebar()
        messagebox.showinfo(
            TranslationService.get("msg.lock_success"),
            TranslationService.get("msg.lock_success_text")
        )

    # =========================
    # Language
    # =========================
    def handle_language_change(self, lang_code):
        try:
            self.wm_attributes("-alpha", 0)
        except Exception:
            pass

        TranslationService.set_language(lang_code)
        self.settings_service.set_setting("language", lang_code)
        self.settings["language"] = lang_code

        restore_note_id = self.current_note.id if self.current_note else None
        self._update_title()
        self._build_ui(restore_note_id=restore_note_id)

        self.update_idletasks()
        try:
            self.wm_attributes("-alpha", 1)
        except Exception:
            pass

    # =========================
    # Reminder + Calendar
    # =========================
    def handle_reminder_due(self, note_dict, is_deadline=False):
        def show_notification():
            note_title = note_dict.get('title', TranslationService.get("sidebar.no_title"))
            if is_deadline:
                title = TranslationService.get("deadline.title")
                msg = TranslationService.get("deadline.text", title=note_title)
            else:
                title = TranslationService.get("reminder.title")
                msg = TranslationService.get("reminder.text", title=note_title)
            messagebox.showinfo(title, msg)
            self.refresh_sidebar()
        self.after(0, show_notification)

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
    def handle_theme_change(self, key, value):
        try:
            self.wm_attributes("-alpha", 0)
        except Exception:
            pass

        self.settings_service.set_setting(key, value)
        self.settings[key] = value

        restore_note_id = self.current_note.id if self.current_note else None

        if key == "appearance_mode":
            ctk.set_appearance_mode(value)
        elif key == "color_theme":
            try:
                ctk.set_default_color_theme(value.lower().replace(" ", "-"))
            except Exception:
                ctk.set_default_color_theme("blue")
            ThemeManager.set_active_theme(value)
            self.configure(fg_color=ThemeManager.get("grid_bg"))

        self._build_ui(restore_note_id=restore_note_id)

        self.update_idletasks()
        try:
            self.wm_attributes("-alpha", 1)
        except Exception:
            pass

    # =========================
    # Export
    # =========================
    def export_md(self):
        if not self.current_note:
            return messagebox.showwarning(
                TranslationService.get("msg.export_no_note"),
                TranslationService.get("msg.export_no_note_text")
            )
        path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown", "*.md")])
        if path:
            self.export_service.export_to_markdown(self.current_note, path)
            messagebox.showinfo(
                TranslationService.get("msg.export_success"),
                TranslationService.get("msg.export_success_text", path=path)
            )

    def export_pdf(self):
        if not self.current_note:
            return messagebox.showwarning(
                TranslationService.get("msg.export_no_note"),
                TranslationService.get("msg.export_no_note_text")
            )
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if path:
            try:
                self.export_service.export_to_pdf(self.current_note, path)
                messagebox.showinfo(
                    TranslationService.get("msg.export_success"),
                    TranslationService.get("msg.export_success_text", path=path)
                )
            except Exception as e:
                messagebox.showerror(
                    TranslationService.get("msg.export_pdf_error"),
                    TranslationService.get("msg.export_pdf_error_text", error=str(e))
                )

    def on_close(self):
        self.iconify()