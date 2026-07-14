from datetime import datetime

class SearchEngine:
    def __init__(self, notes):
        self.notes = notes

    def search_by_keyword(self, keyword: str):
        keyword = keyword.lower()
        return [
            note for note in self.notes
            if keyword in note.title.lower() or keyword in note.content.lower()
        ]

    def filter_by_tag(self, tag_name: str):
        results = []
        for note in self.notes:
            note_tag_names = [t.name if hasattr(t, 'name') else t for t in note.tags]
            if tag_name in note_tag_names:
                results.append(note)
        return results

    def filter_by_date(self, start_date: datetime, end_date: datetime):
        return [
            note for note in self.notes
            if start_date <= note.created_at <= end_date
        ]

    def advanced_search(self, keyword=None, tag=None, start_date=None, end_date=None):
        results = self.notes

        if keyword:
            results = [n for n in results if keyword.lower() in n.title.lower()]

        if tag:
            results = [
                n for n in results 
                if tag in [t.name if hasattr(t, 'name') else t for t in n.tags]
            ]

        if start_date and end_date:
            results = [n for n in results if start_date <= n.created_at <= end_date]

        return results