# Phân chia kiến thức và đầu việc – Nhóm 9 (Đề K)

Tài liệu này chia dự án **Ví điện tử Full Node P2P – chữ ký số ECDSA** cho 4 thành viên. Căn cứ để chia:
- báo cáo `docs/example-Baocao_nhom9_blockchain.docx` (4 chương, khoảng 31 trang nội dung);
- mã nguồn trong `p2p_ecdsa_wallet/`.

Thành viên nhóm (theo bìa báo cáo): Lý Đình Sơn, Nguyễn Đình Tuấn Sơn, Trương Hữu Quang, Trần Giang Sơn.


---

## 0. Bảng tổng quan

| | Người 1 – Tạo chữ ký số | Người 2 – Xác minh chữ ký số | Người 3 – Chuỗi khối & Sổ cái | Người 4 – Mạng P2P & Đồng bộ |
| --- | --- | --- | --- | --- |
| **Người phụ trách** | Tuấn Sơn | Lý Sơn | Quang | Trần Sơn |
| **Trọng tâm** | Băm dữ liệu (SHA-256), đường cong Elliptic & secp256k1, sinh cặp khóa, **tạo chữ ký (r, s)**, vai trò của số ngẫu nhiên k | **Xác minh chữ ký**, chứng minh tính đúng, vì sao sửa dữ liệu thì chữ ký sai, các điểm xác minh trong hệ thống, so với RSA | Giao dịch, Mempool, khối, nonce, số dư, PoW | Full Node, peer discovery, gossip, Longest Chain Rule, node tắt/bật lại |
| **Mục báo cáo** | 1.1, 2.1.1, 2.1.3a, 2.1.3b-Bước 1–2 + số ngẫu nhiên k, 3.1.2, 3.3.1 (khóa + `sign`), 3.3.2 (băm + `sign_transaction`), 3.4.2, 4.3.2 | 1.2, 1.3.1, 1.4, 2.1.2, 2.1.3b-Bước 3 + chứng minh, 2.1.3c, 2.4 (bảng) + 2.4.1, 3.1.3a, 3.3.1 (`verify`), 3.3.2 (`is_valid`), 3.4.3, bảng tổng hợp 3.4, 4.1 | 1.3.2, 2.2, 2.3.2, 2.4.3, 3.2, 3.3.3, 3.4.4, 4.2.2, 4.3.1 | 1.3.3, 2.3.1, 2.3.3, 2.4.2, 3.1.1, 3.1.3b, 3.1.4, 3.3.4, 3.4.1, 3.4.5, 4.2.1, 4.3.3 |
| **≈ Số trang** | ~7,5 | ~7,5 (+ ghép, định dạng, tài liệu tham khảo) | ~8 | ~8 |
| **Code** | `Wallet.__init__`, `sign()`, `load_or_create()`; `Transaction.calculate_hash()`, `sign_transaction()`; `build_signed_tx()` + route `/transactions/sign` | `Wallet.verify()`; `Transaction.is_valid()`; lớp kiểm tra chữ ký trong `try_add_transaction()` và `validate_chain()` | `block.py`, `blockchain.py` (trừ phần xác minh chữ ký) | `network/node.py` (trừ `/transactions/sign`), `run_node.py` |
| **Mục trên giao diện** | Ví của node; nút "1. Ký giao dịch" | Các nút sửa và "3. Gửi tới node để xác minh" | Chuyển tiền, Đào khối, Mempool, Chuỗi khối | Mạng ngang hàng, Đồng bộ ngay, Nhật ký node |
| **Demo** | Kịch bản 1 – Tạo ví & ký giao dịch hợp lệ; bước ký ở Kịch bản 2 | Kịch bản 2 – Giả mạo bị phát hiện; dẫn dắt; chạy 19 test | Kịch bản 3 – Vượt số dư & chi tiêu kép | Khởi chạy mạng; Kịch bản 4 – Tắt/bật lại node |

Số trang ước lượng theo số trang thật của từng mục trong mục lục báo cáo mẫu.

**Ranh giới giữa Người 1 và Người 2:**
- Người 1 trả lời câu hỏi *"chữ ký được tạo ra thế nào?"*: từ dữ liệu giao dịch → mã băm → (d, k) → (r, s).
- Người 2 trả lời câu hỏi *"làm sao biết chữ ký đúng mà không cần khóa bí mật?"*: từ (dữ liệu, r, s, Q) → đúng/sai.
- Cả hai cùng dùng một bộ ký hiệu: d, Q, G, n, k, z, r, s.

---

## 1. Kiến thức chung – cả 4 người đều phải nắm

Ai bị hỏi cũng phải trả lời được những điều sau, không đẩy sang người khác:

1. **Đề K là gì và nhóm mở rộng thế nào.**
   Đề K yêu cầu sinh khóa, ký, xác minh chữ ký. Nhóm đặt chữ ký số vào một mạng ví điện tử gồm nhiều Full Node, mỗi node có ví và sổ cái JSON riêng.
2. **Ba quy tắc** (xem `HOW-TO-PLAY.md`):
   - tiền chỉ sinh ra khi đào khối (thưởng 50 coin);
   - giao dịch chỉ có hiệu lực khi đã vào khối (trước đó nằm trong Mempool);
   - nonce là số thứ tự giao dịch của ví.
