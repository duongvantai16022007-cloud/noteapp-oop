from cryptography.fernet import Fernet

class SecurityManager:
    def __init__(self, key=None):
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt(self, text: str) -> bytes:
        return self.cipher.encrypt(text.encode())

    def decrypt(self, encrypted_text: bytes) -> str:
        return self.cipher.decrypt(encrypted_text).decode()

    def verify_password(self, input_password, stored_password):
        return input_password == stored_password