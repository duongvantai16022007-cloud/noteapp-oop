import json
import uuid
import datetime
from .DatabaseManager import DatabaseManager

class NoteRepository:
    def __init__(self, db=None):
        self.db = db or DatabaseManager()

    def _normalize_content(self, content):
        if isinstance(content, (list, dict)):
            return json.dumps(content, ensure_ascii=False)
        return content if content is not None else ""

    def _normalize_tags(self, tags_data):
        if isinstance(tags_data, (list, dict)):
            return json.dumps(tags_data, ensure_ascii=False)
        return "[]" if tags_data is None else tags_data

    def _row_to_note_dict(self, row):
        note_dict = dict(row)
        try:
            note_dict['tags'] = json.loads(note_dict['tags']) if note_dict.get('tags') else []
        except json.JSONDecodeError:
            note_dict['tags'] = []

        # SQLite trả 0/1, chuyển về bool để UI/model dễ dùng.
        note_dict['is_locked'] = bool(note_dict.get('is_locked', 0))
        note_dict['reminder_notified'] = int(note_dict.get('reminder_notified') or 0)
        note_dict['deadline_notified'] = int(note_dict.get('deadline_notified') or 0)
        return note_dict

    def create_note(self, note):
        note = dict(note)  # Tránh làm biến đổi dict bên ngoài command/model.
        note_id = note.get('id') or str(uuid.uuid4())
        created_at = note.get('created_at') or datetime.datetime.now().replace(microsecond=0).isoformat()
        updated_at = note.get('updated_at') or created_at
        tags_str = self._normalize_tags(note.get('tags', []))
        content_str = self._normalize_content(note.get('content', ''))

        query = '''
                INSERT INTO notes (
                    id, type, title, content, media_path, tags, created_at, updated_at, folder_id,
                    is_locked, password_hash, password_salt, reminder_at, deadline_at, reminder_notified, deadline_notified, deleted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''

        params = (
            note_id,
            note.get('type', 'Text'),
            note.get('title', ''),
            content_str,
            note.get('media_path', None),
            tags_str,
            created_at,
            updated_at,
            note.get('folder_id', None),
            1 if note.get('is_locked') else 0,
            note.get('password_hash'),
            note.get('password_salt'),
            note.get('reminder_at') or None,
            note.get('deadline_at') or None,
            int(note.get('reminder_notified') or 0),
            int(note.get('deadline_notified') or 0),
            note.get('deleted_at') or None,
        )

        self.db.execute_query(query, params)
        return note_id

    def create_folder(self, name, parent_id=None):
        name = str(name or "").strip()
        if not name:
            raise ValueError("Tên thư mục không được để trống")
        if parent_id and not self.get_folder(parent_id):
            raise ValueError("Thư mục cha không tồn tại")
        folder_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().replace(microsecond=0).isoformat()
        query = "INSERT INTO folders (id, name, created_at, parent_id) VALUES (?, ?, ?, ?)"
        self.db.execute_query(query, (folder_id, name, created_at, parent_id or None))
        return folder_id

    def get_all_folders(self):
        query = "SELECT * FROM folders ORDER BY name COLLATE NOCASE ASC, created_at ASC"
        return self.db.fetch_all(query)

    def get_folder(self, folder_id):
        return self.db.fetch_one("SELECT * FROM folders WHERE id = ?", (folder_id,))

    def get_descendant_folder_ids(self, folder_id):
        rows = self.get_all_folders()
        children = {}
        for row in rows:
            children.setdefault(row["parent_id"], []).append(row["id"])
        descendants = []
        pending = list(children.get(folder_id, []))
        seen = {folder_id}
        while pending:
            child_id = pending.pop()
            if child_id in seen:
                continue
            seen.add(child_id)
            descendants.append(child_id)
            pending.extend(children.get(child_id, []))
        return descendants

    def move_folder(self, folder_id, parent_id=None):
        if not self.get_folder(folder_id):
            raise ValueError("Thư mục không tồn tại")
        if parent_id:
            if not self.get_folder(parent_id):
                raise ValueError("Thư mục cha không tồn tại")
            if parent_id == folder_id or parent_id in self.get_descendant_folder_ids(folder_id):
                raise ValueError("Không thể chuyển thư mục vào chính nó hoặc thư mục con")
        self.db.execute_query(
            "UPDATE folders SET parent_id = ? WHERE id = ?",
            (parent_id or None, folder_id),
        )

    def move_note_to_folder(self, note_id, folder_id):
        """Cập nhật folder_id của Note. Nếu folder_id=None nghĩa là đưa ra ngoài thư mục gốc."""
        updated_at = datetime.datetime.now().replace(microsecond=0).isoformat()
        query = "UPDATE notes SET folder_id = ?, updated_at = ? WHERE id = ?"
        self.db.execute_query(query, (folder_id, updated_at, note_id))

    def get_notes_by_folder(self, folder_id):
        """Lấy danh sách các note nằm trong một folder cụ thể"""
        if folder_id is None:
            query = "SELECT * FROM notes WHERE (folder_id IS NULL OR folder_id = '') AND (deleted_at IS NULL OR deleted_at = '')"
            return [self._row_to_note_dict(row) for row in self.db.fetch_all(query)]
        else:
            query = "SELECT * FROM notes WHERE folder_id = ? AND (deleted_at IS NULL OR deleted_at = '')"
            return [self._row_to_note_dict(row) for row in self.db.fetch_all(query, (folder_id,))]

    def get_note(self, note_id):
        query = "SELECT * FROM notes WHERE id = ?"
        row = self.db.fetch_one(query, (note_id, ))
        if row:
            return self._row_to_note_dict(row)
        return None

    def get_all_notes(self):
        query = "SELECT * FROM notes WHERE (deleted_at IS NULL OR deleted_at = '') ORDER BY updated_at DESC"
        rows = self.db.fetch_all(query)
        return [self._row_to_note_dict(row) for row in rows]

    def update_note(self, note):
        note = dict(note)
        content_str = self._normalize_content(note.get('content', ''))
        tags_str = self._normalize_tags(note.get('tags', []))
        updated_at = datetime.datetime.now().replace(microsecond=0).isoformat()

        query = '''
                UPDATE notes
                SET title = ?, content = ?, media_path = ?, tags = ?, folder_id = ?, updated_at = ?,
                    is_locked = ?, password_hash = ?, password_salt = ?,
                    reminder_at = ?, deadline_at = ?, reminder_notified = ?, deadline_notified = ?
                WHERE id = ?
                '''

        params = (
            note.get('title'),
            content_str,
            note.get('media_path', None),
            tags_str,
            note.get('folder_id'),
            updated_at,
            1 if note.get('is_locked') else 0,
            note.get('password_hash'),
            note.get('password_salt'),
            note.get('reminder_at') or None,
            note.get('deadline_at') or None,
            int(note.get('reminder_notified') or 0),
            int(note.get('deadline_notified') or 0),
            note.get('id'),
        )

        self.db.execute_query(query, params)

    def update_note_content(self, note_id, content):
        """Persist migrated media paths without changing the note timestamp."""
        self.db.execute_query(
            "UPDATE notes SET content = ? WHERE id = ?",
            (self._normalize_content(content), note_id),
        )

    def update_note_media_path(self, note_id, media_path):
        """Persist an absolute migrated path without changing updated_at."""
        self.db.execute_query(
            "UPDATE notes SET media_path = ? WHERE id = ?",
            (media_path, note_id),
        )

    def update_note_security(self, note_id, is_locked, password_hash=None, password_salt=None):
        query = '''
            UPDATE notes
            SET is_locked = ?, password_hash = ?, password_salt = ?, updated_at = ?
            WHERE id = ?
        '''
        self.db.execute_query(query, (
            1 if is_locked else 0,
            password_hash,
            password_salt,
            datetime.datetime.now().replace(microsecond=0).isoformat(),
            note_id
        ))

    def mark_reminder_notified(self, note_id):
        query = "UPDATE notes SET reminder_notified = 1 WHERE id = ?"
        self.db.execute_query(query, (note_id,))

    def mark_deadline_notified(self, note_id):
        query = "UPDATE notes SET deadline_notified = 1 WHERE id = ?"
        self.db.execute_query(query, (note_id,))

    def get_due_reminders(self, current_iso):
        query = '''
            SELECT * FROM notes
            WHERE reminder_at IS NOT NULL
              AND reminder_at != ''
              AND reminder_notified = 0
              AND (deleted_at IS NULL OR deleted_at = '')
              AND reminder_at <= ?
            ORDER BY reminder_at ASC
        '''
        rows = self.db.fetch_all(query, (current_iso,))
        return [self._row_to_note_dict(row) for row in rows]

    def get_due_deadlines(self, current_iso):
        query = '''
            SELECT * FROM notes
            WHERE deadline_at IS NOT NULL
              AND deadline_at != ''
              AND deadline_notified = 0
              AND (deleted_at IS NULL OR deleted_at = '')
              AND deadline_at <= ?
            ORDER BY deadline_at ASC
        '''
        rows = self.db.fetch_all(query, (current_iso,))
        return [self._row_to_note_dict(row) for row in rows]

    def get_timed_notes(self):
        query = '''
            SELECT * FROM notes
            WHERE ((reminder_at IS NOT NULL AND reminder_at != '')
               OR (deadline_at IS NOT NULL AND deadline_at != ''))
               AND (deleted_at IS NULL OR deleted_at = '')
            ORDER BY COALESCE(deadline_at, reminder_at) ASC
        '''
        rows = self.db.fetch_all(query)
        return [self._row_to_note_dict(row) for row in rows]

    def delete_note(self, note_id):
        deleted_at = datetime.datetime.now().replace(microsecond=0).isoformat()
        query = "UPDATE notes SET deleted_at = ?, updated_at = ? WHERE id = ?"
        self.db.execute_query(query, (deleted_at, deleted_at, note_id))

    def restore_deleted_note(self, note_id):
        updated_at = datetime.datetime.now().replace(microsecond=0).isoformat()
        query = "UPDATE notes SET deleted_at = NULL, updated_at = ? WHERE id = ?"
        self.db.execute_query(query, (updated_at, note_id))

    def permanently_delete_note(self, note_id):
        query = "DELETE FROM notes WHERE id = ?"
        self.db.execute_query(query, (note_id,))

    def get_deleted_notes(self, limit=20):
        query = '''
            SELECT * FROM notes
            WHERE deleted_at IS NOT NULL AND deleted_at != ''
            ORDER BY deleted_at DESC
            LIMIT ?
        '''
        rows = self.db.fetch_all(query, (limit,))
        return [self._row_to_note_dict(row) for row in rows]

    def purge_expired_deleted_notes(self, days=30):
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).replace(microsecond=0).isoformat()
        select_query = '''
            SELECT id FROM notes
            WHERE deleted_at IS NOT NULL
              AND deleted_at != ''
              AND deleted_at <= ?
        '''
        expired_ids = [row["id"] for row in self.db.fetch_all(select_query, (cutoff,))]
        delete_query = '''
            DELETE FROM notes
            WHERE deleted_at IS NOT NULL
              AND deleted_at != ''
              AND deleted_at <= ?
        '''
        self.db.execute_query(delete_query, (cutoff,))
        return expired_ids

    def delete_folder(self, folder_id):
        """Delete one folder, preserving children by moving them one level up."""
        folder = self.get_folder(folder_id)
        if not folder:
            return
        parent_id = folder["parent_id"]
        self.db.execute_transaction([
            ("UPDATE notes SET folder_id = NULL WHERE folder_id = ?", (folder_id,)),
            ("UPDATE folders SET parent_id = ? WHERE parent_id = ?", (parent_id, folder_id)),
            ("DELETE FROM folders WHERE id = ?", (folder_id,)),
        ])
