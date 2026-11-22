import json
import math
import os
from typing import List, Optional, Tuple

from core.block import Block
from core.transaction import SYSTEM_SENDER, Transaction

TX_DUPLICATE = "Giao dịch đã tồn tại (bị phát lại)"

# Kết quả khi nhận một khối do peer phát tán
BLOCK_ACCEPTED = "accepted"    # Hợp lệ và đã nối vào cuối chuỗi
BLOCK_STALE = "stale"          # Khối cũ hoặc đã có, bỏ qua
BLOCK_NEED_SYNC = "need_sync"  # Không nối được với chuỗi cục bộ (bị thiếu khối hoặc có fork), cần đồng bộ
BLOCK_REJECTED = "rejected"    # Khối không hợp lệ


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

    def get_next_nonce(self, address: str) -> int:
        """Nonce = số thứ tự giao dịch của ví: số giao dịch đã xác nhận + số giao dịch đang chờ."""
        confirmed = sum(1 for b in self.chain for tx in b.transactions if tx.sender == address)
        pending = sum(1 for tx in self.mempool if tx.sender == address)
        return confirmed + pending

    def _confirmed_tx_hashes(self) -> set:
        return {tx.calculate_hash() for block in self.chain for tx in block.transactions}

    def try_add_transaction(self, tx: Transaction) -> Tuple[bool, str]:
        """Xác minh giao dịch trước khi đưa vào Mempool, trả về (thành công, lý do)."""
        # Giao dịch thưởng chỉ được tạo bởi chính node khi đào khối, không nhận từ bên ngoài
        if tx.sender == SYSTEM_SENDER:
            return False, "Giao dịch SYSTEM không được gửi từ bên ngoài"
        if not math.isfinite(tx.amount) or tx.amount <= 0:
            return False, "Số tiền phải là số dương"

        # 1. Xác minh chữ ký số ECDSA bằng Public Key của người gửi
        if not tx.is_valid():
            return False, "Chữ ký ECDSA không hợp lệ (dữ liệu đã bị sửa hoặc ký sai khóa)"

        # 2. Chống phát lại (Replay Attack): giao dịch đã có trong chuỗi hoặc Mempool
        tx_hash = tx.calculate_hash()
        if tx_hash in self._confirmed_tx_hashes() or any(
            t.calculate_hash() == tx_hash for t in self.mempool
        ):
            return False, TX_DUPLICATE

        # 3. Nonce phải đúng số thứ tự tiếp theo của ví người gửi
        expected_nonce = self.get_next_nonce(tx.sender)
        if tx.nonce != expected_nonce:
            return False, f"Sai nonce (mong đợi {expected_nonce}, nhận {tx.nonce})"

        # 4. Chống chi tiêu kép: số dư trừ các khoản đang chờ phải đủ
        pending_spent = sum(t.amount for t in self.mempool if t.sender == tx.sender)
        available = self.get_balance(tx.sender) - pending_spent
        if available < tx.amount:
            return False, f"Không đủ số dư (khả dụng {available:g}, cần {tx.amount:g})"

        self.mempool.append(tx)
        return True, "Chữ ký ECDSA hợp lệ, đã thêm vào Mempool"

    def add_transaction(self, tx: Transaction) -> bool:
        """Xác minh chữ ký số, nonce và số dư trước khi đưa vào Mempool."""
        return self.try_add_transaction(tx)[0]

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

    def validate_chain(self, chain_to_check: List[Block]) -> Optional[str]:
        """Xác thực toàn bộ chuỗi; trả về None nếu hợp lệ, ngược lại trả về lý do."""
        if not chain_to_check:
            return "Chuỗi rỗng"

        # Kiểm tra khối khởi thủy
        genesis = self.create_genesis_block()
        if chain_to_check[0].hash != genesis.hash:
            return "Khối khởi thủy (Genesis) không khớp"

        balances = {}
        next_nonces = {}
        seen_tx_hashes = set()
        target = "0" * self.difficulty

        for i in range(1, len(chain_to_check)):
            current = chain_to_check[i]
            previous = chain_to_check[i - 1]

            # 1. Kiểm tra liên kết chuỗi và tính toàn vẹn của Block
            if current.index != i:
                return f"Khối {i}: sai số thứ tự (index = {current.index})"
            if current.previous_hash != previous.hash:
                return f"Khối {i}: previous_hash không khớp hash của khối {i - 1}"
            if current.hash != current.calculate_hash():
                return f"Khối {i}: hash không khớp nội dung (dữ liệu khối đã bị sửa)"
            if not current.hash.startswith(target):
                return f"Khối {i}: không thỏa mãn Proof of Work (độ khó {self.difficulty})"

            # 2. Mỗi khối có đúng 1 giao dịch thưởng (Coinbase) ở vị trí đầu, đúng mức thưởng
            if not current.transactions:
                return f"Khối {i}: không có giao dịch thưởng"
            coinbase = current.transactions[0]
            if coinbase.sender != SYSTEM_SENDER or coinbase.amount != self.mining_reward:
                return f"Khối {i}: giao dịch thưởng không hợp lệ"
            if any(tx.sender == SYSTEM_SENDER for tx in current.transactions[1:]):
                return f"Khối {i}: có nhiều hơn một giao dịch thưởng"

            # 3. Xác minh chữ ký số ECDSA, chống trùng lặp, nonce và số dư từng giao dịch
            for tx in current.transactions:
                if not tx.is_valid():
                    return f"Khối {i}: chữ ký ECDSA của giao dịch không hợp lệ"
                tx_hash = tx.calculate_hash()
                if tx_hash in seen_tx_hashes:
                    return f"Khối {i}: giao dịch bị lặp lại"
                seen_tx_hashes.add(tx_hash)

                if tx.sender != SYSTEM_SENDER:
                    expected_nonce = next_nonces.get(tx.sender, 0)
                    if tx.nonce != expected_nonce:
                        return f"Khối {i}: sai nonce (mong đợi {expected_nonce}, nhận {tx.nonce})"
                    next_nonces[tx.sender] = expected_nonce + 1
                    if balances.get(tx.sender, 0.0) < tx.amount:
                        return f"Khối {i}: giao dịch chi vượt số dư"
                    balances[tx.sender] -= tx.amount
                balances[tx.recipient] = balances.get(tx.recipient, 0.0) + tx.amount

        return None

    def is_chain_valid(self, chain_to_check: List[Block]) -> bool:
        """Thuật toán xác thực toàn bộ chuỗi khi đồng bộ từ Full Node khác."""
        return self.validate_chain(chain_to_check) is None

    def try_add_block(self, block: Block) -> Tuple[str, str]:
        """Nhận một khối do peer phát tán, trả về (trạng thái, mô tả)."""
        if block.index < len(self.chain):
            return BLOCK_STALE, f"Khối {block.index} đã có hoặc cũ hơn chuỗi cục bộ"
        if block.index > len(self.chain) or block.previous_hash != self.latest_block.hash:
            return BLOCK_NEED_SYNC, (
                f"Khối {block.index} không nối được với chuỗi cục bộ (độ dài {len(self.chain)})"
            )

        candidate = self.chain + [block]
        error = self.validate_chain(candidate)
        if error:
            return BLOCK_REJECTED, error
        self.replace_chain(candidate)
        return BLOCK_ACCEPTED, f"Khối {block.index} hợp lệ, đã nối vào chuỗi"

    def replace_chain(self, new_chain: List[Block]):
        """Thay sổ cái bằng chuỗi mới và dọn Mempool (bỏ giao dịch đã được đóng khối)."""
        # Giao dịch nằm trong các khối bị bỏ (do fork) được trả lại Mempool để không bị mất
        new_hashes = {tx.calculate_hash() for b in new_chain for tx in b.transactions}
        orphaned = [
            tx
            for b in self.chain
            for tx in b.transactions
            if tx.sender != SYSTEM_SENDER and tx.calculate_hash() not in new_hashes
        ]
        pending = orphaned + self.mempool

        self.chain = new_chain
        self.mempool = []
        # Nạp lại theo đúng thứ tự nonce; tự loại giao dịch đã xác nhận hoặc không còn đủ số dư
        for tx in sorted(pending, key=lambda t: (t.sender, t.nonce)):
            self.add_transaction(tx)
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