3. **Luồng một giao dịch:** băm & ký (Người 1) → tự xác minh (Người 2) → Mempool (Người 3) → phát tán (Người 4) → mỗi peer tự xác minh (Người 2) → một node đào khối (Người 3) → khối được phát tán (Người 4) → mọi node xác minh khối và nối vào chuỗi.
4. **Cách chạy 3 node và 4 kịch bản kiểm thử.** Mỗi người tự chạy được cả 4 kịch bản theo `HOW-TO-PLAY.md`, phòng khi người phụ trách vắng.
5. **Cấu trúc thư mục:** `core/` là logic và mật mã, không biết gì về HTTP. `network/` là API Flask và giao diện. `storage/` là dữ liệu chạy, không commit vì chứa Private Key.
6. **Hạn chế lớn nhất:** hiện chỉ chạy trên một máy (`127.0.0.1`); chưa có xác thực API; chưa xuyên NAT.

**Việc chung:** mỗi người clone repo và chạy `python -m unittest discover -s tests -v` (kết quả 19/19), rồi tự chơi hết `HOW-TO-PLAY.md` một lượt.

---

## 2. Người 1 – Tạo chữ ký số (Băm, Khóa và Ký)

**Vai trò trong chủ đề:** phía *người gửi*. Người 1 giải thích cách một ví sinh ra cặp khóa, rồi biến dữ liệu giao dịch thành chữ ký (r, s) mà chỉ chủ khóa bí mật mới tạo được.

### Kiến thức cần nắm
- **SHA-256 – băm trước khi ký:**
  - đầu ra 256 bit (64 hex), FIPS 180-4;
  - các tính chất: một chiều, kháng tiền ảnh thứ hai, kháng va chạm (≈2¹²⁸), tính tất định, hiệu ứng tuyết lở;
  - SHA-256 được dùng ở 3 chỗ: băm giao dịch để ký, băm khối, và làm hàm mục tiêu PoW.
- **Tuần tự hóa nhất quán:**
  - `json.dumps(sort_keys=True)`;
  - ép kiểu `amount` sang float, `nonce` sang int;
  - **không** băm trường `signature` (chữ ký không thể ký lên chính nó).
- **Đường cong Elliptic trên Fp:**
  - phương trình y² ≡ x³ + ax + b (mod p), điều kiện 4a³ + 27b² ≢ 0, điểm vô cực O;
  - phép cộng điểm (công thức λ), phép nhân vô hướng k·G bằng nhân đôi và cộng.
- **Bài toán ECDLP:** cho G và Q = d·G, tìm d là bất khả thi (Pollard's rho cần khoảng √n ≈ 2¹²⁸ phép toán).
- **secp256k1:** a = 0, b = 7; ý nghĩa của p, G, n, h (bảng 2.1).
- **Bước 1 – Sinh cặp khóa:**
  - chọn d ∈ [1, n−1] ngẫu nhiên, tính Q = d·G;
  - Private Key 32 byte (64 hex); Public Key 64 byte x‖y (128 hex) và chính là **địa chỉ ví**.
- **Bước 2 – Tạo chữ ký:**
  - z = 256 bit trái nhất của H(m);
  - chọn k ngẫu nhiên ∈ [1, n−1];
  - (x₁, y₁) = k·G, r = x₁ mod n;
  - s = k⁻¹(z + r·d) mod n;
  - chữ ký (r, s) dài 64 byte (128 hex). Nếu r = 0 hoặc s = 0 thì chọn lại k.
- **Số ngẫu nhiên k:**
  - mỗi lần ký phải dùng một k mới, nên ký hai lần cùng dữ liệu cho hai chữ ký khác nhau nhưng đều hợp lệ;
  - dùng lại k thì lộ d: k = (z₁ − z₂)(s₁ − s₂)⁻¹, d = (s₁·k − z₁)·r⁻¹ (sự cố PS3 năm 2010);
  - hướng khắc phục: RFC 6979.
- **Chi tiết cài đặt:** `Transaction.calculate_hash()` trả về hex SHA-256, rồi `Wallet.sign()` băm chuỗi hex đó thêm lần nữa bằng SHA-256. Như vậy chữ ký thực chất nằm trên **mã băm của mã băm**. Người 2 xác minh cũng làm y hệt.
- **Thư viện `ecdsa`:** `SECP256k1`, `SigningKey.generate()` / `from_string()`, `get_verifying_key()`, `SigningKey.sign(..., hashfunc=sha256)`.

### Phần báo cáo phụ trách
| Mục | Nội dung |
| --- | --- |
| 1.1 (1.1.1, 1.1.2) | Hạn chế của mô hình tập trung; vai trò của Blockchain/DLT (ba trụ cột: mật mã, P2P, đồng thuận) |
| 2.1.1 | Hàm băm SHA-256 + minh họa hiệu ứng tuyết lở trên giao dịch |
| 2.1.3 a) | Cơ sở toán học đường cong Elliptic, Bảng 2.1 (tham số secp256k1) |
| 2.1.3 b) Bước 1–2 | Sinh cặp khóa; tạo chữ ký (r, s); tầm quan trọng của số ngẫu nhiên k |
| 3.1.2 | Sơ đồ lớp UML (Hình 3.2). Người 3 rà phần Block/Blockchain |
| 3.3.1 (phần khóa + ký) | Khởi tạo cặp khóa, `public_key_hex` làm địa chỉ ví, `load_or_create()`, hàm `sign()` |
| 3.3.2 (phần băm + ký) | Tuần tự hóa với `sort_keys=True`, `calculate_hash()`, `sign_transaction()` |
| 3.4.2 | Kịch bản 1 – Giao dịch hợp lệ (Bảng 3.2) |
| 4.3.2 | Hướng mở rộng quản lý khóa: HD Wallet BIP-32/39, mã hóa tệp khóa, ký tất định RFC 6979 |

