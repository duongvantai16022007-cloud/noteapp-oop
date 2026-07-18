from datetime import datetime
import uuid

class Folder:
    """Lớp quản lý thư mục, áp dụng Composite Pattern để chứa Note và Folder con."""

    def __init__(self, name):
        self._id = str(uuid.uuid4())
        self._name = name
        self._items = []
        self._created_at = datetime.now()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if not value or value.strip() == "":
            raise ValueError("Tên thư mục không được trống.")
        self._name = value

    def add_item(self, item):
        """Thêm Note hoặc Folder con."""
        if item not in self._items:
            self._items.append(item)

    def remove_item(self, item):
        """Xóa phần tử khỏi thư mục."""
        if item in self._items:
            self._items.remove(item)

    def get_all_notes(self):
        """Đệ quy lấy toàn bộ Note trong thư mục này và các thư mục con."""
        notes = []
        for item in self._items:
            if isinstance(item, Folder):
                notes.extend(item.get_all_notes())
            else:
                notes.append(item)
        return notes
