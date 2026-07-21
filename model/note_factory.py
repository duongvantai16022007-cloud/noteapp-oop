import json
from typing import Dict, Any
from .basenote import base
from .textnote import TextNote
from .checklist_note import ChecklistNote
from .media_note import MediaNote
from datetime import datetime

class NoteFactory:
    """Factory Design Pattern: Tái tạo lại Object OOP từ dữ liệu thô của Database."""

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> base:
        note_type = data.get("type", "Text")
        note_type_key = str(note_type).strip().lower()

        raw_content = data.get("content", "")
        if isinstance(raw_content, str) and raw_content.strip().startswith(('[', '{')):
            try:
                raw_content = json.loads(raw_content)
            except json.JSONDecodeError:
                pass

        raw_tags = data.get("tags")
        if isinstance(raw_tags, str) and raw_tags.strip().startswith('['):
            try:
                raw_tags = json.loads(raw_tags)
            except json.JSONDecodeError:
                pass

        common_kwargs = {
            "tags": raw_tags,
            "reminder_at": data.get("reminder_at"),
            "deadline_at": data.get("deadline_at"),
            "is_locked": data.get("is_locked", False),
            "password_hash": data.get("password_hash"),
            "password_salt": data.get("password_salt"),
            "reminder_notified": data.get("reminder_notified", 0),
            "deadline_notified": data.get("deadline_notified", 0),
            "folder_id": data.get("folder_id")
        }

        if note_type_key == "checklist":
            note = ChecklistNote(title=data["title"], content=raw_content, **common_kwargs)
        elif note_type_key == "media":
            note = MediaNote(
                title=data["title"],
                content=raw_content,
                file_path=data.get("media_path"),
                file_type="media",
                **common_kwargs
            )
        else:
            note = TextNote(title=data["title"], content=raw_content, **common_kwargs)

        note._id = data.get("id") or note._id

        if isinstance(data.get("created_at"), str):
            try:
                note._created = datetime.fromisoformat(data["created_at"])
            except ValueError:
                pass

        if isinstance(data.get("updated_at"), str):
            try:
                note._updated = datetime.fromisoformat(data["updated_at"])
            except ValueError:
                pass

        return note
