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
│   └── blockchain.py         # Sổ cái, Mempool, số dư, kiểm tra chuỗi, lưu JSON
├── network/
│   └── node.py               # API Flask của Full Node, phát tán, Longest Chain Rule
├── storage/                  # Tự sinh: ledger_<port>.json, wallet_<port>.json
└── tests/test_core.py        # Kiểm thử tầng lõi
```

## Cài đặt & kiểm thử

```bash
cd code
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## Chạy 3 node

```bash
python run_node.py --port 5001 --peers http://127.0.0.1:5002 http://127.0.0.1:5003
python run_node.py --port 5002 --peers http://127.0.0.1:5001 http://127.0.0.1:5003
python run_node.py --port 5003 --peers http://127.0.0.1:5001 http://127.0.0.1:5002
```

## API

| Phương thức | Đường dẫn | Mô tả |
| --- | --- | --- |
| GET | `/wallet` | Địa chỉ ví và số dư của node |
| GET | `/balance/<address>` | Số dư của một địa chỉ bất kỳ |
| GET | `/chain` | Toàn bộ chuỗi khối |
| GET | `/mempool` | Giao dịch đang chờ |
| POST | `/transactions/send` | `{"recipient": "<pubkey hex>", "amount": 10}` – ký và phát tán |
| POST | `/transactions/receive` | Nhận giao dịch đã ký từ peer |
| POST | `/mine` | Đào khối mới (thưởng 50) và báo các peer đồng bộ |
| GET/POST | `/nodes/sync` | Đồng bộ theo Longest Chain Rule |
| GET | `/nodes` | Danh sách peer |
| POST | `/nodes/register` | `{"peers": ["http://127.0.0.1:5004"]}` |

## Kịch bản demo

1. `POST 5001/mine` → node 1 có 50 coin; node 2, 3 tự đồng bộ.
2. `GET 5002/wallet` lấy địa chỉ node 2, rồi `POST 5001/transactions/send` để chuyển tiền.
3. **Giả mạo giao dịch:** lấy JSON `transaction` vừa trả về, tăng `amount` thêm 1 rồi gửi tới
   `POST 5002/transactions/receive` → nhận mã `400` (chữ ký số sai).
4. **Mất kết nối:** tắt node 3 (Ctrl+C), đào/chuyển tiền vài lần trên node 1, bật lại node 3
   → node 3 tự đồng bộ khi khởi động, `ledger_5003.json` khớp với mạng.

## Khác biệt so với code mẫu trong `docs/cau-truc-code.md`

- `timestamp=0.0` của Genesis Block bị `or time.time()` ghi đè → mỗi node có Genesis khác nhau,
  không đồng bộ được. Đã đổi sang `is None`.
- Chặn giao dịch `SYSTEM` gửi từ ngoài vào (trước đây có thể tự "in tiền").
- Kiểm tra chuỗi: đúng 1 giao dịch thưởng ở đầu mỗi khối, đúng mức thưởng, không trùng giao dịch.
- Chống phát lại: từ chối giao dịch đã có trong chuỗi hoặc Mempool; dọn Mempool sau khi đồng bộ.
- Ví của node được lưu tại `storage/wallet_<port>.json` nên giữ nguyên địa chỉ sau khi khởi động lại.
- Thêm khóa `threading.RLock` cho các thao tác ghi sổ cái; `storage/` luôn nằm cạnh `run_node.py`.
