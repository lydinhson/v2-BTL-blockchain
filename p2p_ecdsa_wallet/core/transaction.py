import hashlib
import json
import time

from core.wallet import Wallet

SYSTEM_SENDER = "SYSTEM"


class Transaction:
    def __init__(
        self,
        sender: str,
        recipient: str,
        amount: float,
        timestamp: float = None,
        nonce: int = 0,
        signature: str = None,
    ):
        self.sender = sender          # Public key hex của người gửi ("SYSTEM" nếu là thưởng đào khối)
        self.recipient = recipient    # Public key hex của người nhận
        self.amount = float(amount)
        # Dùng "is None" thay vì "or" để timestamp = 0.0 vẫn được giữ nguyên
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.nonce = int(nonce)       # Chống tấn công phát lại (Replay Attack)
        self.signature = signature

    def calculate_hash(self) -> str:
        """Băm nội dung giao dịch (không gồm chữ ký) với sort_keys để kết quả luôn nhất quán."""
        payload = json.dumps(
            {
                "sender": self.sender,
                "recipient": self.recipient,
                "amount": self.amount,
                "timestamp": self.timestamp,
                "nonce": self.nonce,
            },
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def sign_transaction(self, wallet: Wallet):
        if wallet.public_key_hex != self.sender:
            raise ValueError("Không thể ký giao dịch cho ví của người khác!")
        self.signature = wallet.sign(self.calculate_hash())

    def is_valid(self) -> bool:
        """Kiểm tra tính toàn vẹn và xác minh chữ ký số ECDSA."""
        if self.amount <= 0:
            return False
        if self.sender == SYSTEM_SENDER:  # Giao dịch thưởng đào khối (Coinbase)
            return True
        if not self.signature:
            return False
        return Wallet.verify(self.sender, self.calculate_hash(), self.signature)

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            sender=data["sender"],
            recipient=data["recipient"],
            amount=data["amount"],
            timestamp=data.get("timestamp"),
            nonce=data.get("nonce", 0),
            signature=data.get("signature"),
        )
