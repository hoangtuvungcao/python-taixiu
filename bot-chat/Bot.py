import requests
import time
import random
import os
import threading
import string
from queue import Queue

class AutoRegisterAndSpam:
    def __init__(self):
        self.base_url = self.load_server_config()
        self.target_accounts = 500
        self.accounts_file = "data/account/accounts.txt"
        self.accounts = self.load_accounts()
        self.is_spamming = True
        self.token_lock = threading.Lock()  # Khóa để đồng bộ truy cập token
        self.account_tokens = {}  # Lưu trữ token theo username
        self.token_queue = Queue()  # Hàng đợi để yêu cầu làm mới token (dự phòng)

        # Danh sách prefixes và suffixes để tạo username
        self.prefixes = [
            "TaiXiu", "BauCua", "ChanLe", "LuckyDice", "Game", "Bet", "Dice", "Pro", "King", "Master",
            "Gamer", "Player", "HighRoller", "Lucky", "Winner", "Rich", "ProBet", "DiceLord", "GameStar", "BetKing",
            "Super", "Mega", "Ultra", "Epic", "Golden", "Silver", "Diamond", "Platinum", "Bronze", "Iron",
            "Magic", "Thunder", "Storm", "Fire", "Ice", "Shadow", "Light", "Dark", "Sky", "Ocean"
        ]
        self.suffixes = [
            "Master", "Pro", "King", "Lord", "Star", "Winner", "Guru", "Expert", "Champ", "Hero",
            "Ace", "Boss", "Legend", "God", "Elite", "Top", "Prime", "Ninja", "Wizard", "Sniper",
            "Slayer", "Hunter", "Ruler", "Chief", "Captain", "General", "Knight", "Samurai", "Viking", "Pirate",
            "Dragon", "Phoenix", "Tiger", "Lion", "Wolf", "Bear", "Eagle", "Hawk", "Shark", "Fox"
        ]

        # Chỉ giữ 3 game: Tài Xỉu, Bầu Cua, Chẵn Lẻ
        self.games = ["Tài Xỉu", "Bầu Cua", "Chẵn Lẻ"]
        self.taixiu_choices = ["Tài", "Xỉu"]
        self.chanle_choices = ["Chẵn", "Lẻ"]
        self.baucua_choices = ["Bầu", "Cua", "Tôm", "Cá", "Gà", "Nai"]

        # Danh sách actions, emotions, money_units, streaks, feelings giữ nguyên như cũ
        self.actions = [
            "cược", "húp", "all-in", "thử", "đi", "chơi", "đặt", "vào", "đánh", "bỏ", "tăng", "giảm",
            "chốt", "xem", "theo", "bám", "đu", "call", "vô", "chơi lớn", "đặt mạnh", "đi hết", "đặt nhẹ",
            "chơi nhỏ", "đánh lớn", "vào mạnh", "đi nhẹ", "thử vận may", "đặt thử", "chơi thử", "đánh thử",
            "cược mạnh", "húp nhẹ", "đi mạnh", "chốt mạnh", "vào nhẹ", "đánh nhẹ", "thử sức", "chơi vui",
            "đặt nhanh", "vào nhanh", "chốt nhanh", "đi nhanh", "đánh nhanh", "cược nhanh", "húp nhanh",
            "chơi mạnh", "đặt chậm", "vào chậm", "chốt chậm", "đi chậm", "đánh chậm", "cược chậm", "húp chậm",
            "đặt max", "vào max", "đánh max", "chơi hết", "đặt full", "vào full", "đánh full", "thử max",
            "cược hết", "húp hết", "đi full", "chốt full", "đặt all", "vào all", "đánh all", "chơi all",
            "đặt khủng", "vào khủng", "đánh khủng", "chơi max", "đặt hết luôn", "vào hết luôn", "đánh hết luôn",
            "thử lớn", "cược lớn", "húp lớn", "đi lớn", "chốt lớn", "đặt nhỏ nhẹ", "vào nhỏ nhẹ", "đánh nhỏ nhẹ"
        ]
        self.emotions = [
            "húp nào!", "chắc chắn luôn!", "ai theo không?", "tiếc ghê!", "thắng lớn!", "thua rồi!",
            "hot lắm!", "cược nào!", "đỉnh quá!", "hên ghê!", "xui quá!", "vào đi!", "chốt đi!",
            "đỉnh thật!", "hấp dẫn ghê!", "căng thẳng quá!", "hồi hộp ghê!", "tuyệt vời!", "đi nào!",
            "chơi lớn đi!", "bình tĩnh nào!", "đỉnh của chóp!", "hết hồn!", "quá đã!", "vô đối!",
            "hên thế!", "xui thế!", "đỉnh vãi!", "hấp dẫn thật!", "căng quá!", "hồi hộp vãi!", "đã ghê!",
            "vào nhanh!", "chốt nhanh!", "đỉnh luôn!", "hấp dẫn vãi!", "căng cực!", "hồi hộp thật!",
            "tuyệt quá!", "đi thôi!", "chơi mạnh đi!", "bình tĩnh thôi!", "đỉnh thật sự!", "hết ý!",
            "quá đỉnh!", "vô địch!", "hên vãi!", "xui vãi!", "đỉnh thế!", "hấp dẫn thế!", "căng thế!",
            "hồi hộp thế!", "đã thế!", "vào ngay!", "chốt ngay!", "đỉnh vãi luôn!", "hấp dẫn vãi luôn!",
            "căng vãi luôn!", "hồi hộp vãi luôn!", "đã vãi luôn!", "tuyệt vãi luôn!", "đi ngay nào!",
            "chơi lớn ngay!", "bình tĩnh thôi!", "đỉnh quá trời!", "hết xảy!", "quá đã luôn!", "vô đối thật!",
            "ok luôn!", "chất ghê!", "đỉnh cao!", "hấp dẫn cực!", "căng như dây đàn!", "hồi hộp chết đi được!",
            "đã quá trời!", "vô địch thiên hạ!", "hên xỉu!", "xui xỉu!", "đỉnh không tưởng!", "hấp dẫn không chịu nổi!",
            "căng hết mức!", "hồi hộp muốn xỉu!", "đã không tả nổi!", "tuyệt không tưởng!", "đi luôn nào!",
            "chơi hết mình đi!", "bình tĩnh chút nào!", "đỉnh nhất quả đất!", "hết sảy!", "quá chất luôn!"
        ]
        self.money_units = ["", "k", "củ", "triệu"]
        self.streaks = [
            "", "2 ván rồi", "3 ván rồi", "4 ván rồi", "5 ván rồi", "liên tiếp", "mấy ván rồi",
            "2 lần rồi", "3 lần rồi", "4 lần rồi", "5 lần rồi", "liên tục", "mấy lần rồi",
            "2 ván liên tiếp", "3 ván liên tiếp", "4 ván liên tiếp", "5 ván liên tiếp",
            "2 lần liên tiếp", "3 lần liên tiếp", "4 lần liên tiếp", "5 lần liên tiếp",
            "2 ván liền", "3 ván liền", "4 ván liền", "5 ván liền", "2 lần liền", "3 lần liền",
            "4 lần liền", "5 lần liền", "2 ván liên tục", "3 ván liên tục", "4 ván liên tục",
            "5 ván liên tục", "2 lần liên tục", "3 lần liên tục", "4 lần liên tục", "5 lần liên tục",
            "6 ván rồi", "7 ván rồi", "8 ván rồi", "9 ván rồi", "10 ván rồi", "hơn chục ván rồi",
            "6 lần rồi", "7 lần rồi", "8 lần rồi", "9 lần rồi", "10 lần rồi", "hơn chục lần rồi",
            "6 ván liên tiếp", "7 ván liên tiếp", "8 ván liên tiếp", "9 ván liên tiếp", "10 ván liên tiếp",
            "6 lần liên tiếp", "7 lần liên tiếp", "8 lần liên tiếp", "9 lần liên tiếp", "10 lần liên tiếp",
            "6 ván liền", "7 ván liền", "8 ván liền", "9 ván liền", "10 ván liền", "hơn chục ván liền",
            "6 lần liền", "7 lần liền", "8 lần liền", "9 lần liền", "10 lần liền", "hơn chục lần liền"
        ]
        self.feelings = [
            "", "tui cảm giác", "tui thấy", "tui đoán", "tui nghĩ", "tui tin", "hình như", "chắc là",
            "có vẻ", "tui biết", "tui nghe", "tui bảo", "tui nói", "tui chắc", "tui khẳng định",
            "tui dự", "tui dự đoán", "tui nhận định", "tui phán", "tui tiên đoán", "tui linh cảm",
            "tui cảm nhận", "tui thấy thế", "tui đoán thế", "tui nghĩ thế", "tui tin thế", "hình như thế",
            "chắc là thế", "có vẻ thế", "tui biết thế", "tui nghe thế", "tui bảo thế", "tui nói thế",
            "tui chắc thế", "tui khẳng định thế", "tui dự thế", "tui dự đoán thế", "tui nhận định thế",
            "tui đoán chắc", "tui tin chắc", "tui cảm thấy", "tui thấy rõ", "tui biết chắc", "tui nghe nói",
            "tui dự là", "tui nghĩ chắc", "tui tin là", "tui thấy chắc", "tui đoán là", "tui cảm nhận là",
            "tui linh cảm là", "tui chắc chắn là", "tui khẳng định là", "tui tiên đoán là", "tui phán là",
            "tui thấy rõ ràng", "tui đoán đúng", "tui tin đúng", "tui cảm giác đúng", "tui nghĩ đúng"
        ]

        # Khởi động thread làm mới token (dự phòng)
        threading.Thread(target=self.refresh_token_worker, daemon=True).start()

    def load_server_config(self):
        config = {"ip": "127.0.0.1", "port": 9999}
        try:
            with open("data/config/config.txt", "r", encoding="utf-8") as f:
                for line in f:
                    if ":" in line:
                        key, value = line.strip().split(":", 1)
                        if key == "ip":
                            config["ip"] = value.strip()
                        elif key == "port":
                            config["port"] = int(value.strip())
        except FileNotFoundError:
            print("Không tìm thấy file config/config.txt, sử dụng mặc định ip: 127.0.0.1, port: 9999")
        return f"http://{config['ip']}:{config['port']}"

    def load_accounts(self):
        accounts = []
        if os.path.exists(self.accounts_file):
            with open(self.accounts_file, "r", encoding="utf-8") as f:
                for line in f:
                    if ":" in line:
                        username, password = line.strip().split(":", 1)
                        accounts.append({"username": username, "password": password})
        print(f"Đã tải {len(accounts)} tài khoản từ {self.accounts_file}")
        return accounts

    def save_account(self, username, password):
        with open(self.accounts_file, "a", encoding="utf-8") as f:
            f.write(f"{username}:{password}\n")
        self.accounts.append({"username": username, "password": password})

    def generate_random_username(self):
        while True:
            prefix = random.choice(self.prefixes)
            suffix = random.choice(self.suffixes)
            number = random.randint(1, 999)
            username = f"{prefix}{suffix}{number}"
            if not any(account["username"] == username for account in self.accounts):
                return username

    def generate_random_password(self):
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(8))

    def register_account(self):
        username = self.generate_random_username()
        password = self.generate_random_password()
        data = {"username": username, "password": password}
        try:
            response = requests.post(f"{self.base_url}/register", json=data, timeout=5)
            response.raise_for_status()
            if response.json().get("status") == "success":
                print(f"Đăng ký thành công: {username}:{password}")
                self.save_account(username, password)
                return True
            else:
                print(f"Đăng ký thất bại: {username} - {response.json().get('message')}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Lỗi khi đăng ký tài khoản {username}: {str(e)}")
            return False

    def login_account(self, username, password):
        data = {"username": username, "password": password}
        try:
            response = requests.post(f"{self.base_url}/login", json=data, timeout=5)
            response.raise_for_status()
            result = response.json()
            if result.get("status") == "success":
                token = result.get("access_token")
                print(f"Đăng nhập thành công: {username}")
                return token
            else:
                print(f"Đăng nhập thất bại: {username} - {result.get('message')}")
                if "Tài khoản bị cấm" in result.get("message", ""):
                    print(f"Tài khoản {username} bị cấm, bỏ qua.")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Lỗi khi đăng nhập tài khoản {username}: {str(e)}")
            return None

    def generate_random_money(self):
        unit = random.choice(self.money_units)
        if unit == "triệu" or unit == "củ":
            base_amount = random.randint(1, 1000) * 1000000
            return f"{base_amount // 1000000} {unit}"
        elif unit == "k":
            base_amount = random.randint(1, 1000) * 1000
            return f"{base_amount // 1000}k"
        else:
            base_amount = random.randint(1, 1000) * 1000
            return f"{base_amount:,}"

    def generate_random_message(self):
        game = random.choice(self.games)
        action = random.choice(self.actions)
        emotion = random.choice(self.emotions)
        money = self.generate_random_money()
        streak = random.choice(self.streaks)
        feeling = random.choice(self.feelings)
        message_type = random.randint(1, 5)

        if game == "Tài Xỉu":
            choice = random.choice(self.taixiu_choices)
            result = random.randint(3, 18)
            if message_type == 1:
                return f"{game} tui {action} {money} {choice}, {emotion}"
            elif message_type == 2:
                outcome = "thắng lớn!" if (result > 10 and choice == "Tài") or (result <= 10 and choice == "Xỉu") else "thua rồi!"
                returntalk = random.choice(self.taixiu_choices)
                return f"{game} ra {result}, {choice} {outcome}"
            elif message_type == 3:
                return f"{choice} đi anh em ơi, {feeling} {choice} {streak}, {emotion}"
            elif message_type == 4:
                return f"{feeling} {choice} {streak}, tui {action} {money} {choice}!"
            else:
                return f"{game} {streak}, tui {action} {choice}, ai theo không?"

        elif game == "Chẵn Lẻ":
            choice = random.choice(self.chanle_choices)
            result = random.randint(1, 10)
            if message_type == 1:
                return f"{game} tui {action} {money} {choice}, {emotion}"
            elif message_type == 2:
                outcome = "thắng lớn!" if (result % 2 == 0 and choice == "Chẵn") or (result % 2 != 0 and choice == "Lẻ") else "thua rồi!"
                return f"{game} ra {result}, {choice} {outcome}"
            elif message_type == 3:
                return f"{choice} đi, {feeling} {choice} {streak}, {emotion}"
            elif message_type == 4:
                return f"{feeling} {choice} {streak}, tui {action} {money} {choice}!"
            else:
                return f"{game} {streak}, tui {action} {choice}, ai theo không?"

        else:  # Bầu Cua
            choice = random.choice(self.baucua_choices)
            result = random.choice(self.baucua_choices)
            if message_type == 1:
                return f"{game} tui {action} {money} {choice}, {emotion}"
            elif message_type == 2:
                outcome = "thắng lớn!" if result == choice else "thua rồi!"
                return f"{game} ra {result}, tui {outcome}"
            elif message_type == 3:
                return f"Ai cược {choice} không, {feeling} {choice} {streak}, {emotion}"
            elif message_type == 4:
                return f"{feeling} {choice} {streak}, tui {action} {money} {choice}!"
            else:
                return f"{game} {streak}, tui {action} {choice}, ai theo không?"

    def send_message(self, token, sender, message):
        headers = {"Authorization": f"Bearer {token}"}
        data = {"message": message}
        try:
            response = requests.post(f"{self.base_url}/send_message", json=data, headers=headers, timeout=5)
            response.raise_for_status()
            print(f"Đã gửi tin nhắn: [{sender}] {message}")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print(f"Token hết hạn cho {sender}, sẽ làm mới token ngay lập tức...")
                return False
            else:
                print(f"Lỗi khi gửi tin nhắn: {str(e)}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Lỗi khi gửi tin nhắn: {str(e)}")
            return False

    def refresh_token_worker(self):
        # Giữ lại worker này như một cơ chế dự phòng, nhưng ít được sử dụng nhờ làm mới token ngay lập tức
        while self.is_spamming:
            try:
                username, password = self.token_queue.get(timeout=1)
                new_token = self.login_account(username, password)
                with self.token_lock:
                    if new_token:
                        self.account_tokens[username] = new_token
                        print(f"Đã làm mới token cho {username} từ queue")
                    else:
                        print(f"Không thể làm mới token cho {username}, xóa khỏi danh sách")
                        if username in self.account_tokens:
                            del self.account_tokens[username]
                self.token_queue.task_done()
            except Queue.Empty:
                time.sleep(0.1)  # Tránh CPU usage cao khi queue rỗng

    def spam_messages(self):
        # Đăng nhập ban đầu cho tất cả tài khoản
        for account in self.accounts[:]:  # Sao chép danh sách để tránh lỗi khi xóa
            username = account["username"]
            password = account["password"]
            token = self.login_account(username, password)
            if token:
                with self.token_lock:
                    self.account_tokens[username] = token
            else:
                self.accounts.remove(account)  # Xóa tài khoản không đăng nhập được

        if not self.account_tokens:
            print("Không có tài khoản nào đăng nhập thành công, dừng spam.")
            return

        print("Bắt đầu spam tin nhắn với delay ngẫu nhiên 1-3 giây...")
        while self.is_spamming:
            with self.token_lock:
                if not self.account_tokens:
                    print("Không còn tài khoản nào hoạt động, dừng spam.")
                    break
                username = random.choice(list(self.account_tokens.keys()))
                token = self.account_tokens[username]
            
            message = self.generate_random_message()
            success = self.send_message(token, username, message)
            
            # Làm mới token ngay lập tức bất kể gửi thành công hay thất bại
            password = self.accounts[[acc["username"] for acc in self.accounts].index(username)]["password"]
            new_token = self.login_account(username, password)
            with self.token_lock:
                if new_token:
                    self.account_tokens[username] = new_token
                    print(f"Đã làm mới token cho {username} sau khi gửi tin nhắn")
                else:
                    print(f"Không thể làm mới token cho {username}, xóa khỏi danh sách")
                    if username in self.account_tokens:
                        del self.account_tokens[username]
                    continue  # Bỏ qua nếu không làm mới được token

            # Nếu gửi thất bại, thử lại với token mới
            if not success:
                with self.token_lock:
                    if username in self.account_tokens:
                        token = self.account_tokens[username]
                        self.send_message(token, username, message)  # Thử lại với token mới
            
            delay = random.uniform(0.1, 1.5)
            time.sleep(delay)

    def register_accounts(self):
        while len(self.accounts) < self.target_accounts:
            if self.register_account():
                print(f"Đã tạo {len(self.accounts)}/{self.target_accounts} tài khoản")
            else:
                print("Thử lại sau 5 giây...")
                time.sleep(5)

    def start_spamming(self):
        spam_thread = threading.Thread(target=self.spam_messages, daemon=True)
        spam_thread.start()
        return spam_thread

if __name__ == "__main__":
    spammer = AutoRegisterAndSpam()
    if len(spammer.accounts) < spammer.target_accounts:
        print(f"Chưa đủ {spammer.target_accounts} tài khoản, bắt đầu đăng ký...")
        spammer.register_accounts()
    else:
        print(f"Đã có đủ {spammer.target_accounts} tài khoản, chuyển sang spam...")

    spam_thread = spammer.start_spamming()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Dừng spam tin nhắn...")
        spammer.is_spamming = False
        spam_thread.join()