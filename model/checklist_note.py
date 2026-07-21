from .basenote import base
from .todo_item import TodoItem

class ChecklistNote(base):
    """Lớp quản lý ghi chú dạng danh sách (áp dụng Composition)."""

    def __init__(
        self,
        title,
        content=None,
        tags=None,
        reminder_at=None,
        deadline_at=None,
        is_locked=False,
        password_hash=None,
        password_salt=None,
        reminder_notified=0,
        deadline_notified=0,
        folder_id=None,
    ):
        todo_list = []
        if content:
            for item in content:
                if isinstance(item, TodoItem):
                    todo_list.append(item)
                elif isinstance(item, dict):
                    todo_list.append(TodoItem(item.get("content", ""), item.get("is_done", False)))

        super().__init__(
            title,
            todo_list,
            tags,
            reminder_at=reminder_at,
            deadline_at=deadline_at,
            is_locked=is_locked,
            password_hash=password_hash,
            password_salt=password_salt,
            reminder_notified=reminder_notified,
            deadline_notified=deadline_notified,
            folder_id=folder_id,
        )

    def get_type(self):
        return "Checklist"

    def add_todo(self, content):
        """Thêm TodoItem mới vào danh sách."""
        self._content.append(TodoItem(content))

    def calculate_progress(self):
        """Tính % công việc đã hoàn thành (0.0 - 100.0)."""
        if not self._content:
            return 0.0
        done_count = sum(1 for item in self._content if item.is_done)
        return (done_count / len(self._content)) * 100

    def to_dict(self):
        data = self._base_dict()
        data.update({
            "type": self.get_type(),
            "content": [item.to_dict() for item in self._content]
        })
        return data