### Code phụ trách (giải thích được từng dòng)
- `core/wallet.py`: `__init__` (`generate` / `from_string`), `private_key_hex`, `public_key_hex`, **`sign()`**, `save_to_file()`, `load_or_create()`.
- `core/transaction.py`:
  - `__init__` (ép kiểu, `timestamp is None`);
  - `calculate_hash()`;
  - **`sign_transaction()`** (chặn ký hộ ví người khác);
  - `to_dict()` / `from_dict()`.
- `network/node.py`: `build_signed_tx()` (tự điền nonce rồi ký) và route `/transactions/sign`.
- Giao diện: thẻ **Ví của node** (địa chỉ, nút Sao chép, nonce kế tiếp) và nút **"1. Ký giao dịch"** ở mục Kiểm thử giả mạo.
- Test: `test_sign_and_verify`, `test_restore_from_private_key`, `test_genesis_is_identical_across_nodes`.

### Demo phụ trách
- **Kịch bản 1 – Tạo ví & ký giao dịch hợp lệ:**
  1. **Tạo ví:** mở `storage/wallet_5001.json`, chỉ Private Key 64 hex và địa chỉ (Public Key) 128 hex; đối chiếu với địa chỉ trên giao diện.
     Tắt rồi bật lại node để cho thấy địa chỉ **không đổi**.
  2. **Ký giao dịch:** node 5001 đào khối để có 50 coin, rồi chuyển 10 coin cho 5002. Chỉ chữ ký (r, s) trong ô kết quả.
  3. **Kết quả:** giao dịch được các node khác chấp nhận (nhật ký "Xác minh ECDSA hợp lệ"). Một node đào khối; đối chiếu số dư 3 node.

  Phần Mempool và đào khối do Người 3 giải thích bổ sung.
- **Kịch bản 2, bước 1:** bấm "1. Ký giao dịch". Giải thích mã băm được ký và chữ ký vừa tạo, rồi chuyển cho Người 2.
- (Tùy chọn) **Hiệu ứng tuyết lở / k ngẫu nhiên:**
  - ký amount 10 và amount 11, so sánh hai mã băm;
  - ký hai lần cùng một nội dung, so sánh hai chữ ký.

### Câu hỏi vấn đáp cần chuẩn bị
| Câu hỏi | Ý trả lời |
| --- | --- |
| Vì sao từ Private Key tính được Public Key mà không làm ngược lại được? | Q = d·G tính nhanh bằng nhân đôi và cộng; tìm d từ Q là bài toán ECDLP, cần khoảng 2¹²⁸ phép toán |
| Vì sao ký lên mã băm mà không ký thẳng dữ liệu? | Chữ ký có độ dài cố định, nhanh; ECDSA chỉ dùng z dài bằng bậc n (256 bit) |
| Chữ ký gồm những gì, dài bao nhiêu? | Cặp (r, s), mỗi số 32 byte, tổng 64 byte = 128 ký tự hex trong trường `signature` |
| Ký hai lần cùng dữ liệu có cho cùng chữ ký không? | Không. Thư viện chọn k ngẫu nhiên mỗi lần, nên r và s khác nhau nhưng đều hợp lệ |
| Dùng lại k thì sao? Khắc phục thế nào? | Từ hai chữ ký tính được k rồi suy ra d (sự cố PS3); RFC 6979 sinh k tất định từ d và z |
| Vì sao phải `sort_keys=True` trước khi băm? | Người ký và người xác minh phải băm ra cùng một chuỗi byte; dict đi qua mạng có thể đổi thứ tự khóa |
| Chữ ký trong code thực chất tính trên gì? | SHA-256 của chuỗi hex mã băm giao dịch (băm hai lần); nhất quán giữa người ký và người xác minh nên vẫn đúng |
| Có thể ký giao dịch cho ví của người khác không? | `sign_transaction()` từ chối nếu ví ký khác `sender`; mà dù có cố ký bằng khóa khác thì Người 2 xác minh bằng Public Key của `sender` sẽ thất bại |
| Node khởi động lại có đổi ví không? | Không. Khóa lưu trong `wallet_<port>.json`, nạp lại bằng `from_string()` |

---

## 3. Người 2 – Xác minh chữ ký số

**Vai trò trong chủ đề:** phía *người nhận và toàn mạng*. Người 2 giải thích vì sao bất kỳ node nào, chỉ với dữ liệu, chữ ký và Public Key, cũng kiểm tra được giao dịch, và vì sao mọi sửa đổi sau khi ký đều bị phát hiện. Đây là kết quả trực tiếp của Đề K.

