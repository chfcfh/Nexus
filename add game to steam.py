import os
import re
import glob
import time
import zlib
import struct
import subprocess
import winreg
import json
import threading
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# قائمة استبعاد الملفات المساعدة والخدمية
EXCLUDE_KEYWORDS = [
    'unins', 'setup', 'redist', 'crash', 'handler', 'report', 'update',
    'patch', 'vcredist', 'dxsetup', 'easyanticheat', 'battleye', 'cefprocess',
    'notification', 'benchmark', 'server', 'dotnet', 'support', 'directx',
    'prereq', 'installer', 'cleanup', 'eac_server'
]

# ألوان ثيم ستيم المودرن
STEAM_BLACK      = "#121316"
STEAM_CARD_BG    = "#18191e"
STEAM_INPUT_BG   = "#1f2128"
STEAM_BORDER     = "#2a2d37"
STEAM_CYAN       = "#00a8ff"
STEAM_TEXT_WHITE = "#f0f2f5"
STEAM_TEXT_MUTED = "#8b8f99"
STEAM_BTN_DARK   = "#272a34"
STEAM_BTN_BLUE   = "#0078d4"
STEAM_BTN_GREEN  = "#2ea44f"
STEAM_BTN_RED    = "#2d1b20"

# قاموس اللغتين
STRINGS = {
    "ar": {
        "app_title": "Steam Game Shortcut & Artwork Adder (Modern Edition)",
        "header_title": "STEAM LIBRARY INTEGRATOR",
        "header_sub": "// إدارة وإضافة الألعاب الخارجية والأغلفة",
        "lang_btn": "English 🌐",
        "group_paths": "  الإعدادات والمسارات  ",
        "lbl_steam": "مسار مجلد ستيم:\u200E",
        "btn_browse_steam": "📁 تحديد مجلد ستيم...",
        "lbl_user": "حساب ستيم المستهدف:\u200E",
        "chk_all_users": "🌐 تطبيق على جميع الحسابات",
        "lbl_games": "مسار مجلد الألعاب:\u200E",
        "btn_browse_games": "📁 تحديد مجلد الألعاب...",
        "btn_scan": "🔍 فحص الألعاب",
        "chk_art": "🎨 \u200Fتحميل وتعيين الأغلفة والخلفيات والشعارات تلقائياً من ستيم",
        "lbl_hint": "💡 يمكنك النقر مرتين على أي لعبة لتغيير المشغل (exe) يدوياً قبل الإضافة.",
        "col_name": "اسم اللعبة",
        "col_exe": "مشغل اللعبة المكتشف (EXE)",
        "btn_remove": "حذف المحدد",
        "btn_clear": "🗑️ مسح القائمة بالكامل",
        "btn_add": "🚀 إضافة الألعاب وتعيين الأغلفة",
        "btn_processing": "⏳ جاري الفحص والمعالجة...",
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
        "dialog_steam": "اختر مجلد ستيم الرئيسي",
        "dialog_games": "اختر المجلد الذي يحتوي على ألعابك",
        "dialog_exe": "اختر ملف الـ EXE للعبة"
    },
    "en": {
        "app_title": "Steam Game Shortcut & Artwork Adder (Modern Edition)",
        "header_title": "STEAM LIBRARY INTEGRATOR",
        "header_sub": "// Non-Steam Games & Artwork Manager",
        "lang_btn": "عربي 🌐",
        "group_paths": "  Settings & Paths  ",
        "lbl_steam": "Steam Directory:",
        "btn_browse_steam": "📁 Browse Steam...",
        "lbl_user": "Target Steam Account:",
        "chk_all_users": "🌐 Apply to All Accounts",
        "lbl_games": "Games Directory:",
        "btn_browse_games": "📁 Browse Games...",
        "btn_scan": "🔍 Scan Games",
        "chk_art": "🎨 Auto-download Covers, Backgrounds & Logos from Steam",
        "lbl_hint": "💡 Double-click any game in the list to manually change its executable (.exe).",
        "col_name": "Game Title",
        "col_exe": "Detected Executable (EXE)",
        "btn_remove": "Remove Selected",
        "btn_clear": "🗑️ Clear All",
        "btn_add": "🚀 Add Games & Set Artwork",
        "btn_processing": "⏳ Checking & Processing...",
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
        tasks = subprocess.check_output('tasklist /FI "IMAGENAME eq steam.exe"', shell=True).decode('utf-8', errors='ignore')
        return 'steam.exe' in tasks.lower()
    except Exception:
        return False

def safely_close_steam(steam_path):
    """إغلاق ستيم بأمان باستخدام أمره المدمج وحفظ ملفاته"""
    if not is_steam_running():
        return True

    steam_exe = os.path.join(steam_path, "steam.exe")
    if os.path.exists(steam_exe):
        try:
            subprocess.run([steam_exe, "-shutdown"], capture_output=True, timeout=5)
        except Exception:
            pass

    # انتظار ستيم حتى ينتهي من حفظ الذاكرة ويقفل (بحد أقصى 8 ثوانٍ)
    for _ in range(16):
        if not is_steam_running():
            return True
        time.sleep(0.5)

    # في حال علق في الخلفية، إنهاء العملية
    subprocess.run('taskkill /IM steam.exe /F', shell=True, capture_output=True)
    time.sleep(1)
    return not is_steam_running()

def restart_steam(steam_path):
    """إعادة تشغيل ستيم في الخلفية"""
    steam_exe = os.path.join(steam_path, "steam.exe")
    if os.path.exists(steam_exe):
        try:
            # تشغيل مستقل تماماً عن البرنامج
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
    t = STRINGS[lang]
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

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.current_lang = "ar"
        self.geometry("980x700")
        self.configure(bg=STEAM_BLACK)

        self.option_add('*Font', ('Segoe UI', 9))
        self.option_add('*TCombobox*Listbox.font', ('Segoe UI', 9))
        self.option_add('*TCombobox*Listbox.background', STEAM_INPUT_BG)
        self.option_add('*TCombobox*Listbox.foreground', STEAM_TEXT_WHITE)
        self.option_add('*TCombobox*Listbox.selectBackground', STEAM_BORDER)
        self.option_add('*TCombobox*Listbox.selectForeground', STEAM_CYAN)

        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass

        style.configure("Treeview",
                        background=STEAM_INPUT_BG,
                        foreground=STEAM_TEXT_WHITE,
                        fieldbackground=STEAM_INPUT_BG,
                        rowheight=30,
                        borderwidth=0,
                        font=("Segoe UI", 9))
        style.map("Treeview",
                  background=[("selected", STEAM_CARD_BG)],
                  foreground=[("selected", STEAM_CYAN)])
        style.configure("Treeview.Heading",
                        background=STEAM_CARD_BG,
                        foreground=STEAM_CYAN,
                        relief="flat",
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview.Heading",
                  background=[("active", STEAM_BORDER)])

        style.configure("TCombobox",
                        fieldbackground=STEAM_INPUT_BG,
                        background=STEAM_BTN_DARK,
                        foreground=STEAM_TEXT_WHITE,
                        arrowcolor=STEAM_CYAN)

        # ----------------- شريط العنوان العلوي -----------------
        header_bar = tk.Frame(self, bg=STEAM_BLACK, pady=8, padx=16)
        header_bar.pack(fill=tk.X)
        
        accent_pill = tk.Frame(header_bar, bg=STEAM_CYAN, width=4, height=22)
        accent_pill.pack(side=tk.LEFT, padx=(0, 10))
        accent_pill.pack_propagate(False)

        self.lbl_head_title = tk.Label(header_bar, text="", bg=STEAM_BLACK, fg=STEAM_TEXT_WHITE, font=("Segoe UI", 11, "bold"))
        self.lbl_head_title.pack(side=tk.LEFT)

        self.lbl_head_sub = tk.Label(header_bar, text="", bg=STEAM_BLACK, fg=STEAM_TEXT_MUTED, font=("Segoe UI", 9))
        self.lbl_head_sub.pack(side=tk.LEFT, padx=10)

        self.btn_lang = tk.Button(header_bar, text="", command=self.toggle_language, bg=STEAM_BTN_DARK, fg=STEAM_CYAN, activebackground=STEAM_BORDER, activeforeground="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=2)
        self.btn_lang.pack(side=tk.RIGHT)

        # ----------------- إطار المسارات والإعدادات -----------------
        self.top_frame = tk.LabelFrame(self, text="", bg=STEAM_CARD_BG, fg=STEAM_CYAN, font=("Segoe UI", 9, "bold"), padx=15, pady=12, relief="flat", highlightbackground=STEAM_BORDER, highlightthickness=1)
        self.top_frame.pack(fill=tk.X, padx=16, pady=6)

        # 1. سطر مسار ستيم
        row_steam = tk.Frame(self.top_frame, bg=STEAM_CARD_BG)
        row_steam.pack(fill=tk.X, pady=4)
        self.lbl_steam = tk.Label(row_steam, text="", width=18, anchor="w", bg=STEAM_CARD_BG, fg=STEAM_TEXT_MUTED, font=("Segoe UI", 9, "bold"))
        self.lbl_steam.pack(side=tk.LEFT)
        self.steam_path_var = tk.StringVar(value=detect_steam_path())
        self.steam_entry = tk.Entry(row_steam, textvariable=self.steam_path_var, width=54, bg=STEAM_INPUT_BG, fg=STEAM_TEXT_WHITE, insertbackground=STEAM_CYAN, relief="flat", highlightbackground=STEAM_BORDER, highlightthickness=1)
        self.steam_entry.pack(side=tk.LEFT, padx=5, ipady=4)
        self.btn_browse_steam = tk.Button(row_steam, text="", command=self.browse_steam_folder, bg=STEAM_BTN_DARK, fg=STEAM_TEXT_WHITE, activebackground=STEAM_BORDER, activeforeground=STEAM_CYAN, relief="flat", padx=10, pady=2)
        self.btn_browse_steam.pack(side=tk.LEFT, padx=3)

        # 2. سطر حساب ستيم المستهدف
        row_user = tk.Frame(self.top_frame, bg=STEAM_CARD_BG)
        row_user.pack(fill=tk.X, pady=4)
        self.lbl_user = tk.Label(row_user, text="", width=18, anchor="w", bg=STEAM_CARD_BG, fg=STEAM_TEXT_MUTED, font=("Segoe UI", 9, "bold"))
        self.lbl_user.pack(side=tk.LEFT)
        self.user_combo = ttk.Combobox(row_user, width=42, state="readonly")
        self.user_combo.pack(side=tk.LEFT, padx=5, ipady=3)
        
        self.all_users_var = tk.BooleanVar(value=False)
        self.all_users_chk = tk.Checkbutton(row_user, text="", variable=self.all_users_var, command=self.toggle_all_users, bg=STEAM_CARD_BG, fg=STEAM_CYAN, activebackground=STEAM_CARD_BG, activeforeground=STEAM_CYAN, selectcolor=STEAM_INPUT_BG, font=("Segoe UI", 9, "bold"))
        self.all_users_chk.pack(side=tk.LEFT, padx=8)

        self.users_list = []

        # 3. سطر مسار الألعاب
        row_games = tk.Frame(self.top_frame, bg=STEAM_CARD_BG)
        row_games.pack(fill=tk.X, pady=4)
        self.lbl_games = tk.Label(row_games, text="", width=18, anchor="w", bg=STEAM_CARD_BG, fg=STEAM_TEXT_MUTED, font=("Segoe UI", 9, "bold"))
        self.lbl_games.pack(side=tk.LEFT)
        self.games_path_var = tk.StringVar(value=r"F:\Games")
        self.games_entry = tk.Entry(row_games, textvariable=self.games_path_var, width=54, bg=STEAM_INPUT_BG, fg=STEAM_TEXT_WHITE, insertbackground=STEAM_CYAN, relief="flat", highlightbackground=STEAM_BORDER, highlightthickness=1)
        self.games_entry.pack(side=tk.LEFT, padx=5, ipady=4)
        self.btn_browse_games = tk.Button(row_games, text="", command=self.browse_games_folder, bg=STEAM_BTN_DARK, fg=STEAM_TEXT_WHITE, activebackground=STEAM_BORDER, activeforeground=STEAM_CYAN, relief="flat", padx=10, pady=2)
        self.btn_browse_games.pack(side=tk.LEFT, padx=3)
        self.btn_scan = tk.Button(row_games, text="", command=self.scan_folder, bg=STEAM_BTN_BLUE, fg="#ffffff", activebackground="#0090ff", activeforeground="#ffffff", relief="flat", font=("Segoe UI", 9, "bold"), padx=15, pady=2)
        self.btn_scan.pack(side=tk.LEFT, padx=6)

        # 4. خيار تحميل الأغلفة
        row_opts = tk.Frame(self.top_frame, bg=STEAM_CARD_BG)
        row_opts.pack(fill=tk.X, pady=(6, 0))
        self.download_art_var = tk.BooleanVar(value=True)
        self.chk_art = tk.Checkbutton(row_opts, text="", variable=self.download_art_var, bg=STEAM_CARD_BG, fg=STEAM_TEXT_WHITE, activebackground=STEAM_CARD_BG, activeforeground="#ffffff", selectcolor=STEAM_INPUT_BG, font=("Segoe UI", 9, "bold"))
        self.chk_art.pack(side=tk.LEFT)

        # ملاحظة توجيهية
        self.lbl_hint = tk.Label(self, text="", bg=STEAM_BLACK, fg=STEAM_TEXT_MUTED)
        self.lbl_hint.pack(anchor="w", padx=20, pady=(4, 4))

        # ----------------- جدول الألعاب -----------------
        tree_frame = tk.Frame(self, bg=STEAM_BLACK)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)

        self.tree = ttk.Treeview(tree_frame, columns=("name", "exe"), show="headings", selectmode="browse")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self.on_item_double_click)

        # ----------------- الشريط السفلي -----------------
        bottom_frame = tk.Frame(self, bg=STEAM_BLACK, pady=12, padx=16)
        bottom_frame.pack(fill=tk.X)

        self.btn_remove = tk.Button(bottom_frame, text="", command=self.remove_selected, bg=STEAM_BTN_RED, fg="#ff9999", activebackground="#452329", activeforeground="#ffffff", relief="flat", padx=12, pady=5)
        self.btn_remove.pack(side=tk.LEFT)

        self.btn_clear = tk.Button(bottom_frame, text="", command=self.clear_all, bg="#38181e", fg="#ff7777", activebackground="#542028", activeforeground="#ffffff", relief="flat", padx=14, pady=5)
        self.btn_clear.pack(side=tk.LEFT, padx=8)
        
        self.status_lbl = tk.Label(bottom_frame, text="", bg=STEAM_BLACK, fg=STEAM_CYAN, font=("Segoe UI", 9, "bold"))
        self.status_lbl.pack(side=tk.LEFT, padx=15)

        self.btn_add = tk.Button(bottom_frame, text="", command=self.start_add_process, bg=STEAM_BTN_GREEN, fg="#ffffff", activebackground="#34c45b", activeforeground="#ffffff", font=("Segoe UI", 10, "bold"), relief="flat", padx=22, pady=6)
        self.btn_add.pack(side=tk.RIGHT)

        self.update_ui_texts()
        self.refresh_users_list()

    def toggle_language(self):
        self.current_lang = "en" if self.current_lang == "ar" else "ar"
        self.update_ui_texts()
        self.refresh_users_list()

    def update_ui_texts(self):
        t = STRINGS[self.current_lang]
        self.title(t["app_title"])
        self.lbl_head_title.config(text=t["header_title"])
        self.lbl_head_sub.config(text=t["header_sub"])
        self.btn_lang.config(text=t["lang_btn"])
        self.top_frame.config(text=t["group_paths"])
        self.lbl_steam.config(text=t["lbl_steam"])
        self.btn_browse_steam.config(text=t["btn_browse_steam"])
        self.lbl_user.config(text=t["lbl_user"])
        self.all_users_chk.config(text=t["chk_all_users"])
        self.lbl_games.config(text=t["lbl_games"])
        self.btn_browse_games.config(text=t["btn_browse_games"])
        self.btn_scan.config(text=t["btn_scan"])
        self.chk_art.config(text=t["chk_art"])
        self.lbl_hint.config(text=t["lbl_hint"])
        self.tree.heading("name", text=t["col_name"])
        self.tree.heading("exe", text=t["col_exe"])
        self.btn_remove.config(text=t["btn_remove"])
        self.btn_clear.config(text=t["btn_clear"])
        self.btn_add.config(text=t["btn_add"])

    def toggle_all_users(self):
        if self.all_users_var.get():
            self.user_combo.config(state="disabled")
        else:
            self.user_combo.config(state="readonly")

    def refresh_users_list(self):
        t = STRINGS[self.current_lang]
        steam_path = self.steam_path_var.get().strip().strip('"')
        prev_idx = self.user_combo.current()
        self.users_list = get_steam_users_info(steam_path, self.current_lang)
        if self.users_list:
            displays = [u["display"] for u in self.users_list]
            self.user_combo["values"] = displays
            if 0 <= prev_idx < len(displays):
                self.user_combo.current(prev_idx)
            else:
                self.user_combo.current(0)
        else:
            self.user_combo["values"] = [t["no_users"]]
            self.user_combo.set(t["no_users"])

    def browse_steam_folder(self):
        t = STRINGS[self.current_lang]
        current = self.steam_path_var.get().strip().strip('"')
        initial = current if os.path.exists(current) else None
        folder = filedialog.askdirectory(title=t["dialog_steam"], initialdir=initial)
        if folder:
            self.steam_path_var.set(os.path.normpath(folder))
            self.refresh_users_list()

    def browse_games_folder(self):
        t = STRINGS[self.current_lang]
        current = self.games_path_var.get().strip().strip('"')
        initial = current if os.path.exists(current) else None
        folder = filedialog.askdirectory(title=t["dialog_games"], initialdir=initial)
        if folder:
            self.games_path_var.set(os.path.normpath(folder))

    def scan_folder(self):
        t = STRINGS[self.current_lang]
        folder = self.games_path_var.get().strip().strip('"')
        if not folder or not os.path.exists(folder):
            messagebox.showwarning("!", t["warn_invalid_path"])
            return

        self.tree.delete(*self.tree.get_children())
        subfolders = [f for f in glob.glob(os.path.join(folder, "*")) if os.path.isdir(f)]

        found_count = 0
        for sub in subfolders:
            game_name = os.path.basename(sub)
            best_exe = find_best_exe(sub)
            if best_exe:
                self.tree.insert("", tk.END, values=(game_name, best_exe))
                found_count += 1

        if found_count == 0:
            messagebox.showinfo("Steam Integrator", t["scan_empty"])
        else:
            messagebox.showinfo("Steam Integrator", t["scan_done"].format(count=found_count, total=len(subfolders)))

    def on_item_double_click(self, event):
        t = STRINGS[self.current_lang]
        item = self.tree.selection()
        if not item:
            return
        current_values = self.tree.item(item, "values")
        initial_dir = os.path.dirname(current_values[1]) if current_values[1] else None
        file = filedialog.askopenfilename(title=f"{t['dialog_exe']} {current_values[0]}", initialdir=initial_dir, filetypes=[("Executable Files", "*.exe")])
        if file:
            self.tree.item(item, values=(current_values[0], os.path.normpath(file)))

    def remove_selected(self):
        selected = self.tree.selection()
        for item in selected:
            self.tree.delete(item)

    def clear_all(self):
        items = self.tree.get_children()
        if not items:
            return
        self.tree.delete(*items)

    def start_add_process(self):
        t = STRINGS[self.current_lang]
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("!", t["warn_no_games"])
            return

        steam_path = self.steam_path_var.get().strip().strip('"').strip("'")
        if not os.path.exists(steam_path):
            messagebox.showerror("Error", t["err_steam_path"] + steam_path)
            return

        apply_all = self.all_users_var.get()
        target_users = []

        if apply_all:
            target_users = self.users_list
        else:
            idx = self.user_combo.current()
            if idx < 0 or not self.users_list:
                messagebox.showerror("Error", t["err_no_targets"])
                return
            target_users = [self.users_list[idx]]

        if not target_users:
            messagebox.showerror("Error", t["err_no_targets"])
            return

        to_add = [self.tree.item(it, "values") for it in items]
        
        self.btn_add.config(state=tk.DISABLED, text=t["btn_processing"])
        
        # معرفة ما إذا كان ستيم شغالاً لإعادة فتحه لاحقاً
        was_steam_running = is_steam_running()

        thread = threading.Thread(target=self.process_in_background, args=(to_add, target_users, apply_all, steam_path, was_steam_running))
        thread.daemon = True
        thread.start()

    def process_in_background(self, to_add, target_users, apply_all, steam_path, was_steam_running):
        t = STRINGS[self.current_lang]
        
        # 1. إغلاق ستيم تلقائياً وبأمان إذا كان شغالاً
        if was_steam_running:
            self.update_status(t["status_closing_steam"])
            safely_close_steam(steam_path)

        total_added_count = 0
        total_skipped_count = 0
        newly_added_games_unique = {}

        # 2. فحص وإضافة الألعاب فقط غير الموجودة مسبقاً
        for u in target_users:
            cfg_dir = os.path.join(u["path"], "config")
            os.makedirs(cfg_dir, exist_ok=True)
            vdf_path = os.path.join(cfg_dir, "shortcuts.vdf")
            g_dir = os.path.join(cfg_dir, "grid")
            os.makedirs(g_dir, exist_ok=True)

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
                newly_added_games_unique[clean_n] = (name, exe)

            skipped = len(to_add) - len(user_new_games)
            total_skipped_count = max(total_skipped_count, skipped)

            if user_new_games:
                write_shortcuts_file(vdf_path, user_new_games)
                total_added_count += len(user_new_games)

        # إذا كل الألعاب موجودة مسبقاً
        if total_added_count == 0:
            if was_steam_running:
                restart_steam(steam_path)
            self.after(0, self.finish_all_exist, len(to_add))
            return

        # 3. تحميل الأغلفة للألعاب الجديدة فقط
        art_count = 0
        if self.download_art_var.get() and newly_added_games_unique:
            new_games_list = list(newly_added_games_unique.values())
            total = len(new_games_list)
            self.update_status(t["status_fetching"].format(current=0, total=total))

            target_grid_dirs = [os.path.join(u["path"], "config", "grid") for u in target_users]

            def task(game_data):
                name, exe = game_data
                return download_and_save_artwork(name, exe, target_grid_dirs)

            with ThreadPoolExecutor(max_workers=6) as executor:
                results = executor.map(task, new_games_list)
                for i, res in enumerate(results, 1):
                    if res:
                        art_count += 1
                    self.update_status(t["status_fetching"].format(current=i, total=total))

        # 4. إعادة تشغيل ستيم تلقائياً
        if was_steam_running:
            self.update_status(t["status_restarting_steam"])
            time.sleep(1)
            restart_steam(steam_path)
            time.sleep(1.5)

        added_per_user = total_added_count if not apply_all else len(newly_added_games_unique)
        self.after(0, self.finish_process, added_per_user, total_skipped_count, art_count, len(target_users), apply_all, was_steam_running)

    def update_status(self, text):
        self.after(0, lambda: self.status_lbl.config(text=text))

    def finish_all_exist(self, count):
        t = STRINGS[self.current_lang]
        self.btn_add.config(state=tk.NORMAL, text=t["btn_add"])
        self.status_lbl.config(text="")
        messagebox.showinfo(t["done_title"], t["done_all_exist"].format(count=count))

    def finish_process(self, added_count, skipped_count, art_count, users_count, apply_all, was_restarted):
        t = STRINGS[self.current_lang]
        self.btn_add.config(state=tk.NORMAL, text=t["btn_add"])
        self.status_lbl.config(text="")
        
        target_desc = t["done_all_users"].format(count=users_count) if apply_all else t["done_single_user"]
        restarted_note = t["restarted_text_yes"] if was_restarted else t["restarted_text_no"]
        msg = t["done_msg"].format(added_count=added_count, skipped_count=skipped_count, target_desc=target_desc, art_count=art_count, restarted_note=restarted_note)
        
        messagebox.showinfo(t["done_title"], msg)

if __name__ == "__main__":
    app = App()
    app.mainloop()
