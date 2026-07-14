# from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any


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
    """

    @staticmethod
    def get_id(note: Any) -> str:
        if hasattr(note, "id"):
            return str(note.id)
        if hasattr(note, "_id"):
            return str(note._id)
        raise AttributeError("Note object không có id hoặc _id.")

    @staticmethod
    def set_title(note: Any, new_title: str) -> None:
        if hasattr(note, "title"):
            note.title = new_title
            return
        if hasattr(note, "_title"):
            note._title = new_title
            return
        raise AttributeError("Note object không có title hoặc _title.")

    @staticmethod
    def set_content(note: Any, new_content: Any) -> None:
        if hasattr(note, "update_content"):
            note.update_content(new_content)
            return
        if hasattr(note, "_content"):
            note._content = new_content
            return
        raise AttributeError("Note object không có content hoặc _content.")

    @staticmethod
    def snapshot(note: Any) -> dict[str, Any]:
        return deepcopy(note.__dict__)

    @staticmethod
    def restore(note: Any, state: dict[str, Any]) -> None:
        note.__dict__.clear()
        note.__dict__.update(deepcopy(state))