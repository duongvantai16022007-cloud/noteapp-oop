import customtkinter as ctk
from tkinter import messagebox, filedialog
import os

from data.NoteRepository import NoteRepository
from model.note_factory import NoteFactory 
from commands.command_history import CommandHistory
from commands.note_commands import AddCommand, EditCommand, DeleteCommand
from services.export_service import ExportService

from ui.sidebar import SidebarFrame
from ui.editor import EditorFrame

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.repo = NoteRepository()
        self.history = CommandHistory()
        self.export_service = ExportService()
        self.current_note = None 
        self.title("Engraver Note App - Full Features")
        self.geometry("1100x700")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar = SidebarFrame(
            self, 
            on_note_select=self.load_note, 
            on_new_text_note=lambda: self.prepare_new("Text"),
            on_new_checklist=lambda: self.prepare_new("Checklist"),
            on_search=self.handle_search
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.editor = EditorFrame(
            self, 
            on_save=self.save_note, 
            on_delete=self.delete_note,
            on_undo=self.handle_undo,
            on_redo=self.handle_redo,
            on_export_md=self.export_md,
            on_export_pdf=self.export_pdf
        )
        self.editor.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        self.refresh_sidebar()
        self.prepare_new("Text") 

    def refresh_sidebar(self):
        self.sidebar.update_list(self.repo.get_all_notes())

    def prepare_new(self, note_type):
        self.current_note = None
        self.editor.set_data("", "", note_type)
        self.editor.btn_delete.configure(state="disabled")

    def load_note(self, note_id):
        note_data = self.repo.get_note(note_id)
        if note_data:
            self.current_note = NoteFactory.from_dict(note_data)
            
            
            self.editor.set_data(
                self.current_note.title, 
                self.current_note.content, 
                self.current_note.get_type()
            )
            self.editor.btn_delete.configure(state="normal")

    def save_note(self, data, note_type):
        if not data["title"]: return messagebox.showwarning("Lỗi", "Tiêu đề không được trống!")
        
        if self.current_note is None: 
            raw_data = {"id": "", "type": note_type, "title": data["title"], "content": data["content"]}
            new_note_obj = NoteFactory.from_dict(raw_data)
            
            command = AddCommand(new_note_obj, self.repo)
            self.history.execute_command(command)
            self.current_note = new_note_obj
        else: 
            command = EditCommand(self.current_note, self.repo, new_title=data["title"], new_content=data["content"])
            self.history.execute_command(command)
            
        self.refresh_sidebar()
        self.editor.btn_delete.configure(state="normal")

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

    def handle_search(self, event):
        keyword = self.sidebar.search_entry.get().strip().lower()
        notes = [n for n in self.repo.get_all_notes() if keyword in n['title'].lower() or str(n['content']).lower().find(keyword) != -1]
        self.sidebar.update_list(notes)

    def export_md(self):
        if not self.current_note: return messagebox.showwarning("Lỗi", "Chọn ghi chú để xuất!")
        path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown", "*.md")])
        if path:
            self.export_service.export_to_markdown(self.current_note, path)
            messagebox.showinfo("Thành công", f"Đã xuất tại: {path}")

    def export_pdf(self):
        if not self.current_note: return messagebox.showwarning("Lỗi", "Chọn ghi chú để xuất!")
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if path:
            try:
                self.export_service.export_to_pdf(self.current_note, path)
                messagebox.showinfo("Thành công", f"Đã xuất tại: {path}")
            except Exception as e:
                messagebox.showerror("Lỗi PDF", f"Không xuất được PDF: {e}")