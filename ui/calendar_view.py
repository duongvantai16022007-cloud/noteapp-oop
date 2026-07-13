import customtkinter as ctk
import datetime
import calendar
from services.theme_service import ThemeManager

class CTkCalendarView(ctk.CTkToplevel):
    def __init__(self, master, repo, on_open_note):
        super().__init__(master)
        
        self.repo = repo
        self.on_open_note_callback = on_open_note
        self.calendar_month = datetime.date.today().replace(day=1)

        self.withdraw()  # Hide immediately to prevent alignment jumps
        self.title("📅 Calendar View - Lịch biểu ghi chú")
        self.geometry("950x650")
        
        # Dual-theme window background
        self.configure(fg_color=ThemeManager.get("popup_bg"))
        self.transient(master)
        self.grab_set()

        # Center the window relative to parent
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - 950) // 2
        y = master.winfo_y() + (master.winfo_height() - 650) // 2
        self.geometry(f"+{x}+{y}")

        # Header for Month Navigation
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 8))
        
        self.title_label = ctk.CTkLabel(
            header, 
            text="", 
            font=ctk.CTkFont(size=20, weight="bold"), 
            text_color=ThemeManager.get("text_primary")
        )
        self.title_label.pack(side="left", expand=True)
        
        ctk.CTkButton(
            header, 
            text="← Tháng trước", 
            width=120, 
            fg_color=ThemeManager.get("btn_secondary"),
            text_color=ThemeManager.get("text_primary"),
            hover_color=ThemeManager.get("btn_secondary_hover"),
            command=lambda: self._change_calendar_month(-1)
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            header, 
            text="Tháng sau →", 
            width=120, 
            fg_color=ThemeManager.get("btn_secondary"),
            text_color=ThemeManager.get("text_primary"),
            hover_color=ThemeManager.get("btn_secondary_hover"),
            command=lambda: self._change_calendar_month(1)
        ).pack(side="left", padx=5)

        note = ctk.CTkLabel(
            self,
            text="🔔 = Reminder, 📌 = Deadline. Bấm vào ghi chú trong lịch để mở.",
            text_color=ThemeManager.get("text_secondary")
        )
        note.pack(fill="x", padx=15, pady=(0, 8))

        # Main Calendar Grid Container
        self.grid_frame = ctk.CTkFrame(
            self, 
            fg_color=ThemeManager.get("grid_bg"), 
            border_width=2, 
            border_color=ThemeManager.get("grid_border")
        )
        self.grid_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        self._draw_calendar()
        self.deiconify()  # Show once positioned and styled

    def _date_from_iso(self, iso_str):
        if not iso_str:
            return None
        try:
            return datetime.datetime.fromisoformat(iso_str).date()
        except Exception:
            return None

    def _change_calendar_month(self, delta):
        year = self.calendar_month.year
        month = self.calendar_month.month + delta
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        self.calendar_month = datetime.date(year, month, 1)
        self._draw_calendar()

    def _draw_calendar(self):
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        for col in range(7):
            self.grid_frame.grid_columnconfigure(col, weight=1, uniform="calendar")
        for row in range(7):
            self.grid_frame.grid_rowconfigure(row, weight=1, uniform="calendar")

        self.title_label.configure(text=f"Tháng {self.calendar_month.month:02d}/{self.calendar_month.year}")

        weekdays = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        for col, day_name in enumerate(weekdays):
            ctk.CTkLabel(
                self.grid_frame, 
                text=day_name, 
                font=ctk.CTkFont(weight="bold"),
                text_color=ThemeManager.get("text_weekday")
            ).grid(row=0, column=col, padx=3, pady=3, sticky="nsew")

        events_by_date = {}
        for note in self.repo.get_timed_notes():
            for field, icon in (("reminder_at", "🔔"), ("deadline_at", "📌")):
                date_value = self._date_from_iso(note.get(field))
                if date_value and date_value.year == self.calendar_month.year and date_value.month == self.calendar_month.month:
                    events_by_date.setdefault(date_value, []).append((icon, note))

        month_matrix = calendar.Calendar(firstweekday=0).monthdatescalendar(self.calendar_month.year, self.calendar_month.month)
        for week_index, week in enumerate(month_matrix, start=1):
            for col, day in enumerate(week):
                cell = ctk.CTkFrame(
                    self.grid_frame,
                    border_width=2,
                    fg_color=ThemeManager.get("cell_bg"),
                    border_color=ThemeManager.get("cell_border")
                )
                cell.grid(row=week_index, column=col, padx=3, pady=3, sticky="nsew")
                cell.grid_columnconfigure(0, weight=1)

                is_current_month = day.month == self.calendar_month.month
                day_color = ThemeManager.get("text_primary") if is_current_month else ThemeManager.get("text_muted")
                ctk.CTkLabel(cell, text=str(day.day), anchor="w", text_color=day_color).pack(fill="x", padx=6, pady=(4, 1))

                for icon, note in events_by_date.get(day, [])[:3]:
                    title = note.get("title", "Không có tiêu đề")
                    if len(title) > 13:
                        title = title[:13] + "…"
                    ctk.CTkButton(
                        cell,
                        text=f"{icon} {title}",
                        height=20,
                        font=ctk.CTkFont(size=11),
                        fg_color=ThemeManager.get("btn_note"),
                        text_color=ThemeManager.get("text_primary"),
                        hover_color=ThemeManager.get("btn_note_hover"),
                        anchor="w",
                        command=lambda note_id=note["id"]: self._open_note_from_calendar(note_id)
                    ).pack(fill="x", padx=4, pady=1)

                extra_count = max(0, len(events_by_date.get(day, [])) - 3)
                if extra_count:
                    ctk.CTkLabel(
                        cell, 
                        text=f"+{extra_count} mục khác", 
                        text_color=ThemeManager.get("text_extra"), 
                        font=ctk.CTkFont(size=10)
                    ).pack(fill="x", padx=6)

    def _open_note_from_calendar(self, note_id):
        self.destroy()
        if self.on_open_note_callback:
            self.on_open_note_callback(note_id)
