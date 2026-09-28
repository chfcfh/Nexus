import os
import sys
import json
import math
import time
import shutil
import ssl
import threading
import subprocess
import webbrowser
import winreg
import re
import glob
import zlib
import struct
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    import customtkinter as ctk
    import keyboard
    import pystray
    from PIL import Image, ImageDraw, ImageTk
except ImportError:
    messagebox.showerror(
        "مكتبات ناقصة",
        "يرجى فتح موجه الأوامر (CMD) وتثبيت المكتبات المطلوبة عبر:\n\npip install customtkinter keyboard pystray pillow"
    )
    sys.exit(1)

APP_VERSION = "3.0.0"
GITHUB_REPO = "chfcfh/Nexus"

_RAW_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
# إذا كان شغال من داخل مجلد runtime، ارجع للمجلد الأساسي
if os.path.basename(_RAW_DIR).lower() == "runtime":
    APP_DIR = os.path.dirname(_RAW_DIR)
else:
    APP_DIR = _RAW_DIR
PROFILES_FILE = os.path.join(APP_DIR, "profiles.json")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
RESAMPLE = getattr(Image, "Resampling", Image).LANCZOS

# ألوان الواجهة الثابتة
BG = "#070A10"
SIDEBAR = "#0B0F17"
CARD = "#0D1322"
CARD2 = "#0F1626"
FIELD = "#131B2E"
BORDER = "#1E2B45"
TXT = "#E2E8F0"
MUTED = "#94A3B8"

# خريطة الألوان المتاحة لتخصيص كل وضع
PROFILE_COLORS = {
    "أحمر": {"text": "#FB7185", "bg": "#4C1D24"},
    "أزرق": {"text": "#00D2FF", "bg": "#1E3A5F"},
    "أخضر": {"text": "#10B981", "bg": "#064E3B"},
    "بنفسجي": {"text": "#C084FC", "bg": "#3B185F"},
    "ذهبي": {"text": "#FBBF24", "bg": "#451A03"},
    "برتقالي": {"text": "#FB923C", "bg": "#431407"}
}

PROFILE_ICONS = [
    ("🎮", "gamepad", "ألعاب"),
    ("🎧", "headphones", "سماعة"),
    ("🖥️", "monitor", "شاشة بي سي"),
    ("📺", "tv", "تلفزيون"),
    ("🎬", "film", "سينما"),
    ("⚡", "bolt", "أداء عالي"),
    ("💼", "briefcase", "عمل ومكتب"),
    ("🌙", "moon", "وضع ليلي"),
    ("🎵", "music", "موسيقى"),
    ("🏠", "home", "المنزل"),
]

DISPLAY_MODES = [
    ("تمديد الشاشتين (Extend)", "extend"),
    ("شاشة البي سي فقط (PC Screen Only)", "internal"),
    ("الشاشة الثانية / التلفزيون فقط (Second Screen Only)", "external"),
    ("تطابق الشاشتين (Duplicate)", "clone"),
]
MODE_MAP = dict(DISPLAY_MODES)

KEYSYM_MAP = {
    "return": "enter", "prior": "page up", "next": "page down", "escape": "esc",
    "grave": "`", "minus": "-", "equal": "=", "bracketleft": "[", "bracketright": "]",
    "semicolon": ";", "apostrophe": "'", "comma": ",", "period": ".", "slash": "/",
    "backslash": "\\", "space": "space", "tab": "tab", "insert": "insert", "delete": "delete",
    "home": "home", "end": "end", "up": "up", "down": "down", "left": "left", "right": "right",
    "backspace": "backspace",
}


def icon_key_for(symbol):
    s = (symbol or "").replace("\ufe0f", "").strip()
    for em, key, _ in PROFILE_ICONS:
        if em.replace("\ufe0f", "") == s:
            return key
    return "monitor"


def canonical_icon(symbol):
    s = (symbol or "").replace("\ufe0f", "").strip()
    for em, _, _ in PROFILE_ICONS:
        if em.replace("\ufe0f", "") == s:
            return em
    return PROFILE_ICONS[2][0]


# ==========================================
# 0. دوال التحديث التلقائي عبر GitHub
# ==========================================
def parse_version(v_str):
    """استخراج أرقام الإصدار كمصفوفة للمقارنة (مثال: 'v2.1.0' -> (2, 1, 0))"""
    try:
        nums = [int(x) for x in re.findall(r'\d+', str(v_str))]
        return tuple(nums) if nums else (0,)
    except Exception:
        return (0,)


def check_for_updates():
    """فحص الإصدار الأخير عبر رابط الويب المباشر لتجاوز قيود GitHub API بالكامل"""
    web_url = f"https://github.com/{GITHUB_REPO}/releases/latest"
    req = urllib.request.Request(web_url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, timeout=6, context=ctx) as response:
            final_url = response.geturl()  # مثال: https://github.com/.../releases/tag/v1.0.0
            
            if "/releases/tag/" in final_url:
                latest_tag = final_url.rstrip("/").split("/")[-1]
                v_remote = parse_version(latest_tag)
                v_local = parse_version(APP_VERSION)
                
                print(f"[Update Checker] الإصدار على قيت هوب: {v_remote} ({latest_tag}) | جهازك: {v_local} ({APP_VERSION})")

                if v_remote > v_local:
                    return {
                        "has_update": True,
                        "version": latest_tag,
                        "url": final_url,
                        "notes": "يتوفر إصدار أحدث على GitHub."
                    }
                else:
                    return {"has_update": False, "status": "latest"}
            else:
                return {"has_update": False, "error": "لم يتم العثور على Releases"}
                
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"has_update": False, "error": "لا يوجد Releases منشورة في هذا المستودع"}
        return {"has_update": False, "error": f"خطأ HTTP {e.code}"}
    except Exception as e:
        return {"has_update": False, "error": str(e)}

    return {"has_update": False}

import zipfile

def download_release_zip(tag, progress_callback=None):
    """تحميل ملف Nexus.zip مباشرة من Assets الإصدار في GitHub"""
    zip_url = f"https://github.com/{GITHUB_REPO}/releases/download/{tag}/Nexus.zip"
    zip_path = os.path.join(APP_DIR, "update.zip")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        zip_url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Nexus-App"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            chunk_size = 1024 * 256

            with open(zip_path, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        pct = int((downloaded / total_size) * 100)
                        progress_callback(pct)

        return zip_path, None
    except urllib.error.HTTPError as e:
        return None, f"خطأ HTTP {e.code}"
    except Exception as e:
        return None, str(e)


def apply_update_and_restart(zip_path):
    """فك ضغط التحديث واستبدال الملفات بأمان وإعادة تشغيل البرنامج"""
    temp_extract = os.path.join(APP_DIR, "update_temp")
    try:
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract, ignore_errors=True)

        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(temp_extract)
    except Exception as e:
        return False, f"فشل فك ضغط الملف: {e}"

    # 1. البحث التلقائي عن المجلد الفعلي اللي فيه الملفات داخل الـ ZIP
    src_dir = temp_extract
    for root, dirs, files in os.walk(temp_extract):
        if any(f.lower().endswith((".exe", ".py")) for f in files):
            src_dir = root
            break

    # 2. تحديد الملف التنفيذي الجديد لتشغيله بعد التحديث
    target_exe = None
    for f in os.listdir(src_dir):
        if f.lower() == "nexus.exe":
            target_exe = os.path.join(APP_DIR, f)
            break
        elif f.lower().endswith(".exe") and not f.lower().startswith("unins"):
            target_exe = os.path.join(APP_DIR, f)

    if not target_exe:
        target_exe = sys.executable if getattr(sys, "frozen", False) else f'"{sys.executable}" "{os.path.abspath(__file__)}"'

    # 3. سكربت تثبيت ذكي: ينتظر إغلاق البرنامج الحالي برقم الـ PID لمنع قفل الملفات
    current_pid = os.getpid()
    bat_path = os.path.join(APP_DIR, "apply_update.bat")

    bat_script = f"""@echo off
setlocal
set "PID={current_pid}"

:wait_closed
tasklist /FI "PID eq %PID%" 2>nul | find /I "%PID%" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_closed
)

xcopy "{src_dir}\\*" "{APP_DIR}" /E /Y /I /H /C /Q >nul 2>&1
rmdir /s /q "{temp_extract}" 2>nul
del "{zip_path}" 2>nul
start "" "{target_exe}"
del "%~f0"
"""
    try:
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_script)

        subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=subprocess.CREATE_NO_WINDOW)
        return True, None
    except Exception as e:
        return False, f"فشل تشغيل مثبت التحديث: {e}"


# ==========================================
# 0.5 محرك الأيقونات المرسومة
# ==========================================

_ICON_CACHE = {}


def _rgba(c):
    from PIL import ImageColor
    return tuple(ImageColor.getrgb(c)[:3]) + (255,)


def draw_icon_image(name, color, px=96):
    S = px
    k = S / 100.0
    col = _rgba(color)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = 8 * k

    def sc(p):
        return (p[0] * k, p[1] * k)

    def disc(c, r):
        x, y = sc(c)
        rr = r * k
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=col)

    def ring(c, r, w=lw):
        x, y = sc(c)
        rr = r * k
        d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=col, width=max(1, int(w)))

    def line(pts, w=lw):
        s = [sc(p) for p in pts]
        d.line(s, fill=col, width=max(1, int(w)), joint="curve")
        for p in (s[0], s[-1]):
            d.ellipse((p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2), fill=col)

    def rrect(b, r, w=lw, fill=False):
        bb = tuple(v * k for v in b)
        if fill:
            d.rounded_rectangle(bb, radius=r * k, fill=col)
        else:
            d.rounded_rectangle(bb, radius=r * k, outline=col, width=max(1, int(w)))

    def poly(pts):
        d.polygon([sc(p) for p in pts], fill=col)

    def arc(b, a0, a1, w=lw):
        d.arc(tuple(v * k for v in b), a0, a1, fill=col, width=max(1, int(w)))

    n = name
    if n == "home":
        line([(14, 50), (50, 18), (86, 50)])
        line([(24, 44), (24, 84), (76, 84), (76, 44)])
        line([(42, 84), (42, 62), (58, 62), (58, 84)])
    elif n in ("list", "layers"):
        rrect((22, 12, 78, 88), 9)
        line([(35, 34), (65, 34)])
        line([(35, 50), (65, 50)])
        line([(35, 66), (54, 66)])
    elif n == "speaker":
        poly([(12, 38), (30, 38), (52, 18), (52, 82), (30, 62), (12, 62)])
        arc((44, 32, 72, 68), -55, 55)
        arc((38, 18, 92, 82), -55, 55)
    elif n == "gear":
        ring((50, 50), 27)
        ring((50, 50), 9)
        for i in range(8):
            a = math.radians(i * 45)
            line([(50 + 27 * math.cos(a), 50 + 27 * math.sin(a)),
                  (50 + 40 * math.cos(a), 50 + 40 * math.sin(a))], w=lw * 1.5)
    elif n == "info":
        ring((50, 50), 38)
        disc((50, 31), 5)
        line([(50, 45), (50, 70)])
    elif n == "bolt":
        poly([(58, 6), (22, 56), (46, 56), (40, 94), (78, 42), (54, 42)])
    elif n == "gamepad":
        rrect((8, 28, 92, 74), 22)
        line([(30, 43), (30, 59)])
        line([(22, 51), (38, 51)])
        disc((68, 46), 4.5)
        disc((77, 56), 4.5)
    elif n == "headphones":
        arc((16, 14, 84, 82), 180, 360)
        line([(16, 48), (16, 62)])
        line([(84, 48), (84, 62)])
        rrect((10, 58, 30, 86), 7, fill=True)
        rrect((70, 58, 90, 86), 7, fill=True)
    elif n == "monitor":
        rrect((8, 14, 92, 66), 8)
        line([(50, 66), (50, 82)])
        line([(30, 86), (70, 86)])
    elif n == "tv":
        rrect((8, 30, 92, 84), 8)
        line([(50, 30), (32, 10)])
        line([(50, 30), (68, 10)])
    elif n == "film":
        rrect((14, 14, 86, 86), 8)
        line([(34, 14), (34, 86)])
        line([(66, 14), (66, 86)])
        for y in (34, 50, 66):
            line([(14, y), (34, y)], w=lw * 0.7)
            line([(66, y), (86, y)], w=lw * 0.7)
    elif n == "briefcase":
        rrect((10, 32, 90, 86), 8)
        line([(36, 32), (36, 18), (64, 18), (64, 32)])
        line([(10, 57), (90, 57)])
    elif n == "moon":
        disc((46, 50), 38)
        x, y = sc((66, 36))
        rr = 32 * k
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(0, 0, 0, 0))
    elif n == "music":
        line([(40, 72), (40, 22)])
        line([(72, 62), (72, 16)])
        line([(40, 22), (72, 16)], w=lw * 1.4)
        disc((30, 74), 11)
        disc((62, 64), 11)
    elif n == "trash":
        line([(18, 26), (82, 26)])
        line([(40, 26), (40, 14), (60, 14), (60, 26)])
        line([(26, 26), (31, 86), (69, 86), (74, 26)])
        line([(45, 42), (45, 72)], w=lw * 0.8)
        line([(55, 42), (55, 72)], w=lw * 0.8)
    elif n == "edit":
        line([(22, 80), (28, 56), (64, 20), (80, 36), (44, 72), (22, 80)])
        line([(54, 30), (70, 46)])
    elif n == "play":
        poly([(28, 14), (28, 86), (86, 50)])
    elif n == "keyboard":
        rrect((6, 24, 94, 76), 9)
        for x in (22, 36, 50, 64, 78):
            disc((x, 40), 3.4)
        for x in (29, 43, 57, 71):
            disc((x, 52), 3.4)
        line([(30, 64), (70, 64)], w=lw * 0.9)
    elif n == "download":
        line([(50, 12), (50, 60)])
        line([(30, 42), (50, 62), (70, 42)])
        line([(16, 68), (16, 86), (84, 86), (84, 68)])
    elif n == "upload":
        line([(50, 64), (50, 16)])
        line([(30, 36), (50, 16), (70, 36)])
        line([(16, 68), (16, 86), (84, 86), (84, 68)])
    elif n == "refresh":
        arc((14, 14, 86, 86), 40, 320)
        poly([(84, 35), (83, 16), (67, 31)])
    elif n == "bell":
        arc((26, 16, 74, 64), 180, 360)
        line([(26, 40), (26, 62), (16, 74)])
        line([(74, 40), (74, 62), (84, 74)])
        line([(16, 74), (84, 74)])
        disc((50, 86), 6)
    elif n == "plus":
        line([(50, 18), (50, 82)])
        line([(18, 50), (82, 50)])
    elif n == "check":
        line([(18, 54), (41, 76), (83, 28)], w=lw * 1.2)
    elif n == "copy":
        rrect((12, 12, 62, 62), 8)
        bb = tuple(v * k for v in (34, 34, 88, 88))
        d.rounded_rectangle(bb, radius=8 * k, fill=(0, 0, 0, 0))
        rrect((34, 34, 88, 88), 8)
    elif n == "search":
        ring((38, 38), 25)
        line([(57, 57), (84, 84)])
    elif n == "activity":
        line([(6, 52), (28, 52), (40, 20), (58, 82), (70, 52), (94, 52)])
    elif n == "folder":
        rrect((8, 30, 92, 86), 8)
        line([(8, 30), (8, 20), (36, 20), (46, 30)])
    elif n == "globe":
        ring((50, 50), 38)
        d.ellipse((30 * k, 12 * k, 70 * k, 88 * k), outline=col, width=max(1, int(lw * 0.8)))
        line([(12, 50), (88, 50)], w=lw * 0.8)
    elif n == "sun":
        disc((50, 50), 15)
        for i in range(8):
            a = math.radians(i * 45)
            line([(50 + 26 * math.cos(a), 50 + 26 * math.sin(a)),
                  (50 + 40 * math.cos(a), 50 + 40 * math.sin(a))])
    elif n == "clock":
        ring((50, 50), 38)
        line([(50, 26), (50, 50), (68, 60)])
    elif n == "up":
        line([(22, 64), (50, 36), (78, 64)])
    elif n == "down":
        line([(22, 36), (50, 64), (78, 36)])
    elif n == "right":
        line([(34, 20), (66, 50), (34, 80)])
    elif n == "back":
        line([(16, 50), (84, 50)])
        line([(58, 24), (84, 50), (58, 76)])
    elif n == "x":
        line([(24, 24), (76, 76)])
        line([(76, 24), (24, 76)])
    elif n == "star":
        pts = []
        for i in range(10):
            a = math.radians(-90 + i * 36)
            r = 42 if i % 2 == 0 else 18
            pts.append((50 + r * math.cos(a), 54 + r * math.sin(a)))
        poly(pts)
    else:
        ring((50, 50), 36)
    return img


