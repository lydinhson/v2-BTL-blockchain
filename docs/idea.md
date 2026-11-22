Việc nâng cấp **Đề K (Tạo và xác minh chữ ký số)** thành một **Ví điện tử chạy trên mô hình Full Node phi tập trung** là hướng đi rất sáng giá. Thay vì chỉ làm một công cụ mã hóa đơn lẻ, bạn đang đặt chữ ký số vào đúng bối cảnh sống còn của nó trong Blockchain: **bảo vệ tài sản và đảm bảo sự tin cậy trong mạng ngang hàng không có máy chủ trung tâm**.

Dưới đây là phân tích chi tiết về bản chất bài toán, hệ thống kiến thức cốt lõi, công nghệ đề xuất và cách ánh xạ vào báo cáo 30 trang.

---

## 1. Phân tích bài toán & Kiến trúc hệ thống

Hệ thống của bạn cần giải quyết trọn vẹn 3 lớp bài toán liên kết chặt chẽ với nhau:

1. **Lớp cốt lõi — Chữ ký số (Trọng tâm Đề K):**
* Mỗi ví sở hữu một cặp khóa: **Khóa bí mật (Private Key)** để ký giao dịch và **Khóa công khai (Public Key)** để tạo địa chỉ ví và cho phép toàn mạng xác minh.
* Mọi giao dịch chuyển tiền đều phải được ký trước khi phát lên mạng. Nếu kẻ gian sửa dù chỉ 1 ký tự (số tiền hoặc người nhận), chữ ký sẽ lập tức mất hiệu lực khi các node khác kiểm tra.


2. **Lớp phi tập trung — Mô hình Full Node (Không dùng CSDL tập trung):**
* Khi khởi chạy phần mềm trên một cổng (port) riêng biệt (ví dụ `5001`, `5002`, `5003`), tiến trình đó đóng vai trò là một **Full Node độc lập**.
* Mỗi node tự lưu trữ bản sao toàn bộ sổ cái (Blockchain) dưới dạng tệp cục bộ trên máy (JSON hoặc cơ sở dữ liệu nhúng) thay vì gọi về một máy chủ SQL/MongoDB dùng chung.


3. **Lớp đồng bộ hóa — Xử lý Node ngoại tuyến (Offline Node Recovery):**
* Khi Node C tắt đi trong lúc Node A và Node B vẫn tiếp tục giao dịch và đào khối (mining), sổ cái của Node C sẽ bị cũ.
* Khi Node C bật lại, nó tự động kết nối tới các node lân cận đang hoạt động, tải về chuỗi khối mới nhất, **chạy thuật toán xác thực toàn bộ chuỗi** (kiểm tra liên kết băm, bằng chứng công việc và chữ ký số của từng giao dịch bên trong), rồi áp dụng **Quy tắc chuỗi dài nhất (Longest Chain Rule)** để cập nhật lại sổ cái của mình.



---

## 2. Hệ thống kiến thức cần sử dụng

Để triển khai phần mềm chuẩn xác và viết tốt phần *Cơ sở lý thuyết*, bạn cần nắm vững 4 nhóm kiến thức sau:

### Nhóm 1: Mật mã học ứng dụng (Trọng tâm Đề K)

* **Mật mã đường cong Elliptic — ECDSA (khuyên dùng `secp256k1` hoặc `Ed25519`):** Đây là tiêu chuẩn của Bitcoin và Ethereum. So với RSA, ECDSA tạo ra khóa và chữ ký ngắn hơn nhiều nhưng độ an toàn tương đương, rất phù hợp làm địa chỉ ví.
* **Hàm băm mật mã (SHA-256):** Dùng để băm nội dung giao dịch trước khi ký, băm dữ liệu khối tạo `block_hash`, và liên kết các khối lại với nhau.
* **Quy trình Ký và Xác minh:**
* *Tạo chữ ký:* $h = \text{SHA256}(\text{TxData})$, sau đó tạo chữ ký $S = \text{Sign}(h, K_{\text{private}})$.
* *Xác minh:* Node nhận giao dịch tự tính lại $h' = \text{SHA256}(\text{TxData})$, sau đó kiểm tra $\text{Verify}(h', S, K_{\text{public}}) \rightarrow \text{True/False}$.



### Nhóm 2: Cấu trúc dữ liệu Blockchain & Mô hình Ví

