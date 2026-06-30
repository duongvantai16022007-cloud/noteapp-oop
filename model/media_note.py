from .basenote import base

class MediaNote(base):
    """Lớp quản lý ghi chú có đính kèm file (ảnh/âm thanh)."""

    def __init__(self, title, content, file_path, file_type, tags=None):
        super().__init__(title, content, tags)
        self._file_path = file_path
        self._file_type = file_type

    @property
    def file_path(self):
        return self._file_path

    def get_type(self):
        return "Media"

    def to_dict(self):
        return {
            "id": self._id,
            "type": self.get_type(),
            "title": self._title,
            "content": self._content,
            "file_path": self._file_path,
            "file_type": self._file_type,
            "tags": self._tags,
            "created_at": self._created.isoformat(),
            "updated_at": self._updated.isoformat()
        }