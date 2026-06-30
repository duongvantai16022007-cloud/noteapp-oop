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

        if note_type == "Checklist":
            note = ChecklistNote(title=data["title"], content=raw_content, tags=raw_tags)
        elif note_type == "Media":
            note = MediaNote(
                title=data["title"], 
                content=raw_content, 
                file_path=data.get("media_path"), 
                file_type="media", 
                tags=raw_tags
            )
        else: 
            note = TextNote(title=data["title"], content=raw_content, tags=raw_tags)
            
        note._id = data["id"]
        
        if isinstance(data.get("created_at"), str):
            try: note._created = datetime.fromisoformat(data["created_at"])
            except ValueError: pass
                
        if isinstance(data.get("updated_at"), str):
            try: note._updated = datetime.fromisoformat(data["updated_at"])
            except ValueError: pass
                
        return note