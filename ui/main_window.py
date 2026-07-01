import customtkinter as ctk
from tkinter import messagebox, filedialog, simpledialog
import datetime
import calendar

from data.NoteRepository import NoteRepository
from model.note_factory import NoteFactory
from commands.command_history import CommandHistory
from commands.note_commands import AddCommand, EditCommand, DeleteCommand
from services.export_service import ExportService
from services.security_service import SecurityManager
from services.reminder_service import ReminderService
from services.settings_service import SettingsService

from ui.sidebar import SidebarFrame
from ui.editor import EditorFrame

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.repo = NoteRepository()
        self.history = CommandHistory()
        self.export_service = ExportService()
        self.security_manager = SecurityManager()
        self.settings_service = SettingsService()
        self.settings = self.settings_service.get_all()
        self.current_note = None
        self.calendar_month = datetime.date.today().replace(day=1)

        self.title("Engraver Note App - Full Features")
        self.geometry("1200x760")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar = SidebarFrame(
            self,
            on_note_select=self.load_note,
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

        # Reminder chạy nền, callback đưa thông báo về main thread bằng self.after.
        self.reminder_service = ReminderService(self.repo, callback=self.handle_reminder_due, interval=10)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.refresh_sidebar()
        self.prepare_new("Text")

    # =========================
    # Helpers
    # =========================
    def refresh_sidebar(self):
        self.sidebar.update_list(self.repo.get_all_notes())

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

        return {
            "reminder_at": reminder_at,
            "deadline_at": deadline_at,
            "reminder_notified": reminder_notified
        }

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
                self.history.execute_command(command)
                self.current_note = new_note_obj
            else:
                command = EditCommand(
                    self.current_note,
                    self.repo,
                    new_title=data["title"],
                    new_content=data["content"],
                    new_extra=extra
                )
                self.history.execute_command(command)
        except ValueError as exc:
            return messagebox.showwarning("Lỗi", str(exc))

        self.refresh_sidebar()
        self.editor.btn_delete.configure(state="normal")
        self.editor.set_lock_state(is_locked=self.current_note.is_locked, enabled=True)
        messagebox.showinfo("Thành công", "Đã lưu ghi chú.")

    def delete_note(self):
        if self.current_note and messagebox.askyesno("Xác nhận", "Xóa ghi chú?"):
            command = DeleteCommand(self.current_note.id, self.repo)
            self.history.execute_command(command)
            self.prepare_new("Text")
            self.refresh_sidebar()

    def handle_undo(self):
        self.history.undo()
        self.refresh_sidebar()
        if self.current_note:
            self.load_note(self.current_note.id)

    def handle_redo(self):
        self.history.redo()
        self.refresh_sidebar()
        if self.current_note:
            self.load_note(self.current_note.id)

    def handle_search(self, event=None):
        keyword = self.sidebar.search_entry.get().strip().lower()
        notes = []
        for note in self.repo.get_all_notes():
            title_match = keyword in note.get('title', '').lower()
            # Ghi chú đã khóa không bị search theo content để tránh đọc thuộc tính bên trong khi chưa nhập pass.
            content_match = False if note.get("is_locked") else keyword in str(note.get('content', '')).lower()
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
    def handle_reminder_due(self, note_dict):
        def show_notification():
            messagebox.showinfo(
                "🔔 Nhắc nhở ghi chú",
                f"Đã đến giờ nhắc cho ghi chú: {note_dict.get('title', 'Không có tiêu đề')}"
            )
            self.refresh_sidebar()
        self.after(0, show_notification)

    def _date_from_iso(self, value):
        if not value:
            return None
        try:
            return datetime.datetime.fromisoformat(str(value)).date()
        except ValueError:
            return None

    def _change_calendar_month(self, delta, window, grid_frame, title_label):
        year = self.calendar_month.year
        month = self.calendar_month.month + delta
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        self.calendar_month = datetime.date(year, month, 1)
        self._draw_calendar(window, grid_frame, title_label)

    def open_calendar_view(self):
        window = ctk.CTkToplevel(self)
        window.title("📅 Calendar View - Lịch biểu ghi chú")
        window.geometry("950x650")
        window.transient(self)
        window.grab_set()

        header = ctk.CTkFrame(window, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 8))
        title_label = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(side="left", expand=True)
        ctk.CTkButton(header, text="← Tháng trước", width=120, command=lambda: self._change_calendar_month(-1, window, grid_frame, title_label)).pack(side="left", padx=5)
        ctk.CTkButton(header, text="Tháng sau →", width=120, command=lambda: self._change_calendar_month(1, window, grid_frame, title_label)).pack(side="left", padx=5)

        note = ctk.CTkLabel(
            window,
            text="🔔 = Reminder, 📌 = Deadline. Bấm vào ghi chú trong lịch để mở.",
            text_color=("gray35", "gray75")
        )
        note.pack(fill="x", padx=15, pady=(0, 8))

        grid_frame = ctk.CTkFrame(window)
        grid_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self._draw_calendar(window, grid_frame, title_label)

    def _draw_calendar(self, window, grid_frame, title_label):
        for widget in grid_frame.winfo_children():
            widget.destroy()

        for col in range(7):
            grid_frame.grid_columnconfigure(col, weight=1, uniform="calendar")
        for row in range(7):
            grid_frame.grid_rowconfigure(row, weight=1, uniform="calendar")

        title_label.configure(text=f"Tháng {self.calendar_month.month:02d}/{self.calendar_month.year}")

        weekdays = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        for col, day_name in enumerate(weekdays):
            ctk.CTkLabel(grid_frame, text=day_name, font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=col, padx=3, pady=3, sticky="nsew"
            )

        events_by_date = {}
        for note in self.repo.get_timed_notes():
            for field, icon in (("reminder_at", "🔔"), ("deadline_at", "📌")):
                date_value = self._date_from_iso(note.get(field))
                if date_value and date_value.year == self.calendar_month.year and date_value.month == self.calendar_month.month:
                    events_by_date.setdefault(date_value, []).append((icon, note))

        month_matrix = calendar.Calendar(firstweekday=0).monthdatescalendar(self.calendar_month.year, self.calendar_month.month)
        for week_index, week in enumerate(month_matrix, start=1):
            for col, day in enumerate(week):
                cell = ctk.CTkFrame(grid_frame, border_width=1)
                cell.grid(row=week_index, column=col, padx=3, pady=3, sticky="nsew")
                cell.grid_columnconfigure(0, weight=1)

                is_current_month = day.month == self.calendar_month.month
                day_color = ("gray10", "gray90") if is_current_month else ("gray55", "gray45")
                ctk.CTkLabel(cell, text=str(day.day), anchor="w", text_color=day_color).pack(fill="x", padx=6, pady=(4, 1))

                for icon, note in events_by_date.get(day, [])[:3]:
                    title = note.get("title", "Không có tiêu đề")
                    if len(title) > 13:
                        title = title[:13] + "…"
                    ctk.CTkButton(
                        cell,
                        text=f"{icon} {title}",
                        height=24,
                        anchor="w",
                        command=lambda note_id=note["id"], win=window: self._open_note_from_calendar(note_id, win)
                    ).pack(fill="x", padx=4, pady=1)

                extra_count = max(0, len(events_by_date.get(day, [])) - 3)
                if extra_count:
                    ctk.CTkLabel(cell, text=f"+{extra_count} mục khác", text_color=("gray40", "gray70")).pack(fill="x", padx=6)

    def _open_note_from_calendar(self, note_id, window):
        window.destroy()
        self.load_note(note_id)

    # =========================
    # Theme
    # =========================
    def handle_theme_change(self, key, value):
        self.settings_service.set_setting(key, value)
        self.settings[key] = value

        if key == "appearance_mode":
            ctk.set_appearance_mode(value)
        elif key == "color_theme":
            ctk.set_default_color_theme(value)
            messagebox.showinfo(
                "Đã đổi màu chủ đạo",
                "Một số widget hiện tại sẽ đổi ngay; để đồng bộ toàn bộ màu chủ đạo, hãy tắt và mở lại ứng dụng."
            )

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
        if hasattr(self, "reminder_service"):
            self.reminder_service.stop()
        self.destroy()
