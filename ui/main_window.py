import customtkinter as ctk
from tkinter import messagebox, filedialog, simpledialog
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

        self.title("Engraver Note App - Full Features")
        self.geometry("1200x760")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Apply settings initially
        initial_appearance = self.settings.get("appearance_mode", "System")
        initial_color = self.settings.get("color_theme", "blue")
        ctk.set_appearance_mode(initial_appearance)
        ctk.set_default_color_theme(initial_color.lower().replace(" ", "-"))
        from services.theme_service import ThemeManager
        ThemeManager.set_active_theme(initial_color)

        self._build_ui()

        # Reminder chạy nền, callback đưa thông báo về main thread bằng self.after.
        self.reminder_service = ReminderService(self.repo, callback=self.handle_reminder_due, interval=10)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.refresh_sidebar()
        self.prepare_new("Text")

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
            on_new_text_note=lambda: self.prepare_new("Text"),
            on_new_checklist=lambda: self.prepare_new("Checklist"),
            on_search=self.handle_search,
            on_open_calendar=self.open_calendar_view,
            on_theme_change=self.handle_theme_change,
            initial_settings=self.settings
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.editor = EditorFrame(
            self,
            on_save=self.save_note,
            on_delete=self.delete_note,
            on_undo=self.handle_undo,
            on_redo=self.handle_redo,
            on_export_md=self.export_md,
            on_export_pdf=self.export_pdf,
            on_lock_toggle=self.toggle_note_lock
        )
        self.editor.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        self._ui_built = True
        self.refresh_sidebar()
        if restore_note_id:
            self.load_note(restore_note_id)
        else:
            self.prepare_new("Text")

    def refresh_sidebar(self):
        self.repo.purge_expired_deleted_notes(days=30)
        self.sidebar.update_list(self.repo.get_all_notes())
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
            raise ValueError("Sai định dạng thời gian. Vui lòng dùng YYYY-MM-DD HH:MM, ví dụ 2026-07-01 20:30.")

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
        self.editor.btn_delete.configure(state="disabled")
        self.editor.set_lock_state(enabled=False)

    def load_note(self, note_id):
        note_data = self.repo.get_note(note_id)
        if not note_data:
            return

        if note_data.get("is_locked"):
            password = simpledialog.askstring("Ghi chú đã khóa", "Nhập mật khẩu để mở ghi chú:", show="*", parent=self)
            if password is None:
                return
            if not self.security_manager.verify_password(
                password,
                note_data.get("password_hash"),
                note_data.get("password_salt")
            ):
                messagebox.showerror("Sai mật khẩu", "Không thể mở ghi chú vì mật khẩu không đúng.")
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
        self.editor.btn_delete.configure(state="normal")
        self.editor.set_lock_state(is_locked=self.current_note.is_locked, enabled=True)

    def save_note(self, data, note_type):
        if not data["title"]:
            return messagebox.showwarning("Lỗi", "Tiêu đề không được trống!")

        try:
            extra = self._note_extra_from_form(data)
        except ValueError as exc:
            return messagebox.showwarning("Lỗi thời gian", str(exc))

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
            return messagebox.showwarning("Lỗi", str(exc))

        self.refresh_sidebar()
        self.editor.btn_delete.configure(state="normal")
        self.editor.set_lock_state(is_locked=self.current_note.is_locked, enabled=True)
        messagebox.showinfo("Thành công", "Đã lưu ghi chú.")

    def delete_note(self):
        if self.current_note and messagebox.askyesno("Xác nhận", "Xóa ghi chú?"):
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
        if messagebox.askyesno("Xác nhận", "Xóa vĩnh viễn ghi chú này? Không thể khôi phục lại."):
            self.repo.permanently_delete_note(note_id)
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
            return messagebox.showwarning("Lỗi", "Hãy lưu ghi chú trước khi đặt mật khẩu.")

        note_data = self.repo.get_note(self.current_note.id)
        if not note_data:
            return messagebox.showwarning("Lỗi", "Không tìm thấy ghi chú hiện tại.")

        if note_data.get("is_locked"):
            password = simpledialog.askstring("Gỡ khóa", "Nhập mật khẩu hiện tại:", show="*", parent=self)
            if password is None:
                return
            if not self.security_manager.verify_password(password, note_data.get("password_hash"), note_data.get("password_salt")):
                return messagebox.showerror("Sai mật khẩu", "Không thể gỡ khóa vì mật khẩu không đúng.")

            self.repo.update_note_security(self.current_note.id, False, None, None)
            self.current_note.set_lock_info(False, None, None)
            self.editor.set_lock_state(False, enabled=True)
            self.refresh_sidebar()
            return messagebox.showinfo("Thành công", "Đã gỡ khóa ghi chú.")

        password_1 = simpledialog.askstring("Khóa ghi chú", "Nhập mật khẩu mới:", show="*", parent=self)
        if password_1 is None:
            return
        if len(password_1) < 4:
            return messagebox.showwarning("Mật khẩu yếu", "Mật khẩu nên có ít nhất 4 ký tự.")
        password_2 = simpledialog.askstring("Xác nhận mật khẩu", "Nhập lại mật khẩu:", show="*", parent=self)
        if password_2 is None:
            return
        if password_1 != password_2:
            return messagebox.showwarning("Không khớp", "Hai lần nhập mật khẩu không giống nhau.")

        password_hash, password_salt = self.security_manager.hash_password(password_1)
        self.repo.update_note_security(self.current_note.id, True, password_hash, password_salt)
        self.current_note.set_lock_info(True, password_hash, password_salt)
        self.editor.set_lock_state(True, enabled=True)
        self.refresh_sidebar()
        messagebox.showinfo("Thành công", "Đã khóa ghi chú. Lần mở sau sẽ cần nhập mật khẩu.")

    # =========================
    # Reminder + Calendar
    # =========================
    def handle_reminder_due(self, note_dict, is_deadline=False):
        def show_notification():
            title = "📌 Hạn chót ghi chú" if is_deadline else "🔔 Nhắc nhở ghi chú"
            msg = (
                f"Đã đến hạn chót (deadline) cho ghi chú: {note_dict.get('title', 'Không có tiêu đề')}"
                if is_deadline
                else f"Đã đến giờ nhắc cho ghi chú: {note_dict.get('title', 'Không có tiêu đề')}"
            )
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
            ctk.set_default_color_theme(value.lower().replace(" ", "-"))
            from services.theme_service import ThemeManager
            ThemeManager.set_active_theme(value)

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
            return messagebox.showwarning("Lỗi", "Chọn ghi chú để xuất!")
        path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown", "*.md")])
        if path:
            self.export_service.export_to_markdown(self.current_note, path)
            messagebox.showinfo("Thành công", f"Đã xuất tại: {path}")

    def export_pdf(self):
        if not self.current_note:
            return messagebox.showwarning("Lỗi", "Chọn ghi chú để xuất!")
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if path:
            try:
                self.export_service.export_to_pdf(self.current_note, path)
                messagebox.showinfo("Thành công", f"Đã xuất tại: {path}")
            except Exception as e:
                messagebox.showerror("Lỗi PDF", f"Không xuất được PDF: {e}")

    def on_close(self):
        self.iconify()
