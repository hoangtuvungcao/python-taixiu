import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import time
from socketio import Client
import ctypes
import sys
from PIL import Image, ImageTk  # Thêm Pillow để xử lý ảnh

if sys.platform == "win32":
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

def load_client_config():
    config = {"ip": "127.0.0.1", "port": 9999}
    try:
        with open("data/config/config.txt", "r") as f:
            for line in f:
                if ":" in line:
                    key, value = line.strip().split(":", 1)
                    if key == "ip":
                        config["ip"] = value.strip()
                    elif key == "port":
                        config["port"] = int(value.strip())
    except FileNotFoundError:
        print("Lỗi Config")
    return config

config = load_client_config()
BASE_URL = f"http://{config['ip']}:{config['port']}"
SOCKET_URL = f"http://{config['ip']}:{config['port']}"

class GameClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Luck Dice - VĂN TRỌNG")
        self.root.geometry("1280x720")
        self.root.configure(bg="#0a192f")

        # Đặt biểu tượng cửa sổ (icon) từ file logo.ico
        try:
            self.root.iconbitmap("data/logo/logo.ico")  # Đặt icon cho cửa sổ
        except Exception as e:
            print(f"Error loading window icon: {str(e)}")

        # Load logo để hiển thị trong giao diện
        try:
            logo_path = "data/logo/logo.ico"  # Nếu chỉ có file .ico
            # Chuyển đổi file .ico thành định dạng hiển thị được
            logo_image = Image.open(logo_path)
            # Resize logo cho phù hợp với giao diện (100x100 pixel)
            logo_image = logo_image.resize((100, 100), Image.Resampling.LANCZOS)
            self.logo = ImageTk.PhotoImage(logo_image)
        except Exception as e:
            print(f"Error loading logo for UI: {str(e)}")
            self.logo = None

        self.username = None
        self.token = None
        self.base_url = BASE_URL
        self.coins = 0
        self.session_id = 0
        self.time_left = 60
        self.ui_initialized = False
        self.bet_status = {}

        self.sio = Client()
        self.sio.on("connect", self.on_connect)
        self.sio.on("new_session", self.on_new_session)
        self.sio.on("timer_update", self.on_timer_update)
        self.sio.on("game_result", self.on_game_result)
        self.sio.on("chat_message", self.on_chat_message)
        threading.Thread(target=self.connect_socketio, daemon=True).start()

        self.setup_styles()
        self.login_screen()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background="#0a192f", borderwidth=0)
        style.configure("TNotebook.Tab", font=("Helvetica", 12, "bold"), padding=[15, 8],
                       background="#172a45", foreground="#64ffda", borderwidth=0, relief="flat")
        style.map("TNotebook.Tab", background=[("selected", "#00d4ff")], foreground=[("selected", "white")])
        style.configure("TFrame", background="#0a192f")

    def connect_socketio(self):
        while True:
            try:
                if not self.sio.connected:
                    self.sio.connect(SOCKET_URL)
                time.sleep(1)
            except:
                time.sleep(5)

    def send_request(self, endpoint, data=None, method="POST"):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        try:
            if method == "POST":
                response = requests.post(f"{self.base_url}/{endpoint}", json=data, headers=headers, timeout=5)
            else:
                response = requests.get(f"{self.base_url}/{endpoint}", headers=headers, params=data, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Lỗi khi gửi yêu cầu tới {endpoint}: {e}")
            return {"status": "error", "message": f"Không thể kết nối tới server: {str(e)}"}

    def login_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        frame = tk.Frame(self.root, bg="#0a192f", highlightthickness=2, highlightbackground="#64ffda", bd=10, relief="flat")
        frame.place(relx=0.5, rely=0.5, anchor="center", width=450, height=550)

        # Thêm logo vào màn hình đăng nhập
        if self.logo:
            logo_label = tk.Label(frame, image=self.logo, bg="#0a192f")
            logo_label.pack(pady=10)

        tk.Label(frame, text="Luck Dice", font=("Helvetica", 32, "bold"), bg="#0a192f", fg="#64ffda").pack(pady=10)

        tk.Label(frame, text="Tên đăng nhập", bg="#0a192f", fg="#a3bffa", font=("Helvetica", 12, "bold")).pack(pady=(0, 5))
        username_entry = tk.Entry(frame, font=("Helvetica", 14), bg="#172a45", fg="white", insertbackground="#64ffda",
                                 bd=5, relief="flat", width=30)
        username_entry.pack(pady=10, padx=20, ipady=6)

        tk.Label(frame, text="Mật khẩu", bg="#0a192f", fg="#a3bffa", font=("Helvetica", 12, "bold")).pack(pady=(0, 5))
        password_entry = tk.Entry(frame, font=("Helvetica", 14), show="*", bg="#172a45", fg="white",
                                 insertbackground="#64ffda", bd=5, relief="flat", width=30)
        password_entry.pack(pady=10, padx=20, ipady=6)

        tk.Button(frame, text="Đăng nhập", font=("Helvetica", 14, "bold"), bg="#00d4ff", fg="white", bd=0,
                 relief="flat", command=lambda: self.login(username_entry.get(), password_entry.get()),
                 activebackground="#00b3d1", cursor="hand2", width=15).pack(pady=10, ipady=8)

        tk.Button(frame, text="Đăng ký", font=("Helvetica", 14, "bold"), bg="#172a45", fg="#64ffda", bd=0,
                 relief="flat", command=self.register_screen, activebackground="#00d4ff",
                 activeforeground="white", cursor="hand2", width=15).pack(pady=10, ipady=8)

    def register_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        frame = tk.Frame(self.root, bg="#0a192f", highlightthickness=2, highlightbackground="#64ffda", bd=10, relief="flat")
        frame.place(relx=0.5, rely=0.5, anchor="center", width=450, height=550)

        # Thêm logo vào màn hình đăng ký
        if self.logo:
            logo_label = tk.Label(frame, image=self.logo, bg="#0a192f")
            logo_label.pack(pady=10)

        tk.Label(frame, text="Đăng ký tài khoản", font=("Helvetica", 32, "bold"), bg="#0a192f", fg="#64ffda").pack(pady=10)

        tk.Label(frame, text="Tên đăng nhập", bg="#0a192f", fg="#a3bffa", font=("Helvetica", 12, "bold")).pack(pady=(0, 5))
        username_entry = tk.Entry(frame, font=("Helvetica", 14), bg="#172a45", fg="white", insertbackground="#64ffda",
                                 bd=5, relief="flat", width=30)
        username_entry.pack(pady=10, padx=20, ipady=6)

        tk.Label(frame, text="Mật khẩu", bg="#0a192f", fg="#a3bffa", font=("Helvetica", 12, "bold")).pack(pady=(0, 5))
        password_entry = tk.Entry(frame, font=("Helvetica", 14), show="*", bg="#172a45", fg="white",
                                 insertbackground="#64ffda", bd=5, relief="flat", width=30)
        password_entry.pack(pady=10, padx=20, ipady=6)

        tk.Button(frame, text="Đăng ký", font=("Helvetica", 14, "bold"), bg="#00d4ff", fg="white", bd=0,
                 relief="flat", command=lambda: self.register(username_entry.get(), password_entry.get()),
                 activebackground="#00b3d1", cursor="hand2", width=15).pack(pady=20, ipady=8)

        tk.Button(frame, text="Quay lại", font=("Helvetica", 14, "bold"), bg="#172a45", fg="#64ffda", bd=0,
                 relief="flat", command=self.login_screen, activebackground="#00d4ff",
                 activeforeground="white", cursor="hand2", width=15).pack(pady=0, ipady=8)

    def login(self, username, password):
        response = self.send_request("login", {"username": username, "password": password})
        if response["status"] == "success":
            self.username = username
            self.token = response["access_token"]
            self.coins = response["data"]["coins"]

            session_response = self.send_request("get_current_session", method="GET")
            if session_response["status"] == "success":
                self.session_id = session_response.get("session_id", 0)
                self.time_left = session_response.get("time_left", 60)
            else:
                messagebox.showwarning("Cảnh báo", "Không thể lấy thông tin phiên hiện tại, sử dụng giá trị mặc định.")

            # Lấy trạng thái đặt cược hiện tại từ server
            self.load_pending_bets()

            self.main_screen()
        else:
            messagebox.showerror("Thất Bại!")

    def load_pending_bets(self):
        response = self.send_request("get_pending_bets", method="GET")
        if response["status"] == "success":
            self.bet_status.clear()
            for bet in response["pending_bets"]:
                game = bet["game"]
                amount = bet["amount"]
                choice = bet["choice"]
                self.bet_status[game] = {"amount": amount, "choice": choice}
        else:
            print("Không thể lấy trạng thái đặt cược:", response["message"])

    def register(self, username, password):
        response = self.send_request("register", {"username": username, "password": password})
        if response["status"] == "success":
            messagebox.showinfo("Thành công", "Đăng ký thành công!")
            self.login_screen()
        else:
            messagebox.showerror("Thất Bại!")

    def logout(self):
        self.username = None
        self.token = None
        self.coins = 0
        self.session_id = 0
        self.time_left = 60
        self.ui_initialized = False
        self.sio.disconnect()
        self.login_screen()

    def main_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self.ui_initialized = True

        header = tk.Frame(self.root, bg="#172a45", height=70, relief="raised", bd=2)
        header.pack(fill="x")

        # Thêm logo vào header của màn hình chính
        if self.logo:
            logo_label = tk.Label(header, image=self.logo, bg="#172a45")
            logo_label.pack(side="left", padx=10)

        tk.Label(header, text=f"Người chơi: {self.username}", font=("Helvetica", 18, "bold"), bg="#172a45", fg="#64ffda").pack(side="left", padx=20, pady=10)
        self.coin_label = tk.Label(header, text=f"Xu: {self.coins:,}", font=("Helvetica", 18, "bold"), bg="#172a45", fg="#64ffda")
        self.coin_label.pack(side="right", padx=20, pady=10)
        tk.Button(header, text="Đăng xuất", font=("Helvetica", 12, "bold"), bg="#ff6b6b", fg="white", bd=0,
                 relief="flat", command=self.logout, activebackground="#ff4b4b", cursor="hand2").pack(side="right", padx=20, ipady=6)
        tk.Button(header, text="Top Tài Phú", font=("Helvetica", 12, "bold"), bg="#ff6b6b", fg="white", bd=0,
                 relief="flat", command=self.show_top_rich, activebackground="#ff4b4b", cursor="hand2").pack(side="right", padx=20, ipady=6)
        tk.Button(header, text="Coi Cầu", font=("Helvetica", 12, "bold"), bg="#ff6b6b", fg="white", bd=0,
                 relief="flat", command=self.show_game_results, activebackground="#ff4b4b", cursor="hand2").pack(side="right", padx=20, ipady=6)
        tk.Button(header, text="Gifcode", font=("Helvetica", 12, "bold"), bg="#ff6b6b", fg="white", bd=0,
                 relief="flat", command=self.gifcode_screen, activebackground="#ff4b4b", cursor="hand2").pack(side="right", padx=20, ipady=1)

        session_frame = tk.Frame(self.root, bg="#0a192f", height=50)
        session_frame.pack(fill="x")
        self.session_label = tk.Label(session_frame, text=f"Phiên #{self.session_id}", font=("Helvetica", 16, "bold"), bg="#0a192f", fg="#00d4ff")
        self.session_label.pack(side="left", padx=20, pady=10)
        self.timer_label = tk.Label(session_frame, text=f"Thời gian: {self.time_left}s", font=("Helvetica", 16, "bold"), bg="#0a192f", fg="#ff6b6b")
        self.timer_label.pack(side="left", padx=20, pady=10)

        main_frame = tk.Frame(self.root, bg="#0a192f")
        main_frame.pack(fill="both", expand=True)

        chat_frame = tk.Frame(main_frame, bg="#172a45", width=320, relief="raised", bd=2)
        chat_frame.pack(side="left", fill="y", padx=15, pady=15)
        tk.Label(chat_frame, text="Trò chuyện", font=("Helvetica", 14, "bold"), bg="#172a45", fg="#64ffda").pack(pady=10)
        self.chat_text = tk.Text(chat_frame, height=20, width=35, bg="#0a192f", fg="white", font=("Helvetica", 11),
                                state="disabled", relief="flat", bd=5)
        self.chat_text.pack(padx=10, pady=5)
        self.message_entry = tk.Entry(chat_frame, font=("Helvetica", 12), bg="#0a192f", fg="white", insertbackground="#64ffda",
                                     bd=5, relief="flat", width=30)
        self.message_entry.pack(pady=10, padx=10, ipady=6)
        tk.Button(chat_frame, text="Gửi", font=("Helvetica", 12, "bold"), bg="#00d4ff", fg="white", bd=0,
                 relief="flat", command=self.send_message, activebackground="#00b3d1", cursor="hand2").pack(pady=10, ipady=6)

        game_frame = tk.Frame(main_frame, bg="#0a192f")
        game_frame.pack(side="right", fill="both", expand=True, padx=15, pady=15)

        self.notebook = ttk.Notebook(game_frame)
        self.notebook.pack(fill="both", expand=True)

        taixiu_frame = tk.Frame(self.notebook, bg="#0a192f")
        self.notebook.add(taixiu_frame, text="Tài Xỉu")
        self.setup_game_tab(taixiu_frame, "taixiu", ["Tài", "Xỉu"])

        chanle_frame = tk.Frame(self.notebook, bg="#0a192f")
        self.notebook.add(chanle_frame, text="Chẵn Lẻ")
        self.setup_game_tab(chanle_frame, "chanle", ["Chẵn", "Lẻ"])

        baucua_frame = tk.Frame(self.notebook, bg="#0a192f")
        self.notebook.add(baucua_frame, text="Bầu Cua")
        self.setup_game_tab(baucua_frame, "baucua", ["Bầu", "Cua", "Tôm", "Cá", "Gà", "Nai"])

        self.update_bet_status_labels()
        self.load_chat_history()

    def update_bet_status_labels(self):
        for game in ["taixiu", "chanle", "baucua"]:
            bet_info = self.bet_status.get(game, {"amount": 0, "choice": "N/A"})
            if bet_info["amount"] > 0 and bet_info["choice"] != "N/A":
                getattr(self, f"{game}_bet_status_label").config(
                    text=f"Đã cược: {bet_info['amount']:,} ({bet_info['choice']})", fg="#64ffda"
                )
            else:
                getattr(self, f"{game}_bet_status_label").config(
                    text="Chưa đặt cược", fg="#ff6b6b"
                )

    def load_chat_history(self):
        response = self.send_request("get_chat_history", method="GET")
        if response["status"] == "success":
            for msg in response["chat_history"]:
                self.chat_text.config(state="normal")
                timestamp = msg.get("timestamp", "N/A")
                if 'T' in timestamp:
                    time_part = timestamp.split('T')[1][:8]
                else:
                    time_part = timestamp
                self.chat_text.insert(tk.END, f"[{time_part}] {msg['sender']}: {msg['message']}\n")
                self.chat_text.config(state="disabled")
                self.chat_text.see(tk.END)

    def setup_game_tab(self, frame, game, choices):
        tk.Label(frame, text=f"Trò chơi {game.capitalize()}", font=("Helvetica", 18, "bold"), bg="#0a192f", fg="#64ffda").pack(pady=15)

        bet_frame = tk.Frame(frame, bg="#0a192f", relief="flat", bd=2)
        bet_frame.pack(pady=10)
        choice_var = tk.StringVar()
        for choice in choices:
            tk.Radiobutton(bet_frame, text=choice, variable=choice_var, value=choice, bg="#0a192f", fg="#a3bffa",
                          selectcolor="#172a45", font=("Helvetica", 12), activebackground="#0a192f", cursor="hand2").pack(side="left", padx=15)

        tk.Label(frame, text="Số xu đặt cược", bg="#0a192f", fg="#a3bffa", font=("Helvetica", 12, "bold")).pack(pady=5)
        amount_entry = tk.Entry(frame, font=("Helvetica", 12), bg="#172a45", fg="white", insertbackground="#64ffda",
                               bd=5, relief="flat", width=25)
        amount_entry.pack(pady=10, padx=20, ipady=6)

        tk.Button(frame, text="Đặt cược", font=("Helvetica", 14, "bold"), bg="#ff6b6b", fg="white", bd=0,
                 relief="flat", command=lambda: self.place_bet(game, amount_entry.get(), choice_var.get()),
                 activebackground="#ff4b4b", cursor="hand2", width=15).pack(pady=15, ipady=8)

        setattr(self, f"{game}_bet_status_label", tk.Label(frame, text="Chưa đặt cược", font=("Helvetica", 12), bg="#0a192f", fg="#ff6b6b"))
        getattr(self, f"{game}_bet_status_label").pack(pady=10)

        result_frame = tk.Frame(frame, bg="#172a45", bd=2, relief="raised")
        result_frame.pack(pady=10, fill="x", padx=20)
        setattr(self, f"{game}_result_label", tk.Label(result_frame, text="Kết quả cũ: Chưa có", font=("Helvetica", 16, "bold"), bg="#172a45", fg="#64ffda"))
        getattr(self, f"{game}_result_label").pack(pady=10, padx=15)

    def gifcode_screen(self):
        gifcode_window = tk.Toplevel(self.root)
        gifcode_window.title("Đổi Gifcode")
        gifcode_window.geometry("400x400")
        gifcode_window.configure(bg="#0a192f")

        # Đặt biểu tượng cho cửa sổ gifcode
        try:
            gifcode_window.iconbitmap("data/logo/logo.ico")
        except Exception as e:
            print("Thất Bại!")

        # Thêm logo vào cửa sổ gifcode
        if self.logo:
            logo_label = tk.Label(gifcode_window, image=self.logo, bg="#0a192f")
            logo_label.pack(pady=10)

        tk.Label(gifcode_window, text="Nhập Gifcode", font=("Helvetica", 18, "bold"), bg="#0a192f", fg="#64ffda").pack(pady=10)
        code_entry = tk.Entry(gifcode_window, font=("Helvetica", 14), bg="#172a45", fg="white", insertbackground="#64ffda",
                             bd=5, relief="flat", width=25)
        code_entry.pack(pady=10, padx=20, ipady=6)

        tk.Button(gifcode_window, text="Đổi thưởng", font=("Helvetica", 14, "bold"), bg="#00d4ff", fg="white", bd=0,
                 relief="flat", command=lambda: self.redeem_gifcode(code_entry.get(), gifcode_window),
                 activebackground="#00b3d1", cursor="hand2", width=15).pack(pady=20, ipady=8)

    def redeem_gifcode(self, code, window):
        response = self.send_request("redeem_gifcode", {"code": code})
        if response["status"] == "success":
            self.update_coins()
            messagebox.showinfo("Thành công", response["message"])
            window.destroy()
        else:
            messagebox.showerror("Thất Bại!")

    def show_top_rich(self):
        response = self.send_request("get_top_rich", method="GET")
        if response["status"] == "success":
            top_players = response.get("top_players", [])
            if not top_players:
                messagebox.showinfo("Thông báo", "Hiện tại không có người chơi nào trong bảng xếp hạng!")
                return
            top_window = tk.Toplevel(self.root)
            top_window.title("Top Tài Phú")
            top_window.geometry("400x500")
            top_window.configure(bg="#0a192f")

            # Đặt biểu tượng cho cửa sổ Top Tài Phú
            try:
                top_window.iconbitmap("data/logo/logo.ico")
            except Exception as e:
                print("Thất Bại!")

            # Thêm logo vào cửa sổ Top Tài Phú
            if self.logo:
                logo_label = tk.Label(top_window, image=self.logo, bg="#0a192f")
                logo_label.pack(pady=10)

            tk.Label(top_window, text="Top Tài Phú", font=("Helvetica", 18, "bold"), bg="#0a192f", fg="#64ffda").pack(pady=10)
            for i, player in enumerate(top_players, 1):
                tk.Label(top_window, text=f"{i}. {player['username']}: {player['coins']:,} xu",
                        font=("Helvetica", 12), bg="#0a192f", fg="white").pack(pady=10)
        else:
            messagebox.showerror("Thất Bại!")

    def show_game_results(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        game = "taixiu" if current_tab == "Tài Xỉu" else "chanle" if current_tab == "Chẵn Lẻ" else "baucua"

        response = self.send_request("get_game_history", {"game": game, "limit": 8}, method="GET")
        if response["status"] != "success":
            messagebox.showerror("Thất Bại!")
            return

        results = response["history"]

        result_window = tk.Toplevel(self.root)
        result_window.title(f"Cầu {game.capitalize()}")
        result_window.geometry("400x500")
        result_window.configure(bg="#0a192f")

        # Đặt biểu tượng cho cửa sổ Coi Cầu
        try:
            result_window.iconbitmap("data/logo/logo.ico")
        except Exception as e:
            print("Thất Bại!")

        # Thêm logo vào cửa sổ Coi Cầu
        if self.logo:
            logo_label = tk.Label(result_window, image=self.logo, bg="#0a192f")
            logo_label.pack(pady=10)

        tk.Label(result_window, text=f"Cầu {game.capitalize()} (8 kết quả gần nhất)", font=("Helvetica", 18, "bold"), bg="#0a192f", fg="#64ffda").pack(pady=10)

        if not results:
            tk.Label(result_window, text="Chưa có kết quả!", font=("Helvetica", 12), bg="#0a192f", fg="white").pack(pady=10)
        else:
            for i, entry in enumerate(results, 1):
                session_id = entry["session_id"]
                if game == "taixiu":
                    result = entry["result"]
                    dice = entry["details"]
                    total = entry["total"]
                    display_result = f"#{session_id} - {result} ({total}: {dice})"
                elif game == "chanle":
                    result = entry["result"]
                    num = entry["details"]
                    display_result = f"#{session_id} - {result} ({num})"
                else:
                    result = entry["result"]
                    display_result = f"#{session_id} - {result}"
                tk.Label(result_window, text=f"{i}. {display_result}", font=("Helvetica", 12), bg="#0a192f", fg="white").pack(pady=5)

    def place_bet(self, game, amount_str, choice):
        try:
            amount = int(amount_str)
            if amount <= 0:
                messagebox.showerror("Lỗi", "Số xu phải lớn hơn 0!")
                return
            if not choice:
                messagebox.showerror("Lỗi", "Vui lòng chọn một lựa chọn cược!")
                return
            if amount > self.coins:
                messagebox.showerror("Lỗi", "Bạn không đủ xu để đặt cược!")
                return
            data = {
                "game": game,
                "amount": amount,
                "choice": choice,
                "session_id": int(self.session_id)
            }
            response = self.send_request("bet", data)
            if response["status"] == "success":
                self.coins -= amount
                self.coin_label.config(text=f"Xu: {self.coins:,}")
                self.bet_status[game] = {"amount": amount, "choice": choice}
                getattr(self, f"{game}_bet_status_label").config(text=f"Đã cược: {amount:,} ({choice})", fg="#64ffda")
                messagebox.showinfo("Thành công", f"Đã đặt cược {amount:,} xu vào {choice}, chờ kết quả!")
            else:
                messagebox.showerror("Thất Bại!")
        except ValueError:
            messagebox.showerror("Lỗi", "Số xu không hợp lệ!")

    def send_message(self):
        message = self.message_entry.get().strip()
        if not message:
            messagebox.showerror("Lỗi", "Tin nhắn không được để trống!")
            return
        response = self.send_request("send_message", {"message": message})
        if response["status"] == "success":
            self.message_entry.delete(0, tk.END)
        else:
            messagebox.showerror("Thất Bại!")

    def update_coins(self):
        response = self.send_request("get_user_info", method="GET")
        if response["status"] == "success":
            self.coins = response["data"]["coins"]
            self.coin_label.config(text=f"Xu: {self.coins:,}")
        else:
            messagebox.showwarning("Cảnh báo", "Phiên đăng nhập đã hết hạn vui lòng đăng nhập lại!")

    def on_connect(self):
        print("Đã kết nối tới máy chủ")

    def on_new_session(self, data):
        if self.ui_initialized:
            self.session_id = data["session_id"]
            self.time_left = data["time_left"]
            self.session_label.config(text=f"Phiên #{self.session_id}")
            self.timer_label.config(text=f"Thời gian: {self.time_left}s")
            self.bet_status.clear()
            for game in ["taixiu", "chanle", "baucua"]:
                getattr(self, f"{game}_bet_status_label").config(text="Chưa đặt cược", fg="#ff6b6b")
            self.load_pending_bets()
            self.update_bet_status_labels()

    def on_timer_update(self, data):
        if self.ui_initialized:
            self.time_left = data["time_left"]
            self.timer_label.config(text=f"Thời gian: {self.time_left}s")

    def on_game_result(self, data):
        if self.ui_initialized:
            session_id = data["session_id"]
            results = data["results"]
            result_messages = []

            for game, result in results.items():
                bet_info = self.bet_status.get(game, {"choice": "N/A", "amount": 0})
                choice = bet_info["choice"]
                amount = bet_info["amount"]

                if game == "taixiu":
                    result_str = result[0]
                    dice = result[1]
                    total = sum(dice)
                    display_result = f"{result_str} ({total}: {dice})"
                elif game == "chanle":
                    result_str = result[0]
                    num = result[1]
                    display_result = f"{result_str} ({num})"
                else:
                    result_str = result[0]
                    display_result = result_str

                result_label = getattr(self, f"{game}_result_label")
                result_label.config(text=f"Kết quả cũ: {display_result}", fg="#ff6b6b" if game == "taixiu" and result_str == "Xỉu" else "#64ffda")

                if choice != "N/A":
                    win = (game == "baucua" and result[0] == choice) or \
                          (game != "baucua" and result[0] == choice)
                    if win:
                        winnings = amount * 2
                        result_messages.append(f"Game {game.capitalize()}: Bạn thắng!\nĐã đặt: {choice} ({amount:,} xu)\nKết quả: {display_result}\nNhận: {winnings:,} xu")
                    else:
                        result_messages.append(f"Game {game.capitalize()}: Bạn thua!\nĐã đặt: {choice} ({amount:,} xu)\nKết quả: {display_result}\nMất: {amount:,} xu")

            if result_messages:
                messagebox.showinfo("Kết quả Phiên", "\n\n".join(result_messages))

            self.update_coins()

    def on_chat_message(self, data):
        if self.ui_initialized:
            self.chat_text.config(state="normal")
            timestamp = data.get("timestamp", "N/A")
            if 'T' in timestamp:
                time_part = timestamp.split('T')[1][:8]
            else:
                time_part = timestamp
            self.chat_text.insert(tk.END, f"[{time_part}] {data['sender']}: {data['message']}\n")
            self.chat_text.config(state="disabled")
            self.chat_text.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = GameClient(root)
    root.mainloop()