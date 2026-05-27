from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, MutableSequence


class Command(ABC):
    """
    Interface chung cho tất cả command.

    Mỗi command phải hỗ trợ:
    - execute(): thực thi hành động
    - undo(): hoàn tác hành động
    """

    @abstractmethod
    def execute(self) -> None:
        """Thực thi command."""
        raise NotImplementedError

    @abstractmethod
    def undo(self) -> None:
        """Hoàn tác command."""
        raise NotImplementedError


class NoteModelAdapter:
    """
    Adapter giúp Command Pattern làm việc với Models hiện có.

    Lý do cần Adapter:
    - Models hiện tại dùng _id, _content là protected attributes.
    - Task Command Pattern không được sửa Models.
    - Command cần một cách thống nhất để đọc/ghi id, title, content.

    Khi Models được cải thiện sau này, chỉ cần sửa Adapter này,
    các command bên dưới không cần thay đổi.
    """

    @staticmethod
    def get_id(note: Any) -> str:
        """
        Lấy ID của note.

        Ưu tiên dùng public property 'id' nếu có.
        Nếu không có, fallback sang '_id' của Models hiện tại.
        """
        if hasattr(note, "id"):
            return str(note.id)

        if hasattr(note, "_id"):
            return str(note._id)

        raise AttributeError("Note object không có id hoặc _id.")

    @staticmethod
    def set_title(note: Any, new_title: str) -> None:
        """
        Cập nhật title cho note.

        Ưu tiên dùng property setter 'title' của model hiện có
        để tận dụng validation trong BaseNote/base.
        """
        if hasattr(note, "title"):
            note.title = new_title
            return

        if hasattr(note, "_title"):
            note._title = new_title
            return

        raise AttributeError("Note object không có title hoặc _title.")

    @staticmethod
    def set_content(note: Any, new_content: Any) -> None:
        """
        Cập nhật content cho note.

        Nếu model có method update_content thì dùng method đó.
        Nếu không, fallback sang _content vì Models hiện tại dùng _content.
        """
        if hasattr(note, "update_content"):
            note.update_content(new_content)
            return

        if hasattr(note, "_content"):
            note._content = new_content
            return

        raise AttributeError("Note object không có content hoặc _content.")

    @staticmethod
    def snapshot(note: Any) -> dict[str, Any]:
        """
        Tạo bản sao trạng thái hiện tại của note để phục vụ undo.

        Dùng __dict__ để hỗ trợ được nhiều loại note:
        - TextNote
        - ChecklistNote
        - MediaNote
        """
        return deepcopy(note.__dict__)

    @staticmethod
    def restore(note: Any, state: dict[str, Any]) -> None:
        """
        Khôi phục lại trạng thái note từ snapshot.

        Cách này giúp undo EditCommand mà không cần biết note là loại gì.
        """
        note.__dict__.clear()
        note.__dict__.update(deepcopy(state))


class AddCommand(Command):
    """
    Command thêm note vào danh sách note.

    Phù hợp với giai đoạn hiện tại khi chưa có Repository chính thức.
    Sau này nếu nhóm Data Access làm Repository, ta có thể viết thêm
    AddNoteRepositoryCommand mà không phá code hiện tại.
    """

    def __init__(self, note: Any, note_list: MutableSequence[Any]) -> None:
        self._note = note
        self._note_list = note_list
        self._insert_index: int | None = None

    def execute(self) -> None:
        """
        Thêm note vào danh sách.

        Nếu note đã tồn tại theo id thì không thêm trùng.
        """
        note_id = NoteModelAdapter.get_id(self._note)

        for existing_note in self._note_list:
            if NoteModelAdapter.get_id(existing_note) == note_id:
                return

        self._note_list.append(self._note)
        self._insert_index = len(self._note_list) - 1

    def undo(self) -> None:
        """Hoàn tác thêm note bằng cách xóa note vừa thêm."""
        note_id = NoteModelAdapter.get_id(self._note)

        for index, note in enumerate(self._note_list):
            if NoteModelAdapter.get_id(note) == note_id:
                self._note_list.pop(index)
                return


class EditCommand(Command):
    """
    Command chỉnh sửa note.

    Command này hỗ trợ sửa title và content.
    Có thể dùng cho:
    - TextNote
    - ChecklistNote
    - MediaNote

    Vì content của mỗi loại note có thể khác nhau, kiểu new_content để là Any.
    """

    def __init__(
        self,
        note: Any,
        new_title: str | None = None,
        new_content: Any | None = None,
    ) -> None:
        self._note = note
        self._new_title = new_title
        self._new_content = new_content
        self._old_state: dict[str, Any] | None = None

    def execute(self) -> None:
        """Cập nhật note và lưu trạng thái cũ để undo."""
        if self._old_state is None:
            self._old_state = NoteModelAdapter.snapshot(self._note)

        if self._new_title is not None:
            NoteModelAdapter.set_title(self._note, self._new_title)

        if self._new_content is not None:
            NoteModelAdapter.set_content(self._note, self._new_content)

    def undo(self) -> None:
        """Khôi phục note về trạng thái trước khi sửa."""
        if self._old_state is None:
            return

        NoteModelAdapter.restore(self._note, self._old_state)


class DeleteCommand(Command):
    """
    Command xóa note khỏi danh sách.

    Undo của delete là chèn lại note vào đúng vị trí cũ.
    """

    def __init__(self, note_id: str, note_list: MutableSequence[Any]) -> None:
        self._note_id = note_id
        self._note_list = note_list
        self._backup_note: Any | None = None
        self._backup_index: int | None = None

    def execute(self) -> None:
        """Tìm note theo id, backup lại rồi xóa khỏi danh sách."""
        for index, note in enumerate(self._note_list):
            if NoteModelAdapter.get_id(note) == self._note_id:
                self._backup_note = note
                self._backup_index = index
                self._note_list.pop(index)
                return

    def undo(self) -> None:
        """Chèn lại note đã xóa vào vị trí ban đầu."""
        if self._backup_note is None or self._backup_index is None:
            return

        note_id = NoteModelAdapter.get_id(self._backup_note)

        for existing_note in self._note_list:
            if NoteModelAdapter.get_id(existing_note) == note_id:
                return

        self._note_list.insert(self._backup_index, self._backup_note)


class CommandHistory:
    """
    Quản lý lịch sử undo/redo bằng hai stack.

    - undo_stack: chứa các command đã thực thi
    - redo_stack: chứa các command vừa undo
    """

    def __init__(self) -> None:
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []

    def execute_command(self, command: Command) -> None:
        """
        Thực thi command và đưa vào undo stack.

        Khi có thao tác mới, redo stack phải được xóa.
        """
        command.execute()
        self._undo_stack.append(command)
        self._redo_stack.clear()

    def undo(self) -> None:
        """Hoàn tác command gần nhất."""
        if not self._undo_stack:
            return

        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)

    def redo(self) -> None:
        """Thực hiện lại command vừa undo."""
        if not self._redo_stack:
            return

        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)

    def can_undo(self) -> bool:
        """Kiểm tra có thể undo hay không."""
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        """Kiểm tra có thể redo hay không."""
        return bool(self._redo_stack)

    # Giữ lại tên cũ để tránh lỗi nếu UI hoặc file khác đang gọi tên này.
    def pushExecutedCommand(self, command: Command) -> None:
        """
        Deprecated.

        Dùng execute_command() thay thế.
        Method này được giữ lại để tương thích với code cũ.
        """
        self.execute_command(command)