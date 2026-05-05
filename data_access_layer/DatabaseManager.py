import sqlite3

class DatabaseManager:
    """
    Singleton DatabaseManager quản lý kết nối SQLite duy nhất
    trong suốt vòng đời của ứng dụng.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Tạo hoặc trả về thể hiện duy nhất của DatabaseManager.
        """
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
     
    def __init__(self, db_path = "notes.db"):
        """
        Khởi tạo kết nối đến database và tạo các bảng cần thiết.
        """
        if not hasattr(self, 'connection'):
            self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()
        pass

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
                folder_id TEXT              -- For your Folder Composite Pattern
            )
        ''')

        self.connection.commit()

    def execute_query(self, query, params=()):
        """
        Dùng khi muốn chỉnh sửa database.
        Ví dụ: INSERT, UPDATE, DELETE, v.v
        """
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        self.connection.commit()
        return cursor

    def fetch_all(self, query, params=()):
        """
        Dùng khi muốn truy vấn một danh sách dữ liệu.
        Ví dụ: SELECT * FROM notes.
        """
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def fetch_one(self, query, params=()):
        """
        Dùng khi muốn truy vấn một dữ liệu cụ thể.
        Ví dụ: SELECT * FROM notes WHERE id = 5.
        """
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()