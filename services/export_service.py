from fpdf import FPDF

class ExportService:
    
    def export_to_markdown(self, note, file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {note.title}\n\n")
            f.write(note.content)

    def export_to_pdf(self, note, file_path):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, txt=note.title, ln=True)
        pdf.multi_cell(0, 10, note.content)

        pdf.output(file_path)