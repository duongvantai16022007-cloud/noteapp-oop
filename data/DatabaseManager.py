import sqlite3
import threading
import os
import sys
from pathlib import Path


def _default_db_path():
    """Return an absolute database path independent from the process CWD."""
    if getattr(sys, "frozen", False):
        if sys.platform == "win32":
            app_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Engraver"
        elif sys.platform == "darwin":
            app_dir = Path.home() / "Library" / "Application Support" / "Engraver"
        else:
            app_dir = Path.home() / ".engraver"
    else:
        app_dir = Path(__file__).resolve().parent.parent
    app_dir = app_dir.expanduser().resolve()
    app_dir.mkdir(parents=True, exist_ok=True)
    return str((app_dir / "notes.db").resolve())

class DatabaseManager:

    _instances = {}
    _instance = None

    def __new__(cls, *args, **kwargs):
        if 'db_path' in kwargs and isinstance(kwargs['db_path'], str):
            db_path = kwargs['db_path']
        elif args and isinstance(args[0], str):
            db_path = args[0]
        else:
            db_path = _default_db_path()
        db_path = os.path.abspath(db_path)

        inst = cls._instances.get(db_path)
        if inst is None:
            inst = super(DatabaseManager, cls).__new__(cls)
            cls._instances[db_path] = inst
        cls._instance = inst
        return inst

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = _default_db_path()
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
                self.connection.execute("PRAGMA foreign_keys = ON")
                with self._lock:
                    self._create_tables()

            return

        self.db_path = os.path.abspath(db_path)
        self._lock = threading.RLock()
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        with self._lock:
            self._create_tables()

        self._initialized = True

    def _create_tables(self):
        """
        Tạo bảng mặc định và tự migrate các cột mới nếu database cũ đã tồn tại.
        """
        cursor = self.connection.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,          -- 'Text', 'Checklist', hoặc 'Media'
                title TEXT,
                content TEXT,                -- Text thuần/Markdown, hoặc Checklist JSON
                media_path TEXT,
                tags TEXT,
                created_at TEXT,
                updated_at TEXT,
                folder_id TEXT,
                deleted_at TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS folders (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                parent_id TEXT DEFAULT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        # Các cột bổ sung cho bảo mật, reminder/deadline.
        self._add_column_if_not_exists("notes", "is_locked", "INTEGER DEFAULT 0")
        self._add_column_if_not_exists("notes", "password_hash", "TEXT")
        self._add_column_if_not_exists("notes", "password_salt", "TEXT")
        self._add_column_if_not_exists("notes", "reminder_at", "TEXT")
        self._add_column_if_not_exists("notes", "deadline_at", "TEXT")
        self._add_column_if_not_exists("notes", "reminder_notified", "INTEGER DEFAULT 0")
        self._add_column_if_not_exists("notes", "deadline_notified", "INTEGER DEFAULT 0")
        self._add_column_if_not_exists("notes", "deleted_at", "TEXT")
        self._add_column_if_not_exists("folders", "parent_id", "TEXT DEFAULT NULL")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_folder_id ON notes(folder_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_folders_parent_id ON folders(parent_id)")

        self.connection.commit()

    def _add_column_if_not_exists(self, table_name, column_name, column_def):
        cursor = self.connection.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = [row[1] for row in cursor.fetchall()]
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")

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

    def execute_transaction(self, statements):
        """Execute multiple statements atomically."""
        with self._lock:
            cursor = self.connection.cursor()
            try:
                for query, params in statements:
                    cursor.execute(query, params)
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise

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
