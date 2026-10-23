# -*- coding: utf-8 -*-
import os, time
from playwright.sync_api import sync_playwright

SRC = "file:///C:/Users/saucc/Desktop/星火-专注pro/星火专注pro.html"
FRAMES = r"C:\Users\saucc\Desktop\星火三部曲\assets\gif-frames\ig"
os.makedirs(FRAMES, exist_ok=True)

MASK_ON = """() => {
  var box = document.getElementById('igniteEmbers'); if (box) box.innerHTML='';
  var m = document.getElementById('igniteMask'); if (m) m.classList.add('on');
  // 放大火焰三层
  var fs = document.querySelectorAll('.spark-flame .flame');
  if (fs.length >= 3) {
    fs[0].style.width='108px'; fs[0].style.height='180px';
    fs[1].style.width='75px';  fs[1].style.height='133px';
    fs[2].style.width='47px';  fs[2].style.height='86px';
  }
  // 火星粒子：从火焰根部喷出
  for (var i=0;i<40;i++){
    var p = document.createElement('i'); p.className='ember-p';
    p.style.left = (Math.random()*100)+'%';
    p.style.bottom = (Math.random()*30)+'px';
    p.style.animationDelay = (Math.random()*.5)+'s';
    p.style.animationDuration = (1+Math.random()*.8)+'s';
    if (box) box.appendChild(p);
  }
  return 'mask-on flames='+fs.length;
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 540, "height": 960})
    pg.goto(SRC)
    pg.wait_for_timeout(2200)
    r = pg.evaluate(MASK_ON)
    print("R:", r)
    pg.wait_for_timeout(300)  # 等 ignitePop 弹出完成
    for i in range(16):
        pg.screenshot(path=os.path.join(FRAMES, "ig-%02d.png" % i))
        time.sleep(0.16)
    print("frames-ok 16")
    b.close()
