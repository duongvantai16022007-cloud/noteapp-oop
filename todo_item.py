class TodoItem:
    """Phần tử công việc con trong Checklist."""

    def __init__(self, content, is_done=False):
        self._content = content
        self._is_done = is_done

    @property
    def content(self):
        return self._content

    @property
    def is_done(self):
        return self._is_done

    def toggle_status(self):
        """Đảo ngược trạng thái hoàn thành."""
        self._is_done = not self._is_done

    def to_dict(self):
        return {"content": self._content, "is_done": self._is_done}