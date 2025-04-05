# Luck Dice - Game Cá Cược Trực Tuyến

**Luck Dice** là một ứng dụng game cá cược trực tuyến được phát triển bằng Python, sử dụng Flask làm backend, Flask-SocketIO cho giao tiếp thời gian thực, và Tkinter cho giao diện người dùng. Dự án bao gồm server game, client cho người chơi, giao diện quản trị admin và công cụ tự động đăng ký/spam tin nhắn. Các trò chơi hiện có: Tài Xỉu, Chẵn Lẻ, Bầu Cua.

## Tính Năng Chính

* **Server Game:** Quản lý phiên chơi, xử lý cược, lưu trữ dữ liệu (SQLite).
* **Client Người Chơi:** Đăng ký/đăng nhập, đặt cược, chat, đổi gifcode, xem lịch sử.
* **Admin Control Center:** Cố định kết quả, quản lý người chơi/gifcode, xuất dữ liệu.
* **Auto Register & Spam:** Tự động tạo tài khoản và gửi tin nhắn ngẫu nhiên.

## Cấu Trúc Dự Án
```text
Luck-dice/
├── server.py
├── client.py
├── admin_client.py
├── auto_register_and_spam.py
├── requirements.txt
└── data/
├── game_global.db
├── config/
│   └── config.txt
└── log/
└── server.log
```

## Yêu Cầu Hệ Thống

* Python 3.8+
* Windows, Linux, macOS
* Thư viện: Xem `requirements.txt`

## Cài Đặt

1.  **Clone:**
    ```bash
    git clone <repository_url>
    cd luck-dice
    ```
2.  **Cài đặt:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Cấu hình (`data/config/config.txt`):**
    ```text
    ip: 127.0.0.1
    port: 9999
    ```
4.  **Khởi tạo DB:** Chạy `server.py` lần đầu.

## Cách Sử Dụng

1.  **Chạy Server (`server.py`):**
    ```bash
    python server.py
    ```
    * Địa chỉ: `http://<ip>:<port>` (mặc định: `http://127.0.0.1:9999`).
    * Log: `data/log/server.log`.

2.  **Chạy Client (`client.py`):**
    ```bash
    python client.py
    ```
    * Giao diện đăng nhập/đăng ký.
    * Chơi game, chat, đổi gifcode, xem top.

3.  **Chạy Admin (`admin_client.py`):**
    ```bash
    python admin_client.py
    ```
    * Đăng nhập (mật khẩu mặc định cần thiết lập trong DB).
    * Quản lý game, người chơi, gifcode.

4.  **Chạy Auto Spam (`auto_register_and_spam.py`):**
    ```bash
    python auto_register_and_spam.py
    ```
    * Tạo tối đa 500 tài khoản (`target_accounts`).
    * Gửi tin nhắn ngẫu nhiên.

## Tính Năng Chi Tiết

* **Server:**
    * API: Đăng ký, đăng nhập, cược, chat, gifcode.
    * SocketIO: Realtime phiên chơi, kết quả, tin nhắn.
    * Quản lý phiên: 60 giây/phiên, tự động xử lý cược.
* **Client:**
    * Đăng ký/Đăng nhập: Nhận 100k xu khởi đầu.
    * Đặt cược: Chọn game, xu, cửa cược.
    * Chat: Phòng chat chung.
    * Gifcode: Đổi mã nhận xu.
    * Top Tài Phú: Top 10 người chơi giàu nhất.
* **Admin:**
    * Chỉnh Kết Quả: Cố định kết quả phiên tới.
    * Quản Lý Gifcode: Tạo, sửa, xóa, xem.
    * Quản Lý Người Chơi: Đặt xu, ban/unban, reset, xóa.
    * Xem Cược & Kết Quả: Theo dõi cược hiện tại/lịch sử.
    * Xuất Dữ Liệu: Xuất phiên chơi ra CSV.
* **Auto Spam:**
    * Tạo tài khoản: Username/password ngẫu nhiên (`data/account/accounts.txt`).
    * Spam tin nhắn: Nội dung mô phỏng người chơi.

## Lưu Ý

* **Cơ sở dữ liệu:** `data/game_global.db`.
* **Bảo mật:** JWT (chưa mã hóa mật khẩu trong DB).
* **Hiệu suất:** Spam có thể gây tải server.

## Đóng Góp

1.  Fork repository.
2.  Tạo branch (`git checkout -b feature/your-feature`).
3.  Commit (`git commit -m "Add your feature"`).
4.  Push (`git push origin feature/your-feature`).
5.  Tạo Pull Request.

## Giấy Phép

Mục đích học tập và thử nghiệm. Không có giấy phép chính thức.

## Liên Hệ

Email hoặc tạo issue trên repository.
