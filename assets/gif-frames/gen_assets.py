# -*- coding: utf-8 -*-
import os, time
from playwright.sync_api import sync_playwright

SRC = "file:///C:/Users/saucc/Desktop/星火-专注pro/星火专注pro.html"
OUT = r"C:\Users\saucc\Desktop\星火三部曲\assets"
FRAMES = os.path.join(OUT, "gif-frames")
os.makedirs(FRAMES, exist_ok=True)

INJECT = """() => {
  var now = Date.now();
  S.chain = {currentNo:6, bestNo:9, genesis: now-6*86400000};
  S.blocks = [
    {id:'s1', ignitedAt:now-6*86400000, endedAt:now-6*86400000+1500000, minutes:25, actualSec:1500, state:'done', task:'高数第三章'},
    {id:'s2', ignitedAt:now-5*86400000, endedAt:now-5*86400000+1500000, minutes:25, actualSec:1500, state:'done', task:'线性代数笔记'},
    {id:'s3', ignitedAt:now-4*86400000, endedAt:now-4*86400000+1500000, minutes:25, actualSec:1500, state:'done', task:'英语单词'},
    {id:'s4', ignitedAt:now-3*86400000, endedAt:now-3*86400000+1500000, minutes:25, actualSec:1500, state:'done', task:'概率论习题'},
    {id:'s5', ignitedAt:now-2*86400000, endedAt:now-2*86400000+1500000, minutes:25, actualSec:1500, state:'done', task:'数据结构'},
    {id:'s6', ignitedAt:now-1*86400000, endedAt:now-1*86400000+1500000, minutes:25, actualSec:1500, state:'done', task:'高数第三章复习'}
  ];
  save(); renderChain();
  var m = document.getElementById('igniteMask'); if (m) m.classList.remove('on');
}"""

CLICK_CHAIN = """() => {
  var b = Array.from(document.querySelectorAll('button')).filter(x => x.textContent.trim() === '星链');
  if (b[0]) b[0].click();
  var b2 = Array.from(document.querySelectorAll('button')).filter(x => x.textContent.trim() === '首页');
  return 'clicked';
}"""

MASK_ON = """() => {
  var box = document.getElementById('igniteEmbers'); if (box) box.innerHTML='';
  var m = document.getElementById('igniteMask'); if (m) m.classList.add('on');
  for (var i=0;i<34;i++){
    var p = document.createElement('i'); p.className='ember-p';
    p.style.left = (38+Math.random()*24)+'%';
    p.style.animationDelay = (Math.random()*.5)+'s';
    p.style.animationDuration = (1+Math.random()*.8)+'s';
    if (box) box.appendChild(p);
  }
  return 'mask-on';
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 800, "height": 1000})
    pg.goto(SRC)
    pg.wait_for_timeout(2200)
    pg.evaluate(INJECT)
    pg.wait_for_timeout(300)
    pg.evaluate(CLICK_CHAIN)
    pg.wait_for_timeout(2200)
    pg.screenshot(path=os.path.join(OUT, "focus-chain-v2.png"))
    print("chain-shot-ok")

    pg.evaluate(MASK_ON)
    pg.wait_for_timeout(200)
    for i in range(12):
        pg.screenshot(path=os.path.join(FRAMES, "g2-%02d.png" % i))
        time.sleep(0.28)
    print("frames-ok 12")
    b.close()
