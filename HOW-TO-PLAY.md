# Hướng dẫn sử dụng giao diện Ví Full Node P2P

Tài liệu này giải thích từng phần trên giao diện, cách 3 node tương tác với nhau, và cách chạy
4 kịch bản kiểm thử để chụp ảnh cho báo cáo.

---

## 1. Hiểu đúng mô hình trước khi bấm

**Mỗi tab trình duyệt là một "người" khác nhau trong mạng.**

```text
   Tab :5001                Tab :5002                Tab :5003
  (giao diện)              (giao diện)              (giao diện)
       │                        │                        │
       ▼                        ▼                        ▼
┌──────────────┐  HTTP   ┌──────────────┐  HTTP   ┌──────────────┐
│  Node 5001   │◀──────▶│  Node 5002   │◀──────▶│  Node 5003   │
│  Ví riêng    │         │  Ví riêng    │         │  Ví riêng    │
│  Sổ cái riêng│◀──────────────────────────────▶│  Sổ cái riêng│
└──────────────┘                                 └──────────────┘
 ledger_5001.json         ledger_5002.json         ledger_5003.json
```

- Mỗi node có **ví riêng**: một cặp khóa ECDSA. Địa chỉ ví chính là Public Key.
- Mỗi node giữ **bản sao sổ cái riêng** trong `p2p_ecdsa_wallet/storage/ledger_<port>.json`. Không có máy chủ hay CSDL dùng chung.
- **Giao diện chỉ nói chuyện với node của chính nó.** Tab `:5001` chỉ điều khiển được ví của node 5001.
  Muốn "là" node 5002 thì chuyển sang tab `:5002`.
- Các node tự trao đổi với nhau qua HTTP:
  - giao dịch mới được **phát tán** sang mọi peer;
  - khối mới đào được **phát tán** sang mọi peer;
  - node vừa bật lại tự **đồng bộ** chuỗi dài nhất từ các peer.
- Giao diện tự làm mới **mỗi 3 giây**; danh sách peer làm mới **mỗi 10 giây**.
  Bấm xong mà chưa thấy thay đổi ở tab khác thì đợi vài giây.

### Ba quy tắc quan trọng

| Quy tắc | Ý nghĩa khi dùng |
| --- | --- |
| **Tiền chỉ sinh ra khi đào khối** | Ví nào cũng bắt đầu với 0 coin. Bấm **Đào khối** thì node đó được thưởng **50 coin**. |
| **Giao dịch chỉ có hiệu lực khi đã nằm trong một khối** | Sau khi gửi, giao dịch nằm trong **Mempool** (chờ). Số dư chỉ thay đổi khi có node bất kỳ đào khối chứa giao dịch đó. |
| **Nonce là số thứ tự giao dịch của ví** | Giao dịch đầu tiên của ví có nonce 0, giao dịch tiếp theo nonce 1, … Node tự điền nonce, bạn không cần nhập. |

---

## 2. Khởi động

Mở 3 terminal trong thư mục `p2p_ecdsa_wallet`:

```bash
python run_node.py --port 5001 --peers http://127.0.0.1:5002 http://127.0.0.1:5003
python run_node.py --port 5002 --peers http://127.0.0.1:5001 http://127.0.0.1:5003
python run_node.py --port 5003 --peers http://127.0.0.1:5001
```

Mở 3 tab: <http://127.0.0.1:5001/>, <http://127.0.0.1:5002/>, <http://127.0.0.1:5003/>.
Nên xếp 3 tab cạnh nhau (3 cửa sổ trình duyệt) để quan sát cùng lúc.

> Node khởi động trước có thể mất vài giây vì phải thử kết nối tới các node chưa bật. Đây là bình thường.

**Muốn chơi lại từ đầu:** tắt cả 3 node (Ctrl+C), xóa các file trong `p2p_ecdsa_wallet/storage/` (giữ `.gitkeep`), rồi bật lại.
- Xóa `ledger_*.json`: chuỗi trở về chỉ có khối Genesis, số dư về 0.
- Xóa thêm `wallet_*.json`: mỗi node sinh ví mới với địa chỉ mới.

---

## 3. Các phần trên giao diện

### Thanh trên cùng
- **Ví Full Node P2P :5001**: bạn đang ở node nào.
- **Độ dài chuỗi**: số khối trong sổ cái của node này, tính cả khối Genesis. Ba node đồng bộ thì con số này bằng nhau.
- **Mempool**: số giao dịch đang chờ được đào.
- **Độ khó PoW**: hash của khối phải bắt đầu bằng bấy nhiêu chữ số `0`.