### Kiến thức cần nắm
- **Tổng quan chữ ký số:**
  - mô hình khóa bất đối xứng; ba thuật toán KeyGen / Sign / Verify; Hình 2.1;
  - chữ ký số mang lại ba tính chất: **toàn vẹn**, **xác thực**, **chống chối bỏ**.
- **Bước 3 – Xác minh chữ ký:**
  - kiểm tra Q là điểm hợp lệ trên đường cong và r, s ∈ [1, n−1];
  - tính lại z từ dữ liệu nhận được;
  - w = s⁻¹ mod n; u₁ = z·w; u₂ = r·w; (x₁, y₁) = u₁·G + u₂·Q;
  - chữ ký hợp lệ khi và chỉ khi r ≡ x₁ (mod n).
- **Chứng minh tính đúng:** u₁·G + u₂·Q = w(z + r·d)·G = s⁻¹(z + r·d)·G = k·G. Phải **tự viết lại được trên bảng**.
  Người xác minh chỉ dùng G, Q, r, s, z, không cần d hay k.
- **Vì sao sửa dữ liệu thì chữ ký sai:** dữ liệu đổi nên h' ≠ h, kéo theo z đổi; điểm tính ra khác k·G nên so sánh với r thất bại. Kẻ gian không ký lại được vì không có d.
- **Các điểm xác minh trong hệ thống:**
  1. node gửi tự xác minh trước khi đưa vào Mempool;
  2. mỗi peer xác minh khi nhận giao dịch (`/transactions/receive`);
  3. khi nhận khối mới (`try_add_block`);
  4. khi đồng bộ, xác minh lại **toàn bộ** chữ ký từ Genesis (`validate_chain`).
- **Thứ tự kiểm tra trong `try_add_transaction()`:** chữ ký → trùng lặp (phát lại) → nonce → số dư. Chữ ký sai thì dừng ngay, không xét tiếp.
- **Xử lý dữ liệu không đáng tin:** `verify()` bắt `BadSignatureError`, `ValueError`, `AssertionError` (hex hỏng, điểm không nằm trên đường cong) và trả `False` thay vì làm sập node.
- **So sánh ECDSA và RSA** (Bảng 2.2): kích thước khóa/chữ ký, tốc độ ký và xác minh; số đo thực tế (ký 0,39 ms, xác minh 1,27 ms). Xác minh chậm hơn ký là điểm cần biết khi bàn về đồng bộ chuỗi dài.
- **Thư viện `ecdsa`** (mục 2.4.1): `VerifyingKey.from_string()` (có kiểm tra điểm), `verify(..., hashfunc=sha256)`, `BadSignatureError`.

### Phần báo cáo phụ trách
| Mục | Nội dung |
| --- | --- |
| 1.2 (1.2.1, 1.2.2) | Phát biểu bài toán Đề K và cách mở rộng sang ví Full Node |
| 1.3.1 | Toàn vẹn, xác thực, chống chối bỏ; khái niệm Replay Attack và Double Spending |
| 1.4 | Mục tiêu và phạm vi thực hiện |
| 2.1.2 | Tổng quan chữ ký số, Hình 2.1 (quy trình ký và xác minh) |
| 2.1.3 b) Bước 3 | Xác minh chữ ký và chứng minh tính đúng |
| 2.1.3 c) | So sánh ECDSA và RSA (Bảng 2.2) |
| 2.4 (Bảng 2.6) + 2.4.1 | Bảng công nghệ; Python và thư viện `ecdsa` (lớp `SigningKey`, `VerifyingKey`, `SECP256k1`). Người 1 rà phần `SigningKey` |
| 3.1.3 a) | Sơ đồ tuần tự luồng tạo, ký, xác minh giao dịch (Hình 3.3). Người 1 rà phần ký; Người 3, 4 rà phần Mempool và phát tán |
| 3.3.1 (phần xác minh) | Phương thức tĩnh `verify()` |
| 3.3.2 (phần kiểm tra) | `is_valid()` |
| 3.4.3 | Kịch bản 2 – Tấn công giả mạo giao dịch |
| 3.4 (tổng hợp) | Bảng 3.4 tổng hợp kịch bản và kết quả 19/19 test |
| 4.1 | Giá trị và kết quả đạt được (lý thuyết + sản phẩm) |

**Việc tổng hợp (kiêm):**
- ghép file của cả nhóm; định dạng bìa, mục lục, danh mục hình/bảng;
- đánh số Hình/Bảng thống nhất;
- gom tài liệu tham khảo từ 3 người còn lại về chuẩn IEEE và kiểm tra mọi trích dẫn [n];
- giữ `README.md`, `HOW-TO-PLAY.md` khớp với code.

### Code phụ trách
- `core/wallet.py`: phương thức tĩnh **`verify()`**.
- `core/transaction.py`: **`is_valid()`** (chặn NaN/vô cực, người nhận rỗng, thiếu chữ ký; dòng cuối gọi `Wallet.verify()` trên mã băm tính lại).
- `core/blockchain.py`:
  - lớp kiểm tra chữ ký đầu tiên trong `try_add_transaction()`;
  - vòng xác minh chữ ký từng giao dịch trong `validate_chain()`.

  Phần còn lại của hai hàm này do Người 3 phụ trách.
