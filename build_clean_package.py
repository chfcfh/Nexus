import os
import sys
import shutil
import zipfile
import subprocess
from PIL import Image, ImageDraw

print("=" * 65)
print("🚀 جاري بناء الحزمة النظيفة ودمج الأيقونة في Nexus.exe...")
print("=" * 65)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "Nexus")
RUNTIME_DIR = os.path.join(OUTPUT_DIR, "runtime")
ICO_PATH = os.path.join(BASE_DIR, "logo.ico")

# 1. التأكد من وجود ملف logo.ico أو إنشاؤه فوراً لدمجه
if not os.path.exists(ICO_PATH):
    print("\n[0/4] 🎨 جاري إنشاء ملف الأيقونة logo.ico...")
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([12, 12, 244, 244], radius=55, fill=(11, 15, 23, 255), outline=(30, 43, 69, 255), width=6)
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
    img.save(ICO_PATH, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("  ✔️ تم إنشاء logo.ico بنجاح!")

# 2. تنظيف المجلد القديم
if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)

os.makedirs(RUNTIME_DIR, exist_ok=True)

# 3. بناء المشغل ودمج الأيقونة داخله
print("\n[1/4] 🔨 جاري إنشاء المشغل التنفيذي ودمج الشعار داخله...")
launcher_cs = os.path.join(BASE_DIR, "launcher.cs")
launcher_exe = os.path.join(OUTPUT_DIR, "Nexus.exe")

cs_code = """
using System;
using System.Diagnostics;
using System.IO;

class Program {
    static void Main(string[] args) {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        string pythonw = Path.Combine(baseDir, "runtime", "pythonw.exe");
        string script = Path.Combine(baseDir, "runtime", "app.py");

        if (!File.Exists(pythonw) || !File.Exists(script)) {
            return;
        }

        ProcessStartInfo psi = new ProcessStartInfo();
        psi.FileName = pythonw;
        psi.Arguments = "\\"" + script + "\\"";
        psi.WorkingDirectory = Path.Combine(baseDir, "runtime");
        psi.WindowStyle = ProcessWindowStyle.Hidden;
        psi.CreateNoWindow = true;
        psi.UseShellExecute = false;

        try {
            Process.Start(psi);
        } catch { }
    }
}
"""

with open(launcher_cs, "w", encoding="utf-8") as f:
    f.write(cs_code)

csc_paths = [
    r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
    r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"
]
csc_compiler = next((p for p in csc_paths if os.path.exists(p)), None)

if csc_compiler:
    compile_cmd = [
        csc_compiler,
        "/target:winexe",
        "/optimize+",
        f"/win32icon:{ICO_PATH}",   # دمج الأيقونة في ملف الـ EXE
        f"/out:{launcher_exe}",
        launcher_cs
    ]
    subprocess.run(compile_cmd, check=True)
    if os.path.exists(launcher_cs):
        os.remove(launcher_cs)
    print("  ✔️ تم دمج الأيقونة وبناء Nexus.exe بنجاح!")
else:
    print("  ❌ لم يتم العثور على مترجم ويندوز csc.exe.")

# 4. نقل ملفات بيئة التشغيل
print("\n[2/4] 📦 جاري تجهيز مجلد runtime...")
py_dir = sys.base_prefix

files_to_copy = ["python.exe", "pythonw.exe", "python3.dll"]
for item in os.listdir(py_dir):
    if item.endswith(".dll") and ("python" in item or "vcruntime" in item):
        files_to_copy.append(item)

for f in files_to_copy:
    src = os.path.join(py_dir, f)
    if os.path.exists(src):
        shutil.copy2(src, RUNTIME_DIR)

src_dlls = os.path.join(py_dir, "DLLs")
if os.path.exists(src_dlls):
    shutil.copytree(src_dlls, os.path.join(RUNTIME_DIR, "DLLs"), dirs_exist_ok=True)

print("  ⏳ جاري نقل المكتبات...")
src_lib = os.path.join(py_dir, "Lib")
dst_lib = os.path.join(RUNTIME_DIR, "Lib")

def ignore_patterns(path, names):
    ignored = []
    for n in names:
        if n in ["__pycache__", "idlelib", "test", "turtledemo"]:
            ignored.append(n)
    return ignored

shutil.copytree(src_lib, dst_lib, ignore=ignore_patterns, dirs_exist_ok=True)

# 5. نسخ الملفات الداخلية
print("\n[3/4] 📄 جاري نسخ ملفات البرنامج...")
for item in ["app.py", "logo.ico", "logo.png", "profiles.json", "config.json"]:
    src = os.path.join(BASE_DIR, item)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(RUNTIME_DIR, item))

