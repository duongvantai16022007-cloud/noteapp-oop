import sqlite3
import threading
import os

class DatabaseManager:

    _instances = {}
    _instance = None

    def __new__(cls, *args, **kwargs):
        if 'db_path' in kwargs and isinstance(kwargs['db_path'], str):
            db_path = kwargs['db_path']
        elif args and isinstance(args[0], str):
            db_path = args[0]
        else:
            db_path = 'notes.db'
        db_path = os.path.abspath(db_path)

        inst = cls._instances.get(db_path)
        if inst is None:
            inst = super(DatabaseManager, cls).__new__(cls)
            cls._instances[db_path] = inst
        cls._instance = inst
        return inst

    def __init__(self, db_path = "notes.db"):
        if getattr(self, '_initialized', False):
            if not hasattr(self, '_lock'):
                self._lock = threading.RLock()
            recreate = False
            if not hasattr(self, 'connection') or self.connection is None:
                recreate = True
            else:
                try:
                    self.connection.cursor()
                except sqlite3.ProgrammingError:
                    recreate = True

            if recreate:
                self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
                self.connection.row_factory = sqlite3.Row
                with self._lock:
                    self._create_tables()

            return

        self.db_path = os.path.abspath(db_path)
        self._lock = threading.RLock()
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        with self._lock:
            self._create_tables()

        self._initialized = True
    def _create_tables(self):
        """
        Tạo các bảng mặc định nếu chúng chưa tồn tại.
        """
        cursor = self.connection.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,         -- 'text', 'checklist', or 'media'
                title TEXT,
                content TEXT,               -- Holds text, or checklist JSON
                media_path TEXT,            -- Holds the file path for MediaNotes
                tags TEXT,                  -- Can store tags as a JSON string
                created_at TEXT,
                updated_at TEXT,
                folder_id TEXT              -- For your Folder Composite Pattern
            )
        ''')

        self.connection.commit()

    def execute_query(self, query, params=()):
        """
        Dùng khi muốn chỉnh sửa database.
        Ví dụ: INSERT, UPDATE, DELETE, v.v
        """
        with self._lock:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            return cursor

    def fetch_all(self, query, params=()):
        """
        Dùng khi muốn truy vấn một danh sách dữ liệu.
        Ví dụ: SELECT * FROM notes.
        """
        with self._lock:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def fetch_one(self, query, params=()):
        """
        Dùng khi muốn truy vấn một dữ liệu cụ thể.
        Ví dụ: SELECT * FROM notes WHERE id = 5.
        """
        with self._lock:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()

    def close(self):
        """
        Close the underlying SQLite connection and reset the singleton.
        """
        with getattr(self, '_lock', threading.RLock()):
            if hasattr(self, 'connection') and self.connection:
                try:
                    self.connection.close()
                finally:
                    try:
                        delattr(self, 'connection')
                    except Exception:
                        pass
            inst_map = type(self)._instances
            if self.db_path in inst_map:
                del inst_map[self.db_path]

            if getattr(type(self), '_instance', None) is self:
                type(self)._instance = None