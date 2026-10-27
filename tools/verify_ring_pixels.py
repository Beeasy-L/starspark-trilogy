# -*- coding: utf-8 -*-
"""合并后验证 · ring 视觉真相（修正版：用整页截图 + clip，避开透明背景问题）

上一版直接截 SVG 元素，PNG 带透明通道，convert("RGB") 丢 alpha 后颜色被压暗，
背景色测成了影子的中间值 —— 结果不可信。这一版改为：
  1. page.screenshot(clip=svg.boundingBox()) —— 裁切区域带真实页面背景，不透明
  2. 逐角度采样，底色直接用四个角

用法: python -X utf8 tools/_verify_ring_pixels.py
"""
import http.server
import math
import os
import socketserver
import threading
from collections import Counter

from PIL import Image
from playwright.sync_api import sync_playwright

APP = r"C:\Users\saucc\Desktop\星火三部曲\产品\星火PPT"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_out")
PORT = 8849

TEMPLATES = ["t1", "t2", "t9", "t12"]     # 1 深色 + 3 浅色
CHART = {"type": "ring", "unit": "%", "items": [{"label": "已用", "value": 68}]}

SETUP = """(args) => {
  const [tpl, chart] = args;
  state.template = tpl;
  buildDeck({ title:'占比环', subtitle:'', slides:[
    { title:'占比环', layout:'chart', content:[], chart: chart, note:'' }
  ]});
  renderStage();
  const svg = document.querySelector('#stage .page svg.ring-svg');
  const bg = document.querySelector('#stage .page .ring-bg');
  const fg = document.querySelector('#stage .page .ring-fg');
  const cs = bg ? getComputedStyle(bg) : null;
  const fs = fg ? getComputedStyle(fg) : null;
  const pg = document.querySelector('#stage .page');
  const pcs = pg ? getComputedStyle(pg) : null;
  return {
    ok: !!svg,
    bgStroke: cs ? cs.stroke : null,
    fgStroke: fs ? fs.stroke : null,
    fgLinecap: fs ? fs.strokeLinecap : null,
    fgWidth: fs ? fs.strokeWidth : null,
    dash: fg ? fg.getAttribute('stroke-dasharray') : null,
    pageBg: pcs ? pcs.backgroundColor : null,
    pageBgImg: pcs ? pcs.backgroundImage.slice(0, 70) : null,
  };
}"""


class Q(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=APP, **kw)

    def log_message(self, *a):
        pass


def measure(png):
    im = Image.open(png).convert("RGB")
    W, H = im.size
    px = im.load()
    cx, cy = W / 2.0, H / 2.0
    bg = Counter([px[2, 2], px[W - 3, 2], px[2, H - 3], px[W - 3, H - 3]]).most_common(1)[0][0]

    def d(c):
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(c, bg)))

    # 环半径：沿 12 点方向由内向外扫，取色差最大的半径
    best_r, best_v = 3, -1
    for r in range(3, int(min(W, H) / 2) - 2):
        y = int(cy - r)
        if not (0 <= y < H):
            continue
        v = d(px[int(cx), y])
        if v > best_v:
            best_v, best_r = v, r

    ring = []
    for deg in range(360):
        a = math.radians(deg - 90)
        mx = 0
        for dr in range(-6, 7):
            r = best_r + dr
            if r <= 0:
                continue
            x, y = int(cx + r * math.cos(a)), int(cy + r * math.sin(a))
            if 0 <= x < W and 0 <= y < H:
                mx = max(mx, d(px[x, y]))
        ring.append(mx)

    vals = sorted(ring, reverse=True)
    hi = vals[max(0, len(vals) // 20)]      # 前 5% 的水平 = 亮环
    lit_thr = hi * 0.55
    dim_lo = hi * 0.18

    lit = [v >= lit_thr for v in ring]
    n_lit = sum(lit)

    # 亮段连续区间数（段数）——像素会把相邻段粘连，所以这个数只是下限
    segs = 0
    for i in range(360):
        if lit[i] and not lit[(i - 1) % 360]:
            segs += 1

    # 底环：取未点亮区域（连续暗区）里色差的峰值
    not_lit = [ring[i] for i in range(360) if not lit[i]]
    peak_dim = max(not_lit) if not_lit else 0
    med_dim = sorted(not_lit)[len(not_lit) // 2] if not_lit else 0

    return dict(size=(W, H), bg=bg, r=best_r, hi=hi,
                lit_pct=n_lit / 360 * 100, segs=segs,
                peak_dim=peak_dim, med_dim=med_dim)


def main():
    os.makedirs(OUT, exist_ok=True)
    shots = os.path.join(OUT, "rings")
    os.makedirs(shots, exist_ok=True)

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), Q)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    out = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        pg.goto("http://127.0.0.1:%d/static/index.html" % PORT, wait_until="load", timeout=60000)
        pg.wait_for_timeout(2200)

        for tpl in TEMPLATES:
            info = pg.evaluate(SETUP, [tpl, CHART])
            pg.wait_for_timeout(450)
            box = pg.locator("#stage .page svg.ring-svg").bounding_box()
            png = os.path.join(shots, "clip_%s.png" % tpl)
            if box:
                pg.screenshot(path=png, clip=box)
            try:
                pg.locator("#stage .page").screenshot(path=os.path.join(shots, "full_%s.png" % tpl))
            except Exception:
                pass
            out.append((tpl, info, png))
        b.close()
    httpd.shutdown()

    print("=" * 86)
    print("ring 视觉真相 · 整页截图 clip 到 SVG 区域（背景不透明，可直接测色）")
    print("=" * 86)

    for tpl, info, png in out:
        print("\n■ 模板 %-4s" % tpl)
        print("   底环样式 stroke=%-28s" % info.get("bgStroke"))
        print("   亮环样式 stroke=%-28s linecap=%s width=%s"
              % (info.get("fgStroke"), info.get("fgLinecap"), info.get("fgWidth")))
        print("   dasharray=%s" % info.get("dash"))
        print("   页面背景色=%s  img=%s" % (info.get("pageBg"), info.get("pageBgImg")))
        if not os.path.exists(png):
            print("   ⚠️ 无截图")
            continue
        r = measure(png)
        print("   截图 %dx%d  角背景 rgb%s  环半径 %dpx  亮环水平 %.0f"
              % (r["size"][0], r["size"][1], r["bg"], r["r"], r["hi"]))
        gap = r["lit_pct"] - 68
        print("   亮环角度占比 = %5.1f%%  （数据 68%%）  偏差 %+.1f 个百分点  %s"
              % (r["lit_pct"], gap, "OK" if abs(gap) < 6 else "⚠️"))
        print("   连续亮段数 = %d（像素粘连，只作下限参考；XML 层实测 24 段）" % r["segs"])
        print("   底环可见性: 峰值色差 %.1f  中位 %.1f" % (r["peak_dim"], r["med_dim"]))
        v = "几乎不可见 ❌" if r["peak_dim"] < 10 else ("偏弱 ⚠️" if r["peak_dim"] < 25 else "清晰可见 ✅")
        print("   → %s" % v)

    print("\npageerror:", errs[:3] if errs else "无")
    print("\n截图目录（供能看图的人复核）:", shots)
    print("=" * 86)


if __name__ == "__main__":
    main()
