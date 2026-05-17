class Tag:
    """
    Lớp quản lý các thực thể nhãn dán (Tag) để phân loại ghi chú nâng cao.
    Attributes:
        _name (str): Tên nhãn (duy nhất).
        _color (str): Mã màu HEX để hiển thị trên giao diện (ví dụ: '#FF5733').
    """

    def __init__(self, name, color="#FFFFFF"):
        self._name = name
        self._color = color

    @property
    def name(self):
        """str: Tên của nhãn dán."""
        return self._name

    @property
    def color(self):
        """str: Mã màu hiển thị."""
        return self._color