def ico(name, color=TXT, size=18):
    key = (name, color, size)
    if key not in _ICON_CACHE:
        pil = draw_icon_image(name, color, px=size * 6)
        _ICON_CACHE[key] = ctk.CTkImage(light_image=pil, dark_image=pil, size=(size, size))
    return _ICON_CACHE[key]


# ==========================================
# 1. دوال التحكم في النظام (شاشات، صوت، HDR)
# ==========================================

def get_audio_devices():
    ps_cmd = """
    Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue
    if (Get-Command Get-AudioDevice -ErrorAction SilentlyContinue) {
        Get-AudioDevice -List | Where-Object { $_.Type -eq 'Playback' } | Select-Object -ExpandProperty Name
    } else {
        Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPClass -eq 'AudioEndpoint' } | Select-Object -ExpandProperty Name
    }
    """
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
        playback = [name for name in lines if not any(x in name.lower() for x in ["mic", "ميكروفون", "steam streaming"])]
        return playback if playback else ["Default Audio"]
    except Exception:
        return ["Default Audio"]


def set_audio_device(device_name):
    ps_script = f"""
    Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue
    $target = "{device_name}"
    $dev = Get-AudioDevice -List | Where-Object {{ $_.Type -eq 'Playback' -and ($_.Name -like "*$target*" -or "$target" -like "*$($_.Name)*") }} | Select-Object -First 1
    if ($dev) {{
        Set-AudioDevice -Index $dev.Index
    }}
    """
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"Audio switch error: {e}")


def get_default_audio_device():
    ps = "Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue; (Get-AudioDevice -Playback).Name"
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        return res.stdout.strip().splitlines()[0].strip() if res.stdout.strip() else ""
    except Exception:
        return ""


def get_playback_volume():
    ps = "Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue; Get-AudioDevice -PlaybackVolume"
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        m = re.search(r"\d+(?:\.\d+)?", res.stdout)
        return max(0, min(100, int(float(m.group())))) if m else None
    except Exception:
        return None


def set_volume(level):
    ps = f"Import-Module AudioDeviceCmdlets -ErrorAction SilentlyContinue; Set-AudioDevice -PlaybackVolume {int(level)}"
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"Volume error: {e}")


def play_test_sound():
    cmd = 'powershell -NoProfile -Command "[System.Media.SystemSounds]::Asterisk.Play()"'
    subprocess.run(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)


def set_display_mode(mode):
    arg = f"/{mode.lower()}"
    try:
        subprocess.run(["DisplaySwitch.exe", arg], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"Display switch error: {e}")


def toggle_hdr():
    try:
        time.sleep(0.3)
        keyboard.press_and_release("windows+alt+b")
    except Exception as e:
        print(f"HDR error: {e}")


# ==========================================
# 2. إدارة البيانات والإعدادات
# ==========================================

def load_data(file_path, backup_on_error=False):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            if backup_on_error:
                try:
                    os.replace(file_path, file_path + ".bak")
                except Exception:
                    pass
            return {}
    return {}


def save_data(file_path, data):
    tmp = file_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    os.replace(tmp, file_path)


_STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_STARTUP_NAME = "NexusDisplayAudio"


def _startup_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --tray'
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(pyw):
        exe = pyw
    return f'"{exe}" "{os.path.abspath(__file__)}" --tray'