### Ví của node
- **Số dư**: chỉ tính các giao dịch **đã nằm trong chuỗi**.
- **Địa chỉ ví (Public Key hex)**: 128 ký tự hex. Bấm **Sao chép** để lấy địa chỉ.
- **Nonce giao dịch kế tiếp**: nonce mà giao dịch tiếp theo của ví này sẽ dùng.
- **Đào khối**: gom toàn bộ Mempool cộng giao dịch thưởng 50 coin vào một khối mới, giải Proof of Work, rồi phát tán khối cho các peer.
- **Đồng bộ ngay**: hỏi các peer, nếu có chuỗi dài hơn và hợp lệ thì tải về. Bình thường không cần bấm, vì việc này diễn ra tự động.

### Mạng ngang hàng
- Danh sách peer mà node này biết. Chấm **xanh** là online (kèm địa chỉ ví của peer), chấm **đỏ** là ngoại tuyến.
- **Thêm peer**: nhập URL một node khác (ví dụ `http://127.0.0.1:5004`) để kết nối thủ công.

### Chuyển tiền
- **Người nhận**: chọn ví của peer trong danh sách, hiển thị dạng `Node :5002 — …`, hoặc dán một địa chỉ bất kỳ vào ô bên dưới. Ô dán được ưu tiên.
  Danh sách có thể trống trong khoảng 10 giây đầu, trong lúc giao diện hỏi địa chỉ của các peer.
- **Số tiền** rồi bấm **Ký & gửi giao dịch**: node ký giao dịch bằng Private Key của nó, tự kiểm tra, đưa vào Mempool, rồi phát tán cho các peer.
- Ô kết quả màu **xanh** là thành công (hiện cả chữ ký). Màu **đỏ** là bị từ chối, kèm lý do.

### Kiểm thử giả mạo giao dịch (Đề K)
Dùng để chứng minh: **sửa dữ liệu sau khi ký thì chữ ký mất hiệu lực.**
1. **1. Ký giao dịch**: node ký một giao dịch nhưng **chưa gửi**. JSON của giao dịch hiện trong ô văn bản.
2. **2a. Sửa số tiền +1** hoặc **2b. Sửa 1 ký tự người nhận**: sửa dữ liệu nhưng giữ nguyên chữ ký cũ. Bạn cũng có thể tự sửa JSON trong ô.
3. **3. Gửi tới node để xác minh**: gửi JSON cho node kiểm tra như thể nó đến từ một peer.
- **Khôi phục bản gốc**: quay về JSON chưa bị sửa.

### Nhật ký node
Các sự kiện của node, mới nhất ở trên. Đây là nơi thấy rõ nhất các node tương tác với nhau:
- **Xanh**: hợp lệ, ví dụ "Nhận giao dịch … Xác minh ECDSA hợp lệ", "Nhận khối #2 … nối vào chuỗi", "Đồng bộ: thay chuỗi cục bộ 3 → 5 khối".
- **Đỏ**: bị từ chối, ví dụ chữ ký sai, vượt số dư, sai nonce, phát lại.
- **Không màu**: thông tin, ví dụ khởi động, peer mới đăng ký.

Terminal của node in ra đúng các dòng này.

### Mempool
Các giao dịch đang chờ: Từ, Đến, Số tiền, Nonce, Chữ ký (rút gọn; rê chuột vào để xem đầy đủ).
Bảng trống sau khi có khối mới được đào.

### Chuỗi khối (sổ cái cục bộ)
Danh sách khối, mới nhất ở trên. Bấm vào một khối để xem:
- **Hash**, và **Previous hash** (bằng đúng Hash của khối trước; đây là thứ liên kết các khối thành chuỗi);
- **Nonce (PoW)**: số lần thử để tìm ra hash có đủ số `0` ở đầu;
- danh sách giao dịch. Giao dịch đầu tiên luôn là **SYSTEM (thưởng)** 50 coin cho người đào.

---

## 4. Lượt chơi mẫu: làm theo thứ tự

Ký hiệu: **[5001]** nghĩa là thao tác trên tab `:5001`.

### Bước 0: Kiểm tra kết nối
- Ở mỗi tab, mục **Mạng ngang hàng** có 2 peer chấm xanh.
- **Độ dài chuỗi** = 1 ở cả 3 tab (chỉ có khối Genesis). Số dư = 0.

### Bước 1: Tạo tiền (đào khối đầu tiên)
- **[5001]** bấm **Đào khối**.
- Tab 5001: số dư **50**, độ dài chuỗi **2**. Nhật ký: "Đào khối #1 thành công sau …s: nonce=…, hash=000…".
- Tab 5002 và 5003, sau tối đa 3 giây: độ dài chuỗi cũng là **2**. Nhật ký: "Nhận khối #1 từ http://127.0.0.1:5001: hợp lệ … → nối vào chuỗi".

  → Khối được **phát tán**. Mỗi node tự kiểm tra Proof of Work và hash trước khi chấp nhận khối.

