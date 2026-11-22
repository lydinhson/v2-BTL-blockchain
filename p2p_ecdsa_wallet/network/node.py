import logging
import os
import queue
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import requests
from flask import Flask, jsonify, request

from core.block import Block
from core.blockchain import (
    BLOCK_ACCEPTED,
    BLOCK_NEED_SYNC,
    BLOCK_REJECTED,
    TX_DUPLICATE,
    Blockchain,
)
from core.transaction import Transaction
from core.wallet import Wallet

# Thư mục storage/ nằm cạnh run_node.py, không phụ thuộc thư mục đang đứng khi chạy lệnh
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")

NODE_HEADER = "X-Node-Url"  # Peer gửi kèm URL của mình để tránh phát tán ngược lại


def short(value: str, n: int = 8) -> str:
    return value if not value or len(value) <= n else f"{value[:n]}…"


class _MemoryLogHandler(logging.Handler):
    """Giữ lại các dòng log gần nhất để giao diện Web hiển thị (GET /logs)."""

    def __init__(self, buffer: deque):
        super().__init__()
        self.buffer = buffer

    def emit(self, record):
        self.buffer.append({
            "time": time.strftime("%H:%M:%S", time.localtime(record.created)),
            "kind": getattr(record, "kind", "info"),
            "message": record.getMessage(),
        })


