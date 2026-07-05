import customtkinter as ctk
from services.theme_service import ThemeManager

class CTkColorPicker(ctk.CTkToplevel):
    def __init__(self, master, title="Chọn màu", initial_color="#000000", on_select=None):
        super().__init__(master)
        
        self.on_select_callback = on_select
        self.selected_color = initial_color
        
        self.withdraw()
        self.title(title)
        self.geometry("380x420")
        self.resizable(False, False)
        self.configure(fg_color=ThemeManager.get("popup_bg"))
        self.transient(master)
        self.grab_set()
        
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - 380) // 2
        y = master.winfo_y() + (master.winfo_height() - 420) // 2
        self.geometry(f"+{x}+{y}")
        
        self.preset_colors = [
            "#000000", "#ffffff", "#ef4444", "#f97316", "#f59e0b",
            "#84cc16", "#22c55e", "#10b981", "#06b6d4", "#3b82f6",
            "#6366f1", "#8b5cf6", "#d946ef", "#f43f5e", "#64748b"
        ]
        
        self._build_ui()
        self.deiconify()

    def _build_ui(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(self.main_frame, text="Màu hiện tại:", font=ctk.CTkFont(weight="bold"), text_color=ThemeManager.get("text_primary")).pack(anchor="w", pady=(0, 5))
        
        self.preview = ctk.CTkFrame(
            self.main_frame, 
            height=60, 
            fg_color=self.selected_color,
            border_width=2,
            border_color=ThemeManager.get("grid_border")
        )
        self.preview.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(self.main_frame, text="Bảng màu có sẵn:", font=ctk.CTkFont(weight="bold"), text_color=ThemeManager.get("text_primary")).pack(anchor="w", pady=(0, 10))
        
        grid = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        grid.pack(fill="x", pady=(0, 15))
        
        for i, color in enumerate(self.preset_colors):
            row = i // 5
            col = i % 5
            btn = ctk.CTkButton(
                grid, 
                text="", 
                width=45, 
                height=45, 
                fg_color=color, 
                hover_color=color,
                corner_radius=8,
                command=lambda c=color: self.set_color(c)
            )
            btn.grid(row=row, column=col, padx=8, pady=8)
            
        self.hex_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.hex_frame.pack(fill="x", pady=(10, 0))
        
        ctk.CTkLabel(self.hex_frame, text="Mã Hex:", font=ctk.CTkFont(weight="bold"), text_color=ThemeManager.get("text_primary")).pack(side="left", padx=(0, 10))
        self.hex_entry = ctk.CTkEntry(self.hex_frame, width=120)
        self.hex_entry.insert(0, self.selected_color)
        self.hex_entry.pack(side="left")
        self.hex_entry.bind("<KeyRelease>", self._on_hex_change)
        
        self.footer = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.footer.pack(fill="x", side="bottom", pady=(20, 0))
        
        self.btn_cancel = ctk.CTkButton(self.footer, text="Hủy", fg_color=ThemeManager.get("btn_cancel"), hover_color=ThemeManager.get("btn_cancel_hover"), text_color=ThemeManager.get("text_primary"), width=100, command=self.destroy)
        self.btn_cancel.pack(side="right", padx=(10, 0))
        
        self.btn_apply = ctk.CTkButton(self.footer, text="Áp dụng", fg_color=ThemeManager.get("accent_primary"), hover_color=ThemeManager.get("accent_primary_hover"), text_color=ThemeManager.get("text_on_accent"), width=100, command=self.apply)
        self.btn_apply.pack(side="right")

    def set_color(self, color):
        self.selected_color = color
        self.hex_entry.delete(0, "end")
        self.hex_entry.insert(0, color)

    def _on_hex_change(self, event):
        val = self.hex_entry.get().strip()
        if len(val) == 7 and val.startswith("#"):
            try:
                self.preview.configure(fg_color=val)
                self.selected_color = val
            except Exception:
                pass

    def apply(self):
        val = self.hex_entry.get().strip()
        if not val.startswith("#") or len(val) != 7:
            return
        if self.on_select_callback:
            self.on_select_callback(val)
        self.destroy()
