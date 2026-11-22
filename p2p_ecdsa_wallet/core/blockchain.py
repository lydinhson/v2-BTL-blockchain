import json
import os
from typing import List

from core.block import Block
from core.transaction import SYSTEM_SENDER, Transaction


class Blockchain:
    def __init__(self, storage_path: str, difficulty: int = 3, mining_reward: float = 50.0):
        self.storage_path = storage_path
        self.difficulty = difficulty
        self.mining_reward = mining_reward
        self.chain: List[Block] = []
        self.mempool: List[Transaction] = []

        if os.path.exists(self.storage_path):
            self.load_from_disk()
        else:
            self.chain = [self.create_genesis_block()]
            self.save_to_disk()

    def create_genesis_block(self) -> Block:
        # Khối khởi thủy cố định timestamp=0 để mọi node có cùng Genesis Block
        genesis = Block(index=0, transactions=[], previous_hash="0", timestamp=0.0)
        genesis.hash = genesis.calculate_hash()
        return genesis

    @property
    def latest_block(self) -> Block:
        return self.chain[-1]

    def get_balance(self, address: str, chain: List[Block] = None) -> float:
        """Tính số dư của ví theo mô hình Account-based."""
        target_chain = chain if chain is not None else self.chain
        balance = 0.0
        for block in target_chain:
            for tx in block.transactions:
                if tx.sender == address:
                    balance -= tx.amount
                if tx.recipient == address:
                    balance += tx.amount
        return balance

    def _confirmed_tx_hashes(self) -> set:
        return {tx.calculate_hash() for block in self.chain for tx in block.transactions}

    def add_transaction(self, tx: Transaction) -> bool:
        """Xác minh chữ ký số và kiểm tra đủ số dư trước khi đưa vào Mempool."""
        # Giao dịch thưởng chỉ được tạo bởi chính node khi đào khối, không nhận từ bên ngoài
        if tx.sender == SYSTEM_SENDER:
            return False
        if not tx.is_valid():
            return False

        # Chống phát lại (Replay Attack): giao dịch đã có trong chuỗi hoặc Mempool thì bỏ qua
        tx_hash = tx.calculate_hash()
        if tx_hash in self._confirmed_tx_hashes():
            return False
        if any(t.calculate_hash() == tx_hash for t in self.mempool):
            return False

        pending_spent = sum(t.amount for t in self.mempool if t.sender == tx.sender)
        if self.get_balance(tx.sender) - pending_spent < tx.amount:
            return False

        self.mempool.append(tx)
        return True

    def mine_pending_transactions(self, miner_address: str) -> Block:
        """Đóng gói Mempool + giao dịch thưởng vào Block mới và đào PoW."""
        reward_tx = Transaction(sender=SYSTEM_SENDER, recipient=miner_address, amount=self.mining_reward)
        block_txs = [reward_tx] + self.mempool
        new_block = Block(
            index=len(self.chain),
            transactions=block_txs,
            previous_hash=self.latest_block.hash,
        )
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        self.mempool = []
        self.save_to_disk()
        return new_block

    def is_chain_valid(self, chain_to_check: List[Block]) -> bool:
        """Thuật toán xác thực toàn bộ chuỗi khi đồng bộ từ Full Node khác."""
        if not chain_to_check:
            return False

        # Kiểm tra khối khởi thủy
        genesis = self.create_genesis_block()
        if chain_to_check[0].hash != genesis.hash:
            return False

        balances = {}
        seen_tx_hashes = set()
        target = "0" * self.difficulty

        for i in range(1, len(chain_to_check)):
            current = chain_to_check[i]
            previous = chain_to_check[i - 1]

            # 1. Kiểm tra liên kết chuỗi và tính toàn vẹn của Block
            if current.index != i:
                return False
            if current.previous_hash != previous.hash:
                return False
            if current.hash != current.calculate_hash():
                return False
            if not current.hash.startswith(target):
                return False

            # 2. Mỗi khối có đúng 1 giao dịch thưởng (Coinbase) ở vị trí đầu, đúng mức thưởng
            if not current.transactions:
                return False
            coinbase = current.transactions[0]
            if coinbase.sender != SYSTEM_SENDER or coinbase.amount != self.mining_reward:
                return False
            if any(tx.sender == SYSTEM_SENDER for tx in current.transactions[1:]):
                return False

            # 3. Xác minh chữ ký số ECDSA, chống trùng lặp và kiểm tra số dư từng giao dịch
            for tx in current.transactions:
                if not tx.is_valid():
                    return False
                tx_hash = tx.calculate_hash()
                if tx_hash in seen_tx_hashes:
                    return False
                seen_tx_hashes.add(tx_hash)

                if tx.sender != SYSTEM_SENDER:
                    if balances.get(tx.sender, 0.0) < tx.amount:
                        return False
                    balances[tx.sender] -= tx.amount
                balances[tx.recipient] = balances.get(tx.recipient, 0.0) + tx.amount

        return True

    def replace_chain(self, new_chain: List[Block]):
        """Thay sổ cái bằng chuỗi mới và dọn Mempool (bỏ giao dịch đã được đóng khối)."""
        self.chain = new_chain
        pending = self.mempool
        self.mempool = []
        for tx in pending:
            self.add_transaction(tx)  # Tự loại giao dịch đã xác nhận hoặc không còn đủ số dư
        self.save_to_disk()

    def save_to_disk(self):
        directory = os.path.dirname(self.storage_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump([b.to_dict() for b in self.chain], f, indent=2)

    def load_from_disk(self):
        with open(self.storage_path, "r", encoding="utf-8") as f:
            raw_chain = json.load(f)
            self.chain = [Block.from_dict(b) for b in raw_chain]