* **Cấu trúc Giao dịch (Transaction):** Gồm `sender_public_key`, `recipient_address`, `amount`, `timestamp`, `nonce` (số thứ tự giao dịch để chống tấn công phát lại — *Replay Attack*), và `signature`.
* **Cấu trúc Khối (Block):** Gồm `index`, `timestamp`, `transactions` (danh sách giao dịch đã xác minh chữ ký), `previous_hash`, `nonce` (dùng cho đồng thuận), và `hash`.
* **Mô hình quản lý số dư:** Nên chọn **Account-based Model** (giống Ethereum — duyệt sổ cái tính tổng thu trừ tổng chi của một địa chỉ) thay vì UTXO (giống Bitcoin) để giảm độ phức tạp khi lập trình ví và dễ kiểm tra điều kiện chống chi tiêu kép (*Double Spending*).

### Nhóm 3: Mạng ngang hàng (P2P) & Giao thức truyền tin

* **Khám phá nút mạng (Peer Discovery):** Thiết lập cơ chế đăng ký node (nhập địa chỉ `IP:Port` của một node đang chạy hoặc dùng danh sách Seed Node mặc định) để các node biết nhau.
* **Lan truyền tin (Broadcasting / Gossip):** Khi một ví tạo giao dịch mới, giao dịch được đẩy vào vùng chờ (**Mempool**) và phát tán sang các peer kết nối. Khi một khối mới được đào, khối đó cũng được phát tán tương tự.

### Nhóm 4: Thuật toán Đồng thuận & Đồng bộ chuỗi

* **Proof of Work (PoW) mức nhẹ:** Đặt độ khó thấp (ví dụ `hash` của khối bắt đầu bằng 3 hoặc 4 chữ số `0`) để máy tính cá nhân đào khối trong 1–3 giây khi demo.
* **Thuật toán Đồng bộ & Xác thực chuỗi (`resolve_conflicts` / `is_chain_valid`):**
1. Gửi yêu cầu lấy độ dài và toàn bộ chuỗi từ các peer đang hoạt động.
2. Tìm chuỗi dài hơn chuỗi cục bộ hiện tại.
3. Kiểm tra tính hợp lệ của chuỗi ứng viên từ khối khởi thủy (Genesis Block) đến khối cuối: khớp `previous_hash`, thỏa mãn độ khó PoW, **xác minh chữ ký số của mọi giao dịch**, và đảm bảo không có giao dịch chi tiêu vượt số dư.
4. Nếu toàn bộ hợp lệ, ghi đè chuỗi cục bộ và lưu xuống tệp tin.



---

## 3. Lựa chọn Công nghệ (Tech Stack)

Với phạm vi bài tập lớn cần chạy thử nhiều node cùng lúc trên một máy (hoặc mạng LAN) và trực quan hóa chữ ký số cho giảng viên xem, **Python** hoặc **Node.js (TypeScript/JavaScript)** là hai lựa chọn tối ưu nhất.

| Tiêu chí | Phương án 1: Python (Khuyên dùng) | Phương án 2: Node.js / TypeScript | Phương án 3: Java / C# |
| --- | --- | --- | --- |
| **Thư viện chữ ký số** | `ecdsa` hoặc `cryptography` (rất ngắn gọn, dễ đọc mã nguồn trong báo cáo) | `elliptic` hoặc `crypto` (tích hợp sẵn trong Node.js) | `BouncyCastle` (chuẩn công nghiệp nhưng cấu hình dài) |
| **Giao tiếp P2P** | `FastAPI` / `Flask` (HTTP REST) hoặc `websockets` | `ws` (WebSocket thời gian thực rất mượt) + `Express` | `Spring Boot` / `ASP.NET` (khá nặng khi chạy 3–4 node cùng lúc) |
| **Lưu trữ cục bộ** | Tệp JSON (`chain_5001.json`) hoặc `SQLite` nhúng | Tệp JSON hoặc `LevelDB` (giống Bitcoin Core/Ethereum) | Tệp JSON hoặc `SQLite` |
| **Giao diện Ví (UI)** | Web UI (HTML/JS kết nối API của node) hoặc `Streamlit` | Web UI (React / HTML+Tailwind) tích hợp trực tiếp | WinForms / WPF / JavaFX |
| **Ưu điểm cho Đề K** | Code toán học mật mã và thuật toán kiểm tra chuỗi cực kỳ sáng sủa, dễ giải thích khi bảo vệ | Xử lý bất đồng bộ P2P (WebSocket) tự nhiên, giao diện đẹp | Kiểu dữ liệu chặt chẽ, phù hợp nếu bạn đã rất quen hệ sinh thái này |

