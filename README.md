# Ví điện tử Full Node P2P – Chữ ký số ECDSA (secp256k1)

## Cấu trúc

```text
p2p_ecdsa_wallet/
├── requirements.txt
├── run_node.py               # Khởi chạy một Full Node (--port, --peers, --difficulty)
├── core/
│   ├── wallet.py             # Cặp khóa ECDSA, ký / xác minh, lưu khóa của node
│   ├── transaction.py        # Giao dịch, băm SHA-256, xác thực chữ ký
│   ├── block.py              # Khối, băm khối, Proof of Work
│   └── blockchain.py         # Sổ cái, Mempool, số dư, nonce, kiểm tra chuỗi, nhận khối, lưu JSON
├── network/
│   ├── node.py               # API Flask của Full Node: gossip, peer discovery, Longest Chain Rule, log
│   └── static/               # Giao diện Web của ví (index.html, app.js, style.css)
├── storage/                  # Tự sinh: ledger_<port>.json, wallet_<port>.json
└── tests/
    ├── test_core.py          # Kiểm thử tầng lõi
    └── test_node.py          # Kiểm thử API của node
```

## Cài đặt & kiểm thử

```bash
cd p2p_ecdsa_wallet
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## Chạy 3 node

Mỗi lệnh chạy trong một terminal riêng:

```bash
python run_node.py --port 5001 --peers http://127.0.0.1:5002 http://127.0.0.1:5003
python run_node.py --port 5002 --peers http://127.0.0.1:5001 http://127.0.0.1:5003
python run_node.py --port 5003 --peers http://127.0.0.1:5001
```

Node 3 chỉ cần biết một node đang chạy (seed node). Lúc khởi động, nó tự đăng ký với 5001 và học được địa chỉ 5002 từ đó.

Mở giao diện ví của từng node: <http://127.0.0.1:5001/>, <http://127.0.0.1:5002/>, <http://127.0.0.1:5003/>.

Để demo lại từ đầu, tắt các node rồi xóa `storage/*.json`.

## Kịch bản kiểm thử trên giao diện (theo `docs/idea.md`)

1. **Tạo ví và giao dịch hợp lệ.** Mỗi node tự tạo ví khi chạy lần đầu (khóa lưu ở `storage/wallet_<port>.json`).
   Trên node 5001, bấm **Đào khối** để nhận 50 coin. Ở mục **Chuyển tiền**, chọn ví của node 5002 làm người nhận rồi bấm **Ký & gửi giao dịch**.
   Giao dịch hiện trong Mempool của cả 3 node. Bấm **Đào khối** thêm lần nữa để giao dịch được ghi vào chuỗi.
2. **Giả mạo giao dịch.** Ở mục **Kiểm thử giả mạo**: bấm *1. Ký giao dịch*, sau đó *2a. Sửa số tiền +1* hoặc
   *2b. Sửa 1 ký tự người nhận*, rồi *3. Gửi tới node*. Kết quả là `HTTP 400` với thông báo "Chữ ký ECDSA không hợp lệ".
   Bấm *Khôi phục bản gốc* rồi gửi lại thì được `HTTP 201`. Gửi thêm lần nữa thì bị từ chối vì phát lại.
3. **Chi tiêu vượt số dư.** Ở mục **Chuyển tiền**, nhập số tiền lớn hơn số dư. Kết quả là thông báo "Không đủ số dư (khả dụng X, cần Y)".
4. **Mất kết nối.** Tắt node 5003 (Ctrl+C). Trên node 5001 và 5002, chuyển tiền và đào vài khối.
   Lúc này `storage/ledger_5003.json` vẫn ngắn hơn. Bật lại node 5003: log ghi
   "Đồng bộ: thay chuỗi cục bộ X → Y khối … (đã xác minh liên kết băm, PoW và toàn bộ chữ ký ECDSA)",
   và chuỗi của node 5003 khớp với mạng.

Mỗi sự kiện được ghi ra terminal của node và hiện ở mục **Nhật ký node** trên giao diện: màu xanh là hợp lệ, màu đỏ là bị từ chối.

## API

| Phương thức | Đường dẫn | Mô tả |
| --- | --- | --- |
| GET | `/` | Giao diện Web của ví |
| GET | `/status` | Cổng, địa chỉ ví, số dư, nonce kế tiếp, độ dài chuỗi, mempool, peer |
| GET | `/wallet` | Địa chỉ ví, số dư và nonce kế tiếp của node |
| GET | `/balance/<address>` | Số dư của một địa chỉ bất kỳ |
| GET | `/chain` | Toàn bộ chuỗi khối |
| GET | `/mempool` | Giao dịch đang chờ |
| GET | `/logs` | 200 sự kiện gần nhất của node |
| POST | `/transactions/send` | `{"recipient": "<pubkey hex>", "amount": 10}`: ký (nonce tự điền) và phát tán |
| POST | `/transactions/sign` | Giống `send` nhưng chỉ ký, không gửi (dùng cho kịch bản giả mạo) |
| POST | `/transactions/receive` | Nhận giao dịch đã ký, xác minh ECDSA, nonce, số dư rồi chuyển tiếp |
| POST | `/mine` | Đào khối mới (thưởng 50) và phát tán khối |
| POST | `/blocks/receive` | Nhận khối từ peer: nối vào chuỗi nếu hợp lệ, tự đồng bộ nếu bị thiếu khối |
| GET/POST | `/nodes/sync` | Đồng bộ theo Longest Chain Rule |
| GET | `/nodes` | Danh sách peer |
| GET | `/nodes/addresses` | Địa chỉ ví và trạng thái online của từng peer |
| POST | `/nodes/register` | `{"peers": ["http://127.0.0.1:5004"]}`; trả về danh sách peer đã biết |

## Đối chiếu với `docs/idea.md`

| Yêu cầu trong idea.md | Vị trí trong code |
| --- | --- |
| Cặp khóa ECDSA `secp256k1`, Public Key làm địa chỉ ví | `core/wallet.py` → `Wallet` |
| h = SHA256(TxData), S = Sign(h, K_private), Verify(h', S, K_public) | `Transaction.calculate_hash`, `sign_transaction`, `is_valid` |
| Transaction gồm sender, recipient, amount, timestamp, nonce, signature | `core/transaction.py` |
| Nonce là số thứ tự giao dịch, chống Replay Attack | `Blockchain.get_next_nonce`, `try_add_transaction`, `validate_chain` |
| Block gồm index, timestamp, transactions, previous_hash, nonce, hash; PoW độ khó 3 | `core/block.py` → `mine_block` |
| Account-based, chống chi tiêu kép | `Blockchain.get_balance`, `try_add_transaction` |
| Sổ cái JSON riêng cho từng node, không dùng CSDL tập trung | `storage/ledger_<port>.json` |
| Peer Discovery (seed node + đăng ký) | `register_with_peers`, `/nodes/register` |
| Phát tán giao dịch và khối mới (Gossip) | `broadcast`, `/transactions/receive`, `/blocks/receive` |
| `is_chain_valid` (liên kết băm, PoW, chữ ký, số dư) và Longest Chain Rule | `Blockchain.validate_chain`, `sync_chain` |
| Node offline tự đồng bộ khi bật lại | `sync_chain()` được gọi trong `create_node_app` |
| Giao diện Web và log cho 4 kịch bản kiểm thử | `network/static/`, `/logs` |

## Khác biệt so với code mẫu trong `docs/cau-truc-code.md`

- `timestamp=0.0` của Genesis Block bị `or time.time()` ghi đè, nên mỗi node có một Genesis khác nhau và
  không đồng bộ được. Đã đổi sang kiểm tra `is None`.
- Chặn giao dịch `SYSTEM` gửi từ ngoài vào (trước đây ai cũng có thể tự "in tiền"). Chặn cả số tiền `NaN`/vô cực.
- Khi kiểm tra chuỗi: mỗi khối có đúng 1 giao dịch thưởng ở đầu, đúng mức thưởng; không có giao dịch trùng; nonce tăng dần.
- Chống phát lại bằng nonce và bằng mã băm giao dịch. Mempool được dọn sau khi đồng bộ; giao dịch nằm trong
  khối bị bỏ do fork được trả lại Mempool.
- Ví của node được lưu tại `storage/wallet_<port>.json`, nên giữ nguyên địa chỉ sau khi khởi động lại.
- Mỗi peer có một hàng đợi gửi riêng (giữ đúng thứ tự, peer offline không làm chậm peer khác).
  `/mine` đẩy khối qua `/blocks/receive` thay vì chỉ báo `/nodes/sync`.
- Thêm khóa `threading.RLock` cho các thao tác ghi sổ cái; `storage/` luôn nằm cạnh `run_node.py`.
