import os
import psutil
import time
import datetime
import win32gui
import win32process
import logging
import win32console
import pyautogui
from pywinauto import Application

# Đường dẫn thư mục chứa file cấu hình trên mạng
CONFIG_PATH = r"\\10.0.0.125\\9.2. dùng chung\\3. ERP-KPI-TRIEN KHAI\\ERP_Manager\\Check New App"

# Đường dẫn file log
LOG_FILE_PATH = os.path.join(CONFIG_PATH, "Log_TN.txt")  # Lịch sử duyệt web
LOG_BLOCK = os.path.join(CONFIG_PATH, "Log_BLOCK.txt")   # Web bị chặn
LOG_APPS = os.path.join(CONFIG_PATH, "Log_APPS.txt")     # Ứng dụng đang chạy

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Hàm đọc danh sách từ file, nếu lỗi sẽ dùng danh sách mặc định
def load_list_from_file(filename, default_list):
    file_path = os.path.join(CONFIG_PATH, filename)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            logging.error(f"Lỗi đọc file {filename}: {str(e)}")
    return default_list

# Biến danh sách chặn
BLOCKED_BROWSERS, BROWSERS, BLOCKED_APPS, BLOCKED_SITES = [], [], [], []

def update_blocked_lists():
    """Cập nhật danh sách chặn từ file mỗi 10 giây"""
    global BLOCKED_BROWSERS, BROWSERS, BLOCKED_APPS, BLOCKED_SITES
    BLOCKED_BROWSERS = load_list_from_file("blocked_browsers.txt", ["coccoc.exe", "browser.exe"])
    BROWSERS = load_list_from_file("browsers.txt", ["chrome.exe", "msedge.exe", "firefox.exe"])
    BLOCKED_APPS = load_list_from_file("blocked_apps.txt", ["Zalo.exe", "Discord.exe"])
    BLOCKED_SITES = load_list_from_file("blocked_sites.txt", ["facebook.com", "zalo.me", "discord"])
    logging.info("Cập nhật danh sách chặn thành công.")

# Khung giờ chặn
BLOCK_TIME_RANGES = [("07:30", "11:45"), ("12:45", "17:00")]

def is_block_time():
    """Kiểm tra xem có trong thời gian bị chặn không"""
    now = datetime.datetime.now().time()
    for start, end in BLOCK_TIME_RANGES:
        if datetime.datetime.strptime(start, "%H:%M").time() <= now <= datetime.datetime.strptime(end, "%H:%M").time():
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
            app = Application(backend="uia").connect(process=pid, timeout=1)
            dlg = app.top_window()
            url = dlg.child_window(title_re=".*", control_type="Edit").get_value().lower()
            return title, url, hwnd
    except:
        return "", "", None
    return "", "", None

def log_visited_url(url):
    """Ghi log tất cả URL mà nhân viên truy cập, không trùng lặp"""
    try:
        if not os.path.exists(LOG_FILE_PATH):
            with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
                f.write("Danh sách các URL đã truy cập:\n")

        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            logged_urls = f.readlines()

        if url + "\n" not in logged_urls:
            with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(url + "\n\n")
    except Exception as e:
        logging.error(f"Lỗi ghi log URL: {str(e)}")

def log_running_apps():
    """Ghi log danh sách ứng dụng đang chạy (không trùng lặp)"""
    try:
        running_apps = set(proc.name() for proc in psutil.process_iter(attrs=['name']))
        
        # Đọc danh sách app đã ghi trước đó để tránh trùng lặp
        if os.path.exists(LOG_APPS):
            with open(LOG_APPS, "r", encoding="utf-8") as f:
                logged_apps = set(line.strip() for line in f.readlines())
        else:
            logged_apps = set()

        # Ghi vào file nếu có app mới
        new_apps = running_apps - logged_apps
        if new_apps:
            with open(LOG_APPS, "a", encoding="utf-8") as f:
                for app in new_apps:
                    f.write(f"{datetime.datetime.now()} - {app}\n")
    except Exception as e:
        logging.error(f"Lỗi ghi log ứng dụng đang chạy: {str(e)}")

def close_tab(hwnd):
    """Đóng tab trình duyệt đang vi phạm bằng Ctrl + W"""
    try:
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "w")
    except:
        pass

def open_redirect_page(hwnd):
    """Mở trang chuyển hướng"""
    try:
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "t")
        time.sleep(0.5)
        pyautogui.typewrite("http://10.0.0.3:8009/")
        pyautogui.press("enter")
    except:
        pass

def kill_blocked_apps():
    """Tắt ứng dụng trong danh sách BLOCKED_APPS"""
    for proc in psutil.process_iter():
        try:
            if proc.name() in BLOCKED_APPS:
                proc.kill()
        except:
            pass

def kill_blocked_browsers():
    """Tắt trình duyệt bị chặn"""
    for proc in psutil.process_iter():
        try:
            if proc.name().lower() in BLOCKED_BROWSERS:
                proc.kill()
        except:
            pass

# Bỏ ẩn console (xóa hoặc comment lại nếu muốn ẩn)
# def hide_console():
#     window = win32console.GetConsoleWindow()
#     if window:
#         win32gui.ShowWindow(window, 0)

# Vòng lặp chính
counter = 0

while True:
    try:
        if is_block_time():
            if counter % 5 == 0:  # Mỗi 10 giây cập nhật danh sách chặn & log ứng dụng đang chạy
                update_blocked_lists()
                log_running_apps()

            kill_blocked_browsers()  # Kiểm tra trình duyệt bị chặn

            title, url, browser_hwnd = get_browser_info()

            if url:
                log_visited_url(url)  # Ghi log URL đã truy cập

            if any(site in url for site in BLOCKED_SITES) or any(tit in title for tit in BLOCKED_SITES):
                close_tab(browser_hwnd)
                open_redirect_page(browser_hwnd)

            kill_blocked_apps()  # Kiểm tra ứng dụng bị chặn

        counter += 1
        time.sleep(2)  # Kiểm tra mỗi 2 giây

    except Exception as e:
        logging.error(f"Lỗi vòng lặp chính: {str(e)}")
        time.sleep(5)  # Nếu lỗi, chờ 5 giây rồi thử lại
