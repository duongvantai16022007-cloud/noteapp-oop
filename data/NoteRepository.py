import json
import uuid
import datetime
from .DatabaseManager import DatabaseManager

class NoteRepository:
    def __init__(self):
        self.db = DatabaseManager()
    
    def create_note(self, note):
        if isinstance(note.get('content'), (list, dict)):
            note['content'] = json.dumps(note['content'], ensure_ascii=False)
        tags_data = note.get('tags', [])
        if isinstance(tags_data, (list, dict)):
            tags_str = json.dumps(tags_data, ensure_ascii=False)
        else:
            tags_str = str(tags_data) if tags_data is None else tags_data

        note_id = note.get('id') or str(uuid.uuid4())
        created_at = note.get('created_at') or datetime.datetime.utcnow().isoformat()

        query = '''
                INSERT INTO notes (id, type, title, content, media_path, tags, created_at, folder_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                '''

        params = (
            note_id,
            note.get('type', 'text'),
            note.get('title', ''),
            note.get('content', ''),
            note.get('media_path', None),
            tags_str,
            created_at,
            note.get('folder_id', None)
        )

        self.db.execute_query(query, params)
        return note_id
    
    def get_note(self, note_id):
        query = "SELECT * FROM notes WHERE id = ?"
        row = self.db.fetch_one(query, (note_id, ))

        if row:
            note_dict = dict(row)
            try:
                note_dict['tags'] = json.loads(note_dict['tags']) if note_dict['tags'] else []
            except json.JSONDecodeError:
                note_dict['tags'] = []
            return note_dict
        
        return None
    
    def get_all_notes(self):
        query = "SELECT * FROM notes"
        rows = self.db.fetch_all(query)

        notes = []
        for row in rows:
            note_dict = dict(row)
            try:
                note_dict['tags'] = json.loads(note_dict['tags']) if note_dict['tags'] else []
            except json.JSONDecodeError:
                note_dict['tags'] = []
            notes.append(note_dict)
        
        return notes
    
    def update_note(self, note):
        # Tương tự như hàm create_note
        if isinstance(note.get('content'), (list, dict)):
            note['content'] = json.dumps(note['content'], ensure_ascii=False)
        
        tags_data = note.get('tags', [])
        if isinstance(tags_data, (list, dict)):
            tags_str = json.dumps(tags_data, ensure_ascii=False)
        else:
            tags_str = str(tags_data) if tags_data is None else tags_data

        query = '''
                UPDATE notes
                SET title = ?, content = ?, media_path = ?, tags = ?, folder_id = ? 
                WHERE id = ?
                '''

        params = (
            note.get('title'),
            note.get('content'),
            note.get('media_path', None),
            tags_str,
            note.get('folder_id'),
            note.get('id'),
        )

        self.db.execute_query(query, params)

    def delete_note(self, note_id):
        query = "DELETE FROM notes WHERE id = ?"
        self.db.execute_query(query, (note_id, ))