- `network/node.py`: route `/transactions/receive` (dựng lại `Transaction` từ JSON, trả 400 kèm lý do và không phát tán).
- Giao diện: các nút **"2a. Sửa số tiền +1"**, **"2b. Sửa 1 ký tự người nhận"**, **"Khôi phục bản gốc"**, **"3. Gửi tới node để xác minh"** trong `app.js`.
- Test: `test_tampered_amount_is_rejected`, `test_rejection_reasons`, `test_tampered_signed_transaction_is_rejected`, `test_chain_validation_and_persistence`.

### Demo phụ trách
- **Dẫn dắt buổi demo** theo thứ tự ở mục 6.
- **Kịch bản 2 – Giả mạo bị phát hiện** (nối tiếp sau khi Người 1 đã bấm "1. Ký giao dịch"):
  1. Sửa số tiền +1, gửi đi: nhận HTTP 400 "Chữ ký ECDSA không hợp lệ".
  2. Sửa 1 ký tự người nhận, gửi đi: nhận HTTP 400.
  3. Khôi phục bản gốc, gửi đi: nhận HTTP 201.
  4. Gửi lại lần nữa: bị từ chối "bị phát lại".

  Vừa làm vừa giải thích trên bảng: z' ≠ z nên u₁·G + u₂·Q ≠ k·G.
- **Kết thúc:** chạy `python -m unittest discover -s tests -v` để cho thấy 19/19 đạt.

### Câu hỏi vấn đáp cần chuẩn bị
| Câu hỏi | Ý trả lời |
| --- | --- |
| Xác minh mà không cần Private Key bằng cách nào? | Dùng Q = d·G; chứng minh u₁·G + u₂·Q = s⁻¹(z + r·d)·G = k·G, nên hoành độ bằng r |
| Sửa 1 ký tự thì vì sao xác minh thất bại? | Mã băm đổi hoàn toàn (tuyết lở), z' ≠ z, điểm tính ra khác k·G nên x₁ ≠ r |
| Kẻ gian sửa cả `sender` thành ví mình thì sao? | `sender` chính là Public Key dùng để xác minh; chữ ký cũ không khớp với khóa mới, và kẻ gian không có Private Key của chủ ví để ký lại |
| "Chống chối bỏ" nghĩa là gì trong hệ thống? | Chỉ người có d mới tạo được chữ ký hợp lệ cho `sender`, nên người gửi không thể phủ nhận giao dịch đã ký |
| Giao dịch giả mạo bị chặn ở đâu trong code? | `/transactions/receive` → `try_add_transaction()` → `is_valid()` → `Wallet.verify()` trả `False`; trả 400 và không phát tán |
| Node có tin chữ ký do peer khác đã kiểm tra không? | Không. Mỗi node tự xác minh; khi đồng bộ còn xác minh lại toàn bộ chữ ký từ Genesis (`validate_chain`) |
| Public Key gửi qua mạng bị hỏng hoặc không nằm trên đường cong? | `VerifyingKey.from_string()` báo lỗi; `verify()` bắt lỗi và trả `False`, node không bị sập |
| Vì sao `verify()` là phương thức tĩnh? | Xác minh không cần ví hay khóa bí mật, chỉ cần Public Key, mã băm và chữ ký; ai cũng gọi được |
| Vì sao chọn ECDSA thay vì RSA? | Chữ ký và khóa nhỏ hơn khoảng 6 lần ở cùng mức an toàn 128 bit; sổ cái lưu mọi chữ ký nên kích thước rất quan trọng. RSA xác minh nhanh hơn, nhưng 1,27 ms/chữ ký vẫn đủ để đồng bộ |

---

## 4. Người 3 – Chuỗi khối, Giao dịch & Sổ cái

**Vai trò trong chủ đề:** biến các giao dịch đã ký thành một sổ cái bất biến, chống chi tiêu kép và phát hành tiền đúng quy tắc.

### Kiến thức cần nắm
- **Cấu trúc giao dịch** (bảng 2.3) và vai trò của `SYSTEM` (giao dịch thưởng).
- **Mempool:** vùng chờ trong bộ nhớ; bị dọn khi có khối mới; giao dịch trong khối bị bỏ (fork) được trả lại Mempool.
- **Chống phát lại:** hai lớp, gồm trùng mã băm và **nonce tuần tự** (nonce = số giao dịch đã xác nhận + số đang chờ của ví).
- **Cấu trúc khối:** index, transactions, previous_hash, timestamp, nonce, hash.
  Genesis cố định (`timestamp = 0.0`) để mọi node tự sinh ra cùng một khối khởi thủy. Đây là lỗi của code mẫu mà nhóm đã sửa.
