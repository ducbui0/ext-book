# Tomato Novel Sync (VBook Extension) - Tailscale Edition

Hệ thống kết nối, đồng bộ và tự động tải truyện từ **Tomato Novel Downloader** sang ứng dụng **VBook** trên điện thoại. Phiên bản này được tối ưu hóa đặc biệt với **Tailscale**, mang lại tốc độ truyền tải cực nhanh, độ trễ thấp và bảo mật tuyệt đối so với các phiên bản dùng Ngrok trước đây.

## 🌟 Tính Năng Nổi Bật (Mới Cập Nhật)

Hệ thống đã được lập trình lại toàn diện để đạt hiệu suất cao nhất:
*   **🚀 Smart File Organizer:** Tự động phát hiện file truyện sau khi tải xong từ thư mục gốc và di chuyển gọn gàng vào thư mục riêng của từng cuốn sách. Không bao giờ bị lỗi "không tìm thấy file".
*   **⚡ In-Memory Cache (Bộ Đệm Server):** Server tự động nhớ các thông tin truyện (Tên, Ảnh bìa, Tác giả) trong 5 phút. Khi VBook hỏi liên tục, server trả lời ngay lập tức trong 0.001s mà không cần phải quét web (scrape) lại Fanqie, giúp chống quá tải server và chống bị khóa IP.
*   **🛡️ Process Tracker & Debounce:** Quản lý chặt chẽ các cửa sổ tải truyện (CMD). Mỗi truyện chỉ có tối đa 1 tiến trình tải hoạt động, ngăn chặn triệt để tình trạng "Spam lệnh tải" làm đơ máy tính khi điện thoại mất mạng kết nối lại.
*   **🌐 Auto IP Detection:** Server tự động tìm và hiển thị địa chỉ IP Tailscale của máy tính ngay trên màn hình đen khởi động, bạn không cần phải mò mẫm tự tìm nữa.
*   **🗂️ Chunk File Streaming:** Hỗ trợ truyền mượt mà các file truyện cực lớn bằng cách cắt nhỏ (Chunk 64KB) và bọc lỗi `ConnectionResetError` êm ái khi bạn ngắt mạng giữa chừng.

---

## 🔌 Các Phương Thức Kết Nối

Dự án hỗ trợ 3 cách chạy máy chủ để kết nối tới VBook:

1.  **Tailscale (Khuyên dùng - Nhanh, Ổn định & Bảo mật):**
    *   Chạy file `run_with_tailscale.bat`. File sẽ tự động chạy server Python, quét địa chỉ IP Tailscale và hiển thị ngay trên màn hình.
    *   *Yêu cầu:* Bạn chỉ cần cài app Tailscale trên cả máy tính và điện thoại, rồi đăng nhập chung một tài khoản Google/Microsoft.
2.  **Local LAN (Nhanh nhất - Chỉ dùng khi chung Wi-Fi nhà):**
    *   Chạy file `run_local.bat`. Thích hợp khi điện thoại và PC của bạn kết nối chung một cục phát Wi-Fi.
3.  **Ngrok (Truy cập từ xa qua tên miền công cộng - Cũ):**
    *   Chạy file `run_with_ngrok.bat`. (Hiện tại không khuyên dùng vì tốc độ qua server Singapore khá chậm).

---

## 🚀 HƯỚNG DẪN SỬ DỤNG (DÀNH CHO NGƯỜI MỚI)

### Bước 1: Khởi động Server trên Máy tính (PC)
1. Đảm bảo ứng dụng **Tailscale** trên máy tính đang bật và đã đăng nhập.
2. Mở thư mục chứa dự án này, nhấp đúp chuột vào file **`run_with_tailscale.bat`**.
3. Cửa sổ dòng lệnh hiện ra sẽ quét hệ thống và hiển thị dòng chữ:
   `-> [Tailscale] http://100.x.x.x:18423`
4. Hãy **chép** lại hoặc nhớ địa chỉ URL có số `100.x.x.x` đó.

### Bước 2: Thiết lập trên Điện thoại (VBook)
1. Tải ứng dụng **Tailscale** trên điện thoại, bật lên và đăng nhập chung tài khoản với máy tính.
2. Tải file **`tomato-vbook-ext.zip`** từ dự án này về điện thoại.
3. Mở app **VBook** > Tiện ích > Bấm dấu `+` > Chọn "Thêm từ file Zip" và chọn file vừa tải.
4. Chọn nguồn **Tomato Novel Sync** > Chọn **Cấu hình nguồn**.
3. Điền dòng mã sau vào phần **Mã bổ sung (Additional Code)** của extension:
```javascript
var CONFIG_URL = "http://100.x.x.x:18423";
```
*(Thay `100.x.x.x` bằng dải số chính xác hiển thị trên màn hình PC của bạn. Địa chỉ Tailscale này thường cố định không thay đổi, nên bạn chỉ cần thiết lập 1 lần duy nhất).*

### Bước 3: Tải và Đọc truyện
1. Trên VBook, bấm vào một cuốn truyện bạn muốn đọc.
2. App sẽ báo hiệu PC đang lấy dữ liệu. Lúc này trên màn hình máy tính sẽ tự động nhảy lên một cửa sổ CMD đen để tải truyện bằng Tool Rust.
3. Chờ vài phút cho máy tính tải xong. Trong lúc đó bạn có thể cất điện thoại đi không cần bật liên tục.
4. Sau khi máy tính tải xong, bạn mở lại VBook, ấn **"Tải lại chương"**. Truyện sẽ được nạp đầy vào bộ nhớ Cache (Balo) của điện thoại ngay lập tức!
5. Tắt mạng đọc vô tư!

---

## 🔄 Tự động chạy Server khi bật máy tính
Nếu muốn máy tính tự động khởi động hệ thống này chạy ngầm mỗi khi bạn mở máy:
1. Nhấn tổ hợp phím `Windows + R`, gõ vào `shell:startup` và nhấn **Enter**.
2. Nhấp chuột phải vào file `run_with_tailscale.bat` -> Chọn **Create Shortcut** (Tạo lối tắt).
3. Di chuyển file Shortcut vừa tạo và thả vào thư mục `Startup` vừa hiện ra.
