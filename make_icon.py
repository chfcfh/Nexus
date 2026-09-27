import os
import sys
import subprocess

# تثبيت مكتبة الرسم Pillow تلقائياً إذا لم تكن موجودة
try:
    from PIL import Image, ImageDraw
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image, ImageDraw

size = 256
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 1. الدائرة الخلفية بلون ستيم الكربوني الداكن
draw.ellipse((8, 8, 248, 248), fill="#171a21", outline="#2a475e", width=5)

# 2. رسم ذراع وتروس شعار Steam باللون الأزرق السماوي (Cyan)
# الذراع الواصل
draw.line([(88, 155), (160, 83)], fill="#66c0f4", width=22)
# الترس السفلي الكبير
draw.ellipse((42, 109, 134, 201), outline="#66c0f4", width=13, fill="#1b2838")
draw.ellipse((73, 140, 103, 170), fill="#66c0f4")
# الترس العلوي الصغير
draw.ellipse((135, 58, 185, 108), fill="#66c0f4")
draw.ellipse((147, 70, 173, 96), fill="#171a21")

# 3. شارة علامة الزائد (+) في الزاوية السفلية يمين
bx0, by0, bx1, by1 = 150, 150, 246, 246
# إطار خارجي داكن لعزل الشارة
draw.ellipse((bx0 - 3, by0 - 3, bx1 + 3, by1 + 3), fill="#121316")
# خلفية الشارة بلون أخضر ستيم التفاعلي
draw.ellipse((bx0, by0, bx1, by1), fill="#2ea44f", outline="#34c45b", width=3)

# رسم علامة الزائد (+) البيضاء في المنتصف
cx, cy = 198, 198
pw = 8   # سمك الخط
pl = 24  # طول الذراع
draw.rectangle((cx - pl, cy - pw // 2, cx + pl, cy + pw // 2), fill="#ffffff")
draw.rectangle((cx - pw // 2, cy - pl, cx + pw // 2, cy + pl), fill="#ffffff")

# حفظ الأيقونة بجميع مقاسات نظام ويندوز
icon_name = "icon.ico"
img.save(icon_name, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print(f"تم إنشاء ملف الأيقونة بنجاح: {os.path.abspath(icon_name)}")
