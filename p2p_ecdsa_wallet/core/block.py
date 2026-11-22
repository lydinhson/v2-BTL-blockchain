import hashlib
import json
import time
from typing import List

from core.transaction import Transaction


class Block:
    def __init__(
        self,
        index: int,
        transactions: List[Transaction],
        previous_hash: str,
        timestamp: float = None,
        nonce: int = 0,
        block_hash: str = None,
    ):
        self.index = index
        self.transactions = transactions
        self.previous_hash = previous_hash
        # Dùng "is None" để Genesis Block (timestamp = 0.0) giống hệt nhau trên mọi node
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.nonce = nonce
        self.hash = block_hash or self.calculate_hash()

    def calculate_hash(self) -> str:
        block_data = json.dumps(
            {
                "index": self.index,
                "transactions": [tx.to_dict() for tx in self.transactions],
                "previous_hash": self.previous_hash,
                "timestamp": self.timestamp,
                "nonce": self.nonce,
            },
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(block_data).hexdigest()

    def mine_block(self, difficulty: int):
        """Thuật toán Proof of Work tìm nonce sao cho hash bắt đầu bằng 'difficulty' số 0."""
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "block_hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: dict):
        txs = [Transaction.from_dict(tx) for tx in data["transactions"]]
        return cls(
            index=data["index"],
            transactions=txs,
            previous_hash=data["previous_hash"],
            timestamp=data["timestamp"],
            nonce=data["nonce"],
            block_hash=data["block_hash"],
        )
