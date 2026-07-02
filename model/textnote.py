from .basenote import base

class TextNote(base):
    """
    Lớp đại diện cho ghi chú dạng văn bản/Markdown.
    Nội dung có thể chứa **bold** và *italic* để phục vụ trình soạn thảo thông minh.
    """

    def get_type(self):
        return "Text"

    def to_dict(self):
        data = self._base_dict()
        data.update({
            "type": self.get_type(),
            "content": self._content
        })
        return data
