import os
import psutil
import time
import datetime
import win32gui
import win32process
import logging
import win32console
import pygetwindow as gw
import pyautogui
from pywinauto import Application

# Đường dẫn thư mục chứa file cấu hình trên mạng
CONFIG_PATH = r"\\10.0.0.125\\9.2. dùng chung\\3. ERP-KPI-TRIEN KHAI\\ERP_Manager\\Check New App"

# Đường dẫn file log lưu lịch sử duyệt web
LOG_FILE_PATH = os.path.join(CONFIG_PATH, "Log_TN.txt")
LOG_BLOCK = os.path.join(CONFIG_PATH, "Log_BLOCK.txt")

# Cấu hình log file để ghi thông tin chương trình
# LOG_FILE = "blocked_sites.log"
# logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(message)s")

# Hàm đọc danh sách từ file, nếu file không tồn tại thì dùng danh sách mặc định
def load_list_from_file(filename, default_list):
    file_path = os.path.join(CONFIG_PATH, filename)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            logging.error(f"Lỗi đọc file {filename}: {str(e)}")
    return default_list

# Biến toàn cục để lưu danh sách
BLOCKED_BROWSERS, BROWSERS, BLOCKED_APPS, BLOCKED_SITES = [], [], [], []

def update_blocked_lists():
    """Cập nhật danh sách chặn từ file mỗi 10 giây"""
    global BLOCKED_BROWSERS, BROWSERS, BLOCKED_APPS, BLOCKED_SITES
    BLOCKED_BROWSERS = load_list_from_file("blocked_browsers.txt", ["coccoc.exe", "browser.exe"])
    BROWSERS = load_list_from_file("browsers.txt", ["chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe", "safari.exe", "vivaldi.exe", "torch.exe"])
    BLOCKED_APPS = load_list_from_file("blocked_apps.txt", ["Zalo.exe", "Discord.exe"])
    BLOCKED_SITES = load_list_from_file("blocked_sites.txt", ["facebook.com", "www.facebook.com", "zalo.me", "zalo", "truyen", "peanut", "discord", "facebook"])
    logging.info("Cập nhật danh sách chặn thành công.")

# Cập nhật danh sách lần đầu
update_blocked_lists()

# Khung giờ chặn (dạng HH:MM)
BLOCK_TIME_RANGES = [
    ("07:30", "11:45"),
    ("12:45", "17:00"),
]

# Trang chuyển hướng khi chặn
REDIRECT_URL = "http://10.0.0.3:8009/"

def is_block_time():
    """Kiểm tra xem có trong thời gian bị chặn không"""
    now = datetime.datetime.now().time()
    for start, end in BLOCK_TIME_RANGES:
        start_time = datetime.datetime.strptime(start, "%H:%M").time()
        end_time = datetime.datetime.strptime(end, "%H:%M").time()
        if start_time <= now <= end_time:
            return True
    return False

def get_browser_info():
    """Lấy tiêu đề và URL của trình duyệt cùng với PID"""
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)

        if proc.name().lower() in BROWSERS:
            title = win32gui.GetWindowText(hwnd).lower()
            
            # Lấy URL từ thanh địa chỉ trình duyệt
            app = Application(backend="uia").connect(process=pid, timeout=1)
            dlg = app.top_window()
            url = dlg.child_window(title_re=".*", control_type="Edit").get_value().lower()
            
            return title, url, hwnd
    except:
        return "", "", None
    return "", "", None

def log_visited_url(url):
    """Ghi log tất cả URL mà người dùng truy cập, không trùng lặp"""
    try:
        if not os.path.exists(LOG_FILE_PATH):
            with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
                f.write("Danh sách các URL đã truy cập:\n")

        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            logged_urls = f.readlines()

        if url + "\n" not in logged_urls:  # Kiểm tra xem URL đã tồn tại chưa
            with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(url + "\n\n")
            logging.info(f"Ghi log URL mới: {url}")

    except Exception as e:
        logging.error(f"Lỗi ghi log URL: {str(e)}")

def close_tab(hwnd):
    """Đóng tab trình duyệt đang vi phạm bằng Ctrl + W"""
    try:
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "w")
        logging.info(f"Đã đóng tab có hwnd: {hwnd}")
    except:
        pass

def open_redirect_page(hwnd):
    """Mở tab mới với trang chuyển hướng bằng Ctrl + T"""
    try:
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "t")
        time.sleep(0.5)
        pyautogui.typewrite(REDIRECT_URL)
        pyautogui.press("enter")
        logging.info(f"Đã mở trang chuyển hướng: {REDIRECT_URL}")
    except:
        pass

def kill_blocked_apps():
    """Tắt ứng dụng trong danh sách BLOCKED_APPS ngay lập tức"""
    for proc in psutil.process_iter():
        try:
            if proc.name() in BLOCKED_APPS:
                logging.info(f"Đã đóng ứng dụng: {proc.name()}")
                proc.kill()
        except:
            pass

def kill_blocked_browsers():
    """Tắt trình duyệt trong danh sách BLOCKED_BROWSERS ngay lập tức"""
    for proc in psutil.process_iter():
        try:
            if proc.name().lower() in BLOCKED_BROWSERS:
                logging.info(f"Phát hiện trình duyệt bị cấm: {proc.name()} → Đóng ngay!")
                proc.kill()
        except:
            pass

def hide_console():
    """Ẩn cửa sổ console khi chạy"""
    window = win32console.GetConsoleWindow()
    if window:
        win32gui.ShowWindow(window, 0)

# Ẩn cửa sổ ngay khi chạy
hide_console()

counter = 0  # Đếm số vòng lặp để cập nhật danh sách mỗi 10 giây

while True:
    if is_block_time():
        # Mỗi 10 giây cập nhật lại danh sách từ file
        if counter % 5 == 0:  # Mỗi vòng lặp mất 2 giây, 5 vòng = 10 giây
            update_blocked_lists()

        # Kiểm tra nếu trình duyệt bị chặn đang chạy → Đóng ngay
        kill_blocked_browsers()

        # Kiểm tra các trình duyệt khác
        title, url, browser_hwnd = get_browser_info()

        if url:
            log_visited_url(url)  # Ghi log URL đã truy cập

        # Kiểm tra nếu trang web hoặc tiêu đề có từ khóa cấm
        if any(site in url for site in BLOCKED_SITES) or any(tit in title for tit in BLOCKED_SITES):
            log_message = f"Phát hiện trang cấm: {url or title} → Đóng tab & chuyển hướng!"
        # Ghi vào file LOG_BLOCK.txt
            try:
                if not os.path.exists(LOG_BLOCK):
                    with open(LOG_BLOCK, "w", encoding="utf-8") as f:
                        f.write("Danh sách bị chặn:\n")
                with open(LOG_BLOCK, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.datetime.now()} - {log_message}\n")
            except Exception as e:
                logging.error(f"Lỗi ghi log vào LOG_BLOCK.txt: {str(e)}")
            close_tab(browser_hwnd)
            open_redirect_page(browser_hwnd)

        # Kiểm tra nếu ứng dụng bị chặn đang chạy
        kill_blocked_apps()

    counter += 1
    time.sleep(1)  # Kiểm tra mỗi 2 giây
