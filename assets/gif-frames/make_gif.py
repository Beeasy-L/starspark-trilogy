# -*- coding: utf-8 -*-
import os
from PIL import Image

base = r"C:\Users\saucc\Desktop\星火三部曲\assets\gif-frames"
out = r"C:\Users\saucc\Desktop\星火三部曲\assets\focus-ignite-anim.gif"

files = sorted(f for f in os.listdir(base) if f.lower().startswith("f") and f.lower().endswith(".png"))
assert len(files) >= 10, "frames missing: %d" % len(files)
frames = []
for fn in files:
    im = Image.open(os.path.join(base, fn)).convert("RGB")
    w = 340
    h = round(im.height * w / im.width)
    im = im.resize((w, h), Image.LANCZOS)
    frames.append(im)

frames[0].save(out, save_all=True, append_images=frames[1:],
               duration=280, loop=0, optimize=True)
print("GIF_OK frames=%d size=%dKB" % (len(frames), os.path.getsize(out) // 1024))
