from typing import Any, MutableSequence
from .command import Command, NoteModelAdapter

class AddCommand(Command):
    def __init__(self, note: Any, note_list: MutableSequence[Any]) -> None:
        self._note = note
        self._note_list = note_list
        self._insert_index: int | None = None

    def execute(self) -> None:
        note_id = NoteModelAdapter.get_id(self._note)
        for existing_note in self._note_list:
            if NoteModelAdapter.get_id(existing_note) == note_id:
                return

        self._note_list.append(self._note)
        self._insert_index = len(self._note_list) - 1

    def undo(self) -> None:
        note_id = NoteModelAdapter.get_id(self._note)
        for index, note in enumerate(self._note_list):
            if NoteModelAdapter.get_id(note) == note_id:
                self._note_list.pop(index)
                return

class EditCommand(Command):
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
        if self._old_state is None:
            self._old_state = NoteModelAdapter.snapshot(self._note)

        if self._new_title is not None:
            NoteModelAdapter.set_title(self._note, self._new_title)

        if self._new_content is not None:
            NoteModelAdapter.set_content(self._note, self._new_content)

    def undo(self) -> None:
        if self._old_state is None:
            return
        NoteModelAdapter.restore(self._note, self._old_state)

class DeleteCommand(Command):
    def __init__(self, note_id: str, note_list: MutableSequence[Any]) -> None:
        self._note_id = note_id
        self._note_list = note_list
        self._backup_note: Any | None = None
        self._backup_index: int | None = None

    def execute(self) -> None:
        for index, note in enumerate(self._note_list):
            if NoteModelAdapter.get_id(note) == self._note_id:
                self._backup_note = note
                self._backup_index = index
                self._note_list.pop(index)
                return

    def undo(self) -> None:
        if self._backup_note is None or self._backup_index is None:
            return

        note_id = NoteModelAdapter.get_id(self._backup_note)
        for existing_note in self._note_list:
            if NoteModelAdapter.get_id(existing_note) == note_id:
                return

        self._note_list.insert(self._backup_index, self._backup_note)