from fpdf import FPDF

class ExportService:

    def _content_to_text(self, note):
        content = note.content
        if isinstance(content, list):
            lines = []
            for item in content:
                if isinstance(item, dict):
                    mark = "x" if item.get("is_done") else " "
                    lines.append(f"- [{mark}] {item.get('content', '')}")
                else:
                    mark = "x" if getattr(item, "is_done", False) else " "
                    lines.append(f"- [{mark}] {getattr(item, 'content', str(item))}")
            return "\n".join(lines)
        return str(content or "")

    def export_to_markdown(self, note, file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {note.title}\n\n")
            if note.deadline_at:
                f.write(f"**Deadline:** {note.deadline_at}\n\n")
            if note.reminder_at:
                f.write(f"**Reminder:** {note.reminder_at}\n\n")
            f.write(self._content_to_text(note))

    def export_to_pdf(self, note, file_path):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, txt=note.title, ln=True)
        if note.deadline_at:
            pdf.multi_cell(0, 10, f"Deadline: {note.deadline_at}")
        if note.reminder_at:
            pdf.multi_cell(0, 10, f"Reminder: {note.reminder_at}")
        pdf.multi_cell(0, 10, self._content_to_text(note))

        pdf.output(file_path)
