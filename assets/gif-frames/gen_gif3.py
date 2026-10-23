# -*- coding: utf-8 -*-
import os, time
from playwright.sync_api import sync_playwright

SRC = "file:///C:/Users/saucc/Desktop/星火-专注pro/星火专注pro.html"
FRAMES = r"C:\Users\saucc\Desktop\星火三部曲\assets\gif-frames\ig"

IGNITE_BIG = """() => {
  var fs = document.querySelectorAll('.spark-flame .flame');
  if (fs.length >= 3) {
    fs[0].style.width='96px';  fs[0].style.height='160px';
    fs[1].style.width='67px';  fs[1].style.height='118px';
    fs[2].style.width='42px';  fs[2].style.height='77px';
  }
  if (typeof ignite === 'function') { ignite(); return 'ignited'; }
  return 'no-ignite-fn';
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 540, "height": 960})
    pg.goto(SRC)
    pg.wait_for_timeout(2200)
    r = pg.evaluate(IGNITE_BIG)
    print("R:", r)
    # 立即连拍，0.1s 间隔，总窗口约 1.2-1.6s < 1.9s
    for i in range(12):
        pg.screenshot(path=os.path.join(FRAMES, "ig-%02d.png" % i))
        time.sleep(0.1)
    print("frames-ok 12")
    b.close()
