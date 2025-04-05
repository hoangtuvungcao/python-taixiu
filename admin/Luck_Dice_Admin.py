import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import threading
import time
from socketio import Client
import ctypes
import sys
import json
from datetime import datetime
import os

# Ẩn cửa sổ cmd trên Windows
if sys.platform == "win32":
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# Đọc cấu hình từ config/config.txt
def load_admin_config():
    config = {"ip": "0.0.0.0", "port": 9999}
    config_path = "data/config/config.txt"
    try:
        if not os.path.exists(config_path):
            print(f"Config file not found at {config_path}, using default values")
            return config
        with open(config_path, "r") as f:
            for line in f:
                if ":" in line:
                    key, value = line.strip().split(":", 1)
                    if key == "ip":
                        config["ip"] = value.strip()
                    elif key == "port":
                        config["port"] = int(value.strip())
        print(f"Loaded config: ip={config['ip']}, port={config['port']}")
    except Exception as e:
        print(f"Error loading config file: {str(e)}, using defaults")
    return config

config = load_admin_config()
BASE_URL = f"http://{config['ip']}:{config['port']}"

class AdminClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Luck Dice - Admin Control Center")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1e2a44")

        self.username = "admin"
        self.token = None
        self.base_url = BASE_URL
        self.session_id = 0
        self.time_left = 60
        self.ui_initialized = False

        self.sio = Client()
        self.sio.on("connect", self.on_connect)
        self.sio.on("new_session", self.on_new_session)
        self.sio.on("timer_update", self.on_timer_update)
        self.sio.on("game_result", self.on_game_result)
        threading.Thread(target=self.connect_socketio, daemon=True).start()

        self.setup_styles()
        self.login_screen()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background="#1e2a44", borderwidth=0)
        style.configure("TNotebook.Tab", font=("Helvetica", 14, "bold"), padding=[20, 10],
                       background="#2d3b5a", foreground="#00e6cc", borderwidth=2, relief="raised")
        style.map("TNotebook.Tab", background=[("selected", "#00e6cc"), ("active", "#64ffda")],
                 foreground=[("selected", "#1e2a44"), ("active", "#1e2a44")])
        style.configure("TFrame", background="#1e2a44")
        style.configure("TButton", font=("Helvetica", 12, "bold"), padding=10, background="#00e6cc", foreground="#1e2a44",
                       borderwidth=2, relief="raised")
        style.map("TButton", background=[("active", "#64ffda")])

    def connect_socketio(self):
        while True:
            try:
                if not self.sio.connected:
                    self.sio.connect(self.base_url)
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
        except Exception as e:
            print(f"Error in send_request: {str(e)}")
            return {"status": "error", "message": "Lỗi kết nối server"}

    def login_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        frame = tk.Frame(self.root, bg="#2d3b5a", bd=10, relief="raised")
        frame.place(relx=0.5, rely=0.5, anchor="center", width=450, height=350)

        tk.Label(frame, text="Admin Control Center", font=("Helvetica", 28, "bold"), bg="#2d3b5a", fg="#00e6cc",
                relief="flat", pady=10).pack(pady=30)
        tk.Label(frame, text="Mật khẩu Admin", font=("Helvetica", 14, "bold"), bg="#2d3b5a", fg="#a3bffa").pack(pady=5)
        password_entry = tk.Entry(frame, font=("Helvetica", 16), show="*", bg="#1e2a44", fg="white",
                                 insertbackground="#00e6cc", bd=5, relief="sunken")
        password_entry.pack(pady=15, padx=20, ipady=8)
        tk.Button(frame, text="Đăng nhập", font=("Helvetica", 16, "bold"), bg="#00e6cc", fg="#1e2a44", bd=0,
                 command=lambda: self.login(password_entry.get()), activebackground="#64ffda", cursor="hand2").pack(pady=20)

    def login(self, password):
        response = self.send_request("login", {"username": self.username, "password": password})
        if response["status"] == "success":
            self.token = response["access_token"]
            session_response = self.send_request("get_current_session", method="GET")
            if session_response["status"] == "success":
                self.session_id = session_response.get("session_id", 0)
                self.time_left = session_response.get("time_left", 60)
            self.main_screen()
        else:
            messagebox.showerror("Lỗi", response["message"])

    def main_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self.ui_initialized = True

        header = tk.Frame(self.root, bg="#2d3b5a", height=80, relief="raised", bd=5)
        header.pack(fill="x")
        tk.Label(header, text="Admin Control Center", font=("Helvetica", 22, "bold"), bg="#2d3b5a", fg="#00e6cc").pack(side="left", padx=20, pady=15)
        self.session_label = tk.Label(header, text=f"Phiên #{self.session_id}", font=("Helvetica", 16, "bold"), bg="#2d3b5a", fg="#64ffda")
        self.session_label.pack(side="left", padx=20)
        self.timer_label = tk.Label(header, text=f"Thời gian: {self.time_left}s", font=("Helvetica", 16, "bold"), bg="#2d3b5a", fg="#ff6b6b")
        self.timer_label.pack(side="left", padx=20)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=15, pady=15)

        self.setup_tab(notebook, "Chỉnh Kết Quả", self.setup_fix_result_tab)
        self.setup_tab(notebook, "Quản Lý Gifcode", self.setup_gifcode_tab)
        self.setup_tab(notebook, "Quản Lý Người Chơi", self.setup_player_tab)
        self.setup_tab(notebook, "Danh Sách Người Chơi", self.setup_user_list_tab)
        self.setup_tab(notebook, "Quản Lý Cược", self.setup_bets_tab)
        self.setup_tab(notebook, "Xem Kết Quả Phiên", self.setup_session_tab)
        self.setup_tab(notebook, "Xuất Dữ Liệu", self.setup_export_tab)

    def setup_tab(self, notebook, tab_name, setup_function):
        frame = tk.Frame(notebook, bg="#1e2a44", relief="flat", bd=5)
        notebook.add(frame, text=tab_name)
        setup_function(frame)

    def setup_fix_result_tab(self, frame):
        tk.Label(frame, text="Chỉnh Kết Quả Game", font=("Helvetica", 20, "bold"), bg="#1e2a44", fg="#00e6cc").pack(pady=15)

        main_frame = tk.Frame(frame, bg="#2d3b5a", bd=5, relief="raised")
        main_frame.pack(pady=10, padx=20, fill="both")

        game_var = tk.StringVar(value="taixiu")
        result_var = tk.StringVar()

        tk.Label(main_frame, text="Chọn game:", font=("Helvetica", 12, "bold"), bg="#2d3b5a", fg="#a3bffa").grid(row=0, column=0, pady=10, sticky="w")
        game_frame = tk.Frame(main_frame, bg="#2d3b5a")
        game_frame.grid(row=1, column=0, columnspan=2, pady=5)
        for i, (text, value) in enumerate([("Tài Xỉu", "taixiu"), ("Chẵn Lẻ", "chanle"), ("Bầu Cua", "baucua")]):
            tk.Radiobutton(game_frame, text=text, variable=game_var, value=value, bg="#2d3b5a", fg="#00e6cc",
                          selectcolor="#1e2a44", font=("Helvetica", 12), cursor="hand2").pack(side="left", padx=15)

        tk.Label(main_frame, text="Kết quả:", font=("Helvetica", 12, "bold"), bg="#2d3b5a", fg="#a3bffa").grid(row=2, column=0, pady=10, sticky="w")
        result_entry = ttk.Combobox(main_frame, textvariable=result_var, values=["Tài", "Xỉu"], state="readonly", width=25, font=("Helvetica", 12))
        result_entry.grid(row=3, column=0, columnspan=2, pady=5)

        def update_results(*args):
            game = game_var.get()
            result_entry["values"] = {"taixiu": ["Tài", "Xỉu"], "chanle": ["Chẵn", "Lẻ"], "baucua": ["Bầu", "Cua", "Tôm", "Cá", "Gà", "Nai"]}[game]
            result_entry.set("")

        game_var.trace("w", update_results)

        tk.Button(main_frame, text="Cố định Kết Quả", font=("Helvetica", 14, "bold"), bg="#ff6b6b", fg="white",
                 command=lambda: self.fix_result(game_var.get(), result_var.get()), activebackground="#ff4b4b", cursor="hand2").grid(row=4, column=0, columnspan=2, pady=20)

    def setup_gifcode_tab(self, frame):
        tk.Label(frame, text="Quản Lý Gifcode", font=("Helvetica", 20, "bold"), bg="#1e2a44", fg="#00e6cc").pack(pady=15)

        main_frame = tk.Frame(frame, bg="#2d3b5a", bd=5, relief="raised")
        main_frame.pack(pady=10, padx=20, fill="both")

        create_frame = tk.LabelFrame(main_frame, text="Tạo Gifcode", font=("Helvetica", 12, "bold"), bg="#2d3b5a", fg="#00e6cc", bd=3)
        create_frame.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        tk.Label(create_frame, text="Mã:", font=("Helvetica", 11), bg="#2d3b5a", fg="#a3bffa").pack(pady=5)
        code_entry = tk.Entry(create_frame, font=("Helvetica", 12), bg="#1e2a44", fg="white", width=20, bd=3, relief="sunken")
        code_entry.pack(pady=5)
        tk.Label(create_frame, text="Xu:", font=("Helvetica", 11), bg="#2d3b5a", fg="#a3bffa").pack(pady=5)
        coins_entry = tk.Entry(create_frame, font=("Helvetica", 12), bg="#1e2a44", fg="white", width=20, bd=3, relief="sunken")
        coins_entry.pack(pady=5)
        tk.Label(create_frame, text="Số lượng:", font=("Helvetica", 11), bg="#2d3b5a", fg="#a3bffa").pack(pady=5)
        quantity_entry = tk.Entry(create_frame, font=("Helvetica", 12), bg="#1e2a44", fg="white", width=20, bd=3, relief="sunken")
        quantity_entry.pack(pady=5)
        tk.Button(create_frame, text="Tạo", command=lambda: self.create_gifcode(code_entry.get(), coins_entry.get(), quantity_entry.get()),
                 cursor="hand2").pack(pady=10)

        edit_frame = tk.LabelFrame(main_frame, text="Chỉnh Gifcode", font=("Helvetica", 12, "bold"), bg="#2d3b5a", fg="#00e6cc", bd=3)
        edit_frame.grid(row=0, column=1, padx=15, pady=10, sticky="ew")
        tk.Label(edit_frame, text="Mã:", font=("Helvetica", 11), bg="#2d3b5a", fg="#a3bffa").pack(pady=5)
        edit_code_entry = tk.Entry(edit_frame, font=("Helvetica", 12), bg="#1e2a44", fg="white", width=20, bd=3, relief="sunken")
        edit_code_entry.pack(pady=5)
        tk.Label(edit_frame, text="Xu:", font=("Helvetica", 11), bg="#2d3b5a", fg="#a3bffa").pack(pady=5)
        edit_coins_entry = tk.Entry(edit_frame, font=("Helvetica", 12), bg="#1e2a44", fg="white", width=20, bd=3, relief="sunken")
        edit_coins_entry.pack(pady=5)
        tk.Label(edit_frame, text="Số lượng:", font=("Helvetica", 11), bg="#2d3b5a", fg="#a3bffa").pack(pady=5)
        edit_quantity_entry = tk.Entry(edit_frame, font=("Helvetica", 12), bg="#1e2a44", fg="white", width=20, bd=3, relief="sunken")
        edit_quantity_entry.pack(pady=5)
        tk.Button(edit_frame, text="Chỉnh", command=lambda: self.edit_gifcode(edit_code_entry.get(), edit_coins_entry.get(), edit_quantity_entry.get()),
                 cursor="hand2").pack(pady=10)

        delete_frame = tk.LabelFrame(main_frame, text="Xóa Gifcode", font=("Helvetica", 12, "bold"), bg="#2d3b5a", fg="#00e6cc", bd=3)
        delete_frame.grid(row=0, column=2, padx=15, pady=10, sticky="ew")
        tk.Label(delete_frame, text="Mã:", font=("Helvetica", 11), bg="#2d3b5a", fg="#a3bffa").pack(pady=5)
        delete_code_entry = tk.Entry(delete_frame, font=("Helvetica", 12), bg="#1e2a44", fg="white", width=20, bd=3, relief="sunken")
        delete_code_entry.pack(pady=5)
        tk.Button(delete_frame, text="Xóa", bg="#ff6b6b", fg="white",
                 command=lambda: self.delete_gifcode_with_confirm(delete_code_entry.get()), cursor="hand2").pack(pady=35)

        tk.Button(main_frame, text="Danh Sách Gifcode", command=self.list_giftcodes, cursor="hand2").grid(row=1, column=0, pady=15)
        tk.Button(main_frame, text="Gifcode Còn Lại", command=self.list_remaining_giftcodes, cursor="hand2").grid(row=1, column=2, pady=15)

    def setup_player_tab(self, frame):
        tk.Label(frame, text="Quản Lý Người Chơi", font=("Helvetica", 20, "bold"), bg="#1e2a44", fg="#00e6cc").pack(pady=15)

        main_frame = tk.Frame(frame, bg="#2d3b5a", bd=5, relief="raised")
        main_frame.pack(pady=10, padx=20, fill="both")

        coin_frame = tk.LabelFrame(main_frame, text="Đặt Xu", font=("Helvetica", 12, "bold"), bg="#2d3b5a", fg="#00e6cc", bd=3)
        coin_frame.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        tk.Label(coin_frame, text="Tên:", font=("Helvetica", 11), bg="#2d3b5a", fg="#a3bffa").pack(pady=5)
        player_entry = tk.Entry(coin_frame, font=("Helvetica", 12), bg="#1e2a44", fg="white", width=20, bd=3, relief="sunken")
        player_entry.pack(pady=5)
        tk.Label(coin_frame, text="Xu:", font=("Helvetica", 11), bg="#2d3b5a", fg="#a3bffa").pack(pady=5)
        coins_set_entry = tk.Entry(coin_frame, font=("Helvetica", 12), bg="#1e2a44", fg="white", width=20, bd=3, relief="sunken")
        coins_set_entry.pack(pady=5)
        tk.Button(coin_frame, text="Đặt", command=lambda: self.set_coins(player_entry.get(), coins_set_entry.get()),
                 cursor="hand2").pack(pady=20)

        ban_frame = tk.LabelFrame(main_frame, text="Cấm/Mở Cấm", font=("Helvetica", 12, "bold"), bg="#2d3b5a", fg="#00e6cc", bd=3)
        ban_frame.grid(row=0, column=1, padx=15, pady=10, sticky="ew")
        tk.Label(ban_frame, text="Tên:", font=("Helvetica", 11), bg="#2d3b5a", fg="#a3bffa").pack(pady=5)
        ban_entry = tk.Entry(ban_frame, font=("Helvetica", 12), bg="#1e2a44", fg="white", width=20, bd=3, relief="sunken")
        ban_entry.pack(pady=5)
        tk.Button(ban_frame, text="Cấm", bg="#ff6b6b", fg="white",
                 command=lambda: self.ban_player_with_confirm(ban_entry.get()), cursor="hand2").pack(pady=10)
        tk.Button(ban_frame, text="Mở", bg="#64ffda",
                 command=lambda: self.unban_player_with_confirm(ban_entry.get()), cursor="hand2").pack(pady=10)

    def setup_user_list_tab(self, frame):
        tk.Label(frame, text="Danh Sách Người Chơi", font=("Helvetica", 20, "bold"), bg="#1e2a44", fg="#00e6cc").pack(pady=15)

        main_frame = tk.Frame(frame, bg="#2d3b5a", bd=5, relief="raised")
        main_frame.pack(pady=10, padx=20, fill="both")

        tk.Button(main_frame, text="Xem Danh Sách", command=self.list_users, cursor="hand2").pack(pady=15)

        reset_frame = tk.LabelFrame(main_frame, text="Reset Thông Tin", font=("Helvetica", 12, "bold"), bg="#2d3b5a", fg="#00e6cc", bd=3)
        reset_frame.pack(pady=10, padx=10, fill="x")
        tk.Label(reset_frame, text="Tên:", font=("Helvetica", 11), bg="#2d3b5a", fg="#a3bffa").pack(pady=5)
        reset_entry = tk.Entry(reset_frame, font=("Helvetica", 12), bg="#1e2a44", fg="white", width=20, bd=3, relief="sunken")
        reset_entry.pack(pady=5)
        tk.Button(reset_frame, text="Reset", bg="#ff6b6b", fg="white",
                 command=lambda: self.reset_user_stats_with_confirm(reset_entry.get()), cursor="hand2").pack(pady=10)

        delete_frame = tk.LabelFrame(main_frame, text="Xóa Người Chơi", font=("Helvetica", 12, "bold"), bg="#2d3b5a", fg="#00e6cc", bd=3)
        delete_frame.pack(pady=10, padx=10, fill="x")
        tk.Label(delete_frame, text="Tên:", font=("Helvetica", 11), bg="#2d3b5a", fg="#a3bffa").pack(pady=5)
        delete_entry = tk.Entry(delete_frame, font=("Helvetica", 12), bg="#1e2a44", fg="white", width=20, bd=3, relief="sunken")
        delete_entry.pack(pady=5)
        tk.Button(delete_frame, text="Xóa", bg="#ff6b6b", fg="white",
                 command=lambda: self.delete_user_with_confirm(delete_entry.get()), cursor="hand2").pack(pady=10)

    def setup_bets_tab(self, frame):
        tk.Label(frame, text="Quản Lý Cược", font=("Helvetica", 20, "bold"), bg="#1e2a44", fg="#00e6cc").pack(pady=15)

        main_frame = tk.Frame(frame, bg="#2d3b5a", bd=5, relief="raised")
        main_frame.pack(pady=10, padx=20, fill="both")

        tk.Button(main_frame, text="Xem Cược Hiện Tại", command=self.current_bets, cursor="hand2").pack(pady=15)
        tk.Button(main_frame, text="Hủy Tất Cả Cược", bg="#ff6b6b", fg="white",
                 command=self.cancel_bets_with_confirm, cursor="hand2").pack(pady=15)
        tk.Button(main_frame, text="Trạng Thái Server", command=self.server_status, cursor="hand2").pack(pady=15)

    def setup_session_tab(self, frame):
        tk.Label(frame, text="Xem Kết Quả Phiên", font=("Helvetica", 20, "bold"), bg="#1e2a44", fg="#00e6cc").pack(pady=15)

        main_frame = tk.Frame(frame, bg="#2d3b5a", bd=5, relief="raised")
        main_frame.pack(pady=10, padx=20, fill="both")

        session_frame = tk.LabelFrame(main_frame, text="Tra cứu", font=("Helvetica", 12, "bold"), bg="#2d3b5a", fg="#00e6cc", bd=3)
        session_frame.pack(pady=10, padx=10, fill="x")
        tk.Label(session_frame, text="Phiên:", font=("Helvetica", 11), bg="#2d3b5a", fg="#a3bffa").pack(pady=5)
        session_entry = tk.Entry(session_frame, font=("Helvetica", 12), bg="#1e2a44", fg="white", width=20, bd=3, relief="sunken")
        session_entry.pack(pady=5)
        tk.Button(session_frame, text="Xem", command=lambda: self.view_session_result(session_entry.get()), cursor="hand2").pack(pady=10)

        self.session_result_text = tk.Text(main_frame, height=18, width=90, bg="#1e2a44", fg="white", font=("Helvetica", 11), state="disabled", bd=3, relief="sunken")
        self.session_result_text.pack(pady=15)

    def setup_export_tab(self, frame):
        tk.Label(frame, text="Xuất Dữ Liệu", font=("Helvetica", 20, "bold"), bg="#1e2a44", fg="#00e6cc").pack(pady=15)

        main_frame = tk.Frame(frame, bg="#2d3b5a", bd=5, relief="raised")
        main_frame.pack(pady=10, padx=20, fill="both")

        export_frame = tk.LabelFrame(main_frame, text="Xuất CSV", font=("Helvetica", 12, "bold"), bg="#2d3b5a", fg="#00e6cc", bd=3)
        export_frame.pack(pady=10, padx=10, fill="x")
        tk.Label(export_frame, text="Phiên:", font=("Helvetica", 11), bg="#2d3b5a", fg="#a3bffa").pack(pady=5)
        export_entry = tk.Entry(export_frame, font=("Helvetica", 12), bg="#1e2a44", fg="white", width=20, bd=3, relief="sunken")
        export_entry.pack(pady=5)
        tk.Button(export_frame, text="Xuất", command=lambda: self.export_session(export_entry.get()), cursor="hand2").pack(pady=10)

    def fix_result(self, game, result):
        if not result:
            messagebox.showerror("Lỗi", "Vui lòng chọn kết quả!")
            return
        response = self.send_request("admin/fix_result", {"game": game, "result": result, "session_id": self.session_id})
        messagebox.showinfo("Thành công", response["message"]) if response["status"] == "success" else messagebox.showerror("Lỗi", response["message"])

    def create_gifcode(self, code, coins, quantity):
        try:
            coins, quantity = int(coins), int(quantity)
            if not code or coins <= 0 or quantity <= 0:
                raise ValueError
            response = self.send_request("admin/create_gifcode", {"code": code, "coins": coins, "quantity": quantity})
            messagebox.showinfo("Thành công", response["message"]) if response["status"] == "success" else messagebox.showerror("Lỗi", response["message"])
        except ValueError:
            messagebox.showerror("Lỗi", "Nhập đầy đủ và đúng định dạng!")

    def edit_gifcode(self, code, coins, quantity):
        try:
            coins, quantity = int(coins), int(quantity)
            if not code or coins <= 0 or quantity <= 0:
                raise ValueError
            response = self.send_request("admin/edit_gifcode", {"code": code, "coins": coins, "quantity": quantity})
            messagebox.showinfo("Thành công", response["message"]) if response["status"] == "success" else messagebox.showerror("Lỗi", response["message"])
        except ValueError:
            messagebox.showerror("Lỗi", "Nhập đầy đủ và đúng định dạng!")

    def delete_gifcode_with_confirm(self, code):
        if not code or not messagebox.askyesno("Xác nhận", f"Xóa mã {code}?"):
            return
        response = self.send_request("admin/delete_gifcode", {"code": code})
        messagebox.showinfo("Thành công", response["message"]) if response["status"] == "success" else messagebox.showerror("Lỗi", response["message"])

    def list_giftcodes(self):
        response = self.send_request("admin/list_giftcodes", method="GET")
        if response["status"] == "success":
            window = tk.Toplevel(self.root)
            window.title("Danh Sách Gifcode")
            window.geometry("700x500")
            window.configure(bg="#1e2a44")
            text = tk.Text(window, height=25, width=80, bg="#2d3b5a", fg="white", font=("Helvetica", 11), state="disabled", bd=3, relief="sunken")
            text.pack(pady=20, padx=20)
            text.config(state="normal")
            text.insert(tk.END, "Mã | Xu | Đã Dùng/Tổng | Thời Gian Tạo\n" + "-"*80 + "\n")
            for code in response["giftcodes"]:
                text.insert(tk.END, f"{code['code']} | {code['coins']:,} xu | {code['used_count']}/{code['quantity']} | {code['created_at']}\n")
            text.config(state="disabled")

    def list_remaining_giftcodes(self):
        response = self.send_request("admin/list_giftcodes", method="GET")
        if response["status"] == "success":
            window = tk.Toplevel(self.root)
            window.title("Gifcode Còn Lại")
            window.geometry("600x500")
            window.configure(bg="#1e2a44")
            text = tk.Text(window, height=25, width=70, bg="#2d3b5a", fg="white", font=("Helvetica", 11), state="disabled", bd=3, relief="sunken")
            text.pack(pady=20, padx=20)
            text.config(state="normal")
            text.insert(tk.END, "Mã | Xu | Số Lần Còn Lại\n" + "-"*60 + "\n")
            remaining = [code for code in response["giftcodes"] if code['quantity'] > code['used_count']]
            if not remaining:
                text.insert(tk.END, "Không còn gifcode nào khả dụng.\n")
            else:
                for code in remaining:
                    remaining_count = code['quantity'] - code['used_count']
                    text.insert(tk.END, f"{code['code']} | {code['coins']:,} xu | {remaining_count}\n")
            text.config(state="disabled")

    def set_coins(self, player, coins):
        try:
            coins = int(coins)
            if not player or coins < 0:
                raise ValueError
            response = self.send_request("admin/set_coins", {"username": player, "coins": coins})
            messagebox.showinfo("Thành công", response["message"]) if response["status"] == "success" else messagebox.showerror("Lỗi", response["message"])
        except ValueError:
            messagebox.showerror("Lỗi", "Tên và số xu hợp lệ!")

    def ban_player_with_confirm(self, player):
        if not player or not messagebox.askyesno("Xác nhận", f"Cấm {player}?"):
            return
        response = self.send_request("admin/ban_player", {"username": player})
        messagebox.showinfo("Thành công", response["message"]) if response["status"] == "success" else messagebox.showerror("Lỗi", response["message"])

    def unban_player_with_confirm(self, player):
        if not player or not messagebox.askyesno("Xác nhận", f"Mở cấm {player}?"):
            return
        response = self.send_request("admin/unban_player", {"username": player})
        messagebox.showinfo("Thành công", response["message"]) if response["status"] == "success" else messagebox.showerror("Lỗi", response["message"])

    def list_users(self):
        response = self.send_request("admin/list_users", method="GET")
        if response["status"] == "success":
            window = tk.Toplevel(self.root)
            window.title("Danh Sách Người Chơi")
            window.geometry("800x500")
            window.configure(bg="#1e2a44")
            text = tk.Text(window, height=25, width=90, bg="#2d3b5a", fg="white", font=("Helvetica", 11), state="disabled", bd=3, relief="sunken")
            text.pack(pady=20, padx=20)
            text.config(state="normal")
            text.insert(tk.END, "Tên | Xu | EXP | Cấp | Thắng | Cấm\n" + "-"*90 + "\n")
            for user in response["users"]:
                text.insert(tk.END, f"{user['username']} | {user['coins']:,} xu | {user['exp']} | {user['level']} | {user['wins']} | {'Có' if user['banned'] else 'Không'}\n")
            text.config(state="disabled")

    def reset_user_stats_with_confirm(self, username):
        if not username or not messagebox.askyesno("Xác nhận", f"Reset {username}?"):
            return
        response = self.send_request("admin/reset_user_stats", {"username": username})
        messagebox.showinfo("Thành công", response["message"]) if response["status"] == "success" else messagebox.showerror("Lỗi", response["message"])

    def delete_user_with_confirm(self, username):
        if not username or not messagebox.askyesno("Xác nhận", f"Xóa {username}?"):
            return
        response = self.send_request("admin/delete_user", {"username": username})
        messagebox.showinfo("Thành công", response["message"]) if response["status"] == "success" else messagebox.showerror("Lỗi", response["message"])

    def current_bets(self):
        response = self.send_request("admin/current_bets", method="GET")
        if response["status"] == "success":
            window = tk.Toplevel(self.root)
            window.title(f"Cược Hiện Tại - Phiên #{response['session_id']}")
            window.geometry("700x500")
            window.configure(bg="#1e2a44")
            text = tk.Text(window, height=25, width=80, bg="#2d3b5a", fg="white", font=("Helvetica", 11), state="disabled", bd=3, relief="sunken")
            text.pack(pady=20, padx=20)
            text.config(state="normal")
            text.insert(tk.END, f"Cược Phiên #{response['session_id']}:\nNgười Chơi | Game | Xu | Lựa Chọn\n" + "-"*80 + "\n")
            if not response["bets"]:
                text.insert(tk.END, "Chưa có cược.\n")
            else:
                for bet in response["bets"]:
                    text.insert(tk.END, f"{bet['username']} | {bet['game'].capitalize()} | {bet['amount']:,} xu | {bet['choice']}\n")
            text.config(state="disabled")

    def cancel_bets_with_confirm(self):
        if not messagebox.askyesno("Xác nhận", f"Hủy cược phiên #{self.session_id}?"):
            return
        response = self.send_request("admin/cancel_bets")
        messagebox.showinfo("Thành công", response["message"]) if response["status"] == "success" else messagebox.showerror("Lỗi", response["message"])

    def server_status(self):
        response = self.send_request("admin/server_status", method="GET")
        if response["status"] == "success":
            status = response["server_status"]
            window = tk.Toplevel(self.root)
            window.title("Trạng Thái Server")
            window.geometry("500x400")
            window.configure(bg="#1e2a44")
            text = tk.Text(window, height=15, width=50, bg="#2d3b5a", fg="white", font=("Helvetica", 11), state="disabled", bd=3, relief="sunken")
            text.pack(pady=20, padx=20)
            text.config(state="normal")
            uptime = status["uptime"]
            days, remainder = divmod(int(uptime), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            text.insert(tk.END, f"Thời gian hoạt động: {days}d {hours}h {minutes}m {seconds}s\n")
            text.insert(tk.END, f"Người dùng hoạt động: {status['active_users']}\n")
            text.insert(tk.END, f"Tổng người dùng: {status['total_users']}\n")
            text.insert(tk.END, f"Tổng xu cược: {status['total_bets_amount']:,} xu\n")
            text.insert(tk.END, f"Phiên hiện tại: #{status['current_session']}\n")
            text.config(state="disabled")
        else:
            messagebox.showerror("Lỗi", response["message"])

    def view_session_result(self, session_id):
        try:
            session_id = int(session_id)
            response = self.send_request("admin/session_result", {"session_id": session_id}, method="GET")
            if response["status"] == "success":
                self.session_result_text.config(state="normal")
                self.session_result_text.delete(1.0, tk.END)
                self.session_result_text.insert(tk.END, f"Kết quả phiên #{session_id}:\n" + "-"*80 + "\n")
                if not response["results"]:
                    self.session_result_text.insert(tk.END, "Không có kết quả.\n")
                else:
                    for res in response["results"]:
                        self.session_result_text.insert(tk.END, f"{res['game'].capitalize()} - {res['result']} - {res['bets']} cược\n")
                self.session_result_text.config(state="disabled")
        except ValueError:
            messagebox.showerror("Lỗi", "Phiên phải là số nguyên!")

    def export_session(self, session_id):
        try:
            session_id = int(session_id)
            response = self.send_request("admin/export_session", {"session_id": session_id}, method="GET")
            if response["status"] == "success":
                file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
                if file_path:
                    with open(file_path, "w", newline="") as f:
                        f.write(response["csv_data"])
                    messagebox.showinfo("Thành công", f"Đã xuất phiên #{session_id} vào {file_path}")
        except ValueError:
            messagebox.showerror("Lỗi", "Phiên phải là số nguyên!")

    def on_connect(self):
        print("Đã kết nối tới máy chủ")

    def on_new_session(self, data):
        if self.ui_initialized:
            self.session_id = data["session_id"]
            self.time_left = data["time_left"]
            self.session_label.config(text=f"Phiên #{self.session_id}")
            self.timer_label.config(text=f"Thời gian: {self.time_left}s")

    def on_timer_update(self, data):
        if self.ui_initialized:
            self.time_left = data["time_left"]
            self.timer_label.config(text=f"Thời gian: {self.time_left}s")

    def on_game_result(self, data):
        if self.ui_initialized:
            print(f"Kết quả phiên #{data['session_id']}: {data['results']}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AdminClient(root)
    root.mainloop()