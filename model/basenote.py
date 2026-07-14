from abc import ABC, abstractmethod
from datetime import datetime
import uuid

class base(ABC):
    """
    Lớp cơ sở cho mọi loại ghi chú.

    Các thuộc tính chính vẫn giữ theo code cũ (_id, _title, _content, _tags),
    đồng thời bổ sung metadata cho bảo mật và lịch biểu.
    """
    def __init__(
        self,
        title,
        content,
        tags=None,
        reminder_at=None,
        deadline_at=None,
        is_locked=False,
        password_hash=None,
        password_salt=None,
        reminder_notified=0,
        folder_id=None
    ):
        self._id = str(uuid.uuid4())
        self._title = title
        self._content = content
        self._tags = tags if tags else []
        self._created = datetime.now()
        self._updated = self._created

        # Metadata mới
        self._reminder_at = reminder_at
        self._deadline_at = deadline_at
        self._is_locked = bool(is_locked)
        self._password_hash = password_hash
        self._password_salt = password_salt
        self._reminder_notified = int(reminder_notified or 0)
        self._folder_id = folder_id

    @property
    def id(self):
        return self._id

    @property
    def folder_id(self):
        return self._folder_id

    @folder_id.setter
    def folder_id(self, value):
        self._folder_id = value
        self._updated = datetime.now()

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        if not value or value.strip() == "":
           raise ValueError("Tiêu đề không được để trống hoặc chỉ chứa khoảng trắng.")
        if len(value) > 20:
            raise ValueError(f"Tiêu đề quá dài ({len(value)} ký tự). Tối đa là 20.")
        self._title = value
        self._updated = datetime.now()

    @property
    def content(self):
        return self._content

    @property
    def tags(self):
        return self._tags

    @property
    def created_at(self):
        return self._created

    @property
    def updated_at(self):
        return self._updated

    @property
    def reminder_at(self):
        return self._reminder_at

    @property
    def deadline_at(self):
        return self._deadline_at

    @property
    def is_locked(self):
        return self._is_locked

    @property
    def password_hash(self):
        return self._password_hash

    @property
    def password_salt(self):
        return self._password_salt

    @property
    def reminder_notified(self):
        return self._reminder_notified

    def update_content(self, new_content):
        self._content = new_content
        self._updated = datetime.now()

    def update_metadata(self, **kwargs):
        """Cập nhật các trường metadata mới mà không phá cấu trúc model cũ."""
        for key, value in kwargs.items():
            setattr(self, f"_{key}", value)
        self._updated = datetime.now()

    def set_lock_info(self, is_locked, password_hash=None, password_salt=None):
        self._is_locked = bool(is_locked)
        self._password_hash = password_hash
        self._password_salt = password_salt
        self._updated = datetime.now()

    def _base_dict(self):
        return {
            "id": self._id,
            "title": self._title,
            "tags": self._tags,
            "created_at": self._created.isoformat(),
            "updated_at": self._updated.isoformat(),
            "reminder_at": self._reminder_at,
            "deadline_at": self._deadline_at,
            "is_locked": self._is_locked,
            "password_hash": self._password_hash,
            "password_salt": self._password_salt,
            "reminder_notified": self._reminder_notified,
            "folder_id": self._folder_id
        }

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