def create_node_app(
    port: int,
    initial_peers: list,
    difficulty: int = 3,
    storage_dir: str = STORAGE_DIR,
    host: str = "127.0.0.1",
):
    app = Flask(__name__, static_folder="static")
    app.json.ensure_ascii = False  # Hiển thị tiếng Việt có dấu trong JSON trả về
    self_url = f"http://{host}:{port}"

    # ---------------------------------------------------------------- Nhật ký
    log_buffer = deque(maxlen=200)
    logger = logging.getLogger(f"node.{port}.{id(app)}")
    logger.setLevel(logging.INFO)
    logger.addHandler(_MemoryLogHandler(log_buffer))

    def log(kind: str, message: str):
        """kind: ok (xanh) | bad (đỏ) | info."""
        level = logging.WARNING if kind == "bad" else logging.INFO
        logger.log(level, f"[Node {port}] {message}", extra={"kind": kind})

    # ---------------------------------------------------------------- Trạng thái node
    # Ví của node được lưu lại để giữ nguyên địa chỉ sau khi khởi động lại
    wallet = Wallet.load_or_create(os.path.join(storage_dir, f"wallet_{port}.json"))
    blockchain = Blockchain(
        storage_path=os.path.join(storage_dir, f"ledger_{port}.json"),
        difficulty=difficulty,
    )
    peers = set()
    peers_lock = threading.Lock()
    lock = threading.RLock()  # Flask xử lý đa luồng: tránh ghi đè sổ cái đồng thời

    def add_peers(urls) -> list:
        added = []
        with peers_lock:
            for url in urls:
                if not isinstance(url, str) or not url.startswith("http"):
                    continue
                url = url.rstrip("/")
                if url != self_url and url not in peers:
                    peers.add(url)
                    added.append(url)
        return added

    def peer_list() -> list:
        with peers_lock:
            return sorted(peers)

    def source_of_request() -> str:
        return request.headers.get(NODE_HEADER, "client")

    add_peers(initial_peers)

    # ---------------------------------------------------------------- Phát tán (Gossip)
    # Mỗi peer có một hàng đợi + luồng gửi riêng:
    #  - tin tới cùng một peer luôn đúng thứ tự (giao dịch nonce 0 đến trước nonce 1);
    #  - peer ngoại tuyến (mất ~2s mỗi lần thử trên Windows) không làm chậm các peer khác;
    #  - API trả kết quả ngay, không phải chờ gửi xong.
    outboxes = {}
    outboxes_lock = threading.Lock()

    def peer_worker(peer: str, outbox: queue.Queue):
        while True:
            path, payload = outbox.get()
            try:
                requests.post(f"{peer}{path}", json=payload, headers={NODE_HEADER: self_url}, timeout=3)
            except requests.exceptions.RequestException:
                pass  # Bỏ qua peer đang ngoại tuyến

    def outbox_for(peer: str) -> queue.Queue:
        with outboxes_lock:
            if peer not in outboxes:
                outboxes[peer] = queue.Queue()
                threading.Thread(
                    target=peer_worker, args=(peer, outboxes[peer]), daemon=True, name=f"gossip-{port}-{peer}"
                ).start()
            return outboxes[peer]

    def broadcast(path: str, payload: dict = None, exclude: str = None):
        for peer in peer_list():
            if peer != exclude:
                outbox_for(peer).put((path, payload))

    # ---------------------------------------------------------------- Đồng bộ chuỗi
    def sync_chain() -> bool:
        """
        Thuật toán đồng bộ hóa (Longest Chain Rule):
        Hỏi tất cả các Full Node lân cận, lấy chuỗi dài hơn và kiểm tra hợp lệ toàn bộ.
        """
        longest_chain = None
        longest_peer = None
        max_length = len(blockchain.chain)

        for peer in peer_list():
            try:
                resp = requests.get(f"{peer}/chain", timeout=3)
                if resp.status_code != 200:
                    continue
                candidate_chain = [Block.from_dict(b) for b in resp.json()["chain"]]
            except (requests.exceptions.RequestException, ValueError, KeyError, TypeError):
                continue  # Bỏ qua các peer ngoại tuyến hoặc trả về dữ liệu lỗi

            if len(candidate_chain) <= max_length:
                continue
            error = blockchain.validate_chain(candidate_chain)
            if error:
                log("bad", f"Chuỗi {len(candidate_chain)} khối từ {peer} không hợp lệ: {error}")
                continue
            max_length = len(candidate_chain)
            longest_chain = candidate_chain
            longest_peer = peer

        if longest_chain:
            with lock:
                old_length = len(blockchain.chain)
                if len(longest_chain) > old_length:
                    blockchain.replace_chain(longest_chain)
                    log(
                        "ok",
                        f"Đồng bộ: thay chuỗi cục bộ {old_length} → {len(longest_chain)} khối từ "
                        f"{longest_peer} (đã xác minh liên kết băm, PoW và toàn bộ chữ ký ECDSA)",
                    )
                    return True
        log("info", f"Đồng bộ: chuỗi cục bộ đã là mới nhất ({len(blockchain.chain)} khối)")
        return False

    def register_with_peers():
        """Peer Discovery: giới thiệu mình với các peer và học thêm peer từ họ."""
        to_contact = peer_list()
        contacted = set()
        while to_contact:
            peer = to_contact.pop()
            if peer in contacted:
                continue
            contacted.add(peer)
            try:
                resp = requests.post(
                    f"{peer}/nodes/register",
                    json={"peers": [self_url]},
                    headers={NODE_HEADER: self_url},
                    timeout=3,
                )
                learned = add_peers(resp.json().get("peers", []))
            except (requests.exceptions.RequestException, ValueError, AttributeError):
                continue
            for url in learned:
                log("info", f"Biết thêm peer {url} qua {peer}")
            to_contact.extend(learned)

    # ---------------------------------------------------------------- Giao diện Web
    @app.route("/", methods=["GET"])
    def index():
        return app.send_static_file("index.html")

    # ---------------------------------------------------------------- Ví & sổ cái
    @app.route("/wallet", methods=["GET"])
    def get_wallet():
        return jsonify({
            "address": wallet.public_key_hex,
            "balance": blockchain.get_balance(wallet.public_key_hex),
            "next_nonce": blockchain.get_next_nonce(wallet.public_key_hex),
        })

    @app.route("/status", methods=["GET"])
    def get_status():
        with lock:
            return jsonify({
                "port": port,
                "url": self_url,
                "address": wallet.public_key_hex,
                "balance": blockchain.get_balance(wallet.public_key_hex),
                "next_nonce": blockchain.get_next_nonce(wallet.public_key_hex),
                "chain_length": len(blockchain.chain),
                "latest_hash": blockchain.latest_block.hash,
                "mempool_size": len(blockchain.mempool),
                "difficulty": blockchain.difficulty,
                "mining_reward": blockchain.mining_reward,
                "peers": peer_list(),
            })

    @app.route("/balance/<address>", methods=["GET"])
    def get_balance(address):
        return jsonify({"address": address, "balance": blockchain.get_balance(address)})

    @app.route("/chain", methods=["GET"])
    def get_chain():
        with lock:
            return jsonify({
                "length": len(blockchain.chain),
                "chain": [b.to_dict() for b in blockchain.chain],
            })

    @app.route("/mempool", methods=["GET"])
    def get_mempool():
        with lock:
            return jsonify({
                "size": len(blockchain.mempool),
                "transactions": [tx.to_dict() for tx in blockchain.mempool],
            })

    @app.route("/logs", methods=["GET"])
    def get_logs():
        return jsonify({"logs": list(log_buffer)})

    # ---------------------------------------------------------------- Giao dịch
    def build_signed_tx(data: dict):
        if "recipient" not in data or "amount" not in data:
            raise ValueError("Thiếu trường 'recipient' hoặc 'amount'")
        tx = Transaction(
            sender=wallet.public_key_hex,
            recipient=str(data["recipient"]).strip(),
            amount=data["amount"],
            nonce=blockchain.get_next_nonce(wallet.public_key_hex),  # Số thứ tự giao dịch kế tiếp
        )
        tx.sign_transaction(wallet)
        return tx

    @app.route("/transactions/send", methods=["POST"])
    def create_and_broadcast_tx():
        """Tạo giao dịch từ ví của node này, ký ECDSA và phát tán lên mạng P2P."""
        data = request.get_json(silent=True) or {}
        with lock:
            try:
                tx = build_signed_tx(data)
            except (TypeError, ValueError) as e:
                return jsonify({"error": f"Dữ liệu giao dịch không hợp lệ: {e}"}), 400
            accepted, reason = blockchain.try_add_transaction(tx)

        tx_hash = short(tx.calculate_hash())
        if not accepted:
            log("bad", f"Từ chối giao dịch {tx_hash} ({tx.amount:g} → {short(tx.recipient)}): {reason}")
            return jsonify({"error": reason}), 400

        log(
            "ok",
            f"Đã ký giao dịch {tx_hash}: {tx.amount:g} → {short(tx.recipient)} (nonce {tx.nonce}). "
            f"Xác minh ECDSA hợp lệ → thêm vào Mempool và phát tán",
        )
        broadcast("/transactions/receive", tx.to_dict())
        return jsonify({"message": "Đã ký và phát tán giao dịch", "transaction": tx.to_dict()}), 201

    @app.route("/transactions/sign", methods=["POST"])
    def sign_only():
        """Ký giao dịch nhưng KHÔNG gửi đi — dùng để thử sửa dữ liệu sau khi ký (kịch bản giả mạo)."""
        data = request.get_json(silent=True) or {}
        with lock:
            try:
                tx = build_signed_tx(data)
            except (TypeError, ValueError) as e:
                return jsonify({"error": f"Dữ liệu giao dịch không hợp lệ: {e}"}), 400
        log("info", f"Đã ký (chưa gửi) giao dịch {short(tx.calculate_hash())}: {tx.amount:g} → {short(tx.recipient)}")
        return jsonify({"transaction": tx.to_dict(), "hash": tx.calculate_hash()}), 200

    @app.route("/transactions/receive", methods=["POST"])
    def receive_tx():
        """Nhận giao dịch từ peer khác và xác minh chữ ký số ECDSA."""
        source = source_of_request()
        try:
            tx = Transaction.from_dict(request.get_json(silent=True) or {})
        except (KeyError, TypeError, ValueError):
            log("bad", f"Từ chối dữ liệu giao dịch sai định dạng từ {source}")
            return jsonify({"error": "Dữ liệu giao dịch không đúng định dạng"}), 400

        with lock:
            accepted, reason = blockchain.try_add_transaction(tx)
        tx_hash = short(tx.calculate_hash())

        if accepted:
            log(
                "ok",
                f"Nhận giao dịch {tx_hash} từ {source}: {tx.amount:g} → {short(tx.recipient)} "
                f"(nonce {tx.nonce}). Xác minh ECDSA hợp lệ, đủ số dư → thêm vào Mempool",
            )
            broadcast("/transactions/receive", tx.to_dict(), exclude=source)
            return jsonify({"message": reason}), 201

        if reason == TX_DUPLICATE and source != "client":
            # Bình thường trong gossip: cùng một giao dịch đến từ nhiều peer, không cần báo lỗi
            return jsonify({"error": reason}), 409
        log("bad", f"Từ chối giao dịch {tx_hash} từ {source}: {reason}")
        return jsonify({"error": f"Từ chối: {reason}"}), 400

    # ---------------------------------------------------------------- Khối
    @app.route("/mine", methods=["POST"])
    def mine():
        started = time.time()
        with lock:
            tx_count = len(blockchain.mempool)
            new_block = blockchain.mine_pending_transactions(wallet.public_key_hex)
        elapsed = time.time() - started
        log(
            "ok",
            f"Đào khối #{new_block.index} thành công sau {elapsed:.2f}s: nonce={new_block.nonce}, "
            f"hash={new_block.hash[:16]}…, {tx_count} giao dịch + thưởng {blockchain.mining_reward:g}",
        )
        # Phát tán khối mới cho các peer
        broadcast("/blocks/receive", new_block.to_dict())
        return jsonify({
            "message": "Đào khối thành công",
            "mining_time": round(elapsed, 3),
            "block": new_block.to_dict(),
        }), 200

    @app.route("/blocks/receive", methods=["POST"])
    def receive_block():
        """Nhận khối do peer phát tán: xác minh rồi nối vào chuỗi, hoặc đồng bộ nếu bị thiếu khối."""
        source = source_of_request()
        try:
            block = Block.from_dict(request.get_json(silent=True) or {})
        except (KeyError, TypeError, ValueError):
            log("bad", f"Từ chối dữ liệu khối sai định dạng từ {source}")
            return jsonify({"error": "Dữ liệu khối không đúng định dạng"}), 400

        with lock:
            status, reason = blockchain.try_add_block(block)
            length = len(blockchain.chain)

        if status == BLOCK_ACCEPTED:
            log(
                "ok",
                f"Nhận khối #{block.index} từ {source}: hợp lệ (PoW + {len(block.transactions)} "
                f"chữ ký/giao dịch) → nối vào chuỗi, độ dài {length}",
            )
            broadcast("/blocks/receive", block.to_dict(), exclude=source)
            return jsonify({"message": reason, "length": length}), 200
        if status == BLOCK_NEED_SYNC:
            log("info", f"{reason} → chạy đồng bộ chuỗi")
            sync_chain()
            return jsonify({"message": reason, "length": len(blockchain.chain)}), 202
        if status == BLOCK_REJECTED:
            log("bad", f"Từ chối khối #{block.index} từ {source}: {reason}")
            return jsonify({"error": reason}), 400
        return jsonify({"message": reason, "length": length}), 200  # BLOCK_STALE

    # ---------------------------------------------------------------- Mạng P2P
    @app.route("/nodes/sync", methods=["POST", "GET"])
    def trigger_sync():
        replaced = sync_chain()
        msg = "Đã đồng bộ chuỗi dài hơn từ mạng!" if replaced else "Chuỗi hiện tại đã là mới nhất."
        return jsonify({"message": msg, "length": len(blockchain.chain)}), 200

    @app.route("/nodes", methods=["GET"])
    def list_peers():
        return jsonify({"peers": peer_list()})

    @app.route("/nodes/register", methods=["POST"])
    def register_peers():
        data = request.get_json(silent=True) or {}
        new_peers = data.get("peers", [])
        if not isinstance(new_peers, list):
            return jsonify({"error": "'peers' phải là danh sách URL"}), 400
        for url in add_peers(new_peers):
            log("info", f"Peer mới đăng ký: {url}")
        # Trả về danh sách peer (kèm chính mình) để node mới học thêm peer
        return jsonify({"message": "Đã cập nhật danh sách peer", "peers": peer_list() + [self_url]}), 201

    @app.route("/nodes/addresses", methods=["GET"])
    def peer_addresses():
        """Hỏi địa chỉ ví của từng peer (dùng cho danh sách người nhận trên giao diện)."""
        def fetch(peer):
            try:
                resp = requests.get(f"{peer}/wallet", timeout=2)
                return {"url": peer, "online": True, "address": resp.json()["address"]}
            except (requests.exceptions.RequestException, ValueError, KeyError):
                return {"url": peer, "online": False, "address": None}

        targets = peer_list()
        if not targets:
            return jsonify({"peers": []})
        with ThreadPoolExecutor(max_workers=len(targets)) as pool:
            return jsonify({"peers": list(pool.map(fetch, targets))})

    # ---------------------------------------------------------------- Khởi động
    log("info", f"Khởi động Full Node tại {self_url}, sổ cái {len(blockchain.chain)} khối, độ khó PoW {difficulty}")
    log("info", f"Địa chỉ ví: {wallet.public_key_hex}")
    if peers:
        register_with_peers()
        sync_chain()  # Tự động đồng bộ ngay khi Full Node khởi động lại

    return app
