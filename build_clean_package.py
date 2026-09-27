import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path

print("=" * 60)
print("🚀 جاري بناء النسخة النظيفة المعتمدة (مقاومة لكاسبر سكاي)...")
print("=" * 60)

current_dir = os.path.dirname(os.path.abspath(__file__))
script_source = os.path.join(current_dir, "add game to steam.py")
icon_source = os.path.join(current_dir, "icon.ico")

if not os.path.exists(script_source):
    print(f"❌ لم يتم العثور على ملف: {script_source}")
    sys.exit(1)

# 1. البحث عن مترجم مايكروسوفت الرسمي في ويندوز (csc.exe)
def find_csc():
    candidates = [
        r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
        r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    net_root = r"C:\Windows\Microsoft.NET"
    if os.path.exists(net_root):
        for root, _, files in os.walk(net_root):
            if "csc.exe" in files:
                return os.path.join(root, "csc.exe")
    return None

csc_path = find_csc()
if not csc_path:
    print("❌ لم يتم العثور على مترجم csc.exe في النظام!")
    sys.exit(1)

print(f"✔️ تم العثور على مترجم مايكروسوفت: {csc_path}")

# 2. تجهيز مجلد الإخراج
dist_dir = os.path.join(current_dir, "SteamLibraryIntegrator")
if os.path.exists(dist_dir):
    shutil.rmtree(dist_dir)
os.makedirs(dist_dir, exist_ok=True)

runtime_dir = os.path.join(dist_dir, "runtime")
os.makedirs(runtime_dir, exist_ok=True)

# 3. نسخ كود برنامجك
app_dest = os.path.join(runtime_dir, "app.py")
shutil.copy2(script_source, app_dest)
print("✔️ تم نسخ كود البرنامج.")

# 4. نسخ ملفات بايثون المحمولة الرسمية من جهازك
py_root = sys.base_prefix
print(f"📦 جاري تجهيز بيئة التشغيل الرسمية من: {py_root}")

# نسخ ملفات التشغيل والـ DLLs الأساسية
for item in os.listdir(py_root):
    s = os.path.join(py_root, item)
    if os.path.isfile(s) and (item.lower().endswith(('.exe', '.dll'))):
        shutil.copy2(s, os.path.join(runtime_dir, item))

# نسخ مجلد DLLs
src_dlls = os.path.join(py_root, "DLLs")
if os.path.exists(src_dlls):
    shutil.copytree(src_dlls, os.path.join(runtime_dir, "DLLs"), dirs_exist_ok=True)

# نسخ مجلد Lib (مع استبعاد الملفات الزائدة وغير الضرورية لتخفيف الحجم)
src_lib = os.path.join(py_root, "Lib")
if os.path.exists(src_lib):
    shutil.copytree(
        src_lib,
        os.path.join(runtime_dir, "Lib"),
        ignore=shutil.ignore_patterns('test', '__pycache__', 'site-packages'),
        dirs_exist_ok=True
    )

print("✔️ تم تجهيز محرك بايثون الرسمي بنجاح.")

# 5. برمجة وبناء المشغل الرسمي النظيف (C#)
cs_code = r'''
using System;
using System.Diagnostics;
using System.IO;

namespace SteamIntegratorLauncher
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            try
            {
                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                string pyExe = Path.Combine(baseDir, "runtime", "pythonw.exe");
                string script = Path.Combine(baseDir, "runtime", "app.py");

                if (!File.Exists(pyExe) || !File.Exists(script))
                {
                    return;
                }

                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = pyExe;
                psi.Arguments = "\"" + script + "\"";
                psi.WorkingDirectory = baseDir;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;
                psi.WindowStyle = ProcessWindowStyle.Hidden;

                Process.Start(psi);
            }
            catch
            {
            }
        }
    }
}
'''

cs_file = os.path.join(current_dir, "Launcher.cs")
with open(cs_file, "w", encoding="utf-8") as f:
    f.write(cs_code)

output_exe = os.path.join(dist_dir, "SteamLibraryIntegrator.exe")

cmd = [
    csc_path,
    "/target:winexe",
    "/optimize+",
    f"/out:{output_exe}"
]

if os.path.exists(icon_source):
    cmd.append(f"/win32icon:{icon_source}")

cmd.append(cs_file)

res = subprocess.run(cmd, capture_output=True, text=True)
if os.path.exists(cs_file):
    os.remove(cs_file)

if res.returncode != 0:
    print(f"❌ خطأ أثناء تجميع المشغل: {res.stderr}")
    sys.exit(1)

print("✔️ تم تجميع المشغل التنفيذي (EXE) بواسطة مايكروسوفت بنجاح!")

# 6. ضغط البرنامج بالكامل في ملف ZIP جاهز للإرسال
zip_filename = os.path.join(current_dir, "SteamLibraryIntegrator_Clean.zip")
print("🗜️ جاري ضغط الحزمة في ملف ZIP...")

with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, _, files in os.walk(dist_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, current_dir)
            zipf.write(full_path, rel_path)

print("=" * 60)
print(f"🎉 مبروك! تم إنشاء الحزمة النظيفة المعتمدة بنجاح:")
print(f"📁 {zip_filename}")
print("=" * 60)
print("💡 أرسل ملف 'SteamLibraryIntegrator_Clean.zip' لخويك، يفك ضغطه ويشغل البرنامج فوراً بدون أي اعتراض من كاسبر سكاي نهائياً!")
