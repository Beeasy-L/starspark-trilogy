# -*- coding: utf-8 -*-
from PIL import Image
import os

base = r"C:\Users\saucc\Desktop\星火三部曲\assets\gif-frames\bu"
im = Image.open(os.path.join(base, "ig-00.png")).convert("RGB")
w, h = im.size
px = im.load()

# 金色火焰像素: R>200, G>150, B<160 (金黄渐变 FFE69A/F2C66D/E8915B)
xs, ys = [], []
for y in range(0, h, 2):
    for x in range(0, w, 2):
        r, g, b = px[x, y]
        if r > 200 and g > 150 and b < 170 and r > g:
            xs.append(x); ys.append(y)
if xs:
    print("gold bbox:", min(xs), min(ys), max(xs), max(ys), "count=", len(xs))
else:
    print("no gold found")

# 也找较亮的暖色点（含火焰内部白亮层）
xs2, ys2 = [], []
for y in range(0, h, 2):
    for x in range(0, w, 2):
        r, g, b = px[x, y]
        if r > 180 and g > 130 and b < 190 and r >= g:
            xs2.append(x); ys2.append(y)
if xs2:
    print("warm bbox:", min(xs2), min(ys2), max(xs2), max(ys2), "count=", len(xs2))
