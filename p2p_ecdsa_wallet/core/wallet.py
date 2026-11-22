import hashlib
import json
import os

from ecdsa import SECP256k1, BadSignatureError, SigningKey, VerifyingKey


class Wallet:
    def __init__(self, private_key_hex: str = None):
        if private_key_hex:
            self.private_key = SigningKey.from_string(
                bytes.fromhex(private_key_hex), curve=SECP256k1
            )
        else:
            # Sinh khóa bí mật mới trên đường cong secp256k1 (chuẩn Bitcoin/Ethereum)
            self.private_key = SigningKey.generate(curve=SECP256k1)
        self.public_key = self.private_key.get_verifying_key()

    @property
    def private_key_hex(self) -> str:
        return self.private_key.to_string().hex()

    @property
    def public_key_hex(self) -> str:
        # Dùng trực tiếp chuỗi hex của Public Key làm địa chỉ ví để dễ xác minh
        return self.public_key.to_string().hex()

    def sign(self, data_hash: str) -> str:
        """Ký lên mã băm SHA-256 của giao dịch bằng Private Key."""
        signature_bytes = self.private_key.sign(
            data_hash.encode("utf-8"), hashfunc=hashlib.sha256
        )
        return signature_bytes.hex()

    @staticmethod
    def verify(public_key_hex: str, data_hash: str, signature_hex: str) -> bool:
        """Xác minh chữ ký số bằng Public Key (không cần biết Private Key)."""
        try:
            verifying_key = VerifyingKey.from_string(
                bytes.fromhex(public_key_hex), curve=SECP256k1
            )
            return verifying_key.verify(
                bytes.fromhex(signature_hex),
                data_hash.encode("utf-8"),
                hashfunc=hashlib.sha256,
            )
        except (BadSignatureError, ValueError, AssertionError):
            return False

    # ------------------------------------------------------------------
    # Lưu / nạp khóa để Node giữ nguyên địa chỉ ví sau khi khởi động lại
    # ------------------------------------------------------------------
    def save_to_file(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {"private_key": self.private_key_hex, "address": self.public_key_hex},
                f,
                indent=2,
            )

    @classmethod
    def load_or_create(cls, path: str) -> "Wallet":
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return cls(private_key_hex=json.load(f)["private_key"])
        wallet = cls()
        wallet.save_to_file(path)
        return wallet
