Dưới đây là thiết kế kiến trúc chuẩn mực và bộ khung mã nguồn Python hoàn chỉnh cho hệ thống **Ví điện tử Full Node P2P sử dụng chữ ký số ECDSA (`secp256k1`)**. Thiết kế này dùng `Flask` + `requests` (giao tiếp HTTP ngang hàng) và lưu trữ sổ cái bằng tệp JSON cục bộ theo từng cổng (port) để đảm bảo tính phi tập trung, dễ chạy thử nhiều node trên cùng một máy và rất rõ ràng khi đưa vào báo cáo.

---

## 1. Cấu trúc thư mục dự án

```text
p2p_ecdsa_wallet/
├── requirements.txt          # Khai báo thư viện: ecdsa, flask, requests
├── run_node.py               # File khởi chạy một Full Node (nhận tham số port, peers)
├── core/                     # Tầng lõi mật mã học & Blockchain
│   ├── __init__.py
│   ├── wallet.py             # Tạo cặp khóa ECDSA, địa chỉ ví, hàm ký và xác minh
│   ├── transaction.py        # Cấu trúc giao dịch, băm SHA-256, xác thực chữ ký số
│   ├── block.py              # Cấu trúc khối, băm khối, thuật toán đào Proof of Work
│   └── blockchain.py         # Sổ cái, Mempool, tính số dư, kiểm tra chuỗi & lưu JSON
├── network/                  # Tầng mạng ngang hàng (P2P)
│   ├── __init__.py
│   └── node.py               # API của Full Node: phát tán giao dịch/khối, tự đồng bộ chuỗi
└── storage/                  # Thư mục tự sinh chứa sổ cái cục bộ của từng Node
    ├── ledger_5001.json      # Bản sao Blockchain riêng của Node cổng 5001
    └── ledger_5002.json      # Bản sao Blockchain riêng của Node cổng 5002

```

---

## 2. Thiết kế Sơ đồ lớp (Class Design)

Hệ thống được tách thành **5 lớp độc lập** với trách nhiệm rõ ràng, giúp bạn dễ dàng vẽ lại sơ đồ UML (bằng Draw.io hoặc PlantUML) cho Chương 3 của báo cáo:

| Lớp (Class) | Trách nhiệm chính | Quan hệ với các lớp khác |
| --- | --- | --- |
| **`Wallet`** | Sinh cặp khóa ECDSA (`private_key`, `public_key`), ký dữ liệu (`sign`) và xác minh chữ ký (`verify`). | Tạo và ký các đối tượng **`Transaction`**. |
| **`Transaction`** | Chứa thông tin chuyển tiền (`sender`, `recipient`, `amount`, `timestamp`, `nonce`, `signature`) và tự kiểm tra tính hợp lệ của chữ ký số (`is_valid`). | Được chứa trong **`Block`** và vùng chờ Mempool của **`Blockchain`**. |
| **`Block`** | Đóng gói danh sách giao dịch, liên kết `previous_hash`, tính mã băm SHA-256 và giải bài toán Proof of Work (`mine_block`). | Cấu thành chuỗi tuyến tính trong **`Blockchain`**. |
| **`Blockchain`** | Quản lý chuỗi khối, Mempool, tính số dư theo mô hình Account-based, chạy thuật toán `is_chain_valid()` và đọc/ghi tệp JSON cục bộ. | Được quản lý và đồng bộ bởi **`P2PNode`**. |
| **`P2PNode`** | Đại diện cho một Full Node trên mạng: quản lý danh sách `peers`, phát tán giao dịch/khối mới và thực thi **Longest Chain Rule** (`sync_chain`) khi khởi động lại. | Sở hữu 1 **`Wallet`** (ví của node) và 1 **`Blockchain`** (sổ cái cục bộ). |

---

## 3. Khung mã nguồn mẫu bằng Python

### 3.1. Cài đặt thư viện (`requirements.txt`)

```text
ecdsa==0.19.0
flask==3.0.3
requests==2.32.3

```

### 3.2. Lớp Ví & Chữ ký số ECDSA — Trọng tâm Đề K (`core/wallet.py`)

```python
import hashlib
from ecdsa import SigningKey, VerifyingKey, SECP256k1, BadSignatureError


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
        except (BadSignatureError, ValueError):
            return False

```

### 3.3. Lớp Giao dịch (`core/transaction.py`)

