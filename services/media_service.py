import mimetypes
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


class MediaService:
    """Import and resolve media files managed by the application."""

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"}
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
    MAX_FILE_SIZE = 100 * 1024 * 1024

    def __init__(self, media_dir=None, project_root=None):
        if project_root is not None:
            default_root = Path(project_root)
        elif getattr(sys, "frozen", False):
            default_root = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Engraver"
        else:
            default_root = Path(__file__).resolve().parent.parent
        self.project_root = default_root.resolve()
        self.media_dir = Path(media_dir or self.project_root / "data" / "media")
        self.media_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _default_storage_roots():
        """Return source and packaged storage roots without relying on CWD."""
        project_root = Path(__file__).resolve().parent.parent
        user_root = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Engraver"
        preferred_root = user_root if getattr(sys, "frozen", False) else project_root
        return preferred_root.resolve(), project_root.resolve(), user_root.resolve()

    @classmethod
    def resolve_stored_path(cls, stored_path, project_root=None):
        """Resolve current and legacy media paths across source/packaged builds."""
        path = Path(str(stored_path or ""))
        if path.is_absolute():
            return path.resolve()

        roots = []
        if project_root is not None:
            roots.append(Path(project_root).resolve())
        roots.extend(cls._default_storage_roots())

        candidates = []
        for root in roots:
            candidate = (root / path).resolve()
            if candidate not in candidates:
                candidates.append(candidate)

            # FileSystemManager and old app versions persisted media/<name>,
            # while the current MediaService persists data/media/<name>.
            if path.parts and path.parts[0].lower() == "media":
                legacy_candidate = (root / "data" / path).resolve()
                if legacy_candidate not in candidates:
                    candidates.append(legacy_candidate)

        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return candidates[0]

    @classmethod
    def media_kind(cls, file_path):
        suffix = Path(file_path).suffix.lower()
        if suffix in cls.IMAGE_EXTENSIONS:
            return "image"
        if suffix in cls.AUDIO_EXTENSIONS:
            return "audio"
        if suffix in cls.VIDEO_EXTENSIONS:
            return "video"
        if suffix == '.pdf':
            return 'document'
        return None

    @classmethod
    def supported_filetypes(cls):
        extensions = sorted(cls.IMAGE_EXTENSIONS | cls.AUDIO_EXTENSIONS | cls.VIDEO_EXTENSIONS)
        all_media = " ".join(f"*{extension}" for extension in extensions)
        return [
            ("Media", all_media),
            ("Images", " ".join(f"*{ext}" for ext in sorted(cls.IMAGE_EXTENSIONS))),
            ("Audio", " ".join(f"*{ext}" for ext in sorted(cls.AUDIO_EXTENSIONS))),
            ("Video", " ".join(f"*{ext}" for ext in sorted(cls.VIDEO_EXTENSIONS))),
            ("Document", "*.pdf"),
            ("All files", "*.*"),
        ]

    def import_file(self, source_path):
        source = Path(source_path).expanduser().resolve()
        if not source.is_file():
            raise ValueError(f"Không tìm thấy tệp: {source.name}")

        kind = self.media_kind(source)
        if kind is None:
            raise ValueError(f"Định dạng media không được hỗ trợ: {source.suffix or source.name}")

        size = source.stat().st_size
        if size > self.MAX_FILE_SIZE:
            raise ValueError(f"Tệp {source.name} vượt quá giới hạn 100 MB")

        target = self.media_dir / f"{uuid.uuid4().hex}{source.suffix.lower()}"
        shutil.copy2(source, target)
        try:
            stored_path = target.relative_to(self.project_root).as_posix()
        except ValueError:
            stored_path = str(target)

        return {
            "id": uuid.uuid4().hex,
            "name": source.name,
            "path": stored_path,
            "kind": kind,
            "mime_type": mimetypes.guess_type(source.name)[0] or "application/octet-stream",
            "size": size,
        }

    def resolve_path(self, stored_path):
        return self.resolve_stored_path(stored_path, project_root=self.project_root)

    def open_file(self, stored_path):
        path = self.resolve_path(stored_path)
        if not path.is_file():
            raise FileNotFoundError(f"Không tìm thấy media: {path.name}")
        if sys.platform == "win32":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
