import os
import shutil
import uuid
from platform import system

class FileSystemManager:
    """
    Quản lý việc lưu trữ các tệp phương tiện (ảnh, âm thanh) và đường dẫn động 
    để ứng dụng có thể chạy mượt mà trên nhiều hệ điều hành khác nhau.
    """
    def __init__(self):
        self.app_dir = self._get_app_storage_path()

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
        elif os_name == 'Windows':
            return os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'Engraver')
        else:
            return os.path.join(os.path.expanduser('~'), '.engraver')
    
    def copy_to_internal_storage(self, source_file_path, file_type = "media"):
        """
        Copy một file từ bên ngoài (vd: thư viện ảnh) vào thư mục nội bộ của app.
        Trả về đường dẫn tương đối (vd: 'media/ảnh_123.jpg') để lưu vào Database.
        """
        if not os.path.exists(source_file_path):
            raise FileNotFoundError(f"Không tìm thấy file: {source_file_path}")
        
        _, ext = os.path.splitext(source_file_path)

        unique_filename = f"{file_type}_{uuid.uuid4().hex}{ext}"
        dest_file_path = os.path.join(self.media_dir, unique_filename)

        shutil.copy2(source_file_path, dest_file_path)

        return os.path.join('media', unique_filename)
    
    def get_absolute_path(self, relative_path):
        """
        Biến đường dẫn tương đối (trong DB) thành đường dẫn tuyệt đối để UI hiển thị.
        """
        if not relative_path:
            return None
        return os.path.join(self.app_dir, relative_path)

        