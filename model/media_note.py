from .basenote import base

class MediaNote(base):
    def __init__(
        self,
        title,
        content="",
        file_path=None,
        file_type="media",
        tags=None,
        reminder_at=None,
        deadline_at=None,
        is_locked=False,
        password_hash=None,
        password_salt=None,
        reminder_notified=0
    ):
        super().__init__(
            title,
            content,
            tags,
            reminder_at=reminder_at,
            deadline_at=deadline_at,
            is_locked=is_locked,
            password_hash=password_hash,
            password_salt=password_salt,
            reminder_notified=reminder_notified
        )
        self._file_path = file_path
        self._file_type = file_type

    @property
    def file_path(self):
        return self._file_path

    def get_type(self):
        return "Media"

    def to_dict(self):
        data = self._base_dict()
        data.update({
            "type": self.get_type(),
            "content": self._content,
            "media_path": self._file_path
        })
        return data
