import os
import threading

import requests
from flask import Flask, jsonify, request

from core.block import Block
from core.blockchain import Blockchain
from core.transaction import Transaction
from core.wallet import Wallet

# Thư mục storage/ nằm cạnh run_node.py, không phụ thuộc thư mục đang đứng khi chạy lệnh
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")


def create_node_app(port: int, initial_peers: list, difficulty: int = 3):
    app = Flask(__name__)
    app.json.ensure_ascii = False  # Hiển thị tiếng Việt có dấu trong JSON trả về

    # Ví của node được lưu lại để giữ nguyên địa chỉ sau khi khởi động lại
    wallet = Wallet.load_or_create(os.path.join(STORAGE_DIR, f"wallet_{port}.json"))
    blockchain = Blockchain(
        storage_path=os.path.join(STORAGE_DIR, f"ledger_{port}.json"),
        difficulty=difficulty,
    )
    peers = {p.rstrip("/") for p in initial_peers}
    lock = threading.RLock()  # Flask xử lý đa luồng: tránh ghi đè sổ cái đồng thời

    def broadcast(path: str, payload: dict = None):
        for peer in list(peers):
            try:
                requests.post(f"{peer}{path}", json=payload, timeout=2)
            except requests.exceptions.RequestException:
                pass  # Bỏ qua peer đang ngoại tuyến

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
            except (requests.exceptions.RequestException, ValueError, KeyError, TypeError):
                continue  # Bỏ qua các peer ngoại tuyến hoặc trả về dữ liệu lỗi

        if longest_chain:
            with lock:
                if len(longest_chain) > len(blockchain.chain):
                    blockchain.replace_chain(longest_chain)
                    return True
        return False

    @app.route("/wallet", methods=["GET"])
    def get_wallet():
        return jsonify({
            "address": wallet.public_key_hex,
            "balance": blockchain.get_balance(wallet.public_key_hex),
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

    @app.route("/transactions/send", methods=["POST"])
    def create_and_broadcast_tx():
        """Tạo giao dịch từ ví của node này, ký ECDSA và phát tán lên mạng P2P."""
        data = request.get_json(silent=True) or {}
        if "recipient" not in data or "amount" not in data:
            return jsonify({"error": "Thiếu trường 'recipient' hoặc 'amount'"}), 400

        try:
            tx = Transaction(
                sender=wallet.public_key_hex,
                recipient=data["recipient"],
                amount=data["amount"],
                nonce=data.get("nonce", 0),
            )
        except (TypeError, ValueError):
            return jsonify({"error": "Dữ liệu giao dịch không hợp lệ"}), 400
        tx.sign_transaction(wallet)

        with lock:
            accepted = blockchain.add_transaction(tx)
        if not accepted:
            return jsonify({"error": "Giao dịch không hợp lệ hoặc không đủ số dư"}), 400

        # Phát tán giao dịch đã ký sang các peer khác
        broadcast("/transactions/receive", tx.to_dict())
        return jsonify({"message": "Đã ký và phát tán giao dịch", "transaction": tx.to_dict()}), 201

    @app.route("/transactions/receive", methods=["POST"])
    def receive_tx():
        """Nhận giao dịch từ peer khác và xác minh chữ ký số ECDSA."""
        try:
            tx = Transaction.from_dict(request.get_json(silent=True) or {})
        except (KeyError, TypeError, ValueError):
            return jsonify({"error": "Dữ liệu giao dịch không đúng định dạng"}), 400

        with lock:
            accepted = blockchain.add_transaction(tx)
        if accepted:
            return jsonify({"message": "Chữ ký hợp lệ, đã thêm vào Mempool"}), 201
        return jsonify({"error": "Từ chối: Chữ ký số sai hoặc vượt số dư!"}), 400

    @app.route("/mine", methods=["POST"])
    def mine():
        with lock:
            new_block = blockchain.mine_pending_transactions(wallet.public_key_hex)
        # Thông báo cho các peer khác đồng bộ chuỗi mới
        broadcast("/nodes/sync")
        return jsonify({"message": "Đào khối thành công", "block": new_block.to_dict()}), 200

    @app.route("/nodes/sync", methods=["POST", "GET"])
    def trigger_sync():
        replaced = sync_chain()
        msg = "Đã đồng bộ chuỗi dài hơn từ mạng!" if replaced else "Chuỗi hiện tại đã là mới nhất."
        return jsonify({"message": msg, "length": len(blockchain.chain)}), 200

    @app.route("/nodes", methods=["GET"])
    def list_peers():
        return jsonify({"peers": sorted(peers)})

    @app.route("/nodes/register", methods=["POST"])
    def register_peers():
        data = request.get_json(silent=True) or {}
        new_peers = data.get("peers", [])
        if not isinstance(new_peers, list):
            return jsonify({"error": "'peers' phải là danh sách URL"}), 400
        peers.update(p.rstrip("/") for p in new_peers if isinstance(p, str) and p)
        return jsonify({"message": "Đã cập nhật danh sách peer", "peers": sorted(peers)}), 201

    # Tự động đồng bộ ngay khi Full Node khởi động lại
    if peers:
        replaced = sync_chain()
        if replaced:
            print(f"[Node {port}] Đã đồng bộ chuỗi từ mạng, độ dài hiện tại: {len(blockchain.chain)}")

    print(f"[Node {port}] Địa chỉ ví: {wallet.public_key_hex}")
    print(f"[Node {port}] Sổ cái: {blockchain.storage_path} ({len(blockchain.chain)} khối)")
    return app
