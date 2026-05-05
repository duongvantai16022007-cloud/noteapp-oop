from datetime import datetime

class SearchEngine:
    def __init__(self, notes):
        """
        Khởi tạo SearchEngine

        :param notes: danh sách các đối tượng BaseNote
        """
        self.notes = notes  # list[BaseNote]

    def search_by_keyword(self, keyword: str):
        """
        Tìm kiếm ghi chú theo từ khóa (keyword)

        - So sánh keyword với title và content của note
        - Không phân biệt chữ hoa/thường

        :param keyword: từ khóa cần tìm
        :return: list các note thỏa điều kiện
        """
        keyword = keyword.lower()
        return [
            note for note in self.notes
            if keyword in note.title.lower() or keyword in note.content.lower()
        ]

    def filter_by_tag(self, tag_name: str):
        """
        Lọc các ghi chú theo tag

        - Mỗi note có danh sách tag
        - Kiểm tra xem tag_name có nằm trong list tag của note không

        :param tag_name: tên tag cần lọc
        :return: list các note có chứa tag đó
        """
        return [
            note for note in self.notes
            if tag_name in [tag.name for tag in note.tags]
        ]

    def filter_by_date(self, start_date: datetime, end_date: datetime):
        """
        Lọc ghi chú theo khoảng thời gian

        :param start_date: thời gian bắt đầu
        :param end_date: thời gian kết thúc
        :return: list note có created_at nằm trong khoảng
        """
        return [
            note for note in self.notes
            if start_date <= note.created_at <= end_date
        ]

    def advanced_search(self, keyword=None, tag=None, start_date=None, end_date=None):
        """
        Tìm kiếm nâng cao (kết hợp nhiều điều kiện)

        - Có thể truyền 1 hoặc nhiều điều kiện
        - Lọc lần lượt theo keyword → tag → thời gian

        :param keyword: từ khóa (optional)
        :param tag: tag (optional)
        :param start_date: ngày bắt đầu (optional)
        :param end_date: ngày kết thúc (optional)
        :return: list note thỏa tất cả điều kiện
        """
        results = self.notes

        if keyword:
            results = [n for n in results if keyword.lower() in n.title.lower()]

        if tag:
            results = [n for n in results if tag in [t.name for t in n.tags]]

        if start_date and end_date:
            results = [n for n in results if start_date <= n.created_at <= end_date]

        return results
    
from cryptography.fernet import Fernet

class SecurityManager:
    def __init__(self, key=None):
        """
        Khởi tạo SecurityManager

        - Nếu không có key → tự sinh key mới
        - Dùng Fernet (AES-based) để mã hóa

        :param key: khóa mã hóa (bytes)
        """
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt(self, text: str) -> bytes:
        """
        Mã hóa nội dung text

        :param text: chuỗi cần mã hóa
        :return: dữ liệu đã mã hóa (bytes)
        """
        return self.cipher.encrypt(text.encode())

    def decrypt(self, encrypted_text: bytes) -> str:
        """
        Giải mã nội dung

        :param encrypted_text: dữ liệu đã mã hóa
        :return: chuỗi ban đầu
        """
        return self.cipher.decrypt(encrypted_text).decode()

    def verify_password(self, input_password, stored_password):
        """
        Kiểm tra mật khẩu

        - So sánh trực tiếp (hiện tại đơn giản)
        - Có thể nâng cấp: hash bằng bcrypt

        :param input_password: mật khẩu người dùng nhập
        :param stored_password: mật khẩu đã lưu
        :return: True nếu đúng, False nếu sai
        """
        return input_password == stored_password
    
import threading
import time
from queue import PriorityQueue

class ReminderService:
    def __init__(self):
        """
        Khởi tạo ReminderService

        - Dùng PriorityQueue để lưu reminder theo thời gian
        - Tạo 1 thread chạy nền để kiểm tra liên tục
        """
        self.reminders = PriorityQueue()
        self.running = True

        # Tạo thread chạy hàm _run()
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True  # thread sẽ tắt khi chương trình chính tắt
        self.thread.start()

    def add_reminder(self, remind_time, message):
        """
        Thêm reminder mới

        - Chuyển datetime → timestamp để dễ so sánh

        :param remind_time: datetime cần nhắc
        :param message: nội dung nhắc
        """
        self.reminders.put((remind_time.timestamp(), message))

    def _run(self):
        """
        Hàm chạy nền (background thread)

        - Liên tục kiểm tra reminder gần nhất
        - Nếu đến thời điểm → trigger notify
        """
        while self.running:
            if not self.reminders.empty():
                # Lấy reminder sớm nhất (không xóa)
                remind_time, message = self.reminders.queue[0]
                current_time = time.time()

                # Nếu đã tới giờ
                if current_time >= remind_time:
                    self.reminders.get()  # xóa khỏi queue
                    self.notify(message)

            time.sleep(1)  # tránh chiếm CPU

    def notify(self, message):
        """
        Thực hiện thông báo

        - Hiện tại chỉ print ra console
        - Có thể thay bằng notification mobile

        :param message: nội dung thông báo
        """
        print(f"🔔 Reminder: {message}")

    def stop(self):
        """
        Dừng service

        - Dừng vòng lặp thread
        """
        self.running = False

from fpdf import FPDF

class ExportService:

    def export_to_markdown(self, note, file_path):
        """
        Xuất note ra file Markdown (.md)

        - Ghi title dạng heading (#)
        - Ghi nội dung phía dưới

        :param note: đối tượng note
        :param file_path: đường dẫn file lưu
        """
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {note.title}\n\n")
            f.write(note.content)

    def export_to_pdf(self, note, file_path):
        """
        Xuất note ra file PDF

        - Dùng thư viện FPDF
        - Ghi title và content vào file

        :param note: đối tượng note
        :param file_path: đường dẫn file lưu
        """
        pdf = FPDF()
        pdf.add_page()

        pdf.set_font("Arial", size=12)

        # Ghi tiêu đề
        pdf.cell(200, 10, txt=note.title, ln=True)

        # Ghi nội dung (tự xuống dòng)
        pdf.multi_cell(0, 10, note.content)

        pdf.output(file_path)