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

# Đường dẫn file log trên mạng
LOG_FILE_PATH = r"\\10.0.0.125\\4.3. erp-web\\Check New App\\Log_TN.txt"

# Cấu hình log file để ghi thông tin chương trình
LOG_FILE = "blocked_sites.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(message)s")

# Danh sách trình duyệt cần kiểm tra (chặn tab vi phạm)
BROWSERS = [
    "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe", 
    "safari.exe", "vivaldi.exe", "torch.exe", "browser.exe"
]

# Trình duyệt Cốc Cốc cần chặn hoàn toàn
BLOCKED_BROWSERS = ["coccoc.exe", "browser.exe"]

# Ứng dụng cần chặn (Zalo App)
BLOCKED_APPS = ["Zalo.exe", "Discord.exe"]

# Từ khóa trong URL & tiêu đề cần chặn
BLOCKED_SITES = ["facebook.com", "www.facebook.com", "zalo.me", "zalo", "truyen", "peanut", "discord", "facebook"]

# Từ khóa liên quan đến Zalo Extension (chỉ check trên trình duyệt)
BLOCKED_EXTENSIONS = ["zalo", "chat zalo", "zalo extension", "zalo web"]

# Khung giờ chặn (dạng HH:MM)
BLOCK_TIME_RANGES = [
    ("07:30", "11:45"),
    ("12:45", "17:00"),
]

# Trang chuyển hướng khi chặn
REDIRECT_URL = "https://www.youtube.com/watch?v=wa8D6KwQ3C8"

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

def detect_zalo_extension():
    """Kiểm tra nếu Zalo Extension đang mở trên đúng trình duyệt"""
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'].lower() in BROWSERS:
                browser_pid = proc.info['pid']
                windows = gw.getWindowsWithTitle("")
                for win in windows:
                    _, win_pid = win32process.GetWindowThreadProcessId(win._hWnd)
                    if win_pid == browser_pid and any(ext in win.title.lower() for ext in BLOCKED_EXTENSIONS):
                        logging.info(f"Phát hiện Zalo Extension trên trình duyệt: {win.title} → Đóng tab!")
                        return win._hWnd
    except:
        return None
    return None

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
                f.write(url + "\n")
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

def kill_zalo():
    """Tắt ứng dụng Zalo & Discord ngay lập tức"""
    for proc in psutil.process_iter():
        try:
            if proc.name() in BLOCKED_APPS:
                logging.info(f"Đã đóng ứng dụng: {proc.name()}")
                proc.kill()
        except:
            pass

def kill_coccoc():
    """Tắt Cốc Cốc ngay lập tức"""
    for proc in psutil.process_iter():
        try:
            if proc.name().lower() in BLOCKED_BROWSERS:
                logging.info(f"Phát hiện Cốc Cốc: {proc.name()} → Đóng ngay!")
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

while True:
    if is_block_time():
        # Kiểm tra nếu Cốc Cốc đang chạy → Đóng ngay
        kill_coccoc()

        # Kiểm tra các trình duyệt khác
        title, url, browser_hwnd = get_browser_info()

        if url:
            log_visited_url(url)  # Ghi log URL đã truy cập

        # Kiểm tra nếu trang web hoặc tiêu đề có từ khóa cấm
        if any(site in url for site in BLOCKED_SITES) or any(tit in title for tit in BLOCKED_SITES):
            logging.info(f"Phát hiện trang cấm: {url or title} → Đóng tab & chuyển hướng!")
            close_tab(browser_hwnd)
            open_redirect_page(browser_hwnd)

        # Kiểm tra nếu có Zalo Extension trên trình duyệt
        extension_hwnd = detect_zalo_extension()
        if extension_hwnd:
            close_tab(extension_hwnd)
            open_redirect_page(extension_hwnd)

        # Kiểm tra nếu Zalo App hoặc Discord đang chạy
        kill_zalo()
    
    time.sleep(2)  # Kiểm tra mỗi 2 giây
