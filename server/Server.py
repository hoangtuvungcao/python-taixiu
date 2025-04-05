# -*- coding: utf-8 -*-
import sys
import threading
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import sqlite3
import random
import time
from flask_socketio import SocketIO, emit
from datetime import datetime, timezone
import logging
import os
import csv
from io import StringIO

# Cấu hình UTF-8 cho console trên Windows để tránh UnicodeEncodeError
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/log/server.log', encoding='utf-8'),
        logging.StreamHandler(stream=sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Đọc cấu hình từ config/config.txt
def load_server_config():
    config = {"ip": "0.0.0.0", "port": 9999}
    config_path = "data/config/config.txt"
    try:
        if not os.path.exists(config_path):
            logger.warning("Config file not found at %s, using default ip: 0.0.0.0, port: 9999", config_path)
            return config
        with open(config_path, "r") as f:
            for line in f:
                if ":" in line:
                    key, value = line.strip().split(":", 1)
                    if key == "ip":
                        config["ip"] = value.strip()
                    elif key == "port":
                        config["port"] = int(value.strip())
        logger.info("Loaded config: ip=%s, port=%d", config["ip"], config["port"])
    except Exception as e:
        logger.error("Error loading config file: %s, using defaults", str(e))
    return config

config = load_server_config()

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "BJKJLKLKJLJJhjlklkklk8yb89buHI87b9u976565C6VH6vuyu6"
jwt = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
logger.info("SocketIO initialized with threading")


server_start_time = datetime.now(timezone.utc)

def init_db():
    conn = sqlite3.connect("data/db/game_global.db", check_same_thread=False)
    c = conn.cursor()
    

    c.execute('''CREATE TABLE IF NOT EXISTS players (
                    username TEXT PRIMARY KEY,
                    password TEXT,
                    coins INTEGER DEFAULT 100000,
                    exp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    wins INTEGER DEFAULT 0,
                    banned INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    username TEXT,
                    game TEXT,
                    amount INTEGER,
                    choice TEXT,
                    result TEXT,
                    win INTEGER DEFAULT 0,
                    pending INTEGER DEFAULT 1,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS giftcodes (
                    code TEXT PRIMARY KEY,
                    coins INTEGER,
                    quantity INTEGER DEFAULT 1,
                    used_count INTEGER DEFAULT 0,
                    used_by TEXT DEFAULT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_username TEXT,
                    action TEXT,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS game_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    game TEXT,
                    result TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')


    c.execute("PRAGMA table_info(bets)")
    columns = [col[1] for col in c.fetchall()]
    if 'pending' not in columns:
        logger.warning("Adding missing 'pending' column to bets table")
        c.execute("ALTER TABLE bets ADD COLUMN pending INTEGER DEFAULT 1")
    
    conn.commit()
    return conn

class GameRoom:
    def __init__(self, game_type):
        self.game_type = game_type
        self.players = {}
        self.fixed_result = None
        self.paused = False

    def add_bet(self, username, amount, choice):
        if not self.paused:
            self.players[username] = {"amount": amount, "choice": choice}

    def clear_bets(self):
        self.players.clear()

    def generate_taixiu_dice(self, target_result):
        while True:
            dice = [random.randint(1, 6) for _ in range(3)]
            total = sum(dice)
            if (target_result == "Tài" and total > 10) or (target_result == "Xỉu" and total <= 10):
                return dice

    def generate_chanle_number(self, target_result):
        while True:
            num = random.randint(1, 100)
            if (target_result == "Chẵn" and num % 2 == 0) or (target_result == "Lẻ" and num % 2 != 0):
                return num

    def resolve_game(self):
        if self.paused:
            return None
        if self.fixed_result:
            if self.game_type == "taixiu":
                dice = self.generate_taixiu_dice(self.fixed_result)
                self.result = (self.fixed_result, dice)
            elif self.game_type == "chanle":
                num = self.generate_chanle_number(self.fixed_result)
                self.result = (self.fixed_result, num)
            elif self.game_type == "baucua":
                self.result = (self.fixed_result, None)
            self.fixed_result = None
        else:
            if self.game_type == "taixiu":
                dice = [random.randint(1, 6) for _ in range(3)]
                total = sum(dice)
                self.result = ("Tài" if total > 10 else "Xỉu", dice)
            elif self.game_type == "chanle":
                num = random.randint(1, 100)
                self.result = ("Chẵn" if num % 2 == 0 else "Lẻ", num)
            elif self.game_type == "baucua":
                result = random.choice(["Bầu", "Cua", "Tôm", "Cá", "Gà", "Nai"])
                self.result = (result, None)
        return self.result

class GameServer:
    def __init__(self):
        self.db = init_db()
        self.db_lock = threading.Lock()  # Thêm khóa để tránh xung đột database
        self.rooms = {"taixiu": GameRoom("taixiu"), "chanle": GameRoom("chanle"), "baucua": GameRoom("baucua")}
        self.session_id = self.get_last_session_id() + 1
        self.time_left = 60
        self.running = True
        self.active_connections = set()
        threading.Thread(target=self.run_session_loop, daemon=True).start()
        threading.Thread(target=self.broadcast_server_status, daemon=True).start()
        
        # Thêm thread để xóa lịch sử chat mỗi 20 phút
        self.chat_cleanup_interval = 20 * 60  # 20 phút tính bằng giây
        threading.Thread(target=self.clear_chat_history_loop, daemon=True).start()

    def get_last_session_id(self):
        with self.db_lock:
            c = self.db.cursor()
            c.execute("SELECT MAX(session_id) FROM bets")
            result_bets = c.fetchone()[0]
            c.execute("SELECT MAX(session_id) FROM game_results")
            result_game_results = c.fetchone()[0]
            max_session_id = max(result_bets or -1, result_game_results or -1)
            logger.info(f"Last session ID: {max_session_id}")
            return max_session_id

    def run_session_loop(self):
        while self.running:
            try:
                logger.info(f"Starting session #{self.session_id}")
                socketio.emit("new_session", {"session_id": self.session_id, "time_left": 60})
                for i in range(60, 0, -1):
                    self.time_left = i
                    socketio.emit("timer_update", {"session_id": self.session_id, "time_left": i})
                    time.sleep(1)
                with self.db_lock:
                    c = self.db.cursor()
                    results = {}
                    for game, room in self.rooms.items():
                        result = room.resolve_game()
                        if result is None:
                            logger.info(f"Game {game} is paused, skipping result generation")
                            continue
                        results[game] = result
                        result_str = repr(result)
                        logger.info(f"Storing result for {game} in session #{self.session_id}: {result_str}")
                        c.execute("INSERT INTO game_results (session_id, game, result) VALUES (?, ?, ?)",
                                  (self.session_id, game, result_str))
                        if room.players:
                            logger.info(f"Processing bets for {game} in session #{self.session_id}")
                            for username, bet in room.players.items():
                                win = (game == "baucua" and result[0] == bet["choice"]) or \
                                      (game != "baucua" and result[0] == bet["choice"])
                                winnings = bet["amount"] * 2 if win else 0
                                if win:
                                    c.execute("UPDATE players SET coins = coins + ?, wins = wins + 1 WHERE username = ?",
                                              (winnings, username))
                                c.execute("UPDATE bets SET result = ?, win = ?, pending = 0 WHERE session_id = ? AND username = ? AND game = ? AND pending = 1",
                                          (result_str, 1 if win else 0, self.session_id, username, game))
                            room.players.clear()
                        else:
                            logger.info(f"No bets placed for {game} in session #{self.session_id}")
                    self.db.commit()
                    logger.info(f"Emitting game results for session #{self.session_id}: {results}")
                    socketio.emit("game_result", {"session_id": self.session_id, "results": results})
                self.session_id += 1
            except Exception as e:
                logger.error(f"Error in session loop: {str(e)}")
                time.sleep(5)  # Đợi trước khi thử lại

    def broadcast_server_status(self):
        while self.running:
            socketio.emit("server_status", {
                "uptime": (datetime.now(timezone.utc) - server_start_time).total_seconds(),
                "active_users": len(self.active_connections)
            })
            time.sleep(10)

    def clear_chat_history_loop(self):
        """Xóa lịch sử chat mỗi 20 phút."""
        logger.info(f"Bắt đầu xóa lịch sử chat định kỳ, mỗi {self.chat_cleanup_interval//60} phút")
        while self.running:
            try:
                with self.db_lock:
                    c = self.db.cursor()
                    c.execute("DELETE FROM messages")
                    self.db.commit()
                    logger.info(f"Đã xóa toàn bộ lịch sử chat lúc {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                time.sleep(self.chat_cleanup_interval)  # Đợi 20 phút
            except Exception as e:
                logger.error(f"Lỗi khi xóa lịch sử chat: {str(e)}")
                time.sleep(60)  # Đợi 1 phút trước khi thử lại nếu có lỗi

server = GameServer()

def get_user_rank(username):
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT username FROM players ORDER BY coins DESC LIMIT 10")
        top_players = [row[0] for row in c.fetchall()]
        if username in top_players:
            rank = top_players.index(username) + 1
            return rank
        return None

def log_admin_action(admin_username, action, details):
    with server.db_lock:
        c = server.db.cursor()
        c.execute("INSERT INTO admin_logs (admin_username, action, details) VALUES (?, ?, ?)",
                  (admin_username, action, details))
        server.db.commit()
    logger.info(f"Admin Action: {admin_username} - {action}: {details}")

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"status": "error", "message": "Tên đăng nhập và mật khẩu không được để trống"}), 400
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT username FROM players WHERE username = ?", (username,))
        if c.fetchone():
            return jsonify({"status": "error", "message": "Tài khoản đã tồn tại"}), 400
        c.execute("INSERT INTO players (username, password) VALUES (?, ?)", (username, password))
        server.db.commit()
        return jsonify({"status": "success", "message": "Đăng ký thành công, nhận 100k coin!"}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"status": "error", "message": "Tên đăng nhập và mật khẩu không được để trống"}), 400
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT * FROM players WHERE username = ? AND password = ?", (username, password))
        player = c.fetchone()
        if player:
            if player[6]:
                return jsonify({"status": "error", "message": "Tài khoản bị cấm"}), 403
            access_token = create_access_token(identity=username)
            server.active_connections.add(username)
            return jsonify({
                "status": "success",
                "access_token": access_token,
                "data": {
                    "username": player[0],
                    "coins": player[2],
                    "exp": player[3],
                    "level": player[4],
                    "wins": player[5]
                }
            }), 200
        return jsonify({"status": "error", "message": "Tên đăng nhập hoặc mật khẩu không đúng"}), 401

@app.route("/get_user_info", methods=["GET"])
@jwt_required()
def get_user_info():
    username = get_jwt_identity()
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT * FROM players WHERE username = ?", (username,))
        player = c.fetchone()
        if player:
            return jsonify({
                "status": "success",
                "data": {
                    "username": player[0],
                    "coins": player[2],
                    "exp": player[3],
                    "level": player[4],
                    "wins": player[5],
                    "banned": player[6]
                }
            }), 200
        return jsonify({"status": "error", "message": "Người dùng không tồn tại"}), 404

@app.route("/get_current_session", methods=["GET"])
@jwt_required()
def get_current_session():
    return jsonify({
        "status": "success",
        "session_id": server.session_id,
        "time_left": server.time_left
    }), 200

@app.route("/bet", methods=["POST"])
@jwt_required()
def place_bet():
    username = get_jwt_identity()
    data = request.get_json()
    game = data.get("game")
    amount = data.get("amount")
    choice = data.get("choice")
    session_id = data.get("session_id")

    if game not in server.rooms:
        return jsonify({"status": "error", "message": "Trò chơi không hợp lệ"}), 400
    if not isinstance(amount, int) or amount <= 0:
        return jsonify({"status": "error", "message": "Số xu không hợp lệ"}), 400
    if not choice:
        return jsonify({"status": "error", "message": "Lựa chọn không hợp lệ"}), 400
    if session_id != server.session_id:
        logger.warning(f"Invalid session ID {session_id} from {username}, current session is {server.session_id}")
        return jsonify({"status": "error", "message": "Phiên không hợp lệ"}), 400

    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT coins FROM players WHERE username = ?", (username,))
        player = c.fetchone()
        if not player:
            return jsonify({"status": "error", "message": "Người dùng không tồn tại"}), 404
        if player[0] < amount:
            return jsonify({"status": "error", "message": "Không đủ xu để đặt cược"}), 400

        c.execute("UPDATE players SET coins = coins - ? WHERE username = ?", (amount, username))
        c.execute("INSERT INTO bets (session_id, username, game, amount, choice, pending) VALUES (?, ?, ?, ?, ?, ?)",
                  (session_id, username, game, amount, choice, 1))
        server.db.commit()

    server.rooms[game].add_bet(username, amount, choice)
    return jsonify({"status": "success", "message": "Đặt cược thành công"}), 200

@app.route("/get_pending_bets", methods=["GET"])
@jwt_required()
def get_pending_bets():
    username = get_jwt_identity()
    session_id = server.session_id
    try:
        with server.db_lock:
            c = server.db.cursor()
            c.execute("SELECT game, amount, choice FROM bets WHERE username = ? AND session_id = ? AND pending = 1",
                      (username, session_id))
            pending_bets = [{"game": row[0], "amount": row[1], "choice": row[2]} for row in c.fetchall()]
            return jsonify({"status": "success", "pending_bets": pending_bets}), 200
    except sqlite3.OperationalError as e:
        logger.error("Database error in get_pending_bets: %s", str(e))
        return jsonify({"status": "error", "message": "Lỗi cơ sở dữ liệu, vui lòng thử lại sau"}), 500

@app.route("/send_message", methods=["POST"])
@jwt_required()
def send_message():
    username = get_jwt_identity()
    data = request.get_json()
    message = data.get("message")
    if not message:
        return jsonify({"status": "error", "message": "Tin nhắn không được để trống"}), 400

    rank = get_user_rank(username)
    if rank:
        display_name = f"{username}[Top {rank}]"
    else:
        display_name = username

    with server.db_lock:
        c = server.db.cursor()
        c.execute("INSERT INTO messages (sender, message) VALUES (?, ?)", (display_name, message))
        server.db.commit()
    timestamp = datetime.now(timezone.utc).isoformat()
    socketio.emit("chat_message", {"sender": display_name, "message": message, "timestamp": timestamp})
    return jsonify({"status": "success", "message": "Tin nhắn đã được gửi"}), 200

@app.route("/get_chat_history", methods=["GET"])
@jwt_required()
def get_chat_history():
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT sender, message, timestamp FROM messages ORDER BY timestamp DESC LIMIT 50")
        messages = [{"sender": row[0], "message": row[1], "timestamp": row[2]} for row in c.fetchall()]
        return jsonify({"status": "success", "chat_history": messages[::-1]}), 200

@app.route("/get_game_history", methods=["GET"])
@jwt_required()
def get_game_history():
    game = request.args.get("game", "taixiu")
    limit = request.args.get("limit", 8, type=int)
    if limit <= 0:
        return jsonify({"status": "error", "message": "Limit phải lớn hơn 0"}), 400
    
    try:
        with server.db_lock:
            c = server.db.cursor()
            c.execute("""
                SELECT session_id, result 
                FROM game_results 
                WHERE game = ? 
                ORDER BY session_id DESC 
                LIMIT ?
            """, (game, limit))
            rows = c.fetchall()
            logger.info(f"Retrieved {len(rows)} results for {game} from game_results table")

            history = []
            valid_baucua = ["Bầu", "Cua", "Tôm", "Cá", "Gà", "Nai"]

            for session_id, result_str in rows:
                try:
                    if result_str.startswith("("):
                        result_data = eval(result_str)
                        if game == "taixiu":
                            result, dice = result_data
                            total = sum(dice)
                            history.append({
                                "session_id": session_id,
                                "result": result,
                                "details": dice,
                                "total": total
                            })
                        elif game == "chanle":
                            result, num = result_data
                            history.append({
                                "session_id": session_id,
                                "result": result,
                                "details": num
                            })
                        elif game == "baucua":
                            result, _ = result_data
                            if result in valid_baucua:
                                history.append({
                                    "session_id": session_id,
                                    "result": result
                                })
                            else:
                                logger.warning(f"Invalid baucua result in session #{session_id}: {result}")
                    else:
                        if game == "baucua" and result_str in valid_baucua:
                            history.append({
                                "session_id": session_id,
                                "result": result_str
                            })
                        else:
                            logger.warning(f"Unexpected result format for {game} in session #{session_id}: {result_str}")
                except Exception as e:
                    logger.error(f"Error parsing result for session #{session_id}: {result_str}, error: {str(e)}")
                    if game == "baucua" and result_str in valid_baucua:
                        history.append({
                            "session_id": session_id,
                            "result": result_str
                        })

            history = history[::-1]
            logger.info(f"Returning {len(history)} history entries for {game}")
            return jsonify({"status": "success", "history": history}), 200

    except sqlite3.OperationalError as e:
        logger.error("Database error in get_game_history: %s", str(e))
        return jsonify({"status": "error", "message": "Lỗi cơ sở dữ liệu, vui lòng thử lại sau"}), 500

@app.route("/get_top_rich", methods=["GET"])
@jwt_required()
def get_top_rich():
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT username, coins FROM players ORDER BY coins DESC LIMIT 10")
        top_players = [{"username": row[0], "coins": row[1]} for row in c.fetchall()]
        return jsonify({"status": "success", "top_players": top_players}), 200

@app.route("/redeem_gifcode", methods=["POST"])
@jwt_required()
def redeem_gifcode():
    username = get_jwt_identity()
    data = request.get_json()
    code = data.get("code")
    if not code:
        return jsonify({"status": "error", "message": "Mã gifcode không được để trống"}), 400
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT coins, quantity, used_count, used_by FROM giftcodes WHERE code = ?", (code,))
        giftcode = c.fetchone()
        if not giftcode:
            return jsonify({"status": "error", "message": "Mã gifcode không tồn tại"}), 404
        coins, quantity, used_count, used_by = giftcode
        if used_count >= quantity:
            return jsonify({"status": "error", "message": "Mã gifcode đã hết lượt sử dụng"}), 400
        if used_by and username in used_by.split(","):
            return jsonify({"status": "error", "message": "Bạn đã sử dụng mã này rồi"}), 400
        c.execute("UPDATE giftcodes SET used_count = used_count + 1, used_by = CASE WHEN used_by IS NULL THEN ? ELSE used_by || ',' || ? END WHERE code = ?",
                  (username, username, code))
        c.execute("UPDATE players SET coins = coins + ? WHERE username = ?", (coins, username))
        server.db.commit()
        return jsonify({"status": "success", "message": f"Đổi mã thành công, nhận {coins:,} xu!"}), 200


def check_admin():
    username = get_jwt_identity()
    if username != "admin":
        return False
    return True

@app.route("/admin/fix_result", methods=["POST"])
@jwt_required()
def admin_fix_result():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    data = request.get_json()
    game = data.get("game")
    result = data.get("result")
    session_id = data.get("session_id")
    if game not in server.rooms:
        return jsonify({"status": "error", "message": "Trò chơi không hợp lệ"}), 400
    if session_id != server.session_id:
        return jsonify({"status": "error", "message": "Phiên không hợp lệ"}), 400
    valid_results = {
        "taixiu": ["Tài", "Xỉu"],
        "chanle": ["Chẵn", "Lẻ"],
        "baucua": ["Bầu", "Cua", "Tôm", "Cá", "Gà", "Nai"]
    }
    if result not in valid_results[game]:
        return jsonify({"status": "error", "message": "Kết quả không hợp lệ"}), 400
    server.rooms[game].fixed_result = result
    log_admin_action(get_jwt_identity(), "Fix Result", f"Game: {game}, Result: {result}, Session: {session_id}")
    return jsonify({"status": "success", "message": f"Cố định kết quả {game} thành {result} cho phiên {session_id}"}), 200

@app.route("/admin/create_gifcode", methods=["POST"])
@jwt_required()
def admin_create_gifcode():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    data = request.get_json()
    code = data.get("code")
    coins = data.get("coins")
    quantity = data.get("quantity")
    if not code or not isinstance(coins, int) or not isinstance(quantity, int) or coins <= 0 or quantity <= 0:
        return jsonify({"status": "error", "message": "Thông tin không hợp lệ"}), 400
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT code FROM giftcodes WHERE code = ?", (code,))
        if c.fetchone():
            return jsonify({"status": "error", "message": "Mã gifcode đã tồn tại"}), 400
        c.execute("INSERT INTO giftcodes (code, coins, quantity) VALUES (?, ?, ?)", (code, coins, quantity))
        server.db.commit()
    log_admin_action(get_jwt_identity(), "Create Gifcode", f"Code: {code}, Coins: {coins}, Quantity: {quantity}")
    return jsonify({"status": "success", "message": f"Tạo mã gifcode {code} thành công!"}), 200

@app.route("/admin/edit_gifcode", methods=["POST"])
@jwt_required()
def admin_edit_gifcode():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    data = request.get_json()
    code = data.get("code")
    coins = data.get("coins")
    quantity = data.get("quantity")
    if not code or not isinstance(coins, int) or not isinstance(quantity, int) or coins <= 0 or quantity <= 0:
        return jsonify({"status": "error", "message": "Thông tin không hợp lệ"}), 400
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT code FROM giftcodes WHERE code = ?", (code,))
        if not c.fetchone():
            return jsonify({"status": "error", "message": "Mã gifcode không tồn tại"}), 404
        c.execute("UPDATE giftcodes SET coins = ?, quantity = ? WHERE code = ?", (coins, quantity, code))
        server.db.commit()
    log_admin_action(get_jwt_identity(), "Edit Gifcode", f"Code: {code}, New Coins: {coins}, New Quantity: {quantity}")
    return jsonify({"status": "success", "message": f"Chỉnh sửa mã gifcode {code} thành công!"}), 200

@app.route("/admin/delete_gifcode", methods=["POST"])
@jwt_required()
def admin_delete_gifcode():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    data = request.get_json()
    code = data.get("code")
    if not code:
        return jsonify({"status": "error", "message": "Mã gifcode không được để trống"}), 400
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT code FROM giftcodes WHERE code = ?", (code,))
        if not c.fetchone():
            return jsonify({"status": "error", "message": "Mã gifcode không tồn tại"}), 404
        c.execute("DELETE FROM giftcodes WHERE code = ?", (code,))
        server.db.commit()
    log_admin_action(get_jwt_identity(), "Delete Gifcode", f"Code: {code}")
    return jsonify({"status": "success", "message": f"Xóa mã gifcode {code} thành công!"}), 200

@app.route("/admin/list_giftcodes", methods=["GET"])
@jwt_required()
def admin_list_giftcodes():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT code, coins, quantity, used_count, used_by, created_at FROM giftcodes ORDER BY created_at DESC")
        giftcodes = [
            {
                "code": row[0],
                "coins": row[1],
                "quantity": row[2],
                "used_count": row[3],
                "used_by": row[4],
                "created_at": row[5]
            } for row in c.fetchall()
        ]
    log_admin_action(get_jwt_identity(), "List Giftcodes", f"Retrieved {len(giftcodes)} giftcodes")
    return jsonify({"status": "success", "giftcodes": giftcodes}), 200

@app.route("/admin/set_coins", methods=["POST"])
@jwt_required()
def admin_set_coins():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    data = request.get_json()
    username = data.get("username")
    coins = data.get("coins")
    if not username or not isinstance(coins, int) or coins < 0:
        return jsonify({"status": "error", "message": "Thông tin không hợp lệ"}), 400
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT username FROM players WHERE username = ?", (username,))
        if not c.fetchone():
            return jsonify({"status": "error", "message": "Người chơi không tồn tại"}), 404
        c.execute("UPDATE players SET coins = ? WHERE username = ?", (coins, username))
        server.db.commit()
    log_admin_action(get_jwt_identity(), "Set Coins", f"Username: {username}, Coins: {coins}")
    return jsonify({"status": "success", "message": f"Đặt số xu cho {username} thành {coins:,} xu!"}), 200

@app.route("/admin/ban_player", methods=["POST"])
@jwt_required()
def admin_ban_player():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    data = request.get_json()
    username = data.get("username")
    if not username:
        return jsonify({"status": "error", "message": "Tên người chơi không được để trống"}), 400
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT username FROM players WHERE username = ?", (username,))
        if not c.fetchone():
            return jsonify({"status": "error", "message": "Người chơi không tồn tại"}), 404
        c.execute("UPDATE players SET banned = 1 WHERE username = ?", (username,))
        server.db.commit()
    log_admin_action(get_jwt_identity(), "Ban Player", f"Username: {username}")
    return jsonify({"status": "success", "message": f"Cấm người chơi {username} thành công!"}), 200

@app.route("/admin/unban_player", methods=["POST"])
@jwt_required()
def admin_unban_player():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    data = request.get_json()
    username = data.get("username")
    if not username:
        return jsonify({"status": "error", "message": "Tên người chơi không được để trống"}), 400
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT username FROM players WHERE username = ?", (username,))
        if not c.fetchone():
            return jsonify({"status": "error", "message": "Người chơi không tồn tại"}), 404
        c.execute("UPDATE players SET banned = 0 WHERE username = ?", (username,))
        server.db.commit()
    log_admin_action(get_jwt_identity(), "Unban Player", f"Username: {username}")
    return jsonify({"status": "success", "message": f"Mở cấm người chơi {username} thành công!"}), 200

@app.route("/admin/session_result", methods=["GET"])
@jwt_required()
def admin_session_result():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    session_id = request.args.get("session_id", type=int)
    if not session_id:
        return jsonify({"status": "error", "message": "Số phiên không hợp lệ"}), 400
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT game, result FROM game_results WHERE session_id = ?", (session_id,))
        game_results = c.fetchall()
        results = []
        for game, result_str in game_results:
            c.execute("SELECT COUNT(*) FROM bets WHERE session_id = ? AND game = ?", (session_id, game))
            bet_count = c.fetchone()[0]
            try:
                result_data = eval(result_str)
                if game == "taixiu":
                    result, dice = result_data
                    results.append({"game": game, "result": f"{result} (Dice: {dice}, Total: {sum(dice)})", "bets": bet_count})
                elif game == "chanle":
                    result, num = result_data
                    results.append({"game": game, "result": f"{result} (Number: {num})", "bets": bet_count})
                elif game == "baucua":
                    result, _ = result_data
                    results.append({"game": game, "result": result, "bets": bet_count})
            except Exception as e:
                logger.error("Error parsing session result: %s, error: %s", result_str, str(e))
                results.append({"game": game, "result": result_str, "bets": bet_count})
    log_admin_action(get_jwt_identity(), "View Session Result", f"Session: {session_id}")
    return jsonify({"status": "success", "results": results}), 200

@app.route("/admin/list_users", methods=["GET"])
@jwt_required()
def admin_list_users():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT username, coins, exp, level, wins, banned FROM players ORDER BY coins DESC")
        users = [
            {
                "username": row[0],
                "coins": row[1],
                "exp": row[2],
                "level": row[3],
                "wins": row[4],
                "banned": bool(row[5])
            } for row in c.fetchall()
        ]
    log_admin_action(get_jwt_identity(), "List Users", f"Retrieved {len(users)} users")
    return jsonify({"status": "success", "users": users}), 200

@app.route("/admin/reset_user_stats", methods=["POST"])
@jwt_required()
def admin_reset_user_stats():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    data = request.get_json()
    username = data.get("username")
    if not username:
        return jsonify({"status": "error", "message": "Tên người chơi không được để trống"}), 400
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT username FROM players WHERE username = ?", (username,))
        if not c.fetchone():
            return jsonify({"status": "error", "message": "Người chơi không tồn tại"}), 404
        c.execute("UPDATE players SET coins = 100000, exp = 0, level = 1, wins = 0 WHERE username = ?", (username,))
        server.db.commit()
    log_admin_action(get_jwt_identity(), "Reset User Stats", f"Username: {username}")
    return jsonify({"status": "success", "message": f"Đặt lại thông tin người chơi {username} thành công!"}), 200

@app.route("/admin/delete_user", methods=["POST"])
@jwt_required()
def admin_delete_user():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    data = request.get_json()
    username = data.get("username")
    if not username:
        return jsonify({"status": "error", "message": "Tên người chơi không được để trống"}), 400
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT username FROM players WHERE username = ?", (username,))
        if not c.fetchone():
            return jsonify({"status": "error", "message": "Người chơi không tồn tại"}), 404
        c.execute("DELETE FROM players WHERE username = ?", (username,))
        c.execute("DELETE FROM bets WHERE username = ?", (username,))
        server.db.commit()
    log_admin_action(get_jwt_identity(), "Delete User", f"Username: {username}")
    return jsonify({"status": "success", "message": f"Xóa người chơi {username} thành công!"}), 200

@app.route("/admin/current_bets", methods=["GET"])
@jwt_required()
def admin_current_bets():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    session_id = server.session_id
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT username, game, amount, choice FROM bets WHERE session_id = ? AND pending = 1",
                  (session_id,))
        bets = [
            {
                "username": row[0],
                "game": row[1],
                "amount": row[2],
                "choice": row[3]
            } for row in c.fetchall()
        ]
    log_admin_action(get_jwt_identity(), "View Current Bets", f"Session: {session_id}, Bets: {len(bets)}")
    return jsonify({"status": "success", "session_id": session_id, "bets": bets}), 200

@app.route("/admin/cancel_bets", methods=["POST"])
@jwt_required()
def admin_cancel_bets():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    session_id = server.session_id
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT username, game, amount FROM bets WHERE session_id = ? AND pending = 1",
                  (session_id,))
        bets = c.fetchall()
        for username, game, amount in bets:
            c.execute("UPDATE players SET coins = coins + ? WHERE username = ?", (amount, username))
            c.execute("DELETE FROM bets WHERE session_id = ? AND username = ? AND game = ? AND pending = 1",
                      (session_id, username, game))
            if game in server.rooms:
                server.rooms[game].clear_bets()
        server.db.commit()
    log_admin_action(get_jwt_identity(), "Cancel Bets", f"Session: {session_id}, Bets Canceled: {len(bets)}")
    return jsonify({"status": "success", "message": f"Hủy tất cả cược trong phiên {session_id} thành công!"}), 200

@app.route("/admin/pause_game", methods=["POST"])
@jwt_required()
def admin_pause_game():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    data = request.get_json()
    game = data.get("game")
    if game not in server.rooms:
        return jsonify({"status": "error", "message": "Trò chơi không hợp lệ"}), 400
    server.rooms[game].paused = True
    log_admin_action(get_jwt_identity(), "Pause Game", f"Game: {game}")
    return jsonify({"status": "success", "message": f"Tạm dừng trò chơi {game} thành công!"}), 200

@app.route("/admin/resume_game", methods=["POST"])
@jwt_required()
def admin_resume_game():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    data = request.get_json()
    game = data.get("game")
    if game not in server.rooms:
        return jsonify({"status": "error", "message": "Trò chơi không hợp lệ"}), 400
    server.rooms[game].paused = False
    log_admin_action(get_jwt_identity(), "Resume Game", f"Game: {game}")
    return jsonify({"status": "success", "message": f"Tiếp tục trò chơi {game} thành công!"}), 200

@app.route("/admin/server_status", methods=["GET"])
@jwt_required()
def admin_server_status():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT COUNT(*) FROM players")
        total_users = c.fetchone()[0]
        c.execute("SELECT SUM(amount) FROM bets")
        total_bets_amount = c.fetchone()[0] or 0
    status = {
        "uptime": (datetime.now(timezone.utc) - server_start_time).total_seconds(),
        "active_users": len(server.active_connections),
        "total_users": total_users,
        "total_bets_amount": total_bets_amount,
        "current_session": server.session_id
    }
    log_admin_action(get_jwt_identity(), "View Server Status", f"Status: {status}")
    return jsonify({"status": "success", "server_status": status}), 200

@app.route("/admin/export_session", methods=["GET"])
@jwt_required()
def admin_export_session():
    if not check_admin():
        return jsonify({"status": "error", "message": "Chỉ admin mới có quyền thực hiện hành động này"}), 403
    session_id = request.args.get("session_id", type=int)
    if not session_id:
        return jsonify({"status": "error", "message": "Số phiên không hợp lệ"}), 400
    with server.db_lock:
        c = server.db.cursor()
        c.execute("SELECT username, game, amount, choice, result, win FROM bets WHERE session_id = ?",
                  (session_id,))
        bets = c.fetchall()
        if not bets:
            return jsonify({"status": "error", "message": "Không có dữ liệu cho phiên này"}), 404
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Username", "Game", "Amount", "Choice", "Result", "Win"])
        for bet in bets:
            writer.writerow(bet)
        csv_data = output.getvalue()
        output.close()
    log_admin_action(get_jwt_identity(), "Export Session", f"Session: {session_id}, Bets Exported: {len(bets)}")
    return jsonify({"status": "success", "csv_data": csv_data}), 200

if __name__ == "__main__":
    try:
        socketio.run(app, host=config["ip"], port=config["port"])
    except Exception as e:
        logger.error("Server failed to start: %s", str(e))