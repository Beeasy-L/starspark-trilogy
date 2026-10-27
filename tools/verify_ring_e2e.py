# -*- coding: utf-8 -*-
"""合并后首次执行 · 验收官+解读 双视角端到端验证

本脚本一次回答三个问题（此前只有验收官那边有 Chromium 权限，我这边答不了）：
  ① 三种图表在**浅色模板**（t2 月白清光 / t9 米白学术 / t12 暖砂手记）下渲染是否正确
     —— 重点看 ring 的白色底环在浅底上还能不能看见
  ② ring 在**浏览器里**段落之间有没有视觉缝隙
  ③ 导出 pptx 用**真 PowerPoint** 打开 ring 页 —— 23 个旋转分段会不会触发修复对话框

产出：
  _out/shots/*.png      逐模板逐类型的真实渲染截图
  _out/ring_light.pptx  浅色模板下的 ring 导出件（供 ③ 用）

用法: python -X utf8 tools/_verify_ring_e2e.py
"""
import http.server
import os
import re
import socketserver
import threading
import zipfile

from playwright.sync_api import sync_playwright

APP = r"C:\Users\saucc\Desktop\星火三部曲\产品\星火PPT"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_out")
PORT = 8847

LIGHT_TPL = ["t2", "t9", "t12"]      # 月白清光 / 米白学术 / 暖砂手记
CHART = {"type": "ring", "unit": "%", "items": [{"label": "已用", "value": 68}]}

SETUP = """(args) => {
  const [tpl, chart] = args;
  state.template = tpl;
  buildDeck({ title:'浅色模板 ring', subtitle:'x', slides:[
    { title:'占比环', layout:'chart', content:[], chart: chart, note:'收束句' }
  ]});
  renderStage();
  const pg = document.querySelector('#stage .page');
  const out = { tpl: tpl, hasPage: !!pg };
  if (pg) {
    const svg = pg.querySelector('svg.ring-svg') || pg.querySelector('svg');
    const bg = pg.querySelector('.ring-bg');
    const fg = pg.querySelector('.ring-fg');
    if (svg) {
      const r = svg.getBoundingClientRect();
      out.svgBox = [Math.round(r.width), Math.round(r.height)];
    }
    if (bg) {
      const cs = getComputedStyle(bg);
      out.bgStroke = cs.stroke;
      out.bgStrokeW = cs.strokeWidth;
    }
    if (fg) {
      const cs = getComputedStyle(fg);
      out.fgStroke = cs.stroke;
      out.dash = fg.getAttribute('stroke-dasharray');
    }
    // 页面背景色（用来判底环对比度）
    out.pageBg = getComputedStyle(pg).backgroundColor;
    const bi = getComputedStyle(pg).backgroundImage;
    out.pageBgImg = bi.slice(0, 80);
  }
  try { document.getElementById('btn-export-pptx').classList.remove('hide'); } catch(e){}
  return out;
}"""


class Q(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=APP, **kw)

    def log_message(self, *a):
        pass


def contrast_ratio(c1, c2):
    """两色的 WCAG 对比度（简化：只处理 rgb）"""
    def lum(s):
        m = re.findall(r"[\d.]+", s)
        if len(m) < 3:
            return None
        rgb = [float(x) / 255.0 for x in m[:3]]
        rgb = [(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4) for v in rgb]
        return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    a, b = lum(c1), lum(c2)
    if a is None or b is None:
        return None
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "shots"), exist_ok=True)
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), Q)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    results = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        pg.goto("http://127.0.0.1:%d/static/index.html" % PORT, wait_until="load", timeout=60000)
        pg.wait_for_timeout(2200)

        for tpl in LIGHT_TPL:
            r = pg.evaluate(SETUP, [tpl, CHART])
            pg.wait_for_timeout(400)
            shot = os.path.join(OUT, "shots", "ring_%s.png" % tpl)
            try:
                pg.locator("#stage .page").screenshot(path=shot)
                r["shot"] = shot
            except Exception as e:
                r["shotErr"] = str(e)[:100]
            results.append(r)

        # 导出一份浅色模板的 pptx（供 PowerPoint 验证）
        pg.evaluate(SETUP, ["t9", CHART])
        pg.wait_for_timeout(300)
        dest = os.path.join(OUT, "ring_light.pptx")
        try:
            with pg.expect_download(timeout=30000) as dl:
                pg.evaluate("() => document.getElementById('btn-export-pptx').click()")
            dl.value.save_as(dest)
        except Exception as e:
            print("导出失败:", str(e)[:160])
            dest = None

        b.close()
    httpd.shutdown()

    print("=" * 84)
    print("合并后首次端到端验证 · ring 在浅色模板下")
    print("=" * 84)
    for r in results:
        tpl = r["tpl"]
        print("\n■ 模板 %s" % tpl)
        print("   SVG 盒子: %s" % r.get("svgBox"))
        print("   底环 stroke: %s  width=%s" % (r.get("bgStroke"), r.get("bgStrokeW")))
        print("   亮环 stroke: %s  dasharray=%s" % (r.get("fgStroke"), r.get("dash")))
        print("   页面背景: %s  (img=%s)" % (r.get("pageBg"), r.get("pageBgImg")))
        cr = None
        if r.get("bgStroke") and r.get("pageBg"):
            cr = contrast_ratio(r["bgStroke"], r["pageBg"])
        if cr is not None:
            verdict = "不可见 ❌" if cr < 1.2 else ("偏弱 ⚠️" if cr < 2.0 else "可辨 ✅")
            print("   底环 vs 页面背景 对比度 = %.2f : 1  → %s" % (cr, verdict))
        if r.get("shot"):
            print("   截图: %s" % r["shot"])
    print("\npageerror:", errs[:3] if errs else "无")

    # ---- 导出件里的 ring 形状（浅色模板） ----
    if dest and os.path.exists(dest):
        print("\n" + "=" * 84)
        print("浅色模板导出件：%s（%.1f KB）" % (os.path.basename(dest), os.path.getsize(dest) / 1024))
        print("=" * 84)
        z = zipfile.ZipFile(dest)
        slides = sorted([n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)],
                        key=lambda s: int(re.search(r"(\d+)", s.split("/")[-1]).group(1)))
        for sn in slides:
            x = z.read(sn).decode("utf-8", "ignore")
            rots = re.findall(r"rot=\"(-?\d+)\"", x)
            ring = re.search(r'name="(SvgRing\d+)"[\s\S]{0,400}?val="([0-9A-F]{6})"[\s\S]{0,120}?alpha val="(\d+)"', x)
            print("  %s  形状%d  旋转段%d" % (sn.split("/")[-1], x.count("<p:sp>"), len(rots)))
            if ring:
                print("     底环 %s fill=%s alpha=%s"
                      % (ring.group(1), ring.group(2), int(ring.group(3)) / 1000.0))
        print("\n  导出件路径（供下一步 PowerPoint 验证）:", dest)
    print("\n" + "=" * 84)


if __name__ == "__main__":
    main()