- **Tính bất biến:** sửa một khối cũ thì hash đổi, previous_hash của khối sau không còn khớp; muốn che giấu phải đào lại PoW toàn bộ phía sau. Ngoài ra chữ ký của giao dịch bị sửa cũng sai.
- **Account-based và UTXO:** balance(A) = Σ nhận − Σ gửi; số dư không lưu ở đâu mà luôn tính lại từ chuỗi.
- **Chống chi tiêu kép** ở hai thời điểm: khi vào Mempool (số dư khả dụng = số dư − các khoản đang chờ) và khi xác thực chuỗi.
- **Proof of Work:** kỳ vọng 16^d lần thử; tìm thì khó, kiểm tra thì dễ (bảng 2.5).
  **Coinbase:** đúng 1 giao dịch ở đầu khối, đúng 50 coin; `SYSTEM` không được nhận từ bên ngoài.
- **Lưu trữ JSON** (mục 2.4.3): ưu điểm phi tập trung, minh bạch; nhược điểm phải ghi lại toàn bộ chuỗi mỗi lần.

### Phần báo cáo phụ trách
| Mục | Nội dung |
| --- | --- |
| 1.3.2 | Loại bỏ CSDL tập trung (số dư tính từ chuỗi) |
| 2.2 (2.2.1 → 2.2.3) | Giao dịch & Mempool, khối & liên kết chuỗi, Account-based; Bảng 2.3, Hình 2.2 |
| 2.3.2 | Proof of Work; Bảng 2.5 (số liệu đo độ khó 2–5) |
| 2.4.3 | Lưu trữ sổ cái cục bộ bằng tệp JSON |
| 3.2 | Cây thư mục dự án và trách nhiệm từng tệp |
| 3.3.3 | Giải thích `block.py`, `blockchain.py` |
| 3.4.4 | Kịch bản 3 – Chi vượt số dư và chi tiêu kép |
| 4.2.2, 4.3.1 | Hạn chế về lưu trữ và xác thực; hướng mở rộng Merkle Tree / SPV |

### Code phụ trách
- `core/block.py`: `calculate_hash()`, `mine_block()` (vòng lặp tăng nonce), `to_dict()` / `from_dict()`.
- `core/blockchain.py`:
  - `create_genesis_block()`, `get_balance()`, `get_next_nonce()`;
  - `try_add_transaction()`: các lớp trùng lặp → nonce → số dư (lớp chữ ký do Người 2 phụ trách);
  - `mine_pending_transactions()`;
  - **`validate_chain()` / `is_chain_valid()`** – liên kết, PoW, coinbase, nonce, số dư;
  - `try_add_block()` (accepted / stale / need_sync / rejected);
  - `replace_chain()`, `save_to_disk()` / `load_from_disk()`.
- Giao diện: mục **Chuyển tiền**, nút **Đào khối**, bảng **Mempool**, **Chuỗi khối** (`renderMempool`, `renderChain` trong `app.js`).
- Test: còn lại của `BlockchainTest` trong `tests/test_core.py` (nonce, nhận khối, fork, số dư, SYSTEM); `test_send_*` trong `tests/test_node.py`.

### Demo phụ trách: Kịch bản 3
1. Chuyển số tiền lớn hơn số dư: bị từ chối "Không đủ số dư (khả dụng X, cần Y)".
2. Chi tiêu kép: hai giao dịch liền nhau tiêu cùng một khoản; giao dịch thứ hai bị từ chối.
3. Mở một khối trong mục **Chuỗi khối** để chỉ previous_hash = hash khối trước, nonce PoW, giao dịch thưởng `SYSTEM` 50 coin.
4. Hỗ trợ Người 1 ở Kịch bản 1: giải thích vì sao gửi xong số dư chưa giảm (Mempool) và việc đào khối.

### Câu hỏi vấn đáp cần chuẩn bị
| Câu hỏi | Ý trả lời |
| --- | --- |
| Số dư lưu ở đâu? | Không lưu. Luôn tính lại bằng cách duyệt toàn bộ chuỗi (`get_balance`) |
| "Nonce" của giao dịch và "nonce" của khối khác nhau thế nào? | Nonce giao dịch là số thứ tự giao dịch của ví, dùng chống phát lại. Nonce khối là số tìm được khi đào PoW |
| Gửi tiền xong sao số dư chưa giảm? | Giao dịch còn ở Mempool, chưa vào khối. Số dư chỉ tính giao dịch đã xác nhận |
| Chặn chi tiêu kép thế nào? | Số dư khả dụng = số dư trên chuỗi − tổng các khoản đang chờ của ví; khi xác thực chuỗi còn duyệt tuần tự để không ai bị âm tiền |
| Một node gian lận tự đào khối chứa giao dịch chi vượt? | `validate_chain()` trên các node trung thực từ chối khối: "giao dịch chi vượt số dư" |
| Ai đó gửi giao dịch `SYSTEM` để "in tiền"? | `try_add_transaction` chặn ngay; `validate_chain` chỉ chấp nhận đúng 1 coinbase ở đầu khối, đúng mức thưởng |
| Sửa một giao dịch trong khối cũ thì sao? | Hash khối đổi, nên previous_hash của khối sau không khớp; phải đào lại toàn bộ phía sau; chữ ký giao dịch đó cũng sai |
| Độ khó 3 nghĩa là gì, đào mất bao lâu? | Hash bắt đầu bằng "000"; kỳ vọng 4096 lần thử, khoảng 0,02 giây |

---

## 5. Người 4 – Mạng ngang hàng (P2P) & Đồng bộ

