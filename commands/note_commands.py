from typing import Any
from .command import Command, NoteModelAdapter

class AddCommand(Command):
    def __init__(self, note: Any, repo: Any) -> None:
        self._note = note
        self._repo = repo

    def execute(self) -> None:
        created_id = self._repo.create_note(self._note.to_dict())
        # Nếu note mới đang có id rỗng, đồng bộ lại id object để update/delete hoạt động đúng.
        if hasattr(self._note, "_id") and not getattr(self._note, "_id", None):
            self._note._id = created_id

    def undo(self) -> None:
        note_id = NoteModelAdapter.get_id(self._note)
        self._repo.delete_note(note_id)


class EditCommand(Command):
    def __init__(
        self,
        note: Any,
        repo: Any,
        new_title: str | None = None,
        new_content: Any | None = None,
        new_extra: dict[str, Any] | None = None
    ) -> None:
        self._note = note
        self._repo = repo
        self._new_title = new_title
        self._new_content = new_content
        self._new_extra = new_extra or {}
        self._old_state: dict[str, Any] | None = None

    def execute(self) -> None:
        if self._old_state is None:
            self._old_state = NoteModelAdapter.snapshot(self._note)
        if self._new_title is not None:
            NoteModelAdapter.set_title(self._note, self._new_title)
        if self._new_content is not None:
            NoteModelAdapter.set_content(self._note, self._new_content)
        if self._new_extra:
            if hasattr(self._note, "update_metadata"):
                self._note.update_metadata(**self._new_extra)
            else:
                for key, value in self._new_extra.items():
                    setattr(self._note, f"_{key}", value)
        self._repo.update_note(self._note.to_dict())

    def undo(self) -> None:
        if self._old_state is None:
            return
        NoteModelAdapter.restore(self._note, self._old_state)
        self._repo.update_note(self._note.to_dict())


class DeleteCommand(Command):
    def __init__(self, note_id: str, repo: Any) -> None:
        self._note_id = note_id
        self._repo = repo
        self._backup_note_dict: dict[str, Any] | None = None

    def execute(self) -> None:
        self._backup_note_dict = self._repo.get_note(self._note_id)
        if self._backup_note_dict:
            self._repo.delete_note(self._note_id)

    def undo(self) -> None:
        if self._backup_note_dict:
            restore_note = getattr(self._repo, "restore_deleted_note", None)
            if callable(restore_note):
                restore_note(self._note_id)
            else:
                self._repo.create_note(self._backup_note_dict)
