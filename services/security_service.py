import base64
import hashlib
import hmac
import os

try:
    from cryptography.fernet import Fernet
except ImportError:  # cryptography không bắt buộc cho tính năng khóa bằng mật khẩu.
    Fernet = None

class SecurityManager:
    """
    Quản lý bảo mật cho ghi chú.

    - encrypt/decrypt giữ lại để tương thích với service cũ.
    - hash_password/verify_password dùng PBKDF2-HMAC để không lưu mật khẩu thuần trong SQLite.
    """

    def __init__(self, key=None):
        self.key = key or (Fernet.generate_key() if Fernet else None)
        self.cipher = Fernet(self.key) if Fernet and self.key else None

    def encrypt(self, text: str) -> bytes:
        if not self.cipher:
            raise RuntimeError("Chưa cài cryptography nên không thể mã hóa Fernet.")
        return self.cipher.encrypt(text.encode())

    def decrypt(self, encrypted_text: bytes) -> str:
        if not self.cipher:
            raise RuntimeError("Chưa cài cryptography nên không thể giải mã Fernet.")
        return self.cipher.decrypt(encrypted_text).decode()

    def hash_password(self, password: str, salt: str | None = None):
        if not password:
            raise ValueError("Mật khẩu không được để trống.")

        raw_salt = base64.b64decode(salt.encode()) if salt else os.urandom(16)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            raw_salt,
            120_000
        )
        return (
            base64.b64encode(password_hash).decode("utf-8"),
            base64.b64encode(raw_salt).decode("utf-8")
        )

    def verify_password(self, input_password, stored_password_hash, stored_password_salt=None):
        if not input_password or not stored_password_hash or not stored_password_salt:
            return False
        input_hash, _ = self.hash_password(input_password, stored_password_salt)
        return hmac.compare_digest(input_hash, stored_password_hash)