**Vai trò trong chủ đề:** làm cho hệ thống thực sự phi tập trung – các node tự tìm nhau, tự lan truyền dữ liệu và tự phục hồi khi ngoại tuyến.

### Kiến thức cần nắm
- **Client–Server và P2P Full Node** (bảng 2.4); Full Node khác Light Node.
- **Kiến trúc tổng thể:** 3 node bình đẳng, 5001 làm seed; mỗi node gồm Flask API + Web UI, Blockchain + Mempool, `wallet_<port>.json`, `ledger_<port>.json` (Hình 3.1).
- **Peer Discovery:** node đăng ký với seed qua `/nodes/register` và nhận về danh sách peer. Ví dụ: node 5003 chỉ biết 5001 nhưng tự học được 5002.
- **Gossip:**
  - node chỉ chuyển tiếp dữ liệu **sau khi tự xác minh**;
  - header `X-Node-Url` để không gửi ngược về nơi vừa gửi tới;
  - giao dịch trùng trả `409` và không chuyển tiếp nữa, nên không lặp vô hạn.
- **Hàng đợi riêng cho từng peer:** giữ đúng thứ tự (nonce 0 đến trước nonce 1), và peer offline không làm chậm peer khác.
  Đây là lỗi nhóm đã gặp khi chạy thử: chuỗi bị tách đôi (fork) vì một hàng đợi chung bị kẹt bởi node 5003 đang offline.
- **Longest Chain Rule và đồng bộ:** đồng bộ diễn ra ở 3 thời điểm: khi khởi động, khi nhận một khối không nối được, và khi bấm thủ công.
  Node không tin peer: xác thực lại toàn bộ từ Genesis rồi mới ghi đè.
- **Fork:** hai node đào cùng lúc thì có hai nhánh dài bằng nhau; khối kế tiếp sẽ phân định nhánh thắng; giao dịch thuộc nhánh thua được trả lại Mempool.
- **Đa luồng:** Flask chạy `threaded`, nên dùng `threading.RLock`; timeout 2–3 giây khi gọi peer.
- **Mã trạng thái HTTP:** 200/201 thành công, 202 cần đồng bộ, 400 không hợp lệ, 409 trùng do gossip.
- **Flask và `requests`** (mục 2.4.2).

### Phần báo cáo phụ trách
| Mục | Nội dung |
| --- | --- |
| 1.3.3 | Bài toán đồng bộ khi node ngoại tuyến |
| 2.3.1, 2.3.3 | Mô hình Full Node, peer discovery, gossip (Bảng 2.4); Longest Chain Rule + lưu đồ đồng bộ (Hình 2.3, mã giả) |
| 2.4.2 | Framework Flask và thư viện `requests` |
| 3.1.1 | Sơ đồ kiến trúc mạng 3 Full Node (Hình 3.1) |
| 3.1.3 b) | Sơ đồ tuần tự luồng đồng bộ khi node 5003 khởi động lại (Hình 3.4) |
| 3.1.4 | Bảng endpoint (Bảng 3.1) và ý nghĩa mã trạng thái |
| 3.3.4 | Giải thích `node.py`: phát tán, `sync_chain()` |
| 3.4.1 | Môi trường thử nghiệm, lệnh khởi chạy 3 node, Hình 3.5 (giao diện) |
| 3.4.5 | Kịch bản 4 – Tắt và bật lại node (Bảng 3.3, Hình 3.6) |
| 4.2.1, 4.3.3 | Hạn chế tầng mạng và bảo mật; hướng mở rộng WebSocket, LevelDB, tổng khối lượng công việc, PoS |

### Code phụ trách
- `network/node.py`:
  - `create_node_app()` là "lớp" `P2PNode` trong UML;
  - `add_peers()` / `peer_list()`;
  - `peer_worker()` / `outbox_for()` / `broadcast()` (gossip);
  - **`sync_chain()`**, `register_with_peers()`;
  - các route `/transactions/send`, `/mine`, `/blocks/receive`, `/nodes/*`, `/status`, `/chain`;
  - phần ghi log (`log()`, `_MemoryLogHandler`, `/logs`).
- `run_node.py`: tham số `--port`, `--peers`, `--difficulty`; sửa lỗi in tiếng Việt trên console Windows.
- Giao diện: **Mạng ngang hàng** (`renderPeers`, Thêm peer), **Đồng bộ ngay**, **Nhật ký node** (`renderLogs`), cơ chế tự làm mới (`refresh`, `refreshPeers`).
- Test: `test_receive_block_from_other_node`, `test_register_peers`, `test_index_serves_html`.

### Demo phụ trách
- **Mở đầu:** khởi chạy 3 node trên 3 terminal; chỉ dòng "Biết thêm peer … qua …" trong log của 5003 (peer discovery).
- **Kịch bản 4:**
  1. Ctrl+C tắt node 5003; trên giao diện 5001, peer 5003 chuyển sang chấm đỏ.
  2. Chuyển tiền và đào 2 khối trên 5001/5002.
  3. Mở `storage/ledger_5003.json` để thấy nó ngắn hơn `ledger_5001.json`.
  4. Bật lại 5003: nhật ký ghi "Đồng bộ: thay chuỗi cục bộ 3 → 5 khối…"; độ dài chuỗi và hash khối cuối của 3 node trùng nhau.

