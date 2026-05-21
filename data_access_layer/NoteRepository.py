import json
import uuid
import datetime
from DatabaseManager import DatabaseManager

class NoteRepository:
    """
    Repository cho phép thực hiện các thao tác CRUD lên Database,
    tách biệt logic SQL khỏi UI và Models.
    """
    def __init__(self):
        """
        Khởi tạo NoteRepository và lấy kết nối từ DatabaseManager.
        """
        self.db = DatabaseManager()
    
    def create_note(self, note):
        """
        Nhận vào 1 ghi chú (dictionary hoặc object) và lưu vào SQLite.
        """
        # Provide sensible defaults for missing fields (id, created_at).
        note_id = note.get('id') or str(uuid.uuid4())
        created_at = note.get('created_at') or datetime.datetime.utcnow().isoformat()

        # Ensure media_path is persisted when creating media notes.
        query = '''
                INSERT INTO notes (id, type, title, content, media_path, tags, created_at, folder_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                '''
        tags_json = json.dumps(note.get('tags', []))

        params = (
            note_id,
            note.get('type', 'text'),
            note.get('title', ''),
            note.get('content', ''),
            note.get('media_path', None),
            tags_json,
            created_at,
            note.get('folder_id', None)
        )

        self.db.execute_query(query, params)

        # Return the id so callers can continue using it.
        return note_id
    
    def get_note(self, note_id):
        """
        Đọc một ghi chú cụ thể dựa vào ID.
        """
        query = "SELECT * FROM notes WHERE id = ?"

        row = self.db.fetch_one(query, (note_id, ))

        if row:
            note_dict = dict(row)
            note_dict['tags'] = json.loads(note_dict['tags']) if note_dict['tags'] else []
            return note_dict
        
        return None
    
    def get_all_notes(self):
        """
        Lấy một danh sách tất cả các ghi chú.
        """
        query = "SELECT * FROM notes"
        rows = self.db.fetch_all(query)

        notes = []
        for row in rows:
            note_dict = dict(row)
            note_dict['tags'] = json.loads(note_dict['tags']) if note_dict['tags'] else []
            notes.append(note_dict)
        
        return notes
    
    def update_note(self, note):
        """
        Cập nhật nội dung một ghi chú đã có.
        """
        query = '''
                UPDATE notes
                SET title = ?, content = ?, media_path = ?, tags = ?, folder_id = ? 
                WHERE id = ?
                '''
        tags_json = json.dumps(note.get('tags', []))

        params = (
            note.get('title'),
            note.get('content'),
            note.get('media_path', None),
            tags_json,
            note.get('folder_id'),
            note.get('id'),
        )

        self.db.execute_query(query, params)

    def delete_note(self, note_id):
        """
        Xoá vĩnh viễn một ghi chú theo ID.
        """
        query = "DELETE FROM notes WHERE id = ?"
        self.db.execute_query(query, (note_id, ))