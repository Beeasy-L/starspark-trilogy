# -*- coding: utf-8 -*-
import os
from PIL import Image

base = r"C:\Users\saucc\Desktop\星火三部曲\assets\gif-frames\bu2"
out = r"C:\Users\saucc\Desktop\星火三部曲\assets\focus-ignite-anim.gif"
preview = os.path.join(base, "preview-crop.png")

files = sorted(f for f in os.listdir(base) if f.lower().startswith("ig-") and f.lower().endswith(".png"))
# 均匀取 8 帧
files = [files[i] for i in range(0, len(files), max(1, len(files) // 8))][:8]
print("frames:", len(files))
frames = []
for fn in files:
    im = Image.open(os.path.join(base, fn)).convert("RGB")
    # 完整火焰 + 点火文字 + 火星，背景纯深色
    crop = im.crop((300, 240, 620, 610))  # 320x370
    crop = crop.resize((440, 508), Image.LANCZOS)
    frames.append(crop.convert("P", palette=Image.ADAPTIVE, colors=128))

frames[0].save(out, save_all=True, append_images=frames[1:],
               duration=280, loop=0, optimize=True)
frames[0].save(preview)
print("GIF_OK size=%dKB frames=%d" % (os.path.getsize(out) // 1024, len(frames)))