```python
import hashlib
import json
import time
from core.wallet import Wallet


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
        self.timestamp = timestamp or time.time()
        self.nonce = nonce            # Chống tấn công phát lại (Replay Attack)
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
        if self.sender == "SYSTEM":  # Giao dịch thưởng đào khối (Coinbase)
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
        return cls(**data)

```

### 3.4. Lớp Khối & Đào khối PoW (`core/block.py`)

```python
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
        self.timestamp = timestamp or time.time()
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

```

### 3.5. Lớp Blockchain, Xác thực chuỗi & Lưu JSON cục bộ (`core/blockchain.py`)

```python
import json
import os
from typing import List
from core.block import Block
from core.transaction import Transaction


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

    def add_transaction(self, tx: Transaction) -> bool:
        """Xác minh chữ ký số và kiểm tra đủ số dư trước khi đưa vào Mempool."""
        if not tx.is_valid():
            return False
        if tx.sender != "SYSTEM":
            pending_spent = sum(t.amount for t in self.mempool if t.sender == tx.sender)
            if self.get_balance(tx.sender) - pending_spent < tx.amount:
                return False
        self.mempool.append(tx)
        return True

    def mine_pending_transactions(self, miner_address: str) -> Block:
        """Đóng gói Mempool + giao dịch thưởng vào Block mới và đào PoW."""
        reward_tx = Transaction(sender="SYSTEM", recipient=miner_address, amount=self.mining_reward)
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
        target = "0" * self.difficulty

        for i in range(1, len(chain_to_check)):
            current = chain_to_check[i]
            previous = chain_to_check[i - 1]

            # 1. Kiểm tra liên kết chuỗi và tính toàn vẹn của Block
            if current.previous_hash != previous.hash:
                return False
            if current.hash != current.calculate_hash():
                return False
            if not current.hash.startswith(target):
                return False

            # 2. Xác minh chữ ký số ECDSA và số dư của từng giao dịch trong Block
            for tx in current.transactions:
                if not tx.is_valid():
                    return False
                if tx.sender != "SYSTEM":
                    if balances.get(tx.sender, 0.0) < tx.amount:
                        return False
                    balances[tx.sender] -= tx.amount
                balances[tx.recipient] = balances.get(tx.recipient, 0.0) + tx.amount

        return True

    def save_to_disk(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump([b.to_dict() for b in self.chain], f, indent=2)

    def load_from_disk(self):
        with open(self.storage_path, "r", encoding="utf-8") as f:
            raw_chain = json.load(f)
            self.chain = [Block.from_dict(b) for b in raw_chain]

```

### 3.6. Tầng Mạng Full Node & Tự đồng bộ khi bật lại (`network/node.py`)

