#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R1 发布前检查 · 续火花线上实测（星火架构师）
真 Chromium 访问 http://8.137.60.56:8000，测：
  A. 加载：DOMContentLoaded / load / 控制台错误
  B. 交互：按钮点击响应时间、折叠块展开、页面滑动帧率
  C. API：后端接口耗时（登录墙内则如实报）
只测不改。"""
import json, sys, time
from playwright.sync_api import sync_playwright

URL = "http://8.137.60.56:8000/"
OUT = {}

with sync_playwright() as pw:
    b = pw.chromium.launch()
    # 手机视口（这产品主打移动端）+ 桌面各测一遍
    for tag, vp in (("mobile", {"width":390,"height":844}), ("desktop", {"width":1440,"height":900})):
        ctx = b.new_context(viewport=vp, device_scale_factor=3 if tag=="mobile" else 1)
        pg = ctx.new_page()
        errs, warns = [], []
        pg.on("console", lambda m: (errs if m.type=="error" else warns).append(m.text[:120]) if m.type in ("error","warning") else None)
        api_log = []
        def on_resp(r):
            if "/api/" in r.url or "/static/" in r.url:
                api_log.append({"url": r.url.split("8000")[-1][:60], "status": r.status})
        pg.on("response", on_resp)
        t0 = time.time()
        try:
            pg.goto(URL, wait_until="load", timeout=60000)
        except Exception as e:
            OUT[tag] = {"fatal": str(e)[:200]}
            ctx.close(); continue
        load_s = round(time.time()-t0, 2)
        metrics = pg.evaluate("""() => {
            const nav = performance.getEntriesByType('navigation')[0] || {};
            return {dom_ready_ms: Math.round(nav.domContentLoadedEventEnd||0),
                    load_ms: Math.round(nav.loadEventEnd||0),
                    ttfb_ms: Math.round(nav.responseStart||0),
                    transfer_bytes: performance.getEntriesByType('resource').reduce((a,e)=>a+(e.transferSize||0),0),
                    res_count: performance.getEntriesByType('resource').length,
                    slowest: performance.getEntriesByType('resource').map(e=>({u:(e.name.split('8000')[1]||'').slice(0,50),ms:Math.round(e.duration)})).sort((x,y)=>y.ms-x.ms).slice(0,5)};
        }""")
        # B1. 交互：等首屏稳定后测点击响应
        pg.wait_for_timeout(1500)
        interact = {}
        try:
            btns = pg.locator("button:visible")
            n = btns.count()
            interact["visible_buttons"] = n
            if n > 0:
                t = time.time()
                btns.first.click(timeout=5000)
                pg.wait_for_timeout(400)
                interact["first_btn_click_ms"] = round((time.time()-t)*1000)
                pg.go_back(wait_until="load"); pg.wait_for_timeout(1200)
        except Exception as e:
            interact["click_err"] = str(e)[:120]
        # B2. 折叠块展开（若有）
        try:
            det = pg.locator("details:visible, .collapse-toggle, [class*='fold']")
            if det.count() > 0:
                t = time.time(); det.first.click(timeout=4000); pg.wait_for_timeout(300)
                interact["fold_expand_ms"] = round((time.time()-t)*1000)
                interact["fold_count"] = det.count()
        except Exception as e:
            interact["fold_err"] = str(e)[:100]
        # B3. 滑动帧率：滚动 2 秒采样
        try:
            fps = pg.evaluate("""() => new Promise(res => {
                let frames = [], last = performance.now();
                function tick(now){ frames.push(now-last); last = now;
                    if (frames.length < 90) requestAnimationFrame(tick); else res(frames); }
                requestAnimationFrame(tick);
                let y = 0; const sc = setInterval(() => { y += 28; window.scrollBy(0,28); document.querySelector('.app,.main,#app')?.scrollBy?.(0,28);
                    if (y > 2400) clearInterval(sc); }, 16);
            })""")
            fr = [f for f in fps if f > 0]
            worst = max(fr) if fr else 0
            interact["scroll_frames"] = len(fr)
            interact["scroll_avg_ms"] = round(sum(fr)/len(fr), 1) if fr else None
            interact["scroll_worst_frame_ms"] = round(worst, 1)
            interact["scroll_frames_over_32ms"] = sum(1 for f in fr if f > 32)
        except Exception as e:
            interact["scroll_err"] = str(e)[:100]
        OUT[tag] = {"load_s": load_s, **metrics, "interact": interact,
                    "console_errors": errs[:6], "error_count": len(errs),
                    "api_static_seen": len(api_log)}
        ctx.close()
    b.close()

print(json.dumps(OUT, ensure_ascii=False, indent=1))