readme_content = """# ⚡ NEXUS Suite

> **حزمة أدوات متكاملة لنظام ويندوز تجمع بين إدارة العرض والصوت الذكية ودمج الألعاب الخارجية داخل Steam.**

---

## 📖 نظرة عامة
**NEXUS** هو برنامج محمول (Portable) تم تصميمه لتحسين تجربة استخدام الكمبيوتر والألعاب، حيث يدمج أداتين أساسيتين في واجهة نيون عصرية وموحدة:

1. **NexusFlow (إدارة العرض والصوت):** للتحكم الفوري في إعدادات الشاشات ومخارج الصوت.
2. **SteamLibraryIntegrator (مكتبة ستيم):** لفحص الألعاب الخارجية وإضافتها تلقائياً إلى منصة Steam مع الأغلفة.

---

## ✨ المميزات الرئيسية

### 🎮 NexusFlow | Display & Audio Manager
* **أوضاع مخصصة (Profiles):** إنشاء بروفايلات جاهزة بضغطة زر (مثل وضع اللعب، وضع الأفلام، وضع الشاشة الواحدة).
* **اختصارات كيبورد عالمية (Hotkeys):** التبديل بين الأوضاع فوراً من داخل أي لعبة باستخدام اختصارات مخصصة (مثل `Ctrl + Shift + 1`).
* **تحكم ذكي في العرض:** تمديد الشاشات (Extend)، التكرار (Duplicate)، أو تشغيل شاشة معينة فقط.
* **توجيه الصوت ومستوياته:** حفظ مخرج الصوت الافتراضي ومستوى الصوت المحدد لكل وضع بشكل مستقل.
* **دعم تقنية HDR:** تفعيل أو تعطيل HDR تلقائياً حسب احتياج كل وضع.
* **استوديو الصوت:** قائمة تفاعلية لجميع مخارج الصوت المتصلة مع أداة لاختبار الصوت بضغطة زر.

### 🕹️ SteamLibraryIntegrator
* **فحص المجلدات التلقائي:** اكتشاف المشغلات التنفيذية (`.exe`) الصالحة للألعاب المثبتة خارج منصة Steam تلقائياً.
* **جلب الأغلفة تلقائياً (Artwork Fetcher):** تحميل الأغلفة العمودية، الصور العريضة (Hero)، الشعارات الشفافة (Logo)، والبنرات الرسمية وحفظها في مجلد الحساب.
* **دعم الحسابات المتعددة:** إمكانية تطبيق الألعاب على حساب Steam النشط حالياً أو على جميع الحسابات المسجلة بالجهاز دفعة واحدة.
* **إدارة آمنة:** إغلاق وإعادة تشغيل Steam بأمان لتطبيق التعديلات على ملف `shortcuts.vdf` دون فقدان أي بيانات سابقة.

### ⚙️ مزايا النظام والأداء
* **برنامج محمول بالكامل (Portable):** لا يتطلب تثبيت أي بيئات مسبقة أو حزم خارجية.
* **تصغير لشريط المهام (System Tray):** تشغيل دائم في الخلفية واستجابة فورية للاختصارات بدون استهلاك للموارد.
* **تحديثات مدمجة:** فحص وتحميل أحدث إصدارات البرنامج تلقائياً عبر GitHub بضغطة زر.
* **ثيمات مخصصة:** إمكانية تخصيص ألوان الواجهة النيون حسب رغبتك.

---

## 🚀 طريقة الاستخدام

1. قم بفك ضغط الحزمة في أي مجلد تريده.
2. شغّل البرنامج مباشرة عبر النقر المزدوج على **`Nexus.exe`**.
3. **لإضافة وضع جديد:** اضغط على `وضع جديد` من الصفحة الرئيسية وحدد الشاشات، مخرج الصوت، والاختصار المناسب.
4. **لإضافة ألعابك لـ Steam:** انتقل إلى تبويب `إضافة الألعاب`، اختر مجلد ألعابك واضغط `فحص الألعاب`، ثم اضغط `إضافة الألعاب وتعيين الأغلفة`.

---

## 🛡️ الأمان والخصوصية
* البرنامج مفتوح المصدر وآمن 100%.
* تم بناء الحزمة بمشغل تنفيذي أصلي ونظيف لا يثير أي تنبيهات أمنية كاذبة لدى برامج الحماية (مثل Kaspersky و Windows Defender).

---

**تطوير:** محمد  
**الترخيص:** مفتوح المصدر (Open Source)
"""

with open(os.path.join(OUTPUT_DIR, "README.md"), "w", encoding="utf-8") as f:
    f.write(readme_content)

# 6. ضغط الحزمة إلى ملف ZIP نهائي وسليم تماماً
print("\n[4/4] 🗜️ جاري ضغط الحزمة بالكامل عبر محرك ويندوز المباشر...")
zip_base = os.path.join(BASE_DIR, "Nexus")
zip_file = zip_base + ".zip"

# حذف أي ملف مضغوط قديم تالف أولاً
if os.path.exists(zip_file):
    try:
        os.remove(zip_file)
    except Exception:
        pass

# ضغط مجلد OUTPUT_DIR بشكل نظيف ومستقر
try:
    shutil.make_archive(zip_base, 'zip', root_dir=os.path.dirname(OUTPUT_DIR), base_dir=os.path.basename(OUTPUT_DIR))
    print("\n" + "=" * 65)
    print("🎉 تم الانتهاء بنجاح 100% وتم إنشاء ملف الـ ZIP بدون أي أخطاء!")
    print(f"📦 مسار الملف: {zip_file}")
    print("=" * 65)
except Exception as e:
    print(f"خطأ أثناء الضغط: {e}")
