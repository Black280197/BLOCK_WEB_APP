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

# Cấu hình file log
LOG_FILE = "blocked_sites.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(message)s")

# Danh sách trình duyệt cần kiểm tra
BROWSERS = [
    "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe", 
    "coccoc.exe", "safari.exe", "vivaldi.exe", "torch.exe", "browser.exe"
]

# Ứng dụng cần chặn (Zalo App)
BLOCKED_APPS = ["Zalo.exe"]

# Từ khóa trong URL & tiêu đề cần chặn
BLOCKED_SITES = ["facebook.com", "www.facebook.com", "zalo.me", "zalo", "truyen", "peanut"]

# Từ khóa liên quan đến Zalo Extension (chỉ check trên trình duyệt)
BLOCKED_EXTENSIONS = ["zalo", "chat zalo", "zalo extension", "zalo web"]

# Khung giờ chặn (dạng HH:MM)
BLOCK_TIME_RANGES = [
    ("07:30", "11:45"),
    ("12:45", "17:00"),
]

# Trang chuyển hướng khi chặn
# REDIRECT_URL = "http://10.0.0.3:8009/"
REDIRECT_URL = "https://www.youtube.com/watch?v=aHHZEIXgYwA"

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

def close_tab(hwnd):
    """Đóng tab trình duyệt đang vi phạm bằng Ctrl + W"""
    try:
        win32gui.SetForegroundWindow(hwnd)  # Chuyển cửa sổ thành Active Window
        time.sleep(0.5)  # Chờ một chút để tránh lỗi
        pyautogui.hotkey("ctrl", "w")  # Gửi phím tắt Ctrl + W để đóng tab
        logging.info(f"Đã đóng tab có hwnd: {hwnd}")
    except:
        pass

def open_redirect_page(hwnd):
    """Mở tab mới với trang chuyển hướng bằng Ctrl + T"""
    try:
        win32gui.SetForegroundWindow(hwnd)  # Chuyển cửa sổ thành Active Window
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "t")  # Mở tab mới
        time.sleep(0.5)
        pyautogui.typewrite(REDIRECT_URL)  # Gõ địa chỉ trang chuyển hướng
        pyautogui.press("enter")  # Nhấn Enter để truy cập
        logging.info(f"Đã mở trang chuyển hướng: {REDIRECT_URL}")
    except:
        pass

def kill_zalo():
    """Tắt ứng dụng Zalo ngay lập tức"""
    for proc in psutil.process_iter():
        try:
            if proc.name() in BLOCKED_APPS:
                logging.info(f"Đã đóng Zalo: {proc.name()}")
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
        title, url, browser_hwnd = get_browser_info()

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

        # Kiểm tra nếu Zalo App đang chạy
        kill_zalo()
    
    time.sleep(2)  # Kiểm tra mỗi 2 giây