> **Lưu ý về lưu trữ cục bộ:** Việc lưu sổ cái ra tệp **JSON riêng cho từng node** (ví dụ `node_5001_ledger.json`, `node_5002_ledger.json`) vừa đáp ứng đúng yêu cầu "không dùng CSDL tập trung", vừa giúp bạn dễ dàng mở trực tiếp tệp lên để minh chứng với giảng viên rằng dữ liệu của Node 3 đã thực sự được đồng bộ sau khi bật lại.

---

## 4. Định hướng cấu trúc Báo cáo (~30 trang)

Để báo cáo đạt độ dài chuẩn khoảng **28–32 trang** (không loãng lý thuyết, có chiều sâu kỹ thuật), bạn nên phân bổ dung lượng theo cấu trúc sau:

* **Chương 1: Đặt vấn đề (~3–4 trang)**
* Bối cảnh của hệ thống thanh toán truyền thống (phụ thuộc bên thứ ba) và nhu cầu về sổ cái phân tán.
* Phát biểu bài toán Đề K: Tại sao chữ ký số là nền tảng xác thực trong ví phi tập trung?
* Mục tiêu và phạm vi: Xây dựng mô phỏng ví Full Node P2P, giải quyết bài toán giả mạo giao dịch và đồng bộ hóa khi node ngắt kết nối.


* **Chương 2: Cơ sở lý thuyết và Công nghệ (~10–12 trang)**
* Lý thuyết Mật mã khóa công khai, Hàm băm SHA-256 và **thuật toán chữ ký số ECDSA** (trình bày rõ công thức tạo khóa, ký và xác minh — đây là phần ăn điểm của Đề K).
* Kiến trúc Blockchain, cấu trúc Block/Transaction, cơ chế Mempool và PoW.
* Mô hình mạng P2P, thuật toán đồng bộ chuỗi và Quy tắc chuỗi dài nhất.
* Giới thiệu ngắn gọn công nghệ, thư viện đã chọn và lý do lựa chọn.


* **Chương 3: Thiết kế và Triển khai hệ thống (~12–14 trang)**
* Thiết kế kiến trúc tổng thể (sơ đồ luồng giao dịch, sơ đồ luồng đồng bộ node).
* Cấu trúc thư mục mã nguồn và các lớp đối tượng chính (`Wallet`, `Transaction`, `Block`, `Blockchain`, `P2PNode`).
* Trích dẫn và giải thích các đoạn mã cốt lõi: hàm tạo cặp khóa, hàm ký số, hàm xác minh chữ ký, hàm `is_chain_valid()`, và hàm đồng bộ khi khởi động lại node.
* **Kết quả & Kịch bản kiểm thử (rất quan trọng):** Chụp ảnh giao diện kèm log chứng minh 4 kịch bản:
1. Tạo ví và thực hiện giao dịch hợp lệ.
2. Kịch bản tấn công: Cố tình sửa số tiền/người nhận sau khi ký $\rightarrow$ hệ thống từ chối do sai chữ ký số.
3. Kịch bản chi tiêu vượt số dư $\rightarrow$ hệ thống từ chối.
4. Kịch bản mất kết nối: Tắt Node C, thực hiện giao dịch trên Node A & B, sau đó bật lại Node C $\rightarrow$ Node C tự động tải, kiểm tra và đồng bộ lại toàn bộ chuỗi.




* **Chương 4: Kết luận (~2–3 trang)**
* Giá trị thu được và đánh giá mức độ hoàn thành mục tiêu Đề K.
* Hạn chế hiện tại (chưa xử lý xuyên NAT trên Internet thật, chưa có Merkle Tree tối ưu cho Light Node, chưa phòng chống tấn công Sybil/51% ở quy mô lớn).
* Hướng mở rộng (tích hợp Merkle Proof, ví HD Wallet chuẩn BIP-39 với 12 từ khóa khôi phục, hoặc chuyển sang cơ chế đồng thuận Proof of Stake).

