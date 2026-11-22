## Phân bổ dung lượng dự kiến (~30 trang nội dung chính)

Để báo cáo có độ sâu kỹ thuật, không bị loãng lý thuyết và dừng đẹp trong khoảng **30–33 trang** (tính cả trang bìa, mục lục và tài liệu tham khảo), dung lượng các chương nên được phân bổ như sau:

| Phần / Chương | Số trang dự kiến | Tỷ trọng | Trọng tâm nội dung |
| --- | --- | --- | --- |
| **Phần mở đầu** *(Bìa, Mục lục, Danh mục hình/bảng, Từ viết tắt)* | 2 – 3 trang | — | Trình bày chuẩn quy cách học thuật |
| **Chương 1: Đặt vấn đề** | 3 – 4 trang | ~12% | Bối cảnh, bài toán Đề K, lý do chọn mô hình Full Node P2P |
| **Chương 2: Cơ sở lý thuyết và Công nghệ** | 10 – 11 trang | ~35% | Toán học ECDSA (`secp256k1`), SHA-256, Blockchain, Longest Chain Rule, Tech Stack |
| **Chương 3: Thiết kế và Triển khai hệ thống** | 12 – 13 trang | ~42% | Sơ đồ UML, cấu trúc code Python, giải thích hàm lõi và 4 kịch bản kiểm thử |
| **Chương 4: Kết luận** | 2 – 3 trang | ~11% | Giá trị thu được, hạn chế kỹ thuật và hướng mở rộng |
| **Tài liệu tham khảo** | 1 trang | — | Trích dẫn chuẩn IEEE (Bitcoin Whitepaper, SEC 2 `secp256k1`, tài liệu thư viện) |

---

## Đề cương chi tiết đến mục cấp 3

### CHƯƠNG 1: ĐẶT VẤN ĐỀ (~3 – 4 trang)

* **1.1. Bối cảnh và động lực nghiên cứu**
* **1.1.1. Hạn chế của mô hình lưu trữ và thanh toán tập trung:** Điểm lỗi đơn (Single Point of Failure), phụ thuộc vào bên trung gian xác thực và rủi ro sửa đổi dữ liệu trái phép.
* **1.1.2. Vai trò của Chuỗi khối và Sổ cái phân tán (DLT):** Cách công nghệ Blockchain loại bỏ trung gian thông qua mật mã học và cơ chế đồng thuận ngang hàng.


* **1.2. Phát biểu bài toán (Đề K)**
* **1.2.1. Yêu cầu cốt lõi về tạo và xác minh chữ ký số:** Xây dựng cơ chế sinh cặp khóa, ký lên dữ liệu giao dịch và cho phép bất kỳ ai xác minh mà không cần biết khóa bí mật.
* **1.2.2. Mở rộng bài toán sang mô hình Ví điện tử Full Node phi tập trung:** Đặt chữ ký số vào ngữ cảnh thực tế của một mạng lưới ví điện tử, nơi mỗi máy chạy phần mềm là một Full Node độc lập.


* **1.3. Các vấn đề kỹ thuật liên quan cần giải quyết**
* **1.3.1. Đảm bảo tính toàn vẹn, xác thực và chống chối bỏ giao dịch:** Ngăn chặn kẻ gian sửa đổi số tiền hoặc địa chỉ người nhận sau khi giao dịch đã được phát đi.
* **1.3.2. Loại bỏ cơ sở dữ liệu tập trung:** Thiết kế cơ chế lưu trữ sổ cái cục bộ độc lập trên từng máy.
* **1.3.3. Bài toán đồng bộ hóa khi Full Node ngoại tuyến:** Giải quyết tình huống một node bị tắt trong khi mạng vẫn tiếp tục giao dịch và đào khối, sau đó node bật lại cần tự kiểm tra và cập nhật đúng trạng thái sổ cái.


* **1.4. Mục tiêu, phạm vi thực hiện và bố cục báo cáo**

---

### CHƯƠNG 2: CƠ SỞ LÝ THUYẾT VÀ CÔNG NGHỆ SỬ DỤNG (~10 – 11 trang)

* **2.1. Mật mã học ứng dụng và Chữ ký số (Trọng tâm Đề K)**
* **2.1.1. Hàm băm mật mã SHA-256:** Định nghĩa, tính chất một chiều, tính kháng va chạm và hiệu ứng tuyết lở (Avalanche Effect) khi áp dụng lên giao dịch và khối.
* **2.1.2. Tổng quan về Chữ ký số (Digital Signature):** Mô hình khóa bất đối xứng, quy trình tạo chữ ký và xác minh chữ ký.
* **2.1.3. Thuật toán chữ ký số đường cong Elliptic (ECDSA):**
* Cơ sở toán học đường cong Elliptic trên trường hữu hạn và tham số chuẩn `secp256k1` ($y^2 = x^3 + 7 \pmod p$).
* Quy trình toán học 3 bước: Sinh cặp khóa $(d_A, Q_A)$, Tạo chữ ký $(r, s)$ từ mã băm giao dịch, và Xác minh chữ ký bằng khóa công khai.
* So sánh nhanh ECDSA và RSA về kích thước khóa, tốc độ và lý do chọn ECDSA cho ví điện tử.




