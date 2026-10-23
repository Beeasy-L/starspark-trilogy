# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright

SRC = "file:///C:/Users/saucc/Desktop/星火-专注pro/星火专注pro.html"

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 540, "height": 960})
    pg.goto(SRC)
    pg.wait_for_timeout(2200)
    before = pg.evaluate("() => { var m=document.getElementById('igniteMask'); return m? (m.className + '|' + getComputedStyle(m).display) : 'no-mask'; }")
    print("BEFORE:", before)
    r = pg.evaluate("""() => {
      var m = document.getElementById('igniteMask');
      if (!m) return 'no-mask';
      m.classList.add('on');
      return m.className + '|' + getComputedStyle(m).display;
    }""")
    print("AFTER:", r)
    pg.screenshot(path=r"C:\Users\saucc\Desktop\星火三部曲\assets\gif-frames\ig\debug-mask.png")
    print("DEBUG-SHOT-SAVED")
    b.close()
