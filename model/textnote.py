from .basenote import base
class TextNote(base):
    """
    Lớp đại diện cho ghi chú dạng văn bản thuần túy hoặc Markdown.

    Kế thừa từ lớp cơ sở 'base' và tập trung vào việc lưu trữ, hiển thị
    chuỗi văn bản lớn.
    """

    def get_type(self):
        """
        Trả về loại ghi chú.

        Returns:
            str: Luôn trả về 'Text'.
        """
        return "Text"

    def to_dict(self):
        """
        Chuyển đổi đối tượng TextNote thành dictionary để lưu trữ SQLite/JSON.

        Returns:
            dict: Dữ liệu cấu trúc của ghi chú văn bản.
        """
        return {
            "id": self._id,
            "type": self.get_type(),
            "title": self._title,
            "content": self._content,  
            "tags": self._tags,
            "created_at": self._created.isoformat(),
            "updated_at": self._updated.isoformat()
        }