* **2.2. Kiến trúc Chuỗi khối và Mô hình Ví điện tử**
* **2.2.1. Cấu trúc Giao dịch (Transaction) và vùng chờ Mempool:** Các trường dữ liệu cốt lõi (`sender`, `recipient`, `amount`, `timestamp`, `nonce`, `signature`) và vai trò của `nonce` trong việc chống tấn công phát lại (Replay Attack).
* **2.2.2. Cấu trúc Khối (Block) và liên kết chuỗi:** Khối khởi thủy (Genesis Block), cơ chế liên kết bằng `previous_hash` đảm bảo tính bất biến.
* **2.2.3. Mô hình quản lý số dư Account-based:** Cách tính số dư từ lịch sử sổ cái và kiểm tra điều kiện chống chi tiêu kép (Double Spending).


* **2.3. Mạng ngang hàng (P2P), Đồng thuận và Thuật toán Đồng bộ**
* **2.3.1. Mô hình Full Node trong mạng P2P:** Khác biệt giữa Client-Server và P2P; cơ chế khám phá nút mạng (Peer) và lan truyền giao dịch/khối (Broadcasting).
* **2.3.2. Cơ chế đồng thuận Proof of Work (PoW):** Nguyên lý tìm giá trị `nonce` thỏa mãn độ khó mục tiêu (số lượng chữ số `0` ở đầu mã băm).
* **2.3.3. Thuật toán xác thực chuỗi và Quy tắc chuỗi dài nhất (Longest Chain Rule):** Trình bày lưu đồ/mã giả quá trình một Full Node khi bật lại sẽ hỏi chuỗi từ các node lân cận, kiểm tra lại từ khối Genesis (hash, PoW, chữ ký số từng giao dịch, số dư) và ghi đè sổ cái cục bộ.


* **2.4. Công nghệ và Thư viện lựa chọn**
* **2.4.1. Ngôn ngữ Python và thư viện mật mã `ecdsa`:** Lý do lựa chọn và các lớp sử dụng (`SigningKey`, `VerifyingKey`, `SECP256k1`).
* **2.4.2. Framework `Flask` và thư viện `requests`:** Xây dựng giao tiếp HTTP REST mô phỏng tầng mạng P2P giữa các Full Node.
* **2.4.3. Lưu trữ sổ cái cục bộ bằng tệp JSON:** Ưu điểm minh bạch, dễ kiểm chứng phi tập trung mà không cần hệ quản trị CSDL tập trung.



---

### CHƯƠNG 3: THIẾT KẾ VÀ TRIỂN KHAI HỆ THỐNG (~12 – 13 trang)

* **3.1. Thiết kế kiến trúc tổng thể**
* **3.1.1. Sơ đồ kiến trúc mạng Full Node P2P:** Minh họa 3 node chạy độc lập trên các cổng (`5001`, `5002`, `5003`) với các tệp sổ cái riêng biệt.
* **3.1.2. Sơ đồ lớp (UML Class Diagram):** Mối quan hệ giữa 5 lớp `Wallet`, `Transaction`, `Block`, `Blockchain`, `P2PNode`.
* **3.1.3. Sơ đồ tuần tự (Sequence Diagram):** Vẽ 2 luồng quan trọng nhất: (1) Luồng tạo, ký và xác minh giao dịch; (2) Luồng đồng bộ chuỗi khi Node C khởi động lại.
* **3.1.4. Thiết kế các Endpoint giao tiếp của Full Node:** Bảng mô tả các API (`/wallet`, `/chain`, `/transactions/send`, `/transactions/receive`, `/mine`, `/nodes/sync`).


* **3.2. Cấu trúc mã nguồn chương trình**
* **3.2.1. Cây thư mục dự án:** Mô tả bố cục `core/`, `network/`, `storage/` và tệp khởi chạy `run_node.py`.
* **3.2.2. Trách nhiệm của từng tệp mã nguồn:** Giải thích tính mô-đun hóa giúp tách biệt tầng mật mã với tầng mạng.


* **3.3. Triển khai các phần mã nguồn cốt lõi** *(Trích dẫn đoạn code tiêu biểu kèm giải thích từng khối lệnh)*
* **3.3.1. Mô-đun Ví và Chữ ký số ECDSA (`core/wallet.py`):** Giải thích hàm khởi tạo cặp khóa, hàm `sign()` và phương thức tĩnh `verify()`.
* **3.3.2. Mô-đun Giao dịch (`core/transaction.py`):** Giải thích cách tuần tự hóa JSON với `sort_keys=True` để băm SHA-256 nhất quán, hàm `sign_transaction()` và `is_valid()`.
* **3.3.3. Mô-đun Khối và Sổ cái (`core/block.py`, `core/blockchain.py`):** Giải thích hàm đào khối `mine_block()`, kiểm tra số dư `add_transaction()`, và đặc biệt là thuật toán xác thực toàn chuỗi `is_chain_valid()`.
* **3.3.4. Mô-đun Mạng P2P và Đồng bộ tự động (`network/node.py`):** Giải thích cơ chế phát tán giao dịch sang peer và hàm `sync_chain()` tự kích hoạt khi khởi động node.


