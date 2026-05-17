from abc import ABC, abstractmethod
from datetime import datetime
import uuid

class base(ABC):
    """
    Attributes:
        _id (str): Định danh duy nhất cho ghi chú (UUID).
        _title (str): Tiêu đề của ghi chú.
        _content (any): Nội dung ghi chú (văn bản, danh sách, hoặc đường dẫn tệp).
        _tags (list): Danh sách các nhãn dán (strings) để phân loại.
        _created (datetime): Thời điểm ghi chú được tạo.
        _updated (datetime): Thời điểm ghi chú được cập nhật lần cuối.
    """
    def __init__(self, title, content, tags=None):
        self._id = str(uuid.uuid4())
        self._title = title
        self._content = content
        self._tags = tags if tags else []
        self._created = datetime.now()
        self._updated = self._created

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        if not value or value.strip() == "":
           raise ValueError("Tiêu đề không được để trống hoặc chỉ chứa khoảng trắng.")
        if len(value) >20:
            raise ValueError(f"Tiêu đề quá dài ({len(value)} ký tự). Tối đa là 20.")
        self._title = value
        self._updated = datetime.now()

    @abstractmethod
    def get_type(self):
        """Trả về loại ghi chú (Text, Checklist, Media)"""
        pass

    @abstractmethod
    def to_dict(self):
        """Chuyển đổi object sang dictionary để lưu vào SQL/JSON"""
        pass

    def add_tag(self, tag_name):
        """Thêm một nhãn dán mới vào ghi chú nếu nhãn đó chưa tồn tại."""
        if tag_name not in self._tags:
            self._tags.append(tag_name)