### Câu hỏi vấn đáp cần chuẩn bị
| Câu hỏi | Ý trả lời |
| --- | --- |
| Các node biết nhau bằng cách nào? | Seed peer qua `--peers`; `/nodes/register` trả về danh sách peer đã biết; lặp lại với các peer mới học được |
| Gossip có bị lặp vô hạn không? | Không. Node chỉ chuyển tiếp dữ liệu mới và hợp lệ; dữ liệu trùng bị trả 409 và dừng; `X-Node-Url` loại trừ nơi gửi |
| Peer gian lận gửi chuỗi dài hơn nhưng có giao dịch giả? | `validate_chain()` phát hiện, ghi log lý do, giữ nguyên chuỗi cũ |
| Hai node đào cùng lúc thì sao? | Fork: hai nhánh dài bằng nhau, mỗi node giữ nhánh của mình; khối kế tiếp làm một nhánh dài hơn, các node đồng bộ theo; giao dịch không bị mất |
| Vì sao mỗi peer có hàng đợi riêng? | Giữ thứ tự nonce; peer offline (mất khoảng 2 giây mỗi lần thử trên Windows) không chặn peer khác. Nhóm gặp fork thật khi còn dùng một hàng đợi chung |
| Vì sao cần `RLock`? | Flask xử lý nhiều request song song; tránh hai request cùng sửa chuỗi/Mempool |
| Chạy trên nhiều máy được không? | Hiện **chưa**: node chỉ lắng nghe ở `127.0.0.1`. Muốn chạy LAN phải mở `0.0.0.0`, quảng bá IP LAN và chặn API điều khiển ví từ máy khác |
| "Dài nhất" tính theo gì? | Theo số khối. Bitcoin thật tính theo tổng khối lượng công việc. Đây là hạn chế (mục 4.2.1) |

---

## 6. Kịch bản buổi demo (Người 2 dẫn dắt)

| Thứ tự | Người | Nội dung | Thời lượng gợi ý |
| --- | --- | --- | --- |
| 1 | Người 2 | Giới thiệu đề tài, mục tiêu, phân công | 1–2 phút |
| 2 | Người 4 | Khởi chạy 3 node, giới thiệu giao diện, peer discovery | 2 phút |
| 3 | Người 1 | Kịch bản 1: tạo ví (khóa bí mật / khóa công khai), ký và gửi giao dịch hợp lệ; Người 3 giải thích Mempool và đào khối | 3 phút |
| 4 | Người 1 → Người 2 | Kịch bản 2: Người 1 ký giao dịch và giải thích (r, s); Người 2 sửa dữ liệu, gửi đi, giải thích vì sao xác minh thất bại | 3–4 phút |
| 5 | Người 3 | Kịch bản 3: vượt số dư, chi tiêu kép, xem cấu trúc khối | 2 phút |
| 6 | Người 4 | Kịch bản 4: tắt node, giao dịch tiếp, bật lại và tự đồng bộ | 3 phút |
| 7 | Người 2 | Chạy 19 unit test; tóm tắt kết quả, hạn chế, hướng mở rộng | 2 phút |

---

## 7. Phối hợp & mốc công việc

**Rà chéo theo cặp**, mỗi người đọc và góp ý phần báo cáo của người cùng cặp:
- **Người 1 ↔ Người 2:** ký ↔ xác minh. Phải dùng chung ký hiệu (d, Q, G, n, k, z, r, s) và chung cách viết công thức.
  Mục 2.1.3 b) do hai người viết nối tiếp (Bước 1–2 rồi Bước 3), nên đọc liền mạch phải như một người viết.
- **Người 3 ↔ Người 4:** chuỗi khối ↔ mạng. Hai sơ đồ tuần tự (Hình 3.3 và 3.4) phải khớp với code.

Người 2 đọc toàn bộ khi ghép file.

| Giai đoạn | Việc của từng người | Đầu ra |
| --- | --- | --- |
| 1. Tự học | Đọc phần báo cáo + code của mình; chạy test và `HOW-TO-PLAY.md` | Mỗi người tự giải thích được phần của mình |
| 2. Viết / hoàn thiện báo cáo | Viết hoặc chỉnh các mục được giao cho khớp với code hiện tại; chụp lại ảnh cho kịch bản của mình; gửi danh sách tài liệu tham khảo đã dùng | File mục báo cáo + ảnh + tài liệu tham khảo gửi Người 2 |
| 3. Rà chéo & ghép | Rà chéo theo cặp; Người 2 ghép file, thống nhất định dạng, đánh số hình/bảng, mục lục | Bản báo cáo hoàn chỉnh |
| 4. Tổng duyệt demo | Chạy demo đúng thứ tự ở mục 6; hỏi chéo nhau các câu trong bảng vấn đáp, kể cả phần "Kiến thức chung" | Mỗi người trả lời trôi chảy phần của mình |

**Quy ước khi sửa code:** ai sửa module nào thì chạy lại toàn bộ test (19/19) trước khi đẩy lên GitHub.
Nếu thay đổi làm lệch nội dung báo cáo (tên hàm, thông báo lỗi, số liệu), phải báo người phụ trách mục báo cáo đó.