* **3.4. Kết quả thực nghiệm và Kịch bản kiểm thử** *(Chụp ảnh màn hình Terminal, Postman/UI và nội dung tệp JSON làm minh chứng)*
* **3.4.1. Môi trường thử nghiệm và khởi chạy mạng 3 Full Node:** Lệnh chạy 3 tiến trình độc lập trên các cổng `5001`, `5002`, `5003`.
* **3.4.2. Kịch bản 1 — Giao dịch hợp lệ:** Tạo ví, đào khối thưởng tạo số dư ban đầu, ký giao dịch chuyển tiền trên Node 1 và kiểm chứng Node 2, Node 3 xác minh thành công.
* **3.4.3. Kịch bản 2 — Tấn công giả mạo giao dịch (Kiểm thử trọng tâm Đề K):** Thay đổi trường `amount` hoặc `recipient` của gói tin sau khi đã ký rồi gửi tới `/transactions/receive` $\rightarrow$ Hệ thống trả mã lỗi `400` và từ chối đưa vào Mempool.
* **3.4.4. Kịch bản 3 — Kiểm thử chi tiêu vượt số dư:** Thực hiện giao dịch có số tiền lớn hơn số dư hiện có $\rightarrow$ Hệ thống phát hiện và chặn lại.
* **3.4.5. Kịch bản 4 — Kiểm thử tắt và bật lại Full Node (Offline Recovery):** Tắt Node 3, thực hiện thêm giao dịch và đào 2 khối mới trên Node 1 & 2, đối chiếu độ dài `ledger_5001.json` với `ledger_5003.json`, sau đó bật lại Node 3 và chứng minh `ledger_5003.json` tự động đồng bộ khớp hoàn toàn.



---

### CHƯƠNG 4: KẾT LUẬN (~2 – 3 trang)

* **4.1. Giá trị và kết quả đạt được**
* **4.1.1. Về mặt lý thuyết:** Làm chủ nguyên lý mật mã đường cong Elliptic ECDSA, cấu trúc chuỗi khối và bài toán đồng bộ sổ cái phân tán.
* **4.1.2. Về mặt sản phẩm phần mềm:** Xây dựng thành công mô phỏng ví điện tử Full Node P2P chạy độc lập không cần CSDL tập trung, xác minh chữ ký chặt chẽ và tự phục hồi dữ liệu khi ngoại tuyến.


* **4.2. Những hạn chế còn tồn tại**
* **4.2.1. Về tầng mạng và bảo mật:** Giao tiếp HTTP chạy thử trong mạng nội bộ (`localhost`/LAN), chưa xử lý xuyên NAT trên Internet thật và chưa tích hợp cơ chế chống tấn công Sybil hoặc tấn công 51%.
* **4.2.2. Về hiệu năng lưu trữ và xác thực:** Lưu toàn bộ chuỗi vào tệp JSON sẽ giảm tốc độ đọc/ghi khi số lượng khối tăng lớn; việc xác thực lại từ khối Genesis tốn thời gian với chuỗi rất dài.
* **4.2.3. Về trải nghiệm người dùng:** Chưa có mã hóa tệp khóa bí mật bằng mật khẩu cục bộ (Keystore) và giao diện đồ họa người dùng (GUI) đầy đủ.


* **4.3. Hướng nghiên cứu và khả năng mở rộng**
* **4.3.1. Tối ưu cấu trúc dữ liệu bằng Merkle Tree:** Cho phép xác minh giao dịch nhanh (SPV) và hỗ trợ thêm các nút nhẹ (Light Node) bên cạnh Full Node.
* **4.3.2. Nâng cấp quản lý khóa theo chuẩn công nghiệp:** Áp dụng ví phân cấp tất định HD Wallet (chuẩn BIP-32/BIP-39 với 12 từ khóa khôi phục).
* **4.3.3. Nâng cấp tầng mạng và đồng thuận:** Chuyển sang giao thức WebSocket thời gian thực, thay JSON bằng cơ sở dữ liệu nhúng Key-Value (LevelDB/RocksDB) và thử nghiệm cơ chế đồng thuận Proof of Stake (PoS).



---

### TÀI LIỆU THAM KHẢO (~1 trang)

Liệt kê khoảng 6–8 tài liệu uy tín theo chuẩn IEEE:

1. S. Nakamoto, *"Bitcoin: A Peer-to-Peer Electronic Cash System"*, 2008.
2. Certicom Research, *"SEC 2: Recommended Elliptic Curve Domain Parameters (secp256k1)"*, Standards for Efficient Cryptography, 2010.
3. A. M. Antonopoulos, *"Mastering Bitcoin: Programming the Open Blockchain"*, 2nd ed., O'Reilly Media, 2017.
4. NIST FIPS PUB 186-5, *"Digital Signature Standard (DSS)"*, 2023.
5. Tài liệu chính thức của thư viện Python `ecdsa` và `Flask`.