```python
import requests
from flask import Flask, jsonify, request
from core.block import Block
from core.blockchain import Blockchain
from core.transaction import Transaction
from core.wallet import Wallet


def create_node_app(port: int, initial_peers: list):
    app = Flask(__name__)
    wallet = Wallet()
    blockchain = Blockchain(storage_path=f"storage/ledger_{port}.json")
    peers = set(initial_peers)

    def sync_chain() -> bool:
        """
        Thuật toán đồng bộ hóa (Longest Chain Rule):
        Hỏi tất cả các Full Node lân cận, lấy chuỗi dài hơn và kiểm tra hợp lệ toàn bộ.
        """
        longest_chain = None
        max_length = len(blockchain.chain)

        for peer in list(peers):
            try:
                resp = requests.get(f"{peer}/chain", timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    candidate_chain = [Block.from_dict(b) for b in data["chain"]]
                    if len(candidate_chain) > max_length and blockchain.is_chain_valid(candidate_chain):
                        max_length = len(candidate_chain)
                        longest_chain = candidate_chain
            except requests.exceptions.RequestException:
                continue  # Bỏ qua các peer đang ngoại tuyến

        if longest_chain:
            blockchain.chain = longest_chain
            blockchain.save_to_disk()
            return True
        return False

    @app.route("/wallet", methods=["GET"])
    def get_wallet():
        return jsonify({
            "address": wallet.public_key_hex,
            "balance": blockchain.get_balance(wallet.public_key_hex),
        })

    @app.route("/chain", methods=["GET"])
    def get_chain():
        return jsonify({
            "length": len(blockchain.chain),
            "chain": [b.to_dict() for b in blockchain.chain],
        })

    @app.route("/transactions/send", methods=["POST"])
    def create_and_broadcast_tx():
        """Tạo giao dịch từ ví của node này, ký ECDSA và phát tán lên mạng P2P."""
        data = request.get_json()
        tx = Transaction(
            sender=wallet.public_key_hex,
            recipient=data["recipient"],
            amount=data["amount"],
            nonce=data.get("nonce", 0),
        )
        tx.sign_transaction(wallet)

        if not blockchain.add_transaction(tx):
            return jsonify({"error": "Giao dịch không hợp lệ hoặc không đủ số dư"}), 400

        # Phát tán giao dịch đã ký sang các peer khác
        for peer in peers:
            try:
                requests.post(f"{peer}/transactions/receive", json=tx.to_dict(), timeout=2)
            except requests.exceptions.RequestException:
                pass

        return jsonify({"message": "Đã ký và phát tán giao dịch", "transaction": tx.to_dict()}), 201

    @app.route("/transactions/receive", methods=["POST"])
    def receive_tx():
        """Nhận giao dịch từ peer khác và xác minh chữ ký số ECDSA."""
        tx = Transaction.from_dict(request.get_json())
        if blockchain.add_transaction(tx):
            return jsonify({"message": "Chữ ký hợp lệ, đã thêm vào Mempool"}), 201
        return jsonify({"error": "Từ chối: Chữ ký số sai hoặc vượt số dư!"}), 400

    @app.route("/mine", methods=["POST"])
    def mine():
        new_block = blockchain.mine_pending_transactions(wallet.public_key_hex)
        # Thông báo cho các peer khác đồng bộ chuỗi mới
        for peer in peers:
            try:
                requests.post(f"{peer}/nodes/sync", timeout=2)
            except requests.exceptions.RequestException:
                pass
        return jsonify({"message": "Đào khối thành công", "block": new_block.to_dict()}), 200

    @app.route("/nodes/sync", methods=["POST", "GET"])
    def trigger_sync():
        replaced = sync_chain()
        msg = "Đã đồng bộ chuỗi dài hơn từ mạng!" if replaced else "Chuỗi hiện tại đã là mới nhất."
        return jsonify({"message": msg, "length": len(blockchain.chain)}), 200

    # Tự động đồng bộ ngay khi Full Node khởi động lại
    if peers:
        sync_chain()

    return app

```

### 3.7. File khởi chạy (`run_node.py`)

```python
import argparse
from network.node import create_node_app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Khởi chạy Full Node ví điện tử P2P")
    parser.add_argument("--port", type=int, default=5001, help="Cổng chạy Full Node")
    parser.add_argument("--peers", nargs="*", default=[], help="Danh sách URL các peer lân cận")
    args = parser.parse_args()

    app = create_node_app(port=args.port, initial_peers=args.peers)
    app.run(host="127.0.0.1", port=args.port)

```

---

## 4. Kịch bản chạy thử nghiệm (Dùng chụp ảnh cho Báo cáo)

Mở 3 cửa sổ Terminal riêng biệt để giả lập 3 Full Node phi tập trung:

```bash
# Terminal 1: Khởi chạy Node 1
python run_node.py --port 5001 --peers http://127.0.0.1:5002 http://127.0.0.1:5003

# Terminal 2: Khởi chạy Node 2
python run_node.py --port 5002 --peers http://127.0.0.1:5001 http://127.0.0.1:5003

# Terminal 3: Khởi chạy Node 3
python run_node.py --port 5003 --peers http://127.0.0.1:5001 http://127.0.0.1:5002

```

* **Kiểm thử Đề K (Giả mạo giao dịch):** Dùng Postman/cURL gửi một JSON tới `POST [http://127.0.0.1:5002/transactions/receive](http://127.0.0.1:5002/transactions/receive)` nhưng sửa trường `amount` tăng thêm 1 đồng so với lúc ký $\rightarrow$ Node 2 trả về mã `400` (`Chữ ký số sai`).
* **Kiểm thử Đồng bộ khi mất kết nối:** Nhấn `Ctrl+C` để tắt **Node 3**. Trên **Node 1**, gọi `POST /mine` và `POST /transactions/send` vài lần. Quan sát thấy `ledger_5001.json` và `ledger_5002.json` đã có thêm các block mới trong khi `ledger_5003.json` vẫn ngắn hơn. Bật lại **Node 3** $\rightarrow$ hàm `sync_chain()` tự chạy lúc khởi động, xác minh lại toàn bộ chữ ký số và cập nhật `ledger_5003.json` khớp hoàn toàn với mạng.
