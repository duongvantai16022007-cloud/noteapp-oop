import shutil
import os
import tempfile
import json
import re
from pathlib import Path
from urllib.parse import quote

from fpdf import FPDF, fpdf as fpdf_module
from PIL import Image, UnidentifiedImageError
from services.media_service import MediaService


class ExportService:
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

    def _plain_text_from_content(self, content):
        if content is None:
            return ""
        if isinstance(content, dict):
            return str(content.get("text", ""))
        return str(content)

    def _font_paths(self):
        candidates = (
            Path(__file__).resolve().parent.parent / "assets" / "fonts" / "ArialUnicode.ttf",
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/segoeui.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
            Path("/System/Library/Fonts/Supplemental/NotoSans-Regular.ttf"),
            Path("/Library/Fonts/Arial Unicode.ttf"),
            Path("/Library/Fonts/NotoSans-Regular.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
        )
        for path in candidates:
            if path.is_file():
                yield str(path.resolve())

    @staticmethod
    def _configure_font_cache():
        """Keep PyFPDF's machine-specific pickle cache outside the project."""
        cache_dir = Path(tempfile.gettempdir()) / "noteapp-fpdf-font-cache-v1"
        cache_dir.mkdir(parents=True, exist_ok=True)
        fpdf_module.FPDF_CACHE_MODE = 2
        fpdf_module.FPDF_CACHE_DIR = str(cache_dir)

    def _set_unicode_font(self, pdf):
        self._configure_font_cache()
        errors = []
        for index, font_path in enumerate(self._font_paths()):
            family = f"UnicodeFont{index}"
            try:
                pdf.add_font(family, "", font_path, uni=True)
                pdf.set_font(family, size=12)
                return family
            except (OSError, RuntimeError, ValueError) as exc:
                errors.append(f"{Path(font_path).name}: {exc}")
        details = "; ".join(errors) if errors else "không tìm thấy tệp font Unicode"
        raise RuntimeError(f"Không thể nạp font Unicode để xuất PDF: {details}")

    @staticmethod
    def _resolve_media_path(stored_path):
        return MediaService.resolve_stored_path(stored_path)

    def _content_to_text(self, note):
        content = note.content
        if isinstance(content, list):
            lines = []
            for item in content:
                if isinstance(item, dict):
                    mark = "x" if item.get("is_done") else " "
                    lines.append(f"- [{mark}] {item.get('content', '')}")
                else:
                    mark = "x" if getattr(item, "is_done", False) else " "
                    lines.append(f"- [{mark}] {getattr(item, 'content', str(item))}")
            return "\n".join(lines)
        return self._plain_text_from_content(content)

    def _markdown_content(self, note, output_path):
        content = note.content
        text = self._plain_text_from_content(content)
        media = content.get("media", []) if isinstance(content, dict) else []
        valid_media = [
            item for item in media
            if isinstance(item, dict) and item.get("path")
        ]
        if not valid_media:
            return text

        output_path = Path(output_path)
        assets_dir = output_path.parent / f"{output_path.stem}_media"
        assets_dir.mkdir(parents=True, exist_ok=True)
        links = []
        used_names = set()

        for index, item in enumerate(valid_media, start=1):
            source = self._resolve_media_path(item.get("path"))
            if not source.is_file():
                continue

            original_name = Path(str(item.get("name") or source.name)).name
            target_name = original_name
            if target_name.lower() in used_names:
                target_name = f"{Path(original_name).stem}_{index}{Path(original_name).suffix}"
            used_names.add(target_name.lower())
            shutil.copy2(source, assets_dir / target_name)
            relative_target = quote(
                f"{assets_dir.name}/{target_name}",
                safe="/"
            )
            if item.get("kind") == "image":
                markdown_link = f"![{original_name}]({relative_target})"
            else:
                markdown_link = f"[{original_name}]({relative_target})"
            try:
                position = int(item.get("position", len(text)))
            except (TypeError, ValueError):
                position = len(text)
            links.append((max(0, min(position, len(text))), markdown_link))

        for position, markdown_link in sorted(links, key=lambda value: value[0], reverse=True):
            text = f"{text[:position]}{markdown_link}{text[position:]}"
        return text

    def export_to_markdown(self, note, file_path):
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(f"# {note.title}\n\n")
            if note.deadline_at:
                file.write(f"**Deadline:** {note.deadline_at}\n\n")
            if note.reminder_at:
                file.write(f"**Reminder:** {note.reminder_at}\n\n")
            file.write(self._markdown_content(note, file_path))

    @staticmethod
    def _pdf_multi_cell(pdf, line_height, text):
        """Write a full-width cell without inheriting fpdf2's right-edge cursor."""
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, line_height, str(text))
        pdf.set_x(pdf.l_margin)

    def _write_pdf_text(self, pdf, text):
        if text:
            self._pdf_multi_cell(pdf, 7, text)

    def _write_pdf_media_label(self, pdf, font_family, label):
        pdf.set_font(font_family, size=10)
        self._pdf_multi_cell(pdf, 6, label)
        pdf.set_font(font_family, size=12)

    def _write_pdf_image(self, pdf, attachment, font_family, temp_dir, index):
        source = self._resolve_media_path(attachment.get("path"))
        name = str(attachment.get("name") or source.name)
        if not source.is_file():
            self._write_pdf_media_label(pdf, font_family, f"[Không tìm thấy ảnh: {name}]")
            return

        converted_path = Path(temp_dir) / f"pdf-image-{index}.png"
        try:
            with Image.open(source) as image:
                image.seek(0)
                image = image.convert("RGB")
                pixel_width, pixel_height = image.size
                if pixel_width <= 0 or pixel_height <= 0:
                    raise ValueError("Kích thước ảnh không hợp lệ")
                image.save(converted_path, format="PNG")
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
            self._write_pdf_media_label(pdf, font_family, f"[Không đọc được ảnh {name}: {exc}]")
            return

        usable_width = pdf.w - pdf.l_margin - pdf.r_margin
        max_height = min(120, pdf.h - pdf.t_margin - pdf.b_margin - 18)
        display_width = min(usable_width, max(30, pixel_width * 0.264583))
        display_height = display_width * pixel_height / pixel_width
        if display_height > max_height:
            scale = max_height / display_height
            display_width *= scale
            display_height = max_height

        caption_height = 9
        if pdf.get_y() + display_height + caption_height > pdf.h - pdf.b_margin:
            pdf.add_page()
            pdf.set_font(font_family, size=12)

        x = pdf.l_margin + (usable_width - display_width) / 2
        y = pdf.get_y()
        pdf.image(
            str(converted_path),
            x=x,
            y=y,
            w=display_width,
            h=display_height,
            type="PNG"
        )
        pdf.set_y(y + display_height + 2)
        pdf.set_x(pdf.l_margin)
        self._write_pdf_media_label(pdf, font_family, name)

    def _write_pdf_content(self, pdf, note, font_family, temp_dir):
        content = note.content
        if not isinstance(content, dict):
            self._write_pdf_text(pdf, self._content_to_text(note))
            return

        text = self._plain_text_from_content(content)
        media = [
            item for item in content.get("media", [])
            if isinstance(item, dict) and item.get("path")
        ]
        if not media:
            self._write_pdf_text(pdf, text)
            return

        def position_of(item):
            try:
                return max(0, min(int(item.get("position", len(text))), len(text)))
            except (TypeError, ValueError):
                return len(text)

        cursor = 0
        for index, attachment in enumerate(sorted(media, key=position_of), start=1):
            position = position_of(attachment)
            self._write_pdf_text(pdf, text[cursor:position])
            source = self._resolve_media_path(attachment.get("path"))
            kind = attachment.get("kind")
            if kind == "image" or source.suffix.lower() in self.IMAGE_EXTENSIONS:
                self._write_pdf_image(pdf, attachment, font_family, temp_dir, index)
            else:
                name = str(attachment.get("name") or source.name)
                media_type = "Audio" if kind == "audio" else "Video" if kind == "video" else "Media"
                self._write_pdf_media_label(pdf, font_family, f"[{media_type}: {name}]")
            cursor = position
        self._write_pdf_text(pdf, text[cursor:])

    def export_to_pdf(self, note, file_path):
        pdf = FPDF()
        pdf.add_page()
        font_family = self._set_unicode_font(pdf)

        pdf.set_font(font_family, size=16)
        self._pdf_multi_cell(pdf, 10, note.title)
        pdf.set_font(font_family, size=12)
        if note.deadline_at:
            self._pdf_multi_cell(pdf, 7, f"Deadline: {note.deadline_at}")
        if note.reminder_at:
            self._pdf_multi_cell(pdf, 7, f"Reminder: {note.reminder_at}")

        with tempfile.TemporaryDirectory(prefix="noteapp-pdf-") as temp_dir:
            self._write_pdf_content(pdf, note, font_family, temp_dir)
            pdf.output(file_path)

    @staticmethod
    def _safe_archive_name(value, fallback="media"):
        name = Path(str(value or "")).name.strip()
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
        name = name.rstrip(". ")
        return name or fallback

    def _media_for_archive(self, note):
        content = getattr(note, "content", None)
        media = content.get("media", []) if isinstance(content, dict) else []
        resolved = []
        for item in media:
            if not isinstance(item, dict) or not item.get("path"):
                continue
            source = self._resolve_media_path(item["path"])
            if source.is_file():
                resolved.append((item, source))
        return resolved

    def export_media_archive(self, note, file_path, password):
        """Create an AES-256 encrypted ZIP containing a note's media folder."""
        if not password or len(password) < 4:
            raise ValueError("Mật khẩu ZIP phải có ít nhất 4 ký tự")

        try:
            import pyzipper
        except ImportError as exc:
            raise RuntimeError(
                "Thiếu thư viện pyzipper. Hãy chạy: pip install -r requirements.txt"
            ) from exc

        media = self._media_for_archive(note)
        if not media:
            raise ValueError("Ghi chú không có file media hợp lệ để đóng gói")

        output_path = Path(file_path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        folder_name = self._safe_archive_name(
            f"{getattr(note, 'title', '')}_media",
            "note_media"
        )
        used_names = set()
        manifest_items = []

        temp_file = tempfile.NamedTemporaryFile(
            prefix=f".{output_path.stem}-",
            suffix=".tmp",
            dir=output_path.parent,
            delete=False,
        )
        temp_path = Path(temp_file.name)
        temp_file.close()

        try:
            with pyzipper.AESZipFile(
                temp_path,
                "w",
                compression=pyzipper.ZIP_DEFLATED,
                encryption=pyzipper.WZ_AES,
            ) as archive:
                archive.setpassword(password.encode("utf-8"))
                archive.setencryption(pyzipper.WZ_AES, nbits=256)

                for index, (item, source) in enumerate(media, start=1):
                    original_name = self._safe_archive_name(
                        item.get("name") or source.name,
                        f"media-{index}{source.suffix}"
                    )
                    target_name = original_name
                    suffix_number = 2
                    while target_name.casefold() in used_names:
                        target_name = (
                            f"{Path(original_name).stem}_{suffix_number}"
                            f"{Path(original_name).suffix}"
                        )
                        suffix_number += 1
                    used_names.add(target_name.casefold())
                    archive_name = f"{folder_name}/{target_name}"
                    archive.write(source, arcname=archive_name)
                    manifest_items.append({
                        "name": target_name,
                        "kind": item.get("kind") or MediaService.media_kind(source) or "media",
                        "size": source.stat().st_size,
                    })

                archive.writestr(
                    f"{folder_name}/manifest.json",
                    json.dumps(
                        {
                            "note_title": str(getattr(note, "title", "")),
                            "files": manifest_items,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ).encode("utf-8"),
                )
            os.replace(temp_path, output_path)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

        return len(media)

    @staticmethod
    def _validated_archive_members(archive, destination_dir):
        """Reject absolute and parent-traversal paths before extraction."""
        destination = Path(destination_dir).expanduser().resolve()
        members = archive.infolist()
        for member in members:
            member_name = str(member.filename).replace("\\", "/")
            parts = [part for part in member_name.split("/") if part not in ("", ".")]
            if (
                member_name.startswith("/")
                or any(part == ".." for part in parts)
                or (parts and parts[0].endswith(":"))
            ):
                raise ValueError(f"ZIP chứa đường dẫn không an toàn: {member.filename}")

            target = (destination / Path(*parts)).resolve()
            try:
                target.relative_to(destination)
            except ValueError as exc:
                raise ValueError(
                    f"ZIP chứa đường dẫn vượt ngoài thư mục đích: {member.filename}"
                ) from exc
        return members

    def extract_media_archive(self, file_path, destination_dir, password):
        """Extract an AES media ZIP after validating its member paths."""
        if not password:
            raise ValueError("Mật khẩu ZIP không được để trống")

        try:
            import pyzipper
        except ImportError as exc:
            raise RuntimeError(
                "Thiếu thư viện pyzipper. Hãy chạy: pip install -r requirements.txt"
            ) from exc

        archive_path = Path(file_path).expanduser().resolve()
        if not archive_path.is_file():
            raise FileNotFoundError(f"Không tìm thấy file ZIP: {archive_path.name}")

        destination = Path(destination_dir).expanduser().resolve()
        destination.mkdir(parents=True, exist_ok=True)
        with pyzipper.AESZipFile(archive_path, "r") as archive:
            members = self._validated_archive_members(archive, destination)
            archive.extractall(
                path=destination,
                members=members,
                pwd=password.encode("utf-8"),
            )
        return sum(1 for member in members if not member.is_dir())
