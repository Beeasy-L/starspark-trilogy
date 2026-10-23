# -*- coding: utf-8 -*-
import os
from PIL import Image

base = r"C:\Users\saucc\Desktop\星火三部曲\assets\gif-frames\bu"
out = r"C:\Users\saucc\Desktop\星火三部曲\assets\focus-ignite-anim.gif"
preview = os.path.join(base, "preview-crop.png")

files = sorted(f for f in os.listdir(base) if f.lower().startswith("ig-") and f.lower().endswith(".png"))
# 均匀取 8 帧
files = [files[i] for i in range(0, len(files), 12 // 8)][:8]
print("frames:", len(files))
frames = []
for fn in files:
    im = Image.open(os.path.join(base, fn)).convert("RGB")
    # 只留火焰主体+点火文字+火星（背景为深色遮罩，压缩友好）
    crop = im.crop((390, 470, 610, 680))  # 220x210
    crop = crop.resize((440, 420), Image.LANCZOS)
    frames.append(crop)

frames[0].save(out, save_all=True, append_images=frames[1:],
               duration=300, loop=0, optimize=True)
frames[0].save(preview)
print("GIF_OK size=%dKB preview=%s" % (os.path.getsize(out) // 1024, preview))