### Bước 2: Kịch bản 1 – Giao dịch hợp lệ
- **[5001]** ở mục **Chuyển tiền**, chọn người nhận `Node :5002`, số tiền `10`, bấm **Ký & gửi giao dịch**.
- Tab 5001: ô xanh "Đã ký và phát tán: 10 → Node :5002 (nonce 0)". **Nonce kế tiếp** tăng lên 1.
  **Số dư vẫn là 50**, vì giao dịch chưa được đào.
- Tab 5002 và 5003: Mempool có 1 giao dịch. Nhật ký: "Nhận giao dịch … từ http://127.0.0.1:5001 … Xác minh ECDSA hợp lệ, đủ số dư → thêm vào Mempool".
  → Mỗi node **tự xác minh chữ ký** bằng Public Key của người gửi, không tin node kia.
- **[5003]** bấm **Đào khối**. Node nào đào cũng được; ở đây để node 5003 đào.
- Kết quả trên cả 3 tab: Mempool trống, độ dài chuỗi 3.
  - Số dư 5001 = **40** (50 − 10);
  - số dư 5002 = **10**;
  - số dư 5003 = **50** (thưởng đào).

  Mở khối #2 trong **Chuỗi khối** sẽ thấy giao dịch thưởng cho 5003 và giao dịch 10 coin từ 5001 sang 5002.

### Bước 3: Kịch bản 3 – Chi tiêu vượt số dư
- **[5002]** (đang có 10 coin) chuyển `1000` cho `Node :5001`.
- Kết quả: ô đỏ "Bị từ chối: Không đủ số dư (khả dụng 10, cần 1000)". Nhật ký 5002 có dòng đỏ tương ứng.
  Giao dịch không được phát tán, nên các node khác không thấy gì.
- Mẹo: gửi `8` rồi gửi thêm `8` liền nhau, khi chưa đào. Lần thứ hai bị từ chối "khả dụng 2, cần 8",
  vì node trừ cả số tiền đang chờ trong Mempool. Đây là cơ chế **chống chi tiêu kép** (double spending).

### Bước 4: Kịch bản 2 – Giả mạo giao dịch (trọng tâm Đề K)
- **[5001]** ở mục **Kiểm thử giả mạo**, chọn người nhận, số tiền `5`, rồi bấm **1. Ký giao dịch**.
  JSON hiện ra với `amount: 5` và một `signature` dài.
- Bấm **2a. Sửa số tiền +1**: `amount` thành 6, chữ ký giữ nguyên.
- Bấm **3. Gửi tới node để xác minh**. Kết quả: ô đỏ **"HTTP 400 — Từ chối: Chữ ký ECDSA không hợp lệ (dữ liệu đã bị sửa hoặc ký sai khóa)"**.
  Thử thêm với **2b. Sửa 1 ký tự người nhận**: cũng bị từ chối.
- Bấm **Khôi phục bản gốc**, rồi **3. Gửi**. Kết quả: ô xanh **"HTTP 201 — Chữ ký ECDSA hợp lệ, đã thêm vào Mempool"**.
  Giao dịch này được phát tán như bình thường.
- Bấm **3. Gửi** thêm một lần nữa. Kết quả: **"Từ chối: Giao dịch đã tồn tại (bị phát lại)"**. Đây là cơ chế **chống Replay Attack**.

Vì sao bị từ chối? Node tính lại `h' = SHA256(dữ liệu giao dịch)` rồi kiểm tra `Verify(h', chữ ký, Public Key người gửi)`.
Chỉ cần đổi một ký tự thì `h'` khác hẳn mã băm đã được ký, nên kết quả kiểm tra là False.

> Lưu ý: sau khi bấm **1. Ký giao dịch**, hãy gửi bản đó (gốc hoặc đã sửa) trước khi dùng mục **Chuyển tiền**.
> Nếu chuyển tiền trước, bản đã ký sẽ mang nonce cũ và bị từ chối "Sai nonce". Gặp trường hợp này thì bấm **1. Ký giao dịch** lại.

### Bước 5: Kịch bản 4 – Node mất kết nối rồi tự đồng bộ
1. Tắt node 5003: bấm **Ctrl+C** ở terminal của nó.
   - Tab 5003 hiện "mất kết nối", vì node của tab này đã tắt.
   - Tab 5001 và 5002: sau tối đa 10 giây, peer `5003` chuyển sang chấm **đỏ – Ngoại tuyến**.
2. **[5001]** chuyển tiền cho `Node :5002` rồi **Đào khối**. **[5002]** **Đào khối** thêm một lần.
   Tab 5001 và 5002 có độ dài chuỗi tăng lên, ví dụ 5.
