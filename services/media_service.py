import mimetypes
import os
import shutil
import subprocess
import sys
import uuid
import re
from pathlib import Path, PurePosixPath


class MediaService:
    """Import and resolve media files managed by the application."""

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"}
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
    MAX_FILE_SIZE = 100 * 1024 * 1024

    def __init__(self, media_dir=None, project_root=None):
        default_root = Path(project_root) if project_root is not None else self.app_storage_root()
        self.project_root = default_root.expanduser().resolve()
        self.media_dir = Path(media_dir or self.project_root / "media").expanduser().resolve()
        self.media_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def app_storage_root():
        if not getattr(sys, "frozen", False):
            return Path(__file__).resolve().parent.parent
        if sys.platform == "win32":
            return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Engraver"
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "Engraver"
        return Path.home() / ".engraver"

    @staticmethod
    def _default_storage_roots():
        """Return source and packaged storage roots without relying on CWD."""
        project_root = Path(__file__).resolve().parent.parent
        roots = [MediaService.app_storage_root(), project_root]
        roots.extend([
            Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Engraver",
            Path.home() / "Library" / "Application Support" / "Engraver",
            Path.home() / ".engraver",
        ])
        unique = []
        for root in roots:
            resolved = root.expanduser().resolve()
            if resolved not in unique:
                unique.append(resolved)
        return tuple(unique)

    @classmethod
    def resolve_stored_path(cls, stored_path, project_root=None):
        """Resolve absolute/current/legacy paths, rebasing paths from another PC."""
        raw_path = str(stored_path or "").strip()
        path = Path(raw_path).expanduser()
        if path.is_absolute() and path.is_file():
            return path.resolve()

        roots = []
        if project_root is not None:
            roots.append(Path(project_root).resolve())
        roots.extend(cls._default_storage_roots())

        candidates = [path.resolve()] if path.is_absolute() else []
        for root in roots:
            if not path.is_absolute():
                candidate = (root / path).resolve()
                if candidate not in candidates:
                    candidates.append(candidate)

            # FileSystemManager and old app versions persisted media/<name>,
            # while the current MediaService persists data/media/<name>.
            if not path.is_absolute() and path.parts and path.parts[0].lower() == "media":
                legacy_candidate = (root / "data" / path).resolve()
                if legacy_candidate not in candidates:
                    candidates.append(legacy_candidate)

        # An absolute path copied from Windows to macOS (or vice versa) cannot
        # be opened directly. Preserve the portable note_<id>/file suffix and
        # rebase it onto this machine's managed media root.
        normalized_parts = PurePosixPath(raw_path.replace("\\", "/")).parts
        portable_candidates = []
        note_index = next(
            (index for index, part in enumerate(normalized_parts) if part.startswith("note_")),
            None,
        )
        if note_index is not None:
            suffix = Path(*normalized_parts[note_index:])
            for root in roots:
                candidate = (root / "media" / suffix).resolve()
                if candidate not in candidates:
                    candidates.append(candidate)
                portable_candidates.append(candidate)

        for candidate in candidates:
            if candidate.is_file():
                return candidate
        if portable_candidates:
            return portable_candidates[0]
        if candidates:
            return candidates[0]
        base_root = roots[0] if roots else cls.app_storage_root().resolve()
        return (base_root / raw_path).resolve()

    @staticmethod
    def _safe_note_token(note_id):
        token = re.sub(r"[^A-Za-z0-9_.-]", "_", str(note_id or "").strip())
        if not token:
            raise ValueError("Cần note_id trước khi lưu media")
        return token

    def note_media_dir(self, note_id, create=True):
        target = (self.media_dir / f"note_{self._safe_note_token(note_id)}").resolve()
        target.relative_to(self.media_dir)
        if create:
            target.mkdir(parents=True, exist_ok=True)
        return target

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

    def import_file(self, source_path, note_id=None):
        source = Path(source_path).expanduser().resolve()
        if not source.is_file():
            raise ValueError(f"Không tìm thấy tệp: {source.name}")

        kind = self.media_kind(source)
        if kind is None:
            raise ValueError(f"Định dạng media không được hỗ trợ: {source.suffix or source.name}")

        size = source.stat().st_size
        if size > self.MAX_FILE_SIZE:
            raise ValueError(f"Tệp {source.name} vượt quá giới hạn 100 MB")

        attachment_id = uuid.uuid4().hex
        target = self.note_media_dir(note_id) / f"{attachment_id}{source.suffix.lower()}"
        shutil.copy2(source, target)

        return {
            "id": attachment_id,
            "name": source.name,
            "path": str(target.resolve()),
            "kind": kind,
            "mime_type": mimetypes.guess_type(source.name)[0] or "application/octet-stream",
            "size": size,
        }

    def organize_content_media(self, note_id, content):
        """Copy all attachments into media/note_<id> and persist absolute paths."""
        if not isinstance(content, dict):
            return content
        result = dict(content)
        organized = []
        target_dir = self.note_media_dir(note_id)
        keep_paths = set()
        for raw_item in content.get("media", []):
            if not isinstance(raw_item, dict) or not raw_item.get("path"):
                continue
            item = dict(raw_item)
            source = self.resolve_path(item["path"])
            if not source.is_file():
                item["path"] = str(source.resolve())
                organized.append(item)
                continue

            attachment_id = str(item.get("id") or uuid.uuid4().hex)
            item["id"] = attachment_id
            target = (target_dir / f"{attachment_id}{source.suffix.lower()}").resolve()
            if source.resolve() != target:
                shutil.copy2(source, target)
            item["path"] = str(target)
            keep_paths.add(target)
            item["size"] = target.stat().st_size
            item.setdefault("name", source.name)
            item.setdefault("kind", self.media_kind(target) or "media")
            organized.append(item)
        for managed_file in target_dir.iterdir():
            if (
                managed_file.is_file()
                and not managed_file.name.startswith("legacy_")
                and managed_file.resolve() not in keep_paths
            ):
                managed_file.unlink()
        result["media"] = organized
        return result

    def organize_legacy_media(self, note_id, stored_path):
        """Migrate the legacy notes.media_path value into the note media folder."""
        if not stored_path:
            return stored_path
        source = self.resolve_path(stored_path)
        target_dir = self.note_media_dir(note_id)
        if not source.is_file():
            return str(source.resolve())
        if source.resolve().parent == target_dir:
            return str(source.resolve())

        stable_id = uuid.uuid5(uuid.NAMESPACE_URL, str(stored_path)).hex
        target = (target_dir / f"legacy_{stable_id}{source.suffix.lower()}").resolve()
        if source.resolve() != target:
            shutil.copy2(source, target)
        return str(target)

    def delete_note_media(self, note_id):
        target = self.note_media_dir(note_id, create=False)
        if target.is_dir():
            shutil.rmtree(target)

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
