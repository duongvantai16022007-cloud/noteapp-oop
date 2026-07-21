import os
import shutil
import uuid
import re
import sys
from platform import system
from pathlib import Path

class FileSystemManager:
    """
    Quản lý việc lưu trữ các tệp phương tiện (ảnh, âm thanh) và đường dẫn động 
    để ứng dụng có thể chạy mượt mà trên nhiều hệ điều hành khác nhau.
    """
    def __init__(self, app_dir=None):
        """
        Khởi tạo FileSystemManager, xác định hệ điều hành 
        và tạo thư mục media nội bộ nếu chưa có.
        """
        storage_root = app_dir if app_dir is not None else self._get_app_storage_path()
        self.app_dir = str(Path(storage_root).expanduser().resolve())

        self.media_dir = os.path.join(self.app_dir, 'media')

        if not os.path.exists(self.media_dir):
            os.makedirs(self.media_dir)

    def _get_app_storage_path(self):
        """
        Xác định hệ điều hành và trả về đường dẫn luu trữ phù hợp.
        """
        os_name = system()

        if os_name == 'Android':
            return '/storage/emulated/0/Android/data/org.engraver/files'
        elif os_name == 'IOS':
            return os.path.expanduser('~/Documents')
        elif not getattr(sys, "frozen", False):
            return str(Path(__file__).resolve().parent.parent)
        elif os_name == 'Windows':
            return os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'Engraver')
        elif os_name == 'Darwin':
            return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'Engraver')
        else:
            return os.path.join(os.path.expanduser('~'), '.engraver')
    
    def copy_to_internal_storage(self, source_file_path, file_type="media", note_id="unassigned"):
        """
        Copy một file từ bên ngoài (vd: thư viện ảnh) vào thư mục nội bộ của app.
        Trả về đường dẫn tuyệt đối để lưu vào Database.
        """
        if not os.path.exists(source_file_path):
            raise FileNotFoundError(f"Không tìm thấy file: {source_file_path}")
        
        _, ext = os.path.splitext(source_file_path)

        unique_filename = f"{file_type}_{uuid.uuid4().hex}{ext}"
        safe_note_id = re.sub(r"[^A-Za-z0-9_.-]", "_", str(note_id or "").strip())
        if not safe_note_id:
            raise ValueError("Cần note_id trước khi lưu media")
        note_dir = os.path.join(self.media_dir, f"note_{safe_note_id}")
        os.makedirs(note_dir, exist_ok=True)
        dest_file_path = os.path.abspath(os.path.join(note_dir, unique_filename))

        shutil.copy2(source_file_path, dest_file_path)

        return dest_file_path
    
    def get_absolute_path(self, relative_path):
        """
        Biến đường dẫn tương đối (trong DB) thành đường dẫn tuyệt đối để UI hiển thị.
        """
        if not relative_path:
            return None
        absolute_path = relative_path
        if not os.path.isabs(relative_path):
            absolute_path = os.path.normpath(os.path.join(self.app_dir, relative_path))
        else:
            absolute_path = os.path.normpath(relative_path)

        app_dir = os.path.normpath(self.app_dir)
        try:
            common = os.path.commonpath([app_dir, absolute_path])
            if common != app_dir:
                raise ValueError(f"Đường dẫn vượt ra ngoài thư mục ứng dụng: {relative_path}")
        except ValueError:
            raise ValueError(f"Đường dẫn vượt ra ngoài thư mục ứng dụng hoặc khác ổ đĩa: {relative_path}")

        return absolute_path

