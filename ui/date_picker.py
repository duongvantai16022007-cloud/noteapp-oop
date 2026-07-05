import customtkinter as ctk
import datetime
import calendar
from tkinter import messagebox
from services.theme_service import ThemeManager

class CTkDatePicker(ctk.CTkToplevel):
    def __init__(self, master, initial_dt=None, title="Chọn thời gian", on_select=None):
        super().__init__(master)
        self.withdraw()
        
        self.title(title)
        self.geometry("450x550")
        self.resizable(False, False)
        self.configure(fg_color=ThemeManager.get("popup_bg"))
        self.transient(master)
        self.grab_set()

        self.on_select_callback = on_select
        
        if initial_dt is None:
            initial_dt = datetime.datetime.now().replace(second=0, microsecond=0)
            
        self.selected_date = initial_dt.date()
        self.current_month = self.selected_date.replace(day=1)
        self.selected_time = initial_dt.time()

        # Center Window
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - 450) // 2
        y = master.winfo_y() + (master.winfo_height() - 550) // 2
        self.geometry(f"+{x}+{y}")

        self._build_ui()
        self._draw_calendar()
        self.deiconify()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        
        self.lbl_month = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=18, weight="bold"), text_color=ThemeManager.get("text_primary"))
        self.lbl_month.pack(side="left", expand=True)
        
        ctk.CTkButton(
            header, text="←", width=40,
            fg_color=ThemeManager.get("btn_secondary"), text_color=ThemeManager.get("text_primary"), hover_color=ThemeManager.get("btn_secondary_hover"),
            command=lambda: self._change_month(-1)
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            header, text="→", width=40,
            fg_color=ThemeManager.get("btn_secondary"), text_color=ThemeManager.get("text_primary"), hover_color=ThemeManager.get("btn_secondary_hover"),
            command=lambda: self._change_month(1)
        ).pack(side="left", padx=5)

        # Calendar Grid
        self.grid_frame = ctk.CTkFrame(self, fg_color=ThemeManager.get("grid_bg"), border_width=1, border_color=ThemeManager.get("grid_border"))
        self.grid_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Time Selection
        time_frame = ctk.CTkFrame(self, fg_color="transparent")
        time_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(time_frame, text="Giờ:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        
        hours = [f"{i:02d}" for i in range(24)]
        self.hour_var = ctk.StringVar(value=f"{self.selected_time.hour:02d}")
        self.hour_menu = ctk.CTkOptionMenu(time_frame, values=hours, variable=self.hour_var, width=70)
        self.hour_menu.pack(side="left", padx=(0, 20))
        
        ctk.CTkLabel(time_frame, text="Phút:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        
        minutes = [f"{i:02d}" for i in range(60)]
        self.minute_var = ctk.StringVar(value=f"{self.selected_time.minute:02d}")
        self.minute_menu = ctk.CTkOptionMenu(time_frame, values=minutes, variable=self.minute_var, width=70)
        self.minute_menu.pack(side="left")

        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=(10, 20))
        
        ctk.CTkButton(
            footer, text="Đặt về hiện tại", 
            command=self._set_now
        ).pack(side="left")
        
        ctk.CTkButton(
            footer, text="Áp dụng", 
            command=self._apply
        ).pack(side="right")
        
        ctk.CTkButton(
            footer, text="Hủy", 
            fg_color=ThemeManager.get("btn_cancel"), hover_color=ThemeManager.get("btn_cancel_hover"), text_color=ThemeManager.get("text_primary"),
            command=self.destroy
        ).pack(side="right", padx=10)

    def _set_now(self):
        now = datetime.datetime.now()
        self.selected_date = now.date()
        self.current_month = now.date().replace(day=1)
        self.hour_var.set(f"{now.hour:02d}")
        self.minute_var.set(f"{now.minute:02d}")
        self._draw_calendar()

    def _change_month(self, delta):
        year = self.current_month.year
        month = self.current_month.month + delta
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        self.current_month = datetime.date(year, month, 1)
        self._draw_calendar()

    def _draw_calendar(self):
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        for col in range(7):
            self.grid_frame.grid_columnconfigure(col, weight=1, uniform="cal")
        for row in range(7):
            self.grid_frame.grid_rowconfigure(row, weight=1, uniform="cal")

        self.lbl_month.configure(text=f"Tháng {self.current_month.month:02d}/{self.current_month.year}")

        weekdays = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        for col, day_name in enumerate(weekdays):
            ctk.CTkLabel(
                self.grid_frame, text=day_name, font=ctk.CTkFont(weight="bold"),
                text_color=ThemeManager.get("text_weekday")
            ).grid(row=0, column=col, padx=2, pady=2, sticky="nsew")

        month_matrix = calendar.Calendar(firstweekday=0).monthdatescalendar(self.current_month.year, self.current_month.month)
        
        for week_index, week in enumerate(month_matrix, start=1):
            for col, day in enumerate(week):
                is_current_month = day.month == self.current_month.month
                is_selected = day == self.selected_date
                
                bg_color = ThemeManager.get("accent_primary") if is_selected else (ThemeManager.get("grid_bg") if is_current_month else ThemeManager.get("cell_bg_muted"))
                text_color = ThemeManager.get("text_on_accent") if is_selected else (ThemeManager.get("text_primary") if is_current_month else ThemeManager.get("text_muted"))
                hover_bg = ThemeManager.get("accent_primary_hover") if is_current_month else ThemeManager.get("cell_border")
                
                btn = ctk.CTkButton(
                    self.grid_frame,
                    text=str(day.day),
                    fg_color=bg_color,
                    text_color=text_color,
                    hover_color=hover_bg,
                    corner_radius=4,
                    command=lambda d=day: self._select_date(d)
                )
                btn.grid(row=week_index, column=col, padx=2, pady=2, sticky="nsew")

    def _select_date(self, day):
        self.selected_date = day
        # If user clicks a date outside the current month, optionally jump to that month
        if day.month != self.current_month.month:
            self.current_month = day.replace(day=1)
        self._draw_calendar()

    def _apply(self):
        try:
            h = int(self.hour_var.get())
            m = int(self.minute_var.get())
            selected_dt = datetime.datetime(
                self.selected_date.year,
                self.selected_date.month,
                self.selected_date.day,
                h, m
            )
            
            if self.on_select_callback:
                self.on_select_callback(selected_dt.strftime("%Y-%m-%d %H:%M"))
                
            self.destroy()
        except ValueError:
            messagebox.showwarning("Lỗi thời gian", "Vui lòng chọn ngày, giờ và phút hợp lệ.")