3. Mở file `p2p_ecdsa_wallet/storage/ledger_5003.json`: file này **vẫn ngắn hơn** (ít khối hơn `ledger_5001.json`). Nên chụp ảnh để so sánh.
4. Bật lại node 5003 bằng đúng lệnh cũ, rồi tải lại tab 5003 (F5).
5. Nhật ký và terminal 5003 có dòng:
   **"Đồng bộ: thay chuỗi cục bộ 3 → 5 khối từ http://127.0.0.1:5001 (đã xác minh liên kết băm, PoW và toàn bộ chữ ký ECDSA)"**.
   Độ dài chuỗi và số dư trên tab 5003 giờ khớp với 2 node kia. `ledger_5003.json` cũng đã được cập nhật.

Lúc khởi động, node 5003 tải chuỗi của các peer và **kiểm tra lại toàn bộ** từ khối Genesis:
previous_hash, Proof of Work, chữ ký của từng giao dịch, nonce và số dư.
Chỉ khi tất cả hợp lệ, node mới thay chuỗi cũ của mình bằng **chuỗi dài nhất** (Longest Chain Rule).

---

## 5. Bảng tra nhanh: bấm gì, thấy gì ở đâu

| Thao tác (ở node A) | Node A | Các node khác |
| --- | --- | --- |
| Đào khối | Số dư +50, chuỗi +1, Mempool trống | Chuỗi +1, Mempool trống; nhật ký "Nhận khối #…" |
| Chuyển tiền hợp lệ | Mempool +1, nonce kế tiếp +1, **số dư chưa đổi** | Mempool +1; nhật ký "Nhận giao dịch …" |
| Chuyển vượt số dư | Ô đỏ "Không đủ số dư" | Không thay đổi |
| Gửi giao dịch đã sửa | HTTP 400 "Chữ ký ECDSA không hợp lệ" | Không thay đổi |
| Gửi lại giao dịch cũ | HTTP 400 "bị phát lại" | Không thay đổi |
| Tắt node A | Tab A "mất kết nối" | Peer A chấm đỏ sau ≤ 10 giây |
| Bật lại node A | Nhật ký "Đồng bộ: thay chuỗi cục bộ X → Y khối" | Nhật ký "Peer mới đăng ký" (lần đầu) |

---

## 6. Câu hỏi thường gặp

**Gửi tiền rồi mà số dư không giảm?**
Giao dịch còn trong Mempool. Bấm **Đào khối** ở node bất kỳ.

**Danh sách "Người nhận" trống?**
Đợi khoảng 10 giây để giao diện hỏi địa chỉ các peer, hoặc kiểm tra peer có đang chấm xanh không.
Cách khác: sang tab node kia, bấm **Sao chép** địa chỉ ví, rồi dán vào ô bên dưới danh sách.

**Hai node đào gần như cùng lúc, giờ chuỗi hai bên khác nhau?**
Đó là **fork**: hai khối cùng vị trí trên hai nhánh. Dấu hiệu là độ dài chuỗi bằng nhau nhưng khối mới nhất có hash khác nhau.
Bấm **Đào khối** thêm một lần ở một node. Nhánh dài hơn thắng theo Longest Chain Rule, các node khác tự đồng bộ theo.
Giao dịch thuộc nhánh thua được trả lại Mempool, không bị mất.

**Bị từ chối "Sai nonce"?**
Thường do dùng một giao dịch đã ký từ trước (ở mục Kiểm thử giả mạo) sau khi ví đã gửi giao dịch khác. Ký lại là được.

**Tab báo "mất kết nối" dù node vẫn chạy?**
Kiểm tra terminal của node có bị lỗi không, rồi tải lại trang (F5).

**Đổi độ khó PoW?**
Thêm `--difficulty 4` vào lệnh chạy. Đào sẽ lâu hơn để thấy rõ Proof of Work.
Cả 3 node phải dùng **cùng một độ khó**, nếu không chúng sẽ từ chối khối của nhau.

---

## 7. Gợi ý ảnh chụp cho báo cáo

| Kịch bản | Nên chụp |
| --- | --- |
| 1. Giao dịch hợp lệ | Tab người gửi (ô xanh + Mempool) và tab người nhận (nhật ký "Nhận giao dịch") đặt cạnh nhau; sau khi đào, khối mở rộng trong **Chuỗi khối** |
| 2. Giả mạo | Mục **Kiểm thử giả mạo**: JSON đã sửa và ô đỏ HTTP 400; thêm một ảnh bản gốc với ô xanh HTTP 201 |
| 3. Vượt số dư | Mục **Chuyển tiền** với ô đỏ "Không đủ số dư" |
| 4. Mất kết nối | Peer chấm đỏ trên tab 5001; so sánh `ledger_5003.json` với `ledger_5001.json` trước khi bật lại; nhật ký 5003 sau khi bật lại |
