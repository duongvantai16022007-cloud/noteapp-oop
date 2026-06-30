from .basenote import base
from .todo_item import TodoItem

class ChecklistNote(base):
    """Lớp quản lý ghi chú dạng danh sách (áp dụng Composition)."""

    def __init__(self, title, content=None, tags=None):
        todo_list = []
        if content:
            for item in content:
                if isinstance(item, TodoItem):
                    todo_list.append(item)
                elif isinstance(item, dict):
                    todo_list.append(TodoItem(item["content"], item["is_done"]))
        
        super().__init__(title, todo_list, tags)

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
        return {
            "id": self._id,
            "type": self.get_type(),
            "title": self._title,
            "content": [item.to_dict() for item in self._content],
            "tags": self._tags,
            "created_at": self._created.isoformat(),
            "updated_at": self._updated.isoformat()
        }