def set_startup_registry(enable=True):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_KEY, 0, winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, _STARTUP_NAME, 0, winreg.REG_SZ, _startup_command())
        else:
            try:
                winreg.DeleteValue(key, _STARTUP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Startup registry error: {e}")


def is_startup_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, _STARTUP_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


_MUTEX = None


def ensure_single_instance():
    global _MUTEX
    try:
        import ctypes
        _MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\NexusDisplayAudioManager")
        return ctypes.windll.kernel32.GetLastError() != 183
    except Exception:
        return True


# ==========================================
# 2.5 محرك إدارة مكتبة ألعاب ستيم
# ==========================================

EXCLUDE_KEYWORDS = [
    'unins', 'setup', 'redist', 'crash', 'handler', 'report', 'update',
    'patch', 'vcredist', 'dxsetup', 'easyanticheat', 'battleye', 'cefprocess',
    'notification', 'benchmark', 'server', 'dotnet', 'support', 'directx',
    'prereq', 'installer', 'cleanup', 'eac_server'
]

STEAM_STRINGS = {
"ar": {
        "title_add": "SteamLibraryIntegrator | إضافة الألعاب",
        "sub_add": "افحص مجلد ألعابك وأضفها إلى مكتبة ستيم مع الأغلفة",
        "title_accounts": "SteamLibraryIntegrator | الحسابات والمسارات",
        "sub_accounts": "حدد مسار ستيم والحساب المستهدف وتحقق من حالة ستيم",
        "lbl_target": "الحساب المستهدف:\u200E",
        "btn_change_target": "الحساب تغيير",                    # تظهر: تغيير الحساب
        "lbl_status": "حالة ستيم:\u200E",
        "steam_running": "يعمل حالياً — سيُغلق بأمان ويُعاد تشغيله تلقائياً عند الإضافة",
        "steam_stopped": "متوقف",
        "btn_recheck": "الفحص إعادة",                          # تظهر: إعادة الفحص
        "lang_btn": "English",
        "lbl_steam": "مسار مجلد ستيم:\u200E",
        "btn_browse_steam": "ستيم مجلد تحديد",                 # تظهر: تحديد مجلد ستيم
        "lbl_user": "حساب ستيم المستهدف:\u200E",
        "chk_all_users": "تطبيق على جميع الحسابات",
        "lbl_games": "مسار مجلد الألعاب:\u200E",
        "btn_browse_games": "الألعاب مجلد تحديد",              # تظهر: تحديد مجلد الألعاب
        "btn_scan": "فحص الألعاب",                            # تظهر: فحص الألعاب
        "chk_art": "تحميل وتعيين الأغلفة والخلفيات والشعارات تلقائياً من ستيم",
        "lbl_hint": " (exe) يمكنك النقر مرتين على أي لعبة لتغيير المشغل يدوياً قبل الإضافة.",
        "col_name": "اسم اللعبة",
        "col_exe": "مشغل اللعبة المكتشف (EXE)",
        "btn_remove": "المحدد حذف",                           # تظهر: حذف المحدد
        "btn_clear": "بالكامل القائمة مسح",                   # تظهر: مسح القائمة بالكامل
        "btn_add": "الأغلفة وتعيين الألعاب إضافة",            # تظهر: إضافة الألعاب وتعيين الأغلفة
        "btn_processing": "جاري المعالجة والفحص...",
        "no_users": "لم يتم العثور على حسابات",
        "active_tag": "⭐ [النشط]",
        "user_tag": "👤",
        "account_word": "حساب",
        "warn_no_games": "لا توجد ألعاب في القائمة لإضافتها.",
        "warn_invalid_path": "يرجى اختيار مسار صحيح لمجلد الألعاب.",
        "err_steam_path": "مسار ستيم المكتوب غير موجود بالجهاز:\n",
        "err_no_targets": "لم يتم العثور على حسابات صالحة لتطبيق العملية عليها.",
        "scan_empty": "لم يتم العثور على ألعاب واضحة داخل المجلد.",
        "scan_done": "تم العثور على {count} من أصل {total} مجلد.",
        "status_scanning": "جاري فحص مجلدات الألعاب...",
        "status_closing_steam": "جاري إغلاق ستيم بأمان وتجهيز الملفات...",
        "status_fetching": "جاري جلب الأغلفة والخلفيات للألعاب الجديدة ({current}/{total})...",
        "status_restarting_steam": "جاري إعادة تشغيل ستيم تلقائياً...",
        "done_title": "اكتملت العملية بنجاح",
        "done_all_exist": "جميع الألعاب المحددة ({count} لعبة) موجودة مسبقاً في مكتبتك!\nلم تتم إضافة أي لعبة مكررة.",
        "done_msg": "تمت إضافة {added_count} لعبة جديدة بنجاح إلى: {target_desc}!\nتم تخطي {skipped_count} لعبة لأنها موجودة مسبقاً.\n\n🎨 تم تحميل الأغلفة لـ {art_count} لعبة جديدة بنجاح!\n{restarted_note}",
        "restarted_text_yes": "\n🚀 تم إعادة تشغيل ستيم تلقائياً بمكتبتك المحدثة!",
        "restarted_text_no": "\nشغّل ستيم وستجد ألعابك في مكتبتك.",
        "done_all_users": "جميع الحسابات ({count} حساب)",
        "done_single_user": "حسابك المحدد",
        "dialog_steam": "حدد مجلد ستيم",
        "dialog_games": "حدد مجلد ألعابك",
        "dialog_exe": "اختر ملف الـ EXE للعبة"
    },
    
    "en": {
        "title_add": "SteamLibraryIntegrator | Add Games",
        "sub_add": "Scan your games folder and add them to Steam with artwork",
        "title_accounts": "SteamLibraryIntegrator | Accounts & Paths",
        "sub_accounts": "Set the Steam path, target account and check Steam status",
        "lbl_target": "Target Account:",
        "btn_change_target": "  Change Account",
        "lbl_status": "Steam Status:",
        "steam_running": "Running — will be closed safely and restarted automatically when adding",
        "steam_stopped": "Not running",
        "btn_recheck": "  Re-check",
        "lang_btn": "عربي",
        "lbl_steam": "Steam Directory:",
        "btn_browse_steam": "  Browse Steam...",
        "lbl_user": "Target Steam Account:",
        "chk_all_users": "Apply to All Accounts",
        "lbl_games": "Games Directory:",
        "btn_browse_games": "  Browse Games...",
        "btn_scan": "  Scan Games",
        "chk_art": "Auto-download Covers, Backgrounds & Logos from Steam",
        "lbl_hint": "Double-click any game in the list to manually change its executable (.exe).",
        "col_name": "Game Title",
        "col_exe": "Detected Executable (EXE)",
        "btn_remove": "  Remove Selected",
        "btn_clear": "  Clear All",
        "btn_add": "  Add Games & Set Artwork",
        "btn_processing": "  Checking & Processing...",
        "no_users": "No Steam accounts found",
        "active_tag": "⭐ [Active]",
        "user_tag": "👤",
        "account_word": "Account",
        "warn_no_games": "No games in the list to add.",
        "warn_invalid_path": "Please select a valid games directory path.",
        "err_steam_path": "Steam path does not exist:\n",
        "err_no_targets": "No valid Steam user accounts found to apply.",
        "scan_empty": "No recognizable games found in this folder.",
        "scan_done": "Found {count} out of {total} folders.",
        "status_scanning": "Scanning game folders...",
        "status_closing_steam": "Closing Steam safely to flush cache...",
        "status_fetching": "Fetching artwork for new games ({current}/{total})...",
        "status_restarting_steam": "Restarting Steam automatically...",
        "done_title": "Process Completed",
        "done_all_exist": "All selected games ({count} games) already exist in your library!\nNo duplicates were added.",
        "done_msg": "Successfully added {added_count} new games to: {target_desc}!\nSkipped {skipped_count} games already present in library.\n\n🎨 Downloaded artwork for {art_count} new games!\n{restarted_note}",
        "restarted_text_yes": "\n🚀 Steam was restarted automatically with your updated library!",
        "restarted_text_no": "\nLaunch Steam to view your updated library.",
        "done_all_users": "All Accounts ({count} accounts)",
        "done_single_user": "Selected Account",
        "dialog_steam": "Select Steam Main Folder",
        "dialog_games": "Select Games Folder",
        "dialog_exe": "Select Executable File for"
    }
}


def detect_steam_path():
    if os.path.exists(r"F:\steam"):
        return r"F:\steam"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            val, _ = winreg.QueryValueEx(key, "SteamPath")
            p = val.replace('/', '\\')
            if os.path.exists(p):
                return p
    except Exception:
        pass
    if os.path.exists(r"C:\Program Files (x86)\Steam"):
        return r"C:\Program Files (x86)\Steam"
    return r"F:\steam"


def is_steam_running():
    try:
        tasks = subprocess.check_output('tasklist /FI "IMAGENAME eq steam.exe"', shell=True,
                                        creationflags=subprocess.CREATE_NO_WINDOW).decode('utf-8', errors='ignore')
        return 'steam.exe' in tasks.lower()
    except Exception:
        return False


def safely_close_steam(steam_path):
    if not is_steam_running():
        return True

    steam_exe = os.path.join(steam_path, "steam.exe")
    if os.path.exists(steam_exe):
        try:
            subprocess.run([steam_exe, "-shutdown"], capture_output=True, timeout=5,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass

    for _ in range(16):
        if not is_steam_running():
            return True
        time.sleep(0.5)

    subprocess.run('taskkill /IM steam.exe /F', shell=True, capture_output=True,
                   creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(1)
    return not is_steam_running()


def restart_steam(steam_path):
    steam_exe = os.path.join(steam_path, "steam.exe")
    if os.path.exists(steam_exe):
        try:
            subprocess.Popen([steam_exe], creationflags=0x00000008 if os.name == 'nt' else 0)
        except Exception:
            try:
                os.startfile(steam_exe)
            except Exception:
                pass


def clean_display_name(val):
    if not val:
        return ""
    if '\\u' in val or '\\x' in val:
        try:
            val = val.encode('utf-8').decode('unicode_escape')
        except Exception:
            pass
    return val.strip()


def get_steam_users_info(steam_path, lang="ar"):
    t = STEAM_STRINGS[lang]
    steam_path = steam_path.strip().strip('"').strip("'")
    userdata_dir = os.path.join(steam_path, "userdata")
    if not os.path.exists(userdata_dir):
        return []

    dirs = [d for d in glob.glob(os.path.join(userdata_dir, "*")) if os.path.isdir(d) and os.path.basename(d).isdigit() and os.path.basename(d) != '0']

    loginusers_file = os.path.join(steam_path, "config", "loginusers.vdf")
    user_names = {}
    most_recent_id32 = None

    if os.path.exists(loginusers_file):
        try:
            with open(loginusers_file, "r", encoding="utf-8-sig", errors="replace") as f:
                content = f.read()
            blocks = re.findall(r'"(7656119[0-9]+)"\s*\{([^}]+)\}', content, flags=re.DOTALL)
            for sid64, body in blocks:
                id32 = str(int(sid64) & 0xFFFFFFFF)
                pname = re.search(r'"PersonaName"\s*"([^"]+)"', body)
                accname = re.search(r'"AccountName"\s*"([^"]+)"', body)
                recent = re.search(r'"MostRecent"\s*"1"', body)

                name = ""
                if pname:
                    name = clean_display_name(pname.group(1))
                elif accname:
                    name = accname.group(1).strip()
                else:
                    name = f"User_{id32}"

                user_names[id32] = name
                if recent:
                    most_recent_id32 = id32
        except Exception:
            pass

    results = []
    for d in dirs:
        bid = os.path.basename(d)
        name = user_names.get(bid, f"{t['account_word']} {bid}")
        is_rec = (bid == most_recent_id32)
        star = f"{t['active_tag']} " if is_rec else f"{t['user_tag']} "
        disp = f"{star}{name}  |  ID: {bid}"
        results.append({"id": bid, "path": d, "display": disp, "name": name, "is_recent": is_rec})

    results.sort(key=lambda x: x["is_recent"], reverse=True)
    return results


def get_existing_shortcuts(vdf_path):
    existing_names = set()
    existing_exes = set()
    if not os.path.exists(vdf_path):
        return existing_names, existing_exes

    try:
        with open(vdf_path, 'rb') as f:
            data = f.read()

        for m in re.finditer(rb'\x01AppName\x00([^\x00]+)\x00', data):
            try:
                name_str = m.group(1).decode('utf-8', errors='ignore').strip().lower()
                if name_str:
                    existing_names.add(name_str)
            except Exception:
                pass

        for m in re.finditer(rb'\x01Exe\x00([^\x00]+)\x00', data):
            try:
                exe_str = m.group(1).decode('utf-8', errors='ignore').strip(' "\'').lower()
                if exe_str:
                    existing_exes.add(os.path.normpath(exe_str))
            except Exception:
                pass
    except Exception:
        pass

    return existing_names, existing_exes


def clean_game_name(name):
    cleaned = re.sub(r'[\._]v[0-9].*$', '', name, flags=re.IGNORECASE)
    cleaned = re.sub(r'[\._]Build[0-9\._].*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[\._][0-9]{8}.*$', '', cleaned)
    cleaned = cleaned.replace('.', ' ').replace('_', ' ')
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def fetch_steam_appid(game_name):
    clean_title = clean_game_name(game_name)
    queries = [clean_title]
    words = clean_title.split()
    if len(words) > 2:
        queries.append(' '.join(words[:2]))
        queries.append(words[0])

    for q in queries:
        try:
            url = f"https://store.steampowered.com/api/storesearch/?term={urllib.parse.quote(q)}&l=english&cc=US"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('total', 0) > 0 and data.get('items'):
                    return data['items'][0]['id']
        except Exception:
            continue
    return None


def fetch_image_data(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=6) as resp:
            if resp.status == 200:
                return resp.read()
    except Exception:
        pass
    return None


def download_and_save_artwork(app_name, exe_path, target_grid_dirs):
    appid = fetch_steam_appid(app_name)
    if not appid:
        return False

    quoted_exe = f'"{os.path.abspath(exe_path)}"'
    crc = zlib.crc32(f"{quoted_exe}{app_name}".encode('utf-8')) | 0x80000000
    id_32 = str(crc & 0xFFFFFFFF)

    cover_data = fetch_image_data(f"https://steamcdn-a.akamaihd.net/steam/apps/{appid}/library_600x900.jpg")
    hero_data = fetch_image_data(f"https://steamcdn-a.akamaihd.net/steam/apps/{appid}/library_hero.jpg")
    logo_data = fetch_image_data(f"https://steamcdn-a.akamaihd.net/steam/apps/{appid}/logo.png")
    banner_data = fetch_image_data(f"https://steamcdn-a.akamaihd.net/steam/apps/{appid}/header.jpg")

    has_any = any([cover_data, hero_data, logo_data, banner_data])
    if not has_any:
        return False

    for g_dir in target_grid_dirs:
        if cover_data:
            with open(os.path.join(g_dir, f"{id_32}p.jpg"), "wb") as f:
                f.write(cover_data)
        if hero_data:
            with open(os.path.join(g_dir, f"{id_32}_hero.jpg"), "wb") as f:
                f.write(hero_data)
        if logo_data:
            with open(os.path.join(g_dir, f"{id_32}_logo.png"), "wb") as f:
                f.write(logo_data)
        if banner_data:
            with open(os.path.join(g_dir, f"{id_32}.jpg"), "wb") as f:
                f.write(banner_data)

    return True


def find_best_exe(folder_path):
    candidates = []
    folder_name = os.path.basename(folder_path).lower()
    clean_folder = re.sub(r'[^a-zA-Z0-9]', '', folder_name)

    for root, _, files in os.walk(folder_path):
        depth = len(Path(root).relative_to(folder_path).parts)
        if depth > 6:
            continue

        for file in files:
            if not file.lower().endswith('.exe'):
                continue

            file_lower = file.lower()
            if any(k in file_lower for k in EXCLUDE_KEYWORDS):
                continue

            full_path = os.path.join(root, file)
            try:
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
            except OSError:
                continue

            if size_mb < 0.15:
                continue

            clean_name = re.sub(r'[^a-zA-Z0-9]', '', file_lower.replace('.exe', ''))
            score = size_mb
            if clean_name and (clean_name in clean_folder or clean_folder in clean_name):
                score += 1000

            root_lower = root.lower()
            if depth == 0:
                score += 200
            if 'binaries' in root_lower or 'win64' in root_lower or 'game' in root_lower:
                score += 150
            if 'shipping' in file_lower:
                score += 100

            candidates.append((score, full_path))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def write_shortcuts_file(vdf_path, shortcuts_to_add):
    def str_entry(k, v):
        return b'\x01' + k.encode('utf-8') + b'\x00' + v.encode('utf-8') + b'\x00'

    def int_entry(k, v):
        return b'\x02' + k.encode('utf-8') + b'\x00' + struct.pack('<I', v)

    if os.path.exists(vdf_path):
        with open(vdf_path, 'rb') as f:
            data = bytearray(f.read())
    else:
        data = bytearray(b'\x00shortcuts\x00\x08\x08')

    existing_indices = [int(m) for m in re.findall(rb'\x00([0-9]+)\x00\x02appid\x00', data)]
    next_idx = max(existing_indices) + 1 if existing_indices else 0

    if data.endswith(b'\x08\x08'):
        data = data[:-2]
    elif data.endswith(b'\x08'):
        data = data[:-1]

    for app_name, exe_path in shortcuts_to_add:
        quoted_exe = f'"{os.path.abspath(exe_path)}"'
        start_dir = f'"{os.path.dirname(os.path.abspath(exe_path))}"'
        crc = zlib.crc32(f"{quoted_exe}{app_name}".encode('utf-8')) | 0x80000000

        entry = bytearray(b'\x00' + str(next_idx).encode('ascii') + b'\x00')
        next_idx += 1

        entry += int_entry("appid", crc)
        entry += str_entry("AppName", app_name)
        entry += str_entry("Exe", quoted_exe)
        entry += str_entry("StartDir", start_dir)
        entry += str_entry("icon", "")
        entry += str_entry("ShortcutPath", "")
        entry += str_entry("LaunchOptions", "")
        entry += int_entry("IsHidden", 0)
        entry += int_entry("AllowDesktopConfig", 1)
        entry += int_entry("AllowOverlay", 1)
        entry += int_entry("OpenVR", 0)
        entry += int_entry("Devkit", 0)
        entry += str_entry("DevkitGameID", "")
        entry += int_entry("DevkitOverrideAppID", 0)
        entry += int_entry("LastPlayTime", 0)
        entry += str_entry("FlatpakAppID", "")
        entry += str_entry("SortAs", "")
        entry += b'\x00tags\x00\x08'
        entry += b'\x08'

        data += entry

    data += b'\x08\x08'
    with open(vdf_path, 'wb') as f:
        f.write(data)


# ==========================================
# 3. لوحة الألوان وإدارة الثيم الشامل
# ==========================================

ctk.set_appearance_mode("dark")

THEMES = {
    "cyan": {"accent": "#00D2FF", "btn": "#0284C7", "btn_hover": "#0369A1", "card_border": "#0369A1"},
    "emerald": {"accent": "#10B981", "btn": "#059669", "btn_hover": "#047857", "card_border": "#047857"},
    "purple": {"accent": "#C084FC", "btn": "#7C3AED", "btn_hover": "#6D28D9", "card_border": "#6D28D9"},
    "crimson": {"accent": "#FB7185", "btn": "#E11D48", "btn_hover": "#BE123C", "card_border": "#BE123C"},
    "amber": {"accent": "#FBBF24", "btn": "#D97706", "btn_hover": "#B45309", "card_border": "#B45309"},
}

THEME_PALETTE = [
    ("cyan", "أزرق", "#00D2FF"),
    ("emerald", "أخضر", "#10B981"),
    ("purple", "بنفسجي", "#C084FC"),
    ("crimson", "أحمر", "#FB7185"),
    ("amber", "ذهبي", "#FBBF24"),
]

NAV_GROUPS = [
    ("nexusflow", "NexusFlow", "bolt", [
        ("home", "الرئيسية", "home"),
        ("profiles", "إدارة الأوضاع", "list"),
        ("audio", "استوديو الصوت", "speaker"),
    ]),
    ("steam", "SteamLibraryIntegrator", "gamepad", [
        ("steam_add", "إضافة الألعاب", "plus"),
        ("steam_accounts", "الحسابات والمسارات", "folder"),
        ("steam_about", "حول المشروع", "info"),
    ]),
]
NAV_GLOBAL = [
    ("log", "سجل النشاط", "activity"),
    ("settings", "الإعدادات والثيمات", "gear"),
    ("about", "NEXUS حول", "info"),
]
PAGE_GROUP = {
    "home": "nexusflow", "editor": "nexusflow", "profiles": "nexusflow", "audio": "nexusflow",
    "steam_add": "steam", "steam_accounts": "steam", "steam_about": "steam",
}


def _short(text, n=38):
    text = text or ""
    return text if len(text) <= n else text[:n - 1] + "…"


class NexusApp(ctk.CTk):
    def __init__(self, start_hidden=False):
        super().__init__()

        self.title("NEXUS")
        self.geometry("1150x860")
        self.minsize(1050, 780)
        self.configure(fg_color=BG)
        self.protocol("WM_DELETE_WINDOW", self.hide_window)

        self.profiles = self._sanitize_profiles(load_data(PROFILES_FILE, True))
        self.settings = load_data(CONFIG_FILE, True)
        if not isinstance(self.settings, dict):
            self.settings = {}
        self.theme_key = self.settings.get("theme", "cyan")
        if self.theme_key not in THEMES:
            self.theme_key = "cyan"
        self.theme = THEMES[self.theme_key]

        self.audio_devices = []
        self.current_audio = ""
        self.editing_key = None
        self.primary_key = ""
        self.is_recording = False
        self.current_page_id = "home"
        self.active_profile = self.settings.get("last_profile", "")
        self.log_lines = []
        self.sel_icon = PROFILE_ICONS[0][0]
        self.sel_color = "أزرق سايبر"
        self.pages = {}
        self.nav_buttons = {}
        self._toast = None
        self._vol_job = None
        self._hidden_notified = False
        self._apply_lock = threading.Lock()

        # حالة صفحة إدارة مكتبة ستيم
        self.steam_lang = self.settings.get("steam_lang", "ar")
        if self.steam_lang not in STEAM_STRINGS:
            self.steam_lang = "ar"
        self.steam_path_var = tk.StringVar(value=self.settings.get("steam_path") or detect_steam_path())
        self.games_path_var = tk.StringVar(value=self.settings.get("games_path", r"F:\Games"))
        self.all_users_var = tk.BooleanVar(value=False)
        self.download_art_var = tk.BooleanVar(value=True)
        self.steam_users_list = []
        self._steam_cache = []

        self.build_ui()
        self.register_all_hotkeys()
        self.setup_tray_icon()
        self.show_page("home")
        self.after(450, self._set_window_icon)
        threading.Thread(target=self._bg_refresh_audio, daemon=True).start()
        
        # فحص التحديثات في الخلفية عند الإقلاع
        threading.Thread(target=self.async_check_update, daemon=True).start()

        if start_hidden:
            self.after(300, self.withdraw)
        self.log("تم تشغيل البرنامج")

    @staticmethod
    def _sanitize_profiles(data):
        out = {}
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(k, str) and isinstance(v, dict):
                    out[k] = v
        return out

    def get_accent(self):
        return self.theme["accent"]

    def ui(self, fn):
        for _ in range(30):
            try:
                self.after(0, fn)
                return
            except RuntimeError:
                time.sleep(0.2)
            except Exception:
                return


    def _set_window_icon(self):
        try:
            ico_path = os.path.join(APP_DIR, "logo.ico")

            # 1. إذا لم يكن ملف logo.ico موجوداً، يتم إنشاؤه تلقائياً الآن
            if not os.path.exists(ico_path):
                img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
                d = ImageDraw.Draw(img)
                # خلفية كحلية داكنة بزوايا ناعمة
                d.rounded_rectangle([12, 12, 244, 244], radius=55, fill=(11, 15, 23, 255), outline=(30, 43, 69, 255), width=6)
                # صاعقة البرق الذهبية المطابقة لشعار NEXUS
                S = 256
                bolt_pts = [
                    (0.57 * S, 0.16 * S),
                    (0.25 * S, 0.54 * S),
                    (0.48 * S, 0.54 * S),
                    (0.41 * S, 0.86 * S),
                    (0.76 * S, 0.46 * S),
                    (0.53 * S, 0.46 * S),
                ]
                d.polygon(bolt_pts, fill=(251, 191, 36, 255))
                img.save(ico_path, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

            # 2. تعيين الأيقونة عبر تكنتر
            self.iconbitmap(ico_path)

            # 3. إجبار شريط عنوان ويندوز فوراً على إظهار الأيقونة عبر Win32 API
            try:
                import ctypes
                WM_SETICON = 0x80
                ICON_SMALL = 0
                ICON_BIG = 1
                LR_LOADFROMFILE = 0x0010
                IMAGE_ICON = 1

                h_icon_sm = ctypes.windll.user32.LoadImageW(None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                h_icon_bg = ctypes.windll.user32.LoadImageW(None, ico_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)

                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                if not hwnd:
                    hwnd = self.winfo_id()

                if h_icon_sm:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon_sm)
                if h_icon_bg:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon_bg)
            except Exception:
                pass
        except Exception:
            pass

    def log(self, msg):
        self.log_lines.append(f"[{time.strftime('%H:%M:%S')}]  {msg}")
        self.log_lines = self.log_lines[-300:]
        self.ui(self._render_log_if_visible)

    def toast(self, text, kind="ok"):
        def _show():
            if self._toast is not None:
                try:
                    self._toast.destroy()
                except Exception:
                    pass
            col = {"ok": self.get_accent(), "warn": "#FBBF24", "err": "#F87171"}.get(kind, self.get_accent())
            t = ctk.CTkFrame(self, corner_radius=12, fg_color="#101A2E", border_width=1, border_color=col)
            ctk.CTkLabel(t, text="", image=ico("check" if kind == "ok" else "info", col, 18)).pack(side="right", padx=(8, 14), pady=12)
            tk.Label(t, text=text, font=("Segoe UI", 11, "bold"), fg=TXT, bg="#101A2E").pack(side="right", padx=(16, 0))
            t.place(relx=1.0, rely=1.0, anchor="se", x=-24, y=-24)
            t.lift()
            self._toast = t

            def _kill():
                try:
                    if t.winfo_exists():
                        t.destroy()
                except Exception:
                    pass
            self.after(2800, _kill)
        self.ui(_show)

    def notify(self, text, kind="ok"):
        def _do():
            try:
                hidden = self.state() in ("withdrawn", "iconic")
            except Exception:
                hidden = False
            if hidden:
                if self.settings.get("notifications", True):
                    try:
                        self.tray.notify(text, "Nexus")
                    except Exception:
                        pass
            else:
                self.toast(text, kind)
        self.ui(_do)

    # ---------- دوال التحديث في الواجهة ----------
    def async_check_update(self, manual=False):
        res = check_for_updates()
        if res.get("has_update"):
            self.log(f"يتوفر تحديث جديد: {res['version']}")
            self.ui(lambda: self.show_update_banner(res))
        elif res.get("error"):
            self.log(f"فحص التحديثات: {res['error']}")
            if manual:
                self.ui(lambda: self.toast(f"خطأ: {res['error']}", "err"))
        else:
            if manual:
                self.log("فحص التحديثات: البرنامج محدّث بالكامل")
                self.ui(lambda: self.toast(f"أنت تستخدم أحدث إصدار ({APP_VERSION})"))

    def manual_check_update(self):
        self.toast("جاري فحص التحديثات...")
        threading.Thread(target=self.async_check_update, args=(True,), daemon=True).start()

    def show_update_banner(self, update_info):
        for w in self.update_banner_container.winfo_children():
            w.destroy()

        if self.current_page_id in self.pages and self.pages[self.current_page_id].winfo_ismapped():
            self.update_banner_container.pack(side="top", fill="x", pady=(0, 10), before=self.pages[self.current_page_id])
        else:
            self.update_banner_container.pack(side="top", fill="x", pady=(0, 10))

        new_ver = update_info["version"]
        banner = ctk.CTkFrame(self.update_banner_container, height=44, fg_color="#101A2E",
                              corner_radius=10, border_width=1, border_color=self.get_accent())
        banner.pack(fill="x")
        banner.pack_propagate(False)

        inner = ctk.CTkFrame(banner, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14)

        ctk.CTkLabel(inner, text="", image=ico("bell", self.get_accent(), 16)).pack(side="right", padx=(8, 0))
        tk.Label(inner, text=f" ({new_ver})  يتوفر إصدار جديد هل ترغب في التحديث الآن؟",
                 font=("Segoe UI", 10, "bold"), fg=TXT, bg="#101A2E").pack(side="right")

        btn_up = ctk.CTkButton(inner, text="  تحديث الآن", image=ico("download", "#05101A", 14), width=110, height=28,
                               fg_color=self.get_accent(), hover_color=self.theme["btn_hover"], text_color="#05101A",
                               font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), corner_radius=6,
                               command=lambda: self.perform_update(new_ver))
        btn_up.pack(side="left", padx=(0, 8), pady=8)

        def _close_banner():
            banner.destroy()
            self.update_banner_container.pack_forget()

        btn_close = ctk.CTkButton(inner, text="", image=ico("x", MUTED, 12), width=26, height=26,
                                  fg_color="transparent", hover_color="#1E2B45", corner_radius=6,
                                  command=_close_banner)
        btn_close.pack(side="left", pady=8)

    def perform_update(self, new_ver):
        if messagebox.askyesno("تأكيد التحديث", f"سيتم تنزيل تحديث {new_ver} وتثبيته تلقائياً.\nهل ترغب بالمتابعة؟"):
            self.toast("جاري تنزيل التحديث...")

            def _work():
                def _prog(pct):
                    self.ui(lambda: self.toast(f": {pct}% جاري التحميل"))

                zip_file, err = download_release_zip(new_ver, progress_callback=_prog)

                if zip_file:
                    self.log(f"تم تنزيل {new_ver} بنجاح، جاري فك الضغط والتثبيت...")
                    ok, apply_err = apply_update_and_restart(zip_file)
                    if ok:
                        self.log("جاري إعادة تشغيل البرنامج بالنسخة الجديدة")
                        self.ui(self.quit_app)
                    else:
                        self.log(f"خطأ في تثبيت التحديث: {apply_err}")
                        self.ui(lambda: messagebox.showerror("خطأ في التحديث", apply_err))
                else:
                    self.log(f"فشل تنزيل التحديث: {err}")
                    self.ui(lambda: messagebox.showerror(
                        "خطأ في التحديث",
                        f"تعذر تنزيل ملف Nexus.zip تلقائياً ({err}).\nيرجى تنزيله يدوياً من صفحة GitHub."
                    ))

            threading.Thread(target=_work, daemon=True).start()

    # ---------- بناء الواجهة ----------
    def build_ui(self):
        try:
            self._steam_cache = [self.steam_tree.item(i, "values") for i in self.steam_tree.get_children()]
        except Exception:
            pass
        for attr in ("sidebar", "content_container"):
            old = getattr(self, attr, None)
            if old is not None:
                try:
                    old.destroy()
                except Exception:
                    pass
        self.pages = {}
        self.nav_buttons = {}
        self.nav_icons = {}
        self._build_sidebar()

        self.content_container = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.content_container.pack(side="right", fill="both", expand=True, padx=25, pady=20)

        # حاوية التحديث (مخفية تلقائياً ولا تأخذ أي مساحة إلا عند توفر تحديث)
        self.update_banner_container = ctk.CTkFrame(self.content_container, fg_color="transparent")

        self.build_page_home()
        self.build_page_editor()
        self.build_page_profiles()
        self.build_page_audio()
        self.build_page_steam_add()
        self.build_page_steam_accounts()
        self.build_page_steam_about()
        self.build_page_log()
        self.build_page_settings()
        self.build_page_about()
        self._steam_init()

    def _nav_button(self, parent, pid, name, ic, indent=12):
        btn = ctk.CTkButton(
            parent, text=f"  {name}", image=ico(ic, "#94A3B8", 18),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="transparent", hover_color="#141C2B", text_color="#94A3B8",
            height=38, corner_radius=10, anchor="w", command=lambda p=pid: self.show_page(p))
        btn.pack(fill="x", padx=(indent, 12), pady=2)
        self.nav_buttons[pid] = btn
        self.nav_icons[pid] = ic

    def _build_sidebar(self):
        acc = self.get_accent()
        self.sidebar = ctk.CTkFrame(self, width=270, corner_radius=0, fg_color=SIDEBAR)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        logo = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo.pack(fill="x", pady=(24, 14), padx=18)
        ctk.CTkLabel(logo, text="", image=ico("bolt", acc, 28)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(logo, text="NEXUS", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
                     text_color=acc).pack(side="left")

        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.pack(side="bottom", fill="x", pady=14, padx=12)
        self.footer_active = tk.Label(footer, text="", font=("Segoe UI", 9, "bold"), fg=acc, bg=SIDEBAR)
        self.footer_active.pack(pady=(0, 6))
        ctk.CTkLabel(footer, text="NEXUS", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                     text_color=acc).pack()
        ctk.CTkLabel(footer, text=f"v{APP_VERSION}", font=ctk.CTkFont(family="Segoe UI", size=9),
                     text_color="#64748B").pack()

        glob_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        glob_frame.pack(side="bottom", fill="x", pady=(0, 4))
        ctk.CTkFrame(glob_frame, height=1, fg_color="#1A253D").pack(fill="x", padx=16, pady=(0, 6))
        for pid, name, ic in NAV_GLOBAL:
            self._nav_button(glob_frame, pid, name, ic)

        host = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        host.pack(fill="both", expand=True)

        self.nav_groups = {}
        open_state = self.settings.get("nav_open", {})
        if not isinstance(open_state, dict):
            open_state = {}
        for gid, gname, gicon, children in NAV_GROUPS:
            is_open = bool(open_state.get(gid, True))
            hdr = ctk.CTkButton(
                host, text=f"  {gname}", image=ico(gicon, acc, 20), anchor="w", height=42,
                fg_color="#0F1626", hover_color="#141C2B", text_color=acc, corner_radius=10,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                command=lambda g=gid: self.toggle_nav_group(g))
            hdr.pack(fill="x", padx=12, pady=(8, 2))
            chev = ctk.CTkLabel(host, text="", image=ico("down" if is_open else "right", MUTED, 14),
                                fg_color="#0F1626", width=20)
            chev.place(in_=hdr, relx=1.0, x=-14, rely=0.5, anchor="e")
            chev.bind("<Button-1>", lambda e, g=gid: self.toggle_nav_group(g))
            body = ctk.CTkFrame(host, fg_color="transparent")
            if is_open:
                body.pack(fill="x")
            self.nav_groups[gid] = {"hdr": hdr, "chev": chev, "body": body, "open": is_open}
            for pid, name, ic in children:
                self._nav_button(body, pid, name, ic, indent=26)

    def toggle_nav_group(self, gid, force=None):
        g = self.nav_groups.get(gid)
        if not g:
            return
        new = (not g["open"]) if force is None else force
        if new == g["open"]:
            return
        g["open"] = new
        if new:
            g["body"].pack(fill="x", after=g["hdr"])
        else:
            g["body"].pack_forget()
        g["chev"].configure(image=ico("down" if new else "right", MUTED, 14))
        try:
            st = self.settings.setdefault("nav_open", {})
            st[gid] = new
            save_data(CONFIG_FILE, self.settings)
        except Exception:
            pass

    def show_page(self, page_id):
        if self.is_recording and page_id != "editor":
            self._stop_recording()
        self.current_page_id = page_id
        for p in self.pages.values():
            p.pack_forget()

        highlight = "home" if page_id == "editor" else page_id
        active_group = PAGE_GROUP.get(page_id)
        for pid, btn in self.nav_buttons.items():
            if pid == highlight:
                btn.configure(fg_color=self.theme["btn"], hover_color=self.theme["btn_hover"], text_color="white",
                              image=ico(self.nav_icons[pid], "#FFFFFF", 18))
            else:
                btn.configure(fg_color="transparent", text_color="#94A3B8",
                              image=ico(self.nav_icons[pid], "#94A3B8", 18))
        for gid, g in self.nav_groups.items():
            col = "#152238" if gid == active_group else "#0F1626"
            g["hdr"].configure(fg_color=col)
            g["chev"].configure(fg_color=col)
        if active_group:
            self.toggle_nav_group(active_group, True)

        if page_id in self.pages:
            self.pages[page_id].pack(fill="both", expand=True)

        if page_id == "home":
            self.populate_home_profiles()
            self.refresh_stats()
        elif page_id == "profiles":
            self.populate_manage_profiles()
        elif page_id == "audio":
            self.populate_audio_page()
        elif page_id in ("steam_add", "steam_accounts"):
            self.refresh_steam_users()
        elif page_id == "log":
            self._render_log_if_visible()

    def _page_header(self, parent, title, subtitle):
        lbl = ctk.CTkLabel(parent, text=title, font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
                           text_color=self.get_accent())
        lbl.pack(anchor="w", pady=(0, 4))
        tk.Label(parent, text=subtitle, font=("Segoe UI", 11), fg=MUTED, bg=BG).pack(anchor="w", pady=(0, 14))
        return lbl

    def _card(self, parent, **kw):
        return ctk.CTkFrame(parent, fg_color=kw.pop("fg_color", CARD), corner_radius=12, border_width=1,
                            border_color=kw.pop("border_color", BORDER), **kw)

    def _profile_style(self, data):
        ck = data.get("color")
        if ck in PROFILE_COLORS:
            return PROFILE_COLORS[ck]["text"], PROFILE_COLORS[ck]["bg"]
        return self.get_accent(), "#1E3A5F"

    def _details_text(self, data):
        parts = [data.get("display", ""), data.get("audio", "")]
        s = "  |  ".join(p for p in parts if p)
        if data.get("hdr") == "toggle":
            s += "  |  HDR"
        if isinstance(data.get("volume"), int):
            s += f"  |  {data['volume']}%"
        if data.get("launch"):
            s += "  |  + تشغيل تطبيق"
        return s

    # ==========================================
    # صفحة 1: الرئيسية
    # ==========================================
    def _stat_card(self, parent, icon, title):
        # زيادة الهامش ومنع فيضان النصوص
        c = self._card(parent, height=84)
        c.pack(side="right", fill="x", expand=True, padx=6)
        c.pack_propagate(False)

        # حاوية الأيقونة باليمين
        ib = ctk.CTkFrame(c, width=44, height=44, corner_radius=10, fg_color=FIELD)
        ib.pack(side="right", padx=(8, 12), pady=20)
        ib.pack_propagate(False)
        ctk.CTkLabel(ib, text="", image=ico(icon, self.get_accent(), 22)).pack(expand=True)

        # حاوية النصوص باليسار مع تحديد هوامش أمان
        tb = tk.Frame(c, bg=CARD)
        tb.pack(side="right", fill="both", expand=True, padx=(10, 0))

        tk.Label(tb, text=title, font=("Segoe UI", 9), fg=MUTED, bg=CARD, anchor="e").pack(fill="x", pady=(18, 2))
        val = tk.Label(tb, text="—", font=("Segoe UI", 11, "bold"), fg=TXT, bg=CARD, anchor="e")
        val.pack(fill="x")
        return val

    def build_page_home(self):
        p = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.pages["home"] = p

        self._page_header(p, "NexusFlow | Display & Audio Manager", "تحكم فوري في إعدادات العرض والشاشات ومخارج الصوت وأوضاع اللعب")

        stats = ctk.CTkFrame(p, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 14))
        self.stat_count = self._stat_card(stats, "layers", "الأوضاع المحفوظة")
        self.stat_audio = self._stat_card(stats, "speaker", "مخرج الصوت الحالي")
        self.stat_active = self._stat_card(stats, "bolt", "آخر وضع تم تفعيله")

        bar = ctk.CTkFrame(p, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(bar, text="  وضع جديد", image=ico("plus", "#05101A", 18), height=38, width=140,
                      fg_color=self.get_accent(), hover_color=self.theme["btn_hover"], text_color="#05101A",
                      font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), corner_radius=10,
                      command=lambda: self.open_editor(None)).pack(side="right", padx=(10, 0))
        tk.Label(bar, text=":الأوضاع الجاهزة (PROFILES)", font=("Segoe UI", 12, "bold"), fg=TXT, bg=BG).pack(side="right", padx=(0, 10))
        self.search_entry = ctk.CTkEntry(bar, placeholder_text="ابحث عن وضع...", height=36, corner_radius=10,
                                         fg_color=FIELD, border_color="#243048", width=260,
                                         font=ctk.CTkFont(family="Segoe UI", size=12))
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", lambda e: self.populate_home_profiles())

        self.home_cards_scroll = ctk.CTkScrollableFrame(p, fg_color="transparent", corner_radius=0)
        self.home_cards_scroll.pack(fill="both", expand=True)

    def refresh_stats(self):
        try:
            self.stat_count.configure(text=str(len(self.profiles)))
            # تقصير عدد الحروف إلى 20 حرفاً كحد أقصى لمنع تمدد وكسر المربع
            self.stat_audio.configure(text=_short(self.current_audio, 20) or "—")
            self.stat_active.configure(text=_short(self.active_profile, 20) or "—")
            self.footer_active.configure(text=(f"الوضع النشط: {_short(self.active_profile, 20)}" if self.active_profile else ""))
        except Exception:
            pass
        
        
    def populate_home_profiles(self):
        for w in self.home_cards_scroll.winfo_children():
            w.destroy()

        q = ""
        try:
            q = self.search_entry.get().strip().lower()
        except Exception:
            pass

        items = [(n, d) for n, d in self.profiles.items()
                 if not q or q in (n + " " + d.get("audio", "") + " " + d.get("display", "")).lower()]

        if not items:
            msg = "لا يوجد أوضاع محفوظة حالياً. اضغط «وضع جديد» لإضافة وضعك الأول!" if not self.profiles else "لا توجد نتائج مطابقة للبحث."
            tk.Label(self.home_cards_scroll, text=msg, font=("Segoe UI", 12), fg="#64748B", bg=BG).pack(pady=60)
            return

        for name, data in items:
            t_color, b_bg = self._profile_style(data)
            active = (name == self.active_profile)
            card = ctk.CTkFrame(self.home_cards_scroll, height=78, corner_radius=12, fg_color=CARD2,
                                border_width=1, border_color=(t_color if active else "#1A253D"))
            card.pack(fill="x", pady=4)
            card.pack_propagate(False)

            ibox = ctk.CTkFrame(card, width=50, height=50, corner_radius=12, fg_color=b_bg)
            ibox.pack(side="right", padx=(6, 14), pady=14)
            ibox.pack_propagate(False)
            ctk.CTkLabel(ibox, text="", image=ico(icon_key_for(data.get("icon")), t_color, 28)).pack(expand=True)

            ctk.CTkButton(card, text="", image=ico("trash", "#EF4444", 18), width=38, height=38, fg_color="#2D1515",
                          hover_color="#451818", corner_radius=8,
                          command=lambda n=name: self.delete_profile(n)).pack(side="left", padx=(14, 6))
            ctk.CTkButton(card, text="", image=ico("copy", "#94A3B8", 18), width=38, height=38, fg_color="#182236",
                          hover_color="#23324E", corner_radius=8,
                          command=lambda n=name: self.duplicate_profile(n)).pack(side="left", padx=(0, 6))
            ctk.CTkButton(card, text="", image=ico("edit", "#38BDF8", 18), width=38, height=38, fg_color="#182236",
                          hover_color="#23324E", corner_radius=8,
                          command=lambda n=name: self.edit_profile(n)).pack(side="left", padx=(0, 8))
            ctk.CTkButton(card, text="  تفعيل", image=ico("play", "#05101A", 14), width=100, height=38,
                          fg_color=self.get_accent(), hover_color=self.theme["btn_hover"], text_color="#05101A",
                          font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), corner_radius=8,
                          command=lambda n=name, d=data: self.apply_profile_async(n, d)).pack(side="left", padx=(0, 10))

            hk = data.get("hotkey", "").strip()
            if hk:
                badge = ctk.CTkFrame(card, corner_radius=8, fg_color="#2D1B4E")
                badge.pack(side="left", padx=(0, 10))
                ctk.CTkLabel(badge, text=f" {hk.upper()}", image=ico("keyboard", "#C084FC", 16), compound="left",
                             font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                             text_color="#C084FC").pack(padx=10, pady=6)

            txt = tk.Frame(card, bg=CARD2)
            txt.pack(side="right", fill="both", expand=True)
            row = tk.Frame(txt, bg=CARD2)
            row.pack(fill="x", pady=(16, 0))
            tk.Label(row, text=name, font=("Segoe UI", 13, "bold"), fg=t_color, bg=CARD2, anchor="e").pack(side="right")
            if active:
                ctk.CTkLabel(row, text=" نشط ", image=ico("star", "#05101A", 12), compound="left", corner_radius=6,
                             fg_color=t_color, text_color="#05101A",
                             font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold")).pack(side="right", padx=8)
            tk.Label(txt, text=_short(self._details_text(data), 95), font=("Segoe UI", 9), fg=MUTED, bg=CARD2,
                     anchor="e").pack(fill="x", pady=(2, 0))

    # ==========================================
    # صفحة المحرر: إضافة / تعديل وضع
    # ==========================================
    def _row(self, parent):
        r = ctk.CTkFrame(parent, fg_color="transparent")
        r.pack(fill="x", padx=22, pady=8)
        return r

    def _flabel(self, row, text, icon=None, width=14):
        if icon:
            ctk.CTkLabel(row, text="", image=ico(icon, self.get_accent(), 18)).pack(side="right", padx=(8, 0))
        lbl = tk.Label(row, text=text, font=("Segoe UI", 11, "bold"), fg=TXT, bg=CARD, width=width, anchor="e")
        lbl.pack(side="right")
        return lbl

    def build_page_editor(self):
        p = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.pages["editor"] = p

        head = ctk.CTkFrame(p, fg_color="transparent")
        head.pack(fill="x", pady=(0, 12))
        ctk.CTkButton(head, text="  رجوع", image=ico("back", MUTED, 16), width=100, height=34, fg_color=FIELD,
                      hover_color="#1E3354", text_color=MUTED, corner_radius=8,
                      font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                      command=self.cancel_edit).pack(side="right")
        self.editor_title = ctk.CTkLabel(head, text="وضع جديد", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
                                         text_color=self.get_accent())
        self.editor_title.pack(side="left")

        bottom = ctk.CTkFrame(p, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", pady=(12, 0))
        ctk.CTkButton(bottom, text="إلغاء", width=110, height=42, fg_color="#3B1824", hover_color="#501B2E",
                      text_color="#FF8888", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                      corner_radius=10, command=self.cancel_edit).pack(side="left", padx=(0, 10))
        self.btn_save_apply = ctk.CTkButton(bottom, text="  حفظ وتفعيل الآن", image=ico("bolt", "white", 16), height=42,
                                            fg_color=self.theme["btn"], hover_color=self.theme["btn_hover"],
                                            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), corner_radius=10,
                                            command=lambda: self.save_profile(apply_now=True))
        self.btn_save_apply.pack(side="right", fill="x", expand=True, padx=(10, 0))
        self.btn_save = ctk.CTkButton(bottom, text="  حفظ الوضع", image=ico("check", "white", 16), height=42, width=170,
                                      fg_color="#059669", hover_color="#047857",
                                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), corner_radius=10,
                                      command=lambda: self.save_profile(apply_now=False))
        self.btn_save.pack(side="right")

        form = ctk.CTkScrollableFrame(p, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
        form.pack(fill="both", expand=True)

        r = self._row(form)
        self._flabel(r, ":اسم الوضع", "gear")
        self.name_entry = ctk.CTkEntry(r, placeholder_text="اكتب اسم الوضع...", font=ctk.CTkFont(family="Segoe UI", size=12),
                                       fg_color=FIELD, border_color="#243048", height=36, corner_radius=8)
        self.name_entry.pack(side="left", fill="x", expand=True, padx=(0, 15))

        r = self._row(form)
        self._flabel(r, ":الأيقونة", "star")
        self.icon_btns = {}
        for em, key, label in PROFILE_ICONS:
            b = ctk.CTkButton(r, text="", image=ico(key, TXT, 22), width=46, height=42, corner_radius=10,
                              fg_color=FIELD, hover_color="#1E3354", border_width=2, border_color="#243048",
                              command=lambda e=em: self._select_icon(e))
            b.pack(side="right", padx=3)
            self.icon_btns[em] = b

        r = self._row(form)
        self._flabel(r, ":اللون", "sun")
        self.color_btns = {}
        for cname, cd in PROFILE_COLORS.items():
            b = ctk.CTkButton(r, text="", width=34, height=34, corner_radius=17, fg_color=cd["text"],
                              hover_color=cd["text"], border_width=0, border_color="white",
                              command=lambda c=cname: self._select_color(c))
            b.pack(side="right", padx=5)
            self.color_btns[cname] = b
        self.color_name_lbl = tk.Label(r, text="", font=("Segoe UI", 10), fg=MUTED, bg=CARD)
        self.color_name_lbl.pack(side="left")

        r = self._row(form)
        self._flabel(r, ":مفتاح الاختصار", "keyboard")
        ctk.CTkButton(r, text="", image=ico("x", "#F87171", 14), width=36, height=34, fg_color="#3B1824",
                      hover_color="#501B2E", corner_radius=8, command=self.clear_hotkey).pack(side="left", padx=(0, 8))
        self.btn_key_capture = ctk.CTkButton(r, text="  اضغط لاختيار زر", image=ico("keyboard", "#38BDF8", 16), height=34,
                                             fg_color="#16233B", hover_color="#1E3354", text_color="#38BDF8",
                                             font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                                             corner_radius=8, command=self.start_key_listen)
        self.btn_key_capture.pack(side="left", padx=(0, 15))
        self.var_shift = ctk.BooleanVar(value=False)
        self.var_alt = ctk.BooleanVar(value=False)
        self.var_ctrl = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(r, text="SHIFT", variable=self.var_shift, font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                        text_color="#FBBF24", fg_color="#F59E0B", corner_radius=6, width=65).pack(side="left", padx=4)
        ctk.CTkCheckBox(r, text="ALT", variable=self.var_alt, font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                        text_color="#38BDF8", fg_color="#0284C7", corner_radius=6, width=60).pack(side="left", padx=4)
        ctk.CTkCheckBox(r, text="CTRL", variable=self.var_ctrl, font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                        text_color="#C084FC", fg_color="#7C3AED", corner_radius=6, width=65).pack(side="left", padx=4)

        r = self._row(form)
        self._flabel(r, ":وضع العرض", "monitor")
        self.display_combobox = ctk.CTkComboBox(r, values=[d[0] for d in DISPLAY_MODES], height=36, corner_radius=8,
                                                fg_color=FIELD, border_color="#243048", dropdown_fg_color=CARD,
                                                font=ctk.CTkFont(family="Segoe UI", size=11))
        self.display_combobox.set(DISPLAY_MODES[0][0])
        self.display_combobox.pack(side="left", fill="x", expand=True, padx=(0, 15))

        r = self._row(form)
        self._flabel(r, ":مخرج الصوت", "speaker")
        self.audio_combobox = ctk.CTkComboBox(r, values=self.audio_devices or ["Default Audio"], height=36, corner_radius=8,
                                              fg_color=FIELD, border_color="#243048", dropdown_fg_color=CARD,
                                              font=ctk.CTkFont(family="Segoe UI", size=11))
        self.audio_combobox.set((self.audio_devices or ["Default Audio"])[0])
        self.audio_combobox.pack(side="left", fill="x", expand=True, padx=(0, 15))

        r = self._row(form)
        self._flabel(r, ":مستوى الصوت", "speaker")
        self.vol_enabled = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(r, text="ضبط عند التفعيل", variable=self.vol_enabled, command=self._toggle_vol_state,
                        font=ctk.CTkFont(family="Segoe UI", size=11), text_color=MUTED, corner_radius=6,
                        width=130).pack(side="right", padx=10)
        self.vol_val_lbl = tk.Label(r, text="50%", font=("Segoe UI", 11, "bold"), fg=self.get_accent(), bg=CARD, width=5)
        self.vol_val_lbl.pack(side="left")
        self.vol_editor_slider = ctk.CTkSlider(r, from_=0, to=100, number_of_steps=100, button_color=self.get_accent(),
                                               progress_color=self.theme["btn"], state="disabled",
                                               command=lambda v: self.vol_val_lbl.configure(text=f"{int(v)}%"))
        self.vol_editor_slider.set(50)
        self.vol_editor_slider.pack(side="left", fill="x", expand=True, padx=10)

        r = self._row(form)
        self._flabel(r, ":إعدادات HDR", "sun")
        self.hdr_var = ctk.StringVar(value="none")
        ctk.CTkRadioButton(r, text="بدون تغيير", variable=self.hdr_var, value="none", text_color=MUTED,
                           font=ctk.CTkFont(family="Segoe UI", size=11)).pack(side="left", padx=15)
        ctk.CTkRadioButton(r, text="تبديل HDR (تفعيل / إيقاف)", variable=self.hdr_var, value="toggle", text_color="#00FF88",
                           font=ctk.CTkFont(family="Segoe UI", size=11)).pack(side="left", padx=15)

        r = self._row(form)
        self._flabel(r, ":تشغيل تطبيق", "folder")
        ctk.CTkButton(r, text="", image=ico("x", "#F87171", 14), width=36, height=34, fg_color="#3B1824",
                      hover_color="#501B2E", corner_radius=8,
                      command=lambda: self.launch_entry.delete(0, tk.END)).pack(side="left", padx=(0, 8))
        ctk.CTkButton(r, text="  استعراض", image=ico("folder", "#38BDF8", 16), width=110, height=34, fg_color="#16233B",
                      hover_color="#1E3354", text_color="#38BDF8", corner_radius=8,
                      font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                      command=self._browse_launch).pack(side="left", padx=(0, 10))
        self.launch_entry = ctk.CTkEntry(r, placeholder_text="اختياري: مسار برنامج أو رابط (مثل steam://...) يُشغَّل مع الوضع",
                                         fg_color=FIELD, border_color="#243048", height=36, corner_radius=8,
                                         font=ctk.CTkFont(family="Segoe UI", size=11))
        self.launch_entry.pack(side="left", fill="x", expand=True, padx=(0, 15))

        self._refresh_icon_picker()
        self._refresh_color_picker()

    def _toggle_vol_state(self):
        self.vol_editor_slider.configure(state="normal" if self.vol_enabled.get() else "disabled")

    def _browse_launch(self):
        f = filedialog.askopenfilename(filetypes=[("Programs / Shortcuts", "*.exe *.lnk *.bat"), ("All files", "*.*")])
        if f:
            self.launch_entry.delete(0, tk.END)
            self.launch_entry.insert(0, f)

    def _select_icon(self, em):
        self.sel_icon = em
        self._refresh_icon_picker()

    def _refresh_icon_picker(self):
        for em, b in self.icon_btns.items():
            sel = (em == self.sel_icon)
            b.configure(border_color=(self.get_accent() if sel else "#243048"), fg_color=("#1B2A45" if sel else FIELD))

    def _select_color(self, cname):
        self.sel_color = cname
        self._refresh_color_picker()

    def _refresh_color_picker(self):
        for cname, b in self.color_btns.items():
            b.configure(border_width=(3 if cname == self.sel_color else 0))
        self.color_name_lbl.configure(text=self.sel_color)

    def open_editor(self, name=None):
        self.editing_key = name
        self._reset_editor()
        if name and name in self.profiles:
            self._fill_editor(name, self.profiles[name])
            self.editor_title.configure(text=f"تعديل الوضع: {name}")
        else:
            self.editor_title.configure(text="وضع جديد")
        self.show_page("editor")

    def _reset_editor(self):
        self.name_entry.delete(0, tk.END)
        self.sel_icon = PROFILE_ICONS[0][0]
        self.sel_color = "أزرق"
        self._refresh_icon_picker()
        self._refresh_color_picker()
        self.primary_key = ""
        self.var_ctrl.set(True)
        self.var_alt.set(False)
        self.var_shift.set(False)
        self._refresh_key_button()
        self.display_combobox.set(DISPLAY_MODES[0][0])
        devs = self.audio_devices or ["Default Audio"]
        self.audio_combobox.configure(values=devs)
        self.audio_combobox.set(self.current_audio if self.current_audio in devs else devs[0])
        self.vol_enabled.set(False)
        self.vol_editor_slider.set(50)
        self.vol_val_lbl.configure(text="50%")
        self._toggle_vol_state()
        self.hdr_var.set("none")
        self.launch_entry.delete(0, tk.END)

    def _fill_editor(self, name, data):
        self.name_entry.insert(0, name)
        self.sel_icon = canonical_icon(data.get("icon"))
        self.sel_color = data.get("color") if data.get("color") in PROFILE_COLORS else "أزرق"
        self._refresh_icon_picker()
        self._refresh_color_picker()

        hk = data.get("hotkey", "").strip().lower()
        self.var_ctrl.set(False)
        self.var_alt.set(False)
        self.var_shift.set(False)
        self.primary_key = ""
        if hk:
            for part in hk.split("+"):
                part = part.strip()
                if part == "ctrl":
                    self.var_ctrl.set(True)
                elif part == "alt":
                    self.var_alt.set(True)
                elif part == "shift":
                    self.var_shift.set(True)
                elif part:
                    self.primary_key = part
        self._refresh_key_button()

        self.display_combobox.set(data.get("display", DISPLAY_MODES[0][0]))
        self.audio_combobox.set(data.get("audio", ""))
        self.hdr_var.set(data.get("hdr", "none"))

        vol = data.get("volume")
        if isinstance(vol, int):
            self.vol_enabled.set(True)
            self.vol_editor_slider.set(vol)
            self.vol_val_lbl.configure(text=f"{vol}%")
        self._toggle_vol_state()

        if data.get("launch"):
            self.launch_entry.insert(0, data["launch"])

    def cancel_edit(self):
        self._stop_recording()
        self.editing_key = None
        self.show_page("home")

    def _refresh_key_button(self):
        if self.primary_key:
            self.btn_key_capture.configure(text=f"  زر: {self.primary_key.upper()}", fg_color="#16233B", text_color="#00FF88")
        else:
            self.btn_key_capture.configure(text="  اضغط لاختيار زر", fg_color="#16233B", text_color="#38BDF8")

    def start_key_listen(self):
        self.is_recording = True
        self.btn_key_capture.configure(text="  [ اضغط الزر الآن... ]", fg_color="#7C3AED", text_color="white")
        self.bind("<KeyPress>", self._on_key_captured)

    def _stop_recording(self):
        if self.is_recording:
            try:
                self.unbind("<KeyPress>")
            except Exception:
                pass
            self.is_recording = False
            try:
                self._refresh_key_button()
            except Exception:
                pass

    def _on_key_captured(self, event):
        k = event.keysym.lower()
        if k in ['control_l', 'control_r', 'alt_l', 'alt_r', 'shift_l', 'shift_r', 'win_l', 'win_r', 'caps_lock']:
            return
        if k == "escape":
            self._stop_recording()
            return

        if event.char and event.char.isalnum():
            k = event.char.lower()
        elif k.startswith("kp_"):
            k = k.replace("kp_", "")
        else:
            k = KEYSYM_MAP.get(k, k)

        self.primary_key = k
        self.unbind("<KeyPress>")
        self.is_recording = False
        self._refresh_key_button()

    def clear_hotkey(self):
        self._stop_recording()
        self.primary_key = ""
        self._refresh_key_button()

    def build_full_hotkey_string(self):
        if not self.primary_key:
            return ""
        parts = []
        if self.var_ctrl.get():
            parts.append("ctrl")
        if self.var_alt.get():
            parts.append("alt")
        if self.var_shift.get():
            parts.append("shift")
        parts.append(self.primary_key)
        return "+".join(parts)

    def edit_profile(self, name, data=None):
        self.open_editor(name)

    def save_profile(self, apply_now=False):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("تنبيه", "يرجى كتابة اسم للوضع أولاً!")
            return

        if name in self.profiles and name != self.editing_key:
            if not messagebox.askyesno("الاسم مستخدم", f"يوجد وضع باسم '{name}' مسبقاً. هل تريد استبداله؟"):
                return

        hk = self.build_full_hotkey_string()
        if hk:
            try:
                keyboard.parse_hotkey(hk)
            except Exception:
                messagebox.showerror("اختصار غير صالح", f"الاختصار '{hk}' غير مدعوم. جرّب زراً آخر.")
                return
            for other, od in self.profiles.items():
                if other != self.editing_key and other != name and od.get("hotkey", "").strip().lower() == hk.lower():
                    if not messagebox.askyesno("تعارض اختصار", f"الاختصار {hk.upper()} مستخدم في وضع '{other}'.\nهل تريد المتابعة على أي حال؟"):
                        return
                    break

        disp = self.display_combobox.get()
        entry = {
            "display": disp,
            "display_mode": MODE_MAP.get(disp, "extend"),
            "audio": self.audio_combobox.get(),
            "hdr": self.hdr_var.get(),
            "hotkey": hk,
            "color": self.sel_color,
            "icon": self.sel_icon,
        }
        if self.vol_enabled.get():
            entry["volume"] = int(self.vol_editor_slider.get())
        launch = self.launch_entry.get().strip()
        if launch:
            entry["launch"] = launch

        new = {}
        for k, v in self.profiles.items():
            if k == self.editing_key or (self.editing_key is None and k == name):
                new[name] = entry
            elif k == name:
                continue
            else:
                new[k] = v
        if name not in new:
            new[name] = entry

        if self.editing_key and self.editing_key != name and self.active_profile == self.editing_key:
            self.active_profile = name
            self.settings["last_profile"] = name
            save_data(CONFIG_FILE, self.settings)

        self.profiles = new
        self.editing_key = None
        self._stop_recording()
        self.commit_profiles()
        self.log(f"تم حفظ الوضع: {name}")
        self.show_page("home")
        self.toast("تم حفظ الوضع بنجاح")
        if apply_now:
            self.apply_profile_async(name, entry)

    def commit_profiles(self, hotkeys=True):
        save_data(PROFILES_FILE, self.profiles)
        if hotkeys:
            self.register_all_hotkeys()
        self.update_tray_menu()
        self.refresh_stats()

    def delete_profile(self, name):
        if messagebox.askyesno("تأكيد الحذف", f"هل ترغب في حذف وضع '{name}'؟"):
            if name in self.profiles:
                del self.profiles[name]
                if self.active_profile == name:
                    self.active_profile = ""
                    self.settings["last_profile"] = ""
                    save_data(CONFIG_FILE, self.settings)
                self.commit_profiles()
                self.log(f"تم حذف الوضع: {name}")
                self._refresh_current_lists()

    def duplicate_profile(self, name):
        if name not in self.profiles:
            return
        base = f"{name} (نسخة)"
        new_name, i = base, 2
        while new_name in self.profiles:
            new_name = f"{base} {i}"
            i += 1
        copy = dict(self.profiles[name])
        copy["hotkey"] = ""
        new = {}
        for k, v in self.profiles.items():
            new[k] = v
            if k == name:
                new[new_name] = copy
        self.profiles = new
        self.commit_profiles()
        self.log(f"تم نسخ الوضع: {name}")
        self._refresh_current_lists()
        self.toast("تم إنشاء نسخة (بدون اختصار)")

    def move_profile(self, name, delta):
        keys = list(self.profiles.keys())
        if name not in keys:
            return
        i = keys.index(name)
        j = i + delta
        if 0 <= j < len(keys):
            keys[i], keys[j] = keys[j], keys[i]
            self.profiles = {k: self.profiles[k] for k in keys}
            self.commit_profiles(hotkeys=False)
            self._refresh_current_lists()

    def _refresh_current_lists(self):
        if self.current_page_id == "home":
            self.populate_home_profiles()
        elif self.current_page_id == "profiles":
            self.populate_manage_profiles()

    # ==========================================
    # صفحة 2: إدارة الأوضاع
    # ==========================================
    def build_page_profiles(self):
        p = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.pages["profiles"] = p

        self._page_header(p, "Profiles Studio | إدارة واستيراد الأوضاع", "يمكنك أخذ نسخة احتياطية من جميع أوضاعك واسترجاعها بضغطة زر")

        tools = self._card(p)
        tools.pack(fill="x", pady=(0, 15), padx=2)
        ti = ctk.CTkFrame(tools, fg_color="transparent")
        ti.pack(fill="x", padx=15, pady=12)

        bf = ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        ctk.CTkButton(ti, text="  استيراد أوضاع من ملف", image=ico("download", "white", 16), fg_color=self.theme["btn"],
                      hover_color=self.theme["btn_hover"], font=bf, height=36, corner_radius=8,
                      command=self.import_profiles_action).pack(side="left", padx=5)
        ctk.CTkButton(ti, text="  تصدير نسخة احتياطية", image=ico("upload", "white", 16), fg_color="#059669",
                      hover_color="#10B981", font=bf, height=36, corner_radius=8,
                      command=self.export_profiles_action).pack(side="left", padx=5)
        ctk.CTkButton(ti, text="  حذف جميع الأوضاع", image=ico("trash", "white", 16), fg_color="#991B1B",
                      hover_color="#DC2626", font=bf, height=36, corner_radius=8,
                      command=self.clear_all_profiles).pack(side="right", padx=5)

        self.manage_scroll = ctk.CTkScrollableFrame(p, fg_color="transparent")
        self.manage_scroll.pack(fill="both", expand=True)

    def populate_manage_profiles(self):
        for w in self.manage_scroll.winfo_children():
            w.destroy()

        if not self.profiles:
            tk.Label(self.manage_scroll, text="لا توجد أوضاع محفوظة حالياً.", font=("Segoe UI", 13),
                     fg="#64748B", bg=BG).pack(pady=40)
            return

        for name, data in self.profiles.items():
            t_color, b_bg = self._profile_style(data)
            card = ctk.CTkFrame(self.manage_scroll, height=68, fg_color=CARD2, corner_radius=12,
                                border_width=1, border_color="#1A253D")
            card.pack(fill="x", pady=5, padx=5)
            card.pack_propagate(False)

            ibox = ctk.CTkFrame(card, width=42, height=42, corner_radius=10, fg_color=b_bg)
            ibox.pack(side="right", padx=(6, 14), pady=13)
            ibox.pack_propagate(False)
            ctk.CTkLabel(ibox, text="", image=ico(icon_key_for(data.get("icon")), t_color, 24)).pack(expand=True)

            ctk.CTkButton(card, text="  حذف", image=ico("trash", "#F87171", 16), width=86, height=34, fg_color="#3B1824",
                          hover_color="#501B2E", text_color="#F87171", corner_radius=8,
                          font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                          command=lambda n=name: self.delete_profile(n)).pack(side="left", padx=(14, 6))
            for icn, dlt in (("down", 1), ("up", -1)):
                ctk.CTkButton(card, text="", image=ico(icn, MUTED, 16), width=34, height=34, fg_color="#182236",
                              hover_color="#23324E", corner_radius=8,
                              command=lambda n=name, dd=dlt: self.move_profile(n, dd)).pack(side="left", padx=(0, 6))
            ctk.CTkButton(card, text="", image=ico("copy", MUTED, 16), width=34, height=34, fg_color="#182236",
                          hover_color="#23324E", corner_radius=8,
                          command=lambda n=name: self.duplicate_profile(n)).pack(side="left", padx=(0, 6))
            ctk.CTkButton(card, text="", image=ico("edit", "#38BDF8", 16), width=34, height=34, fg_color="#182236",
                          hover_color="#23324E", corner_radius=8,
                          command=lambda n=name: self.edit_profile(n)).pack(side="left", padx=(0, 10))

            hk = data.get("hotkey", "").strip()
            ctk.CTkLabel(card, text=f" {hk.upper() if hk else 'بدون اختصار'}", image=ico("keyboard", "#C084FC", 16),
                         compound="left", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                         text_color="#C084FC").pack(side="left", padx=10)

            txt = tk.Frame(card, bg=CARD2)
            txt.pack(side="right", fill="both", expand=True)
            tk.Label(txt, text=name, font=("Segoe UI", 13, "bold"), fg=t_color, bg=CARD2, anchor="e").pack(fill="x", pady=(12, 0))
            tk.Label(txt, text=_short(self._details_text(data), 80), font=("Segoe UI", 9), fg=MUTED, bg=CARD2,
                     anchor="e").pack(fill="x")

    def export_profiles_action(self):
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if f:
            save_data(f, self.profiles)
            self.log("تم تصدير نسخة احتياطية")
            messagebox.showinfo("تم التصدير", "تم تصدير نسختك الاحتياطية بنجاح!")

    def import_profiles_action(self):
        f = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not f:
            return
        data = self._sanitize_profiles(load_data(f))
        if not data:
            messagebox.showerror("ملف غير صالح", "لم يتم العثور على أوضاع صالحة داخل هذا الملف.")
            return
        self.profiles.update(data)
        self.commit_profiles()
        self.populate_manage_profiles()
        self.log(f"تم استيراد {len(data)} وضع")
        messagebox.showinfo("تم الاستيراد", f"تم استيراد ودمج {len(data)} وضع بنجاح!")

    def clear_all_profiles(self):
        if messagebox.askyesno("تأكيد الحذف", "هل أنت متأكد من رغبتك في حذف جميع الأوضاع المحفوظة؟"):
            self.profiles = {}
            self.active_profile = ""
            self.settings["last_profile"] = ""
            save_data(CONFIG_FILE, self.settings)
            self.commit_profiles()
            self.populate_manage_profiles()
            self.log("تم حذف جميع الأوضاع")

    # ==========================================
    # صفحة 3: استوديو الصوت
    # ==========================================
    def build_page_audio(self):
        p = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.pages["audio"] = p

        self._page_header(p, "Audio Studio | استوديو ومختبر مخارج الصوت", "تحكم فوري بمخارج الصوت المتاحة في جهازك واختبر تشغيلها مباشرة")

        top = self._card(p)
        top.pack(fill="x", pady=(0, 12))
        tin = ctk.CTkFrame(top, fg_color="transparent")
        tin.pack(fill="x", padx=20, pady=14)
        bf = ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        ctk.CTkButton(tin, text="  تشغيل نغمة اختبار الصوت", image=ico("bell", "white", 16), fg_color=self.theme["btn"],
                      hover_color=self.theme["btn_hover"], font=bf, height=38, corner_radius=8,
                      command=lambda: threading.Thread(target=play_test_sound, daemon=True).start()).pack(side="left")
        ctk.CTkButton(tin, text="  إعادة فحص الأجهزة المتصلة", image=ico("refresh", TXT, 16), fg_color="#16233B",
                      hover_color="#1E3354", font=bf, height=38, corner_radius=8,
                      command=self.refresh_devices_ui).pack(side="right")

        vc = self._card(p)
        vc.pack(fill="x", pady=(0, 12))
        vi = ctk.CTkFrame(vc, fg_color="transparent")
        vi.pack(fill="x", padx=20, pady=14)
        ctk.CTkLabel(vi, text="", image=ico("speaker", self.get_accent(), 20)).pack(side="right", padx=(8, 0))
        tk.Label(vi, text=":مستوى الصوت الرئيسي", font=("Segoe UI", 11, "bold"), fg=TXT, bg=CARD).pack(side="right")
        self.vol_label = tk.Label(vi, text="—", font=("Segoe UI", 12, "bold"), fg=self.get_accent(), bg=CARD, width=5)
        self.vol_label.pack(side="left")
        self.vol_slider = ctk.CTkSlider(vi, from_=0, to=100, number_of_steps=100, button_color=self.get_accent(),
                                        progress_color=self.theme["btn"], command=self._on_master_volume)
        self.vol_slider.set(50)
        self.vol_slider.pack(side="left", fill="x", expand=True, padx=15)

        tk.Label(p, text=":الأجهزة ومخارج الصوت المتصلة حالياً", font=("Segoe UI", 12, "bold"), fg=TXT, bg=BG).pack(anchor="e", pady=(0, 8))
        self.audio_list_scroll = ctk.CTkScrollableFrame(p, fg_color="transparent")
        self.audio_list_scroll.pack(fill="both", expand=True)

    def _on_master_volume(self, v):
        v = int(v)
        self.vol_label.configure(text=f"{v}%")
        if self._vol_job:
            try:
                self.after_cancel(self._vol_job)
            except Exception:
                pass
        self._vol_job = self.after(400, lambda: threading.Thread(target=set_volume, args=(v,), daemon=True).start())

    def _is_active_dev(self, dev):
        a, b = dev.lower(), (self.current_audio or "").lower()
        return bool(b) and (a == b or a in b or b in a)

    def populate_audio_page(self):
        for w in self.audio_list_scroll.winfo_children():
            w.destroy()

        for dev in self.audio_devices:
            active = self._is_active_dev(dev)
            card = ctk.CTkFrame(self.audio_list_scroll, height=64, fg_color=CARD2, corner_radius=12, border_width=1,
                                border_color=(self.get_accent() if active else "#1A253D"))
            card.pack(fill="x", pady=5)
            card.pack_propagate(False)

            ibox = ctk.CTkFrame(card, width=40, height=40, corner_radius=10, fg_color=FIELD)
            ibox.pack(side="right", padx=(6, 14), pady=12)
            ibox.pack_propagate(False)
            ctk.CTkLabel(ibox, text="", image=ico("speaker", self.get_accent() if active else MUTED, 22)).pack(expand=True)

            if active:
                ctk.CTkLabel(card, text="  الجهاز الحالي", image=ico("check", "#05101A", 14), compound="left", corner_radius=8,
                             fg_color=self.get_accent(), text_color="#05101A", height=32, width=130,
                             font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(side="left", padx=14)
            else:
                ctk.CTkButton(card, text="  توجيه الصوت هنا", image=ico("bolt", "#05101A", 14), fg_color=self.get_accent(),
                              hover_color=self.theme["btn_hover"], text_color="#05101A", width=130,
                              font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), height=34, corner_radius=8,
                              command=lambda d=dev: self.route_audio(d)).pack(side="left", padx=14)

            tk.Label(card, text=dev, font=("Segoe UI", 12, "bold"), fg=TXT, bg=CARD2, anchor="e").pack(side="right", fill="x", expand=True)

    def route_audio(self, dev):
        def work():
            self.log(f"توجيه الصوت إلى: {dev}")
            set_audio_device(dev)
            time.sleep(0.6)
            cur = get_default_audio_device()
            self.ui(lambda: self._after_route(cur))
        threading.Thread(target=work, daemon=True).start()

    def _after_route(self, cur):
        self.current_audio = cur or self.current_audio
        self.refresh_stats()
        if self.current_page_id == "audio":
            self.populate_audio_page()
        self.toast("تم تغيير مخرج الصوت")

    def refresh_devices_ui(self):
        threading.Thread(target=self._bg_refresh_audio, args=(True,), daemon=True).start()

    def _bg_refresh_audio(self, announce=False):
        devices = get_audio_devices()
        cur = get_default_audio_device()
        vol = get_playback_volume()
        self.ui(lambda: self._apply_audio_info(devices, cur, vol, announce))

    def _apply_audio_info(self, devices, cur, vol, announce):
        self.audio_devices = devices
        self.current_audio = cur or self.current_audio
        try:
            self.audio_combobox.configure(values=devices)
            if not self.audio_combobox.get():
                self.audio_combobox.set(devices[0])
        except Exception:
            pass
        if vol is not None:
            try:
                self.vol_slider.set(vol)
                self.vol_label.configure(text=f"{vol}%")
            except Exception:
                pass
        self.refresh_stats()
        if self.current_page_id == "audio":
            self.populate_audio_page()
        if announce:
            self.toast("تم تحديث قائمة مخارج الصوت")

    # ==========================================
    # صفحة سجل النشاط
    # ==========================================
    def build_page_log(self):
        p = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.pages["log"] = p

        self._page_header(p, "Activity Log | سجل النشاط", "كل ما يحدث في البرنامج: تفعيل الأوضاع، تغيير الصوت، الأخطاء، التحديثات")

        tools = ctk.CTkFrame(p, fg_color="transparent")
        tools.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(tools, text="  مسح السجل", image=ico("trash", "#F87171", 16), fg_color="#3B1824", hover_color="#501B2E",
                      text_color="#F87171", height=34, corner_radius=8, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                      command=self._clear_log).pack(side="left")

        self.log_box = ctk.CTkTextbox(p, fg_color=CARD, border_width=1, border_color=BORDER, corner_radius=12,
                                      font=ctk.CTkFont(family="Consolas", size=12), text_color=TXT, wrap="word")
        self.log_box.pack(fill="both", expand=True)
        self.log_box.configure(state="disabled")

    def _clear_log(self):
        self.log_lines = []
        self._render_log_if_visible()

    def _render_log_if_visible(self):
        if self.current_page_id != "log":
            return
        try:
            self.log_box.configure(state="normal")
            self.log_box.delete("1.0", "end")
            self.log_box.insert("1.0", "\n".join(reversed(self.log_lines)) if self.log_lines else "السجل فارغ.")
            self.log_box.configure(state="disabled")
        except Exception:
            pass

    # ==========================================
    # صفحة 4: الإعدادات والثيمات
    # ==========================================
    def build_page_settings(self):
        p = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.pages["settings"] = p

        self._page_header(p, "Settings | إعدادات البرنامج والتخصيص الجمالي", "خصص ألوان الواجهة وسلوك البرنامج حسب تفضيلاتك")

        theme_card = self._card(p)
        theme_card.pack(fill="x", pady=(0, 15))
        tk.Label(theme_card, text=":اختر لون الثيم النيون المفضل", font=("Segoe UI", 12, "bold"), fg=TXT, bg=CARD).pack(anchor="e", padx=20, pady=(14, 8))

        cf = ctk.CTkFrame(theme_card, fg_color="transparent")
        cf.pack(fill="x", padx=20, pady=(0, 16))
        for code, label, hex_col in THEME_PALETTE:
            sel = (code == self.theme_key)
            ctk.CTkButton(cf, text=f"  {label}", image=(ico("check", "#05101A", 16) if sel else None), fg_color=hex_col,
                          hover_color=hex_col, text_color="#05101A", height=38, corner_radius=10,
                          border_width=(3 if sel else 0), border_color="white",
                          font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                          command=lambda c=code: self.change_theme(c)).pack(side="left", padx=5, expand=True, fill="x")

        sys_card = self._card(p)
        sys_card.pack(fill="x", pady=(0, 15))
        cbf = ctk.CTkFont(family="Segoe UI", size=12, weight="bold")

        self.startup_var = ctk.BooleanVar(value=is_startup_enabled())
        ctk.CTkCheckBox(sys_card, text="تشغيل البرنامج تلقائياً مع بداء النظام",
                        variable=self.startup_var, font=cbf, text_color=TXT, fg_color=self.theme["btn"],
                        corner_radius=6, command=self.toggle_startup).pack(anchor="e", padx=20, pady=(16, 10))

        self.tray_var = ctk.BooleanVar(value=self.settings.get("tray_close", True))
        ctk.CTkCheckBox(sys_card, text="تصغير البرنامج إلى شريط النظام عند الإغلاق",
                        variable=self.tray_var, font=cbf, text_color=TXT, fg_color=self.theme["btn"],
                        corner_radius=6, command=self.save_settings).pack(anchor="e", padx=20, pady=(0, 10))

        self.notif_var = ctk.BooleanVar(value=self.settings.get("notifications", True))
        ctk.CTkCheckBox(sys_card, text="إشعارات ويندوز عند تفعيل وضع والبرنامج في الخلفية",
                        variable=self.notif_var, font=cbf, text_color=TXT, fg_color=self.theme["btn"],
                        corner_radius=6, command=self.save_settings).pack(anchor="e", padx=20, pady=(0, 16))

        data_card = self._card(p)
        data_card.pack(fill="x")
        ctk.CTkButton(data_card, text="  فتح مجلد البيانات (profiles.json / config.json)", image=ico("folder", "#38BDF8", 16),
                      fg_color="#16233B", hover_color="#1E3354", text_color="#38BDF8", height=38, corner_radius=8,
                      font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                      command=lambda: os.startfile(APP_DIR)).pack(anchor="e", padx=20, pady=16)

    def change_theme(self, theme_key):
        self.theme_key = theme_key
        self.theme = THEMES.get(theme_key, THEMES["cyan"])
        self.settings["theme"] = theme_key
        save_data(CONFIG_FILE, self.settings)

        def rebuild():
            self.build_ui()
            self.show_page("settings")
            self.update_tray_icon()
            self.refresh_stats()
            self.toast("تم تطبيق الثيم الجديد")
        self.after(150, rebuild)

    def toggle_startup(self):
        val = self.startup_var.get()
        self.settings["startup"] = val
        save_data(CONFIG_FILE, self.settings)
        set_startup_registry(val)
        self.log("تم تفعيل التشغيل مع ويندوز" if val else "تم إيقاف التشغيل مع ويندوز")

    def save_settings(self):
        self.settings["tray_close"] = self.tray_var.get()
        self.settings["notifications"] = self.notif_var.get()
        save_data(CONFIG_FILE, self.settings)

    # ==========================================
    # صفحة 5: حول البرنامج
    # ==========================================
    def build_page_about(self):
        p = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.pages["about"] = p
        acc = self.get_accent()

        card = self._card(p)
        card.pack(fill="both", expand=True, padx=10, pady=10)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(expand=True)

        tr = ctk.CTkFrame(inner, fg_color="transparent")
        tr.pack(pady=(0, 6))
        ctk.CTkLabel(tr, text="", image=ico("bolt", acc, 40)).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(tr, text="NEXUS", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
                     text_color=acc).pack(side="left")

        tk.Label(inner, text="",
                 font=("Segoe UI", 12), fg=MUTED, bg=CARD).pack(pady=(0, 15))

        info = ctk.CTkFrame(inner, fg_color=FIELD, corner_radius=10, border_width=1, border_color="#243048")
        info.pack(pady=10, padx=20, fill="x")
        details = [
            ("الإصدار:", f"v{APP_VERSION}"),
            ("github:", GITHUB_REPO),
            ("الترخيص:", "مفتوح المصدر (Open Source)"),
            ("المطور:", "محمد"),
        ]
        for k, v in details:
            r = ctk.CTkFrame(info, fg_color="transparent")
            r.pack(fill="x", padx=15, pady=6)
            ctk.CTkLabel(r, text=v, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                         text_color=acc).pack(side="left")
            tk.Label(r, text=k, font=("Segoe UI", 11, "bold"), fg=TXT, bg=FIELD).pack(side="right", padx=(30, 0))

        btns = ctk.CTkFrame(inner, fg_color="transparent")
        btns.pack(pady=15)
        
        ctk.CTkButton(btns, text="التحقق من وجود تحديثات", image=ico("refresh", "white", 16),
                      fg_color="#1E293B", hover_color="#334155", height=42, corner_radius=10, width=220,
                      font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                      command=self.manual_check_update).pack(side="left", padx=8)

        ctk.CTkButton(btns, text="GitHub فتح صفحة البرنامج على", image=ico("globe", "white", 16),
                      fg_color=self.theme["btn"], hover_color=self.theme["btn_hover"], height=42, corner_radius=10, width=260,
                      font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                      command=lambda: webbrowser.open(f"https://github.com/{GITHUB_REPO}")).pack(side="left", padx=8)

    # ==========================================
    # صفحة: إدارة مكتبة ألعاب ستيم
    # ==========================================
    def _steam_head(self, p, key):
        acc = self.get_accent()
        head = ctk.CTkFrame(p, fg_color="transparent")
        head.pack(fill="x", pady=(0, 4))
        btn = ctk.CTkButton(head, text="", image=ico("globe", acc, 16), width=110, height=32,
                            fg_color=FIELD, hover_color="#1E3354", text_color=acc, corner_radius=8,
                            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                            command=self.toggle_steam_language)
        btn.pack(side="right")
        title = ctk.CTkLabel(head, text="", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=acc)
        title.pack(side="left")
        sub = tk.Label(p, text="", font=("Segoe UI", 11), fg=MUTED, bg=BG)
        sub.pack(anchor="w", pady=(0, 12))
        self.steam_lang_btns.append(btn)
        self.steam_heads.append((title, sub, key))

    def build_page_steam_add(self):
        self.steam_heads = []
        self.steam_lang_btns = []
        p = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.pages["steam_add"] = p
        acc = self.get_accent()
        bf = ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        self._steam_head(p, "add")

        tcard = self._card(p)
        tcard.pack(fill="x", pady=(0, 8))
        r = self._row(tcard)
        self.lbl_target = self._flabel(r, "", "gamepad", width=20)
        self.btn_change_target = ctk.CTkButton(r, text="", image=ico("gear", TXT, 16), width=160, height=32,
                                               fg_color="#272A34", hover_color="#343846", corner_radius=8,
                                               command=lambda: self.show_page("steam_accounts"))
        self.btn_change_target.pack(side="left", padx=(0, 10))
        self.steam_target_lbl = tk.Label(r, text="", font=("Segoe UI", 11, "bold"), fg=acc, bg=CARD, anchor="e")
        self.steam_target_lbl.pack(side="left", fill="x", expand=True, padx=(0, 10))

        card = self._card(p)
        card.pack(fill="x", pady=(0, 6))

        r = self._row(card)
        self.lbl_games = self._flabel(r, "", "folder", width=20)
        self.btn_steam_scan = ctk.CTkButton(r, text="", image=ico("search", "white", 16), width=130, height=34,
                                            fg_color=self.theme["btn"], hover_color=self.theme["btn_hover"],
                                            corner_radius=8, font=bf, command=self.steam_scan_folder)
        self.btn_steam_scan.pack(side="left", padx=(0, 8))
        self.btn_browse_games = ctk.CTkButton(r, text="", image=ico("folder", TXT, 16), width=190, height=34,
                                              fg_color="#272A34", hover_color="#343846", corner_radius=8,
                                              command=self.browse_games_folder)
        self.btn_browse_games.pack(side="left", padx=(0, 8))
        self.games_entry = ctk.CTkEntry(r, textvariable=self.games_path_var, height=34, fg_color=FIELD,
                                        border_color="#243048", corner_radius=8)
        self.games_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.chk_art = ctk.CTkCheckBox(card, text="", variable=self.download_art_var, text_color=TXT,
                                       fg_color=self.theme["btn"], corner_radius=6,
                                       font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"))
        self.chk_art.pack(anchor="e", padx=22, pady=(4, 14))

        self.lbl_hint = tk.Label(p, text="", font=("Segoe UI", 10), fg=MUTED, bg=BG)
        self.lbl_hint.pack(anchor="w", pady=(2, 6))

        bottom = ctk.CTkFrame(p, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", pady=(12, 0))
        self.btn_steam_add = ctk.CTkButton(bottom, text="", image=ico("plus", "white", 18), height=44, width=280,
                                           fg_color="#2EA44F", hover_color="#34C45B", corner_radius=10,
                                           font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                                           command=self.steam_start_add)
        self.btn_steam_add.pack(side="right")
        self.btn_steam_remove = ctk.CTkButton(bottom, text="", image=ico("x", "#FF9999", 14), height=40, width=130,
                                              fg_color="#2D1B20", hover_color="#452329", text_color="#FF9999",
                                              corner_radius=10, command=self.steam_remove_selected)
        self.btn_steam_remove.pack(side="left")
        self.btn_steam_clear = ctk.CTkButton(bottom, text="", image=ico("trash", "#FF7777", 16), height=40, width=180,
                                             fg_color="#38181E", hover_color="#542028", text_color="#FF7777",
                                             corner_radius=10, command=self.steam_clear_all)
        self.btn_steam_clear.pack(side="left", padx=8)
        self.steam_status_lbl = tk.Label(bottom, text="", font=("Segoe UI", 10, "bold"), fg=acc, bg=BG)
        self.steam_status_lbl.pack(side="left", padx=15)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Nexus.Treeview", background=FIELD, foreground=TXT, fieldbackground=FIELD, rowheight=32,
                        borderwidth=0, font=("Segoe UI", 10))
        style.map("Nexus.Treeview", background=[("selected", "#1B2A45")], foreground=[("selected", acc)])
        style.configure("Nexus.Treeview.Heading", background=CARD2, foreground=acc, relief="flat",
                        font=("Segoe UI", 10, "bold"))
        style.map("Nexus.Treeview.Heading", background=[("active", BORDER)])

        tf = ctk.CTkFrame(p, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
        tf.pack(fill="both", expand=True)
        self.steam_tree = ttk.Treeview(tf, style="Nexus.Treeview", columns=("name", "exe"), show="headings",
                                       selectmode="browse")
        sb = ctk.CTkScrollbar(tf, command=self.steam_tree.yview)
        self.steam_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=(0, 4), pady=6)
        self.steam_tree.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.steam_tree.column("name", width=280, anchor="w")
        self.steam_tree.column("exe", width=520, anchor="w")
        self.steam_tree.bind("<Double-1>", self.on_steam_item_double_click)
        for v in self._steam_cache:
            self.steam_tree.insert("", tk.END, values=v)

    def build_page_steam_accounts(self):
        p = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.pages["steam_accounts"] = p
        acc = self.get_accent()
        self._steam_head(p, "accounts")

        card = self._card(p)
        card.pack(fill="x", pady=(0, 8))

        r = self._row(card)
        self.lbl_steam = self._flabel(r, "", "folder", width=20)
        self.btn_browse_steam = ctk.CTkButton(r, text="", image=ico("folder", TXT, 16), width=190, height=34,
                                              fg_color="#272A34", hover_color="#343846", corner_radius=8,
                                              command=self.browse_steam_folder)
        self.btn_browse_steam.pack(side="left", padx=(0, 8))
        self.steam_entry = ctk.CTkEntry(r, textvariable=self.steam_path_var, height=34, fg_color=FIELD,
                                        border_color="#243048", corner_radius=8)
        self.steam_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.steam_entry.bind("<FocusOut>", lambda e: self.refresh_steam_users())
        self.steam_entry.bind("<Return>", lambda e: self.refresh_steam_users())

        r = self._row(card)
        self.lbl_user = self._flabel(r, "", "gamepad", width=20)
        self.all_users_chk = ctk.CTkCheckBox(r, text="", variable=self.all_users_var, command=self.toggle_all_users,
                                             font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                                             text_color=acc, fg_color=self.theme["btn"], corner_radius=6)
        self.all_users_chk.pack(side="left", padx=(0, 10))
        self.user_combo = ctk.CTkComboBox(r, values=[""], state="readonly", height=34, corner_radius=8, fg_color=FIELD,
                                          border_color="#243048", dropdown_fg_color=CARD,
                                          font=ctk.CTkFont(family="Segoe UI", size=11),
                                          command=lambda v: self._update_steam_target())
        self.user_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))

        r = self._row(card)
        self.lbl_steam_status = self._flabel(r, "", "activity", width=20)
        self.btn_steam_recheck = ctk.CTkButton(r, text="", image=ico("refresh", TXT, 16), width=150, height=32,
                                               fg_color="#16233B", hover_color="#1E3354", corner_radius=8,
                                               command=self.refresh_steam_users)
        self.btn_steam_recheck.pack(side="left", padx=(0, 10))
        self.steam_running_lbl = tk.Label(r, text="", font=("Segoe UI", 10, "bold"), fg=MUTED, bg=CARD, anchor="e")
        self.steam_running_lbl.pack(side="left", fill="x", expand=True, padx=(0, 10))

    def build_page_steam_about(self):
        p = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.pages["steam_about"] = p
        acc = self.get_accent()

        card = self._card(p)
        card.pack(fill="both", expand=True, padx=10, pady=10)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(expand=True)

        tr = ctk.CTkFrame(inner, fg_color="transparent")
        tr.pack(pady=(0, 6))
        ctk.CTkLabel(tr, text="", image=ico("gamepad", acc, 40)).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(tr, text="SteamLibraryIntegrator", font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
                     text_color=acc).pack(side="left")
        tk.Label(inner, text="برنامج فرعي داخل NEXUS لإضافة الألعاب الخارجية وأغلفتها إلى مكتبة ستيم",
                 font=("Segoe UI", 12), fg=MUTED, bg=CARD).pack(pady=(0, 15))

        info = ctk.CTkFrame(inner, fg_color=FIELD, corner_radius=10, border_width=1, border_color="#243048")
        info.pack(pady=10, padx=20, fill="x")
        for k, v in [("النوع:", "برنامج فرعي (Non-Steam Games Manager)"),
                     ("الوظيفة:", "shortcuts.vdf + الأغلفة والخلفيات والشعارات"),
                     ("الترخيص:", "مفتوح المصدر (Open Source)")]:
            r = ctk.CTkFrame(info, fg_color="transparent")
            r.pack(fill="x", padx=15, pady=6)
            ctk.CTkLabel(r, text=v, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                         text_color=acc).pack(side="left")
            tk.Label(r, text=k, font=("Segoe UI", 11, "bold"), fg=TXT, bg=FIELD).pack(side="right", padx=(30, 0))

        ctk.CTkButton(inner, text="GitHub فتح صفحة البرنامج على", image=ico("globe", "white", 18),
                      fg_color=self.theme["btn"], hover_color=self.theme["btn_hover"],
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), height=42, corner_radius=10, width=260,
                      command=lambda: webbrowser.open(f"https://github.com/{GITHUB_REPO}")).pack(pady=20)

    def _steam_init(self):
        self.update_steam_texts()
        self.refresh_steam_users()
        self.toggle_all_users()

    def update_steam_texts(self):
        t = STEAM_STRINGS[self.steam_lang]
        for title, sub, key in self.steam_heads:
            title.configure(text=t["title_" + key])
            sub.configure(text=t["sub_" + key])
        for b in self.steam_lang_btns:
            b.configure(text="  " + t["lang_btn"])
        self.lbl_target.configure(text=t["lbl_target"])
        self.btn_change_target.configure(text=t["btn_change_target"])
        self.lbl_steam.configure(text=t["lbl_steam"])
        self.btn_browse_steam.configure(text=t["btn_browse_steam"])
        self.lbl_user.configure(text=t["lbl_user"])
        self.all_users_chk.configure(text=t["chk_all_users"])
        self.lbl_steam_status.configure(text=t["lbl_status"])
        self.btn_steam_recheck.configure(text=t["btn_recheck"])
        self.lbl_games.configure(text=t["lbl_games"])
        self.btn_browse_games.configure(text=t["btn_browse_games"])
        self.btn_steam_scan.configure(text=t["btn_scan"])
        self.chk_art.configure(text=t["chk_art"])
        self.lbl_hint.configure(text=t["lbl_hint"])
        self.steam_tree.heading("name", text=t["col_name"])
        self.steam_tree.heading("exe", text=t["col_exe"])
        self.btn_steam_remove.configure(text=t["btn_remove"])
        self.btn_steam_clear.configure(text=t["btn_clear"])
        if str(self.btn_steam_add.cget("state")) != "disabled":
            self.btn_steam_add.configure(text=t["btn_add"])

    def _update_steam_target(self):
        try:
            t = STEAM_STRINGS[self.steam_lang]
            if self.all_users_var.get():
                txt = t["done_all_users"].format(count=len(self.steam_users_list))
            else:
                idx = self._steam_combo_index()
                txt = self.steam_users_list[idx]["display"] if 0 <= idx < len(self.steam_users_list) else t["no_users"]
            self.steam_target_lbl.configure(text=txt)
        except Exception:
            pass

    def _update_steam_running(self):
        try:
            t = STEAM_STRINGS[self.steam_lang]
            running = is_steam_running()
            self.steam_running_lbl.configure(text=t["steam_running"] if running else t["steam_stopped"],
                                             fg="#FBBF24" if running else "#10B981")
        except Exception:
            pass

    def toggle_steam_language(self):
        self.steam_lang = "en" if self.steam_lang == "ar" else "ar"
        self.settings["steam_lang"] = self.steam_lang
        save_data(CONFIG_FILE, self.settings)
        self.refresh_steam_users()
        self.update_steam_texts()

    def toggle_all_users(self):
        self.user_combo.configure(state="disabled" if self.all_users_var.get() else "readonly")
        self._update_steam_target()

    def _steam_combo_index(self):
        try:
            vals = list(self.user_combo.cget("values"))
            cur = self.user_combo.get()
            return vals.index(cur) if cur in vals else -1
        except Exception:
            return -1

    def refresh_steam_users(self):
        t = STEAM_STRINGS[self.steam_lang]
        steam_path = self.steam_path_var.get().strip().strip('"')
        prev_idx = self._steam_combo_index()
        self.steam_users_list = get_steam_users_info(steam_path, self.steam_lang)
        if self.steam_users_list:
            displays = [u["display"] for u in self.steam_users_list]
            self.user_combo.configure(values=displays)
            self.user_combo.set(displays[prev_idx] if 0 <= prev_idx < len(displays) else displays[0])
        else:
            self.user_combo.configure(values=[t["no_users"]])
            self.user_combo.set(t["no_users"])
        self._update_steam_target()
        self._update_steam_running()

    def _save_steam_paths(self):
        self.settings["steam_path"] = self.steam_path_var.get().strip().strip('"')
        self.settings["games_path"] = self.games_path_var.get().strip().strip('"')
        try:
            save_data(CONFIG_FILE, self.settings)
        except Exception:
            pass

    def _steam_status(self, text):
        def _set():
            try:
                self.steam_status_lbl.configure(text=text)
            except Exception:
                pass
        self.ui(_set)

    def browse_steam_folder(self):
        t = STEAM_STRINGS[self.steam_lang]
        current = self.steam_path_var.get().strip().strip('"')
        folder = filedialog.askdirectory(title=t["dialog_steam"], initialdir=current if os.path.exists(current) else None)
        if folder:
            self.steam_path_var.set(os.path.normpath(folder))
            self.refresh_steam_users()
            self._save_steam_paths()

    def browse_games_folder(self):
        t = STEAM_STRINGS[self.steam_lang]
        current = self.games_path_var.get().strip().strip('"')
        folder = filedialog.askdirectory(title=t["dialog_games"], initialdir=current if os.path.exists(current) else None)
        if folder:
            self.games_path_var.set(os.path.normpath(folder))
            self._save_steam_paths()

    # ----- فحص الألعاب -----
    def steam_scan_folder(self):
        t = STEAM_STRINGS[self.steam_lang]
        folder = self.games_path_var.get().strip().strip('"')
        if not folder or not os.path.exists(folder):
            messagebox.showwarning("!", t["warn_invalid_path"])
            return
        self._save_steam_paths()
        self.btn_steam_scan.configure(state="disabled")
        self._steam_status(t["status_scanning"])
        threading.Thread(target=self._steam_scan_worker, args=(folder, self.steam_lang), daemon=True).start()

    def _steam_scan_worker(self, folder, lang):
        subfolders = [f for f in glob.glob(os.path.join(folder, "*")) if os.path.isdir(f)]
        found = []
        for sub in subfolders:
            best = find_best_exe(sub)
            if best:
                found.append((os.path.basename(sub), best))
        self.ui(lambda: self._steam_scan_done(found, len(subfolders), lang))

    def _steam_scan_done(self, found, total, lang):
        t = STEAM_STRINGS[lang]
        self.btn_steam_scan.configure(state="normal")
        self._steam_status("")
        self.steam_tree.delete(*self.steam_tree.get_children())
        for v in found:
            self.steam_tree.insert("", tk.END, values=v)
        self.log(f"فحص ألعاب ستيم: {len(found)} من {total} مجلد")
        if not found:
            messagebox.showinfo("Steam Integrator", t["scan_empty"])
        else:
            messagebox.showinfo("Steam Integrator", t["scan_done"].format(count=len(found), total=total))

    def on_steam_item_double_click(self, event):
        t = STEAM_STRINGS[self.steam_lang]
        item = self.steam_tree.selection()
        if not item:
            return
        vals = self.steam_tree.item(item, "values")
        initial_dir = os.path.dirname(str(vals[1])) if vals[1] else None
        f = filedialog.askopenfilename(title=f"{t['dialog_exe']} {vals[0]}", initialdir=initial_dir,
                                       filetypes=[("Executable Files", "*.exe")])
        if f:
            self.steam_tree.item(item, values=(vals[0], os.path.normpath(f)))

    def steam_remove_selected(self):
        for item in self.steam_tree.selection():
            self.steam_tree.delete(item)

    def steam_clear_all(self):
        items = self.steam_tree.get_children()
        if items:
            self.steam_tree.delete(*items)

    # ----- إضافة الألعاب -----
    def steam_start_add(self):
        t = STEAM_STRINGS[self.steam_lang]
        items = self.steam_tree.get_children()
        if not items:
            messagebox.showwarning("!", t["warn_no_games"])
            return

        steam_path = self.steam_path_var.get().strip().strip('"').strip("'")
        if not os.path.exists(steam_path):
            messagebox.showerror("Error", t["err_steam_path"] + steam_path)
            return

        self.refresh_steam_users()
        apply_all = self.all_users_var.get()
        if apply_all:
            target_users = list(self.steam_users_list)
        else:
            idx = self._steam_combo_index()
            if idx < 0 or not self.steam_users_list:
                messagebox.showerror("Error", t["err_no_targets"])
                return
            target_users = [self.steam_users_list[idx]]

        if not target_users:
            messagebox.showerror("Error", t["err_no_targets"])
            return

        to_add = [tuple(str(x) for x in self.steam_tree.item(it, "values")) for it in items]
        self._save_steam_paths()
        self.btn_steam_add.configure(state="disabled", text=t["btn_processing"])
        was_running = is_steam_running()

        threading.Thread(
            target=self._steam_add_worker,
            args=(to_add, target_users, apply_all, steam_path, was_running, self.download_art_var.get(), self.steam_lang),
            daemon=True).start()

    def _steam_add_worker(self, to_add, target_users, apply_all, steam_path, was_running, want_art, lang):
        t = STEAM_STRINGS[lang]
        try:
            if was_running:
                self._steam_status(t["status_closing_steam"])
                safely_close_steam(steam_path)

            total_added_count = 0
            total_skipped_count = 0
            newly_added_unique = {}

            for u in target_users:
                cfg_dir = os.path.join(u["path"], "config")
                os.makedirs(cfg_dir, exist_ok=True)
                vdf_path = os.path.join(cfg_dir, "shortcuts.vdf")
                os.makedirs(os.path.join(cfg_dir, "grid"), exist_ok=True)

                existing_names, existing_exes = get_existing_shortcuts(vdf_path)

                user_new_games = []
                for name, exe in to_add:
                    norm_exe = os.path.normpath(exe.strip(' "\'')).lower()
                    clean_n = name.strip().lower()
                    if clean_n in existing_names or norm_exe in existing_exes:
                        continue
                    user_new_games.append((name, exe))
                    existing_names.add(clean_n)
                    existing_exes.add(norm_exe)
                    newly_added_unique[clean_n] = (name, exe)

                skipped = len(to_add) - len(user_new_games)
                total_skipped_count = max(total_skipped_count, skipped)

                if user_new_games:
                    write_shortcuts_file(vdf_path, user_new_games)
                    total_added_count += len(user_new_games)

            if total_added_count == 0:
                if was_running:
                    restart_steam(steam_path)
                self.ui(lambda: self._steam_finish_all_exist(len(to_add), lang))
                return

            art_count = 0
            if want_art and newly_added_unique:
                new_list = list(newly_added_unique.values())
                total = len(new_list)
                self._steam_status(t["status_fetching"].format(current=0, total=total))
                grid_dirs = [os.path.join(u["path"], "config", "grid") for u in target_users]

                def task(game_data):
                    n, e = game_data
                    return download_and_save_artwork(n, e, grid_dirs)

                with ThreadPoolExecutor(max_workers=6) as executor:
                    for i, res in enumerate(executor.map(task, new_list), 1):
                        if res:
                            art_count += 1
                        self._steam_status(t["status_fetching"].format(current=i, total=total))

            if was_running:
                self._steam_status(t["status_restarting_steam"])
                time.sleep(1)
                restart_steam(steam_path)
                time.sleep(1.5)

            added_per_user = total_added_count if not apply_all else len(newly_added_unique)
            self.ui(lambda: self._steam_finish(added_per_user, total_skipped_count, art_count,
                                               len(target_users), apply_all, was_running, lang))
        except Exception as e:
            self.log(f"خطأ في إضافة ألعاب ستيم: {e}")
            self.ui(lambda: self._steam_reset_add(lang))
            self.toast("حدث خطأ أثناء إضافة الألعاب", "err")

    def _steam_reset_add(self, lang):
        t = STEAM_STRINGS[lang]
        self.btn_steam_add.configure(state="normal", text=t["btn_add"])
        self.steam_status_lbl.configure(text="")

    def _steam_finish_all_exist(self, count, lang):
        t = STEAM_STRINGS[lang]
        self._steam_reset_add(lang)
        self.log("ألعاب ستيم: كل الألعاب موجودة مسبقاً")
        messagebox.showinfo(t["done_title"], t["done_all_exist"].format(count=count))

    def _steam_finish(self, added_count, skipped_count, art_count, users_count, apply_all, was_restarted, lang):
        t = STEAM_STRINGS[lang]
        self._steam_reset_add(lang)
        target_desc = t["done_all_users"].format(count=users_count) if apply_all else t["done_single_user"]
        restarted_note = t["restarted_text_yes"] if was_restarted else t["restarted_text_no"]
        self.log(f"ألعاب ستيم: أضيفت {added_count} وتخطي {skipped_count} وأغلفة {art_count}")
        messagebox.showinfo(t["done_title"], t["done_msg"].format(
            added_count=added_count, skipped_count=skipped_count, target_desc=target_desc,
            art_count=art_count, restarted_note=restarted_note))

    # ==========================================
    # 4. تسجيل الاختصارات وتطبيق الأوضاع
    # ==========================================
    def register_all_hotkeys(self):
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

        count = 0
        for name, data in self.profiles.items():
            hk = data.get("hotkey", "").strip()
            if hk:
                try:
                    keyboard.add_hotkey(hk, self._hotkey_fire, args=(name,))
                    count += 1
                except Exception as e:
                    print(f"Failed to bind {hk}: {e}")
                    self.log(f"فشل ربط الاختصار {hk}: {e}")
        self.log(f"تم تسجيل {count} اختصار")

    def _hotkey_fire(self, name):
        data = self.profiles.get(name)
        if data:
            self.apply_profile_async(name, data)

    def apply_profile(self, data):
        mode = data.get("display_mode")
        if mode:
            set_display_mode(mode)
            time.sleep(1.5)
        if data.get("audio"):
            set_audio_device(data["audio"])
        vol = data.get("volume")
        if isinstance(vol, int):
            time.sleep(0.4)
            set_volume(vol)
        if data.get("hdr") == "toggle":
            time.sleep(0.4)
            toggle_hdr()
        launch = data.get("launch")
        if launch and (os.path.exists(launch) or "://" in launch):
            try:
                os.startfile(launch)
            except Exception as e:
                self.log(f"تعذر تشغيل التطبيق: {e}")

    def apply_profile_async(self, name, data):
        threading.Thread(target=self._apply_worker, args=(name, data), daemon=True).start()

    def _apply_worker(self, name, data):
        if not self._apply_lock.acquire(blocking=False):
            self.toast("جارٍ تطبيق وضع آخر... انتظر لحظة", "warn")
            return
        try:
            self.log(f"بدء تفعيل الوضع: {name}")
            self.apply_profile(data)
            cur = get_default_audio_device()
            self.log(f"تم تفعيل الوضع: {name}")
            self.ui(lambda: self._after_apply(name, cur))
        except Exception as e:
            self.log(f"خطأ أثناء التفعيل: {e}")
            self.toast("حدث خطأ أثناء التفعيل", "err")
        finally:
            self._apply_lock.release()

    def _after_apply(self, name, cur):
        self.active_profile = name
        self.settings["last_profile"] = name
        try:
            save_data(CONFIG_FILE, self.settings)
        except Exception:
            pass
        if cur:
            self.current_audio = cur
        self.refresh_stats()
        if self.current_page_id == "home":
            self.populate_home_profiles()
        elif self.current_page_id == "audio":
            self.populate_audio_page()
        self.update_tray_menu()
        self.notify(f"تم تفعيل وضع: {name}")

    # ==========================================
    # 5. شريط المهام في الخلفية
    # ==========================================
    def create_tray_image(self):
        acc = self.get_accent()
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((2, 2, 62, 62), fill=(11, 15, 23, 255), outline=acc, width=4)
        bolt = draw_icon_image("bolt", acc, 160).resize((36, 36), RESAMPLE)
        img.paste(bolt, (14, 14), bolt)
        return img

    def setup_tray_icon(self):
        self.tray = pystray.Icon("nexus_switcher", self.create_tray_image(), "NEXUS")
        self.update_tray_menu()
        threading.Thread(target=self.tray.run, daemon=True).start()

    def update_tray_icon(self):
        try:
            self.tray.icon = self.create_tray_image()
        except Exception:
            pass

    def update_tray_menu(self):
        if not hasattr(self, "tray"):
            return

        def act_show(icon, item):
            self.ui(self._restore_ui)

        def act_quit(icon, item):
            self.ui(self.quit_app)

        def make_action(n):
            def act(icon, item):
                d = self.profiles.get(n)
                if d:
                    self.apply_profile_async(n, d)
            return act

        def make_checked(n):
            return lambda item: self.active_profile == n

        items = [pystray.MenuItem("فتح البرنامج", act_show, default=True), pystray.Menu.SEPARATOR]
        for name in self.profiles:
            items.append(pystray.MenuItem(name, make_action(name), checked=make_checked(name)))
        items.extend([pystray.Menu.SEPARATOR, pystray.MenuItem("خروج نهائي", act_quit)])

        self.tray.menu = pystray.Menu(*items)
        try:
            self.tray.update_menu()
        except Exception:
            pass

    def hide_window(self):
        if self.settings.get("tray_close", True):
            self.withdraw()
            if not self._hidden_notified and self.settings.get("notifications", True):
                self._hidden_notified = True
                try:
                    self.tray.notify("البرنامج يعمل في الخلفية. الاختصارات فعّالة.", "Nexus")
                except Exception:
                    pass
        else:
            self.quit_app()

    def show_window(self, icon=None, item=None):
        self.ui(self._restore_ui)

    def _restore_ui(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def quit_app(self, icon=None, item=None):
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        try:
            self.tray.stop()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    if not ensure_single_instance():
        _r = tk.Tk()
        _r.withdraw()
        messagebox.showinfo("Nexus", "البرنامج يعمل بالفعل")
        sys.exit(0)
    app = NexusApp(start_hidden=("--tray" in sys.argv))
    app.mainloop()
