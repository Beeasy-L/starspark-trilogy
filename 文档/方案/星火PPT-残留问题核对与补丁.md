# 星火PPT · 残留问题核对与补丁

> 星火专注Pro 核对 — 2026-10-24 18:2x
> 核对基准：`static/index.html` **992 行版**（你正在实时改，行号会漂，**认选择器不认行号**）
>
> 你已经完成的（我核对过，不重复建议）：12 种版式全部实现、`checkRenderer()` 已实现**并已挂到脚本末尾**、`normLayout()` 别名表、`note` 已渲染成 `.pnote`、编辑器下拉同步、三处渲染路径统一走 `normLayout`+`pageHTML`。
> **下面只列还没解决的，按严重度排序。**

---

## 🔴 P0 — 导出独立 HTML 的 CSS 断档（预览好看，导出崩）

### 现象

`buildExportCSS()`（#799-809）是**第二份手写的样式表**，它只覆盖：

```
.page .pt / .page .phr / .page .ulist
.page.cover / .page.closing
theme-t2~t6 的色板
```

**但导出用的 DOM 已经是新渲染器产出的**（#779）：

```js
const body=state.slides.map((s,i)=>
  `<div class="page ... ${normLayout(s.layout)} s${i}">${pageHTML(s,i,total)}</div>`).join("\n");
```

`pageHTML` 会输出 `.kpi-row / .kpi-cell / .kpi-num / .kpi-lab`、`.tl / .tl-item / .tl-h / .tl-d`、
`.steps / .step / .step-n / .step-t / .step-d`、`.cmp / .cmp-col / .cmp-rule / .cmp-item`、
`.lgrid / .lcell`、`.tbl`、`.zz / .zz-row / .zz-h / .zz-d`、`.qk / .qt / .qsrc`、`.pnote`、`.twocol-body / .tc-col`。

**这些类名，导出的 CSS 里一个都没有。**

### 后果

导出一份用了 `kpi` / `timeline` / `compare` / `quote` / `zigzag` 的 deck →
在**网页里预览是好的**，导出成独立 HTML 后：
- `.kpi-row` 没有 grid → 大数字和标签全部堆成一列纯文本
- `.tl` 没有竖线、`.tl-item` 没有圆点 → 时间轴退化成一行行文字
- `.cmp` 没有栅格、`.cmp-rule` 那条中缝细线是空 div（**display 没设，高度 0，直接看不见**）
- `.qk / .qt` 没有字号 → 金句页变成 15px 正文，**节奏武器失效**
- `.pnote` 没有吸底和顶线 → 收束句飘在正文下面

**这是目前最伤的一处**：boss 预览满意 → 导出发给别人 → 打开是崩的。

### 根因：两份样式表，必然漂移

主 `<style>` 和 `buildExportCSS()` 是同一套版式的两次手写。你每加一个版式，
必须记得改两个地方 —— 这次就漏了 8 个。**继续维护两份，下次还会漏。**

### 推荐修法：导出时从已解析的样式表里「捞」版式规则

不要手抄第二份，直接序列化当前页面的样式表。**单一来源，永不再漂移**：

```js
/* 从当前文档已解析的样式表里，挑出幻灯片版式相关的规则 */
function collectSlideCSS(){
  const KEEP=/\.(page|pt|phr|pnote|pno|cover|closing|deco|ck|ct|cb|cs|cm|ulist|twocol|tc-col|lgrid|lcell|kpi|tl|step|cmp|tbl|zz|qk|qt|qsrc|theme-t)\b/;
  const out=[];
  for(const sheet of document.styleSheets){
    let rules;
    try{ rules=sheet.cssRules; }catch(e){ continue; }   // 跨域样式表会抛，跳过
    for(const r of rules){
      if(r.type!==1) continue;                          // 只要 CSSStyleRule，跳过 @media/@keyframes
      const t=r.cssText||"";
      if(KEEP.test(t)) out.push(t);
    }
  }
  return out.join("\n");
}
```

然后 `buildExportCSS()` 改成 **基础壳 + 捞上来的版式 CSS**：

```js
function buildExportCSS(){
  const shell=`
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",system-ui,sans-serif;background:#05070f}
.topbar{display:flex;align-items:center;gap:14px;padding:12px 20px;background:#0D1226;color:#ECEAF4;border-bottom:1px solid rgba(255,255,255,.12)}
.topbar .logo{font-family:"Noto Serif SC","Songti SC",serif;font-weight:700;color:#FFD98A}
.topbar .nav{margin-left:auto;display:flex;gap:10px}
.topbar button{background:none;border:1px solid rgba(255,255,255,.2);color:#fff;padding:5px 14px;border-radius:8px;cursor:pointer;font-size:15px}
.topbar #c{color:#B7BDDA;font-size:13px;font-family:monospace;align-self:center}
.stage{position:relative;height:calc(100vh - 56px)}
.page{position:absolute;inset:0}
`;
  return shell + "\n" + collectSlideCSS();   // ← 关键：版式样式从主样式表来
}
```

**收益**：以后再加版式，导出自动跟上，**不需要动 `buildExportCSS()`**。

**注意事项**：
1. `.page` 上的 `--gutter/--ts-*` 令牌写在 `.page{...}` 选择器里（#161-164），所以会被一起捞到 ✓
2. `@media` 里的响应式规则（`r.type===4`）不会被捞。导出主要给桌面看，可接受；要更稳就递归展开 `r.cssRules`
3. 捞到的规则里如果有 `.stage`、`.topbar` 之类的页面外壳类，会被外壳样式覆盖（外壳在后、优先级同级时后者胜）—— 我把外壳放前面正是为此
4. `collectSlideCSS()` 必须**在导出时调用**（此时样式表已解析完成）

---

## 🟠 P1 — 四个残留排版数值

### 1. 正文行长仍是 53 字 —— 「文字不工整」的主因还没解决

```css
/* #189 现状 */
.ulist{list-style:none;margin:16px 0 0;max-width:800px}
```
`800px ÷ 15px ≈ 53 字/行`。中文舒适行长 20–28 字，**这是标准的 2 倍**。
而且内容区正好 828px，`max-width:800px` ≈ 没限制。

```css
/* 改为 */
.ulist{list-style:none;margin:16px 0 0;max-width:26em}   /* 26 × 15px = 390px ≈ 26 字/行 */
```

> 单栏会右侧留白约 400px。**留白本身是对的**（尤其配合 `bullets` 的疏朗节奏）。
> 若嫌空，当 `content ≥ 5` 条时给 `.ulist` 加 `column-count:2;column-gap:48px;max-width:none`，
> 而不是把行长拉回去。

### 2. `grid` 版式仍然是均分 —— skill 点名的违规还在这

```css
/* #200 现状：auto-fit + 1fr 的语义就是「永远等分」 */
.lgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:22px 28px;...}
```
3 个 cell → 三等分；4 个 → 四等分。**「禁止均分」的提示词赢不了这行 CSS。**

```css
/* 改为：首格横跨两列 = 明确非均分，且任意条数都稳 */
.lgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:18px 32px;margin-top:18px;flex:1;align-content:start}
.lcell:first-child{grid-column:span 2}                     /* 主角占满整行 */
.lcell:first-child p{font-size:calc(var(--ts-body) * 1.15)} /* 且字号更大 */
```

> 介绍页开发建议的「6 列基准 + 首格 span 3 + span 2 行」在 3/5 条时会出现
> 自动换行错位（span 累计超过 6），所以这里退到 **2 列 + 首格跨列**，
> 非均分的表达一样清楚，但对任意条数都稳。

### 3. 正文字号 13 / 14 / 15 三种混用 —— 「不工整」的第二个来源

| 位置 | 现状 | 问题 |
|---|---|---|
| `.tc-col p`（两栏） | `var(--ts-body)` = 15px | ✓ |
| `.lcell p`（grid） | `14px` | ✗ 第三种 |
| `.tl-d`（time­line） | `13px` | ✗ 第二种 |
| `.kpi-lab` | `12.5px` | ✗ 不在任何档 |

同一份 deck 里翻页时正文字号跳来跳去，读者会觉得「没对齐」。

```css
.lcell p{font-size:var(--ts-body);color:var(--tp);line-height:1.75}
.tl-d  {font-size:var(--ts-body);color:var(--tp);line-height:1.75}
.kpi-lab{font-size:var(--ts-note);color:var(--tsub);margin-top:9px;letter-spacing:.5px;line-height:1.6}
```

> ⚠️ `.tl-d` 从 13 → 15 可能让 5 节点时间轴变挤。
> 这正是需要**溢出兜底**的地方：渲染后量 `scrollHeight > clientHeight`，超了就整页降一档。
> 如果暂时不做兜底，保守做法是保留 13px 但**把它定义成新的一档 `--ts-small:13px`**，
> 至少让「哪个位置用哪一档」是显式规定的，而不是随手写。
> **不要**把两种做法混着来。

### 4. 字阶 2.07× —— 仍低于 2.3 的下限

```css
/* #163 现状 */
--ts-title:31px;--ts-body:15px;--ts-note:11px;   /* 31/15 = 2.07×  ✗ */
```
标题压不住正文，读者找不到视觉入口。

```css
/* 改为 */
--ts-title:35px;--ts-body:15px;--ts-note:11px;   /* 35/15 = 2.33× ✓  11/15 = 0.73× ✓ */
```
并给标题改用字符行长，而不是百分比：

```css
/* #166 */
.page .pt{font-family:var(--serif);font-size:var(--ts-title);color:var(--th);
  font-weight:700;line-height:1.34;margin-bottom:8px;max-width:20ch}
```
> `max-width:88%` 在 940px 页面上是 827px，35px 字 → 约 23 字/行才换行，
> 长标题会占两行半把内容压下去。`20ch` 让标题最多 20 字/行，**两行封顶**。

**高度核算**（页面 940×528.75，padding 上40 下34 → 内容高 454.75）：
```
标题 35×1.34 = 46.9（一行）～93.8（两行）
phr 与小计   ≈ 30
pnote        ≈ 42（顶线+11px 一行）
剩余正文     ≈ 289 ～ 336  →  15px×1.75 = 26.25/行  →  11 ～ 12 行
```
够用，不会溢出。

### 5. 顺手：`kpi` 大数字加等宽数字

```css
.kpi-num{font-family:var(--serif);font-size:44px;font-weight:900;color:var(--th);
  line-height:1.05;letter-spacing:-.5px;font-variant-numeric:tabular-nums}
```
多个 KPI 并排时数字位宽一致，**小数点才会对齐**。没有这行，`2.4` 和 `18` 的视觉重量不同、基线看起来是歪的。

### 6. 顺手：padding 归到 8 的倍数

```css
/* #162 */
.page{...;padding:40px var(--gutter) 34px;...}   /* 34 = 8×4.25 ✗ */
/* 改为 */
.page{...;padding:40px var(--gutter) 32px;...}
```

---

## 🟡 P2 — `.pptx` 导出仍只有 3 个分支

`buildPptxScript()` 的生成脚本（#893-899）：

```python
if lay == "cover":    cover(...)
elif lay == "closing": closing(...)
else:                 content(...)     # ← 其余 10 种版式全部 = 要点列表
```

而且 `spec.slides` 里**没有传 `note`**（#815-816），所以收束句在 .pptx 里也丢了。

网页端补得再好，**导出 .pptx 依然全是圆点列表** —— 又是一个「预览好看、导出打回原形」。

### 最小补齐：5 种版式 + note 条

按你的辅助函数签名（`txt(slide,text,l,t,w,h,size,color,bold,align)`、`bullets(slide,items,color,size,top,left)`、`bg(slide)`、`C(hex)`、`THEME` 键 `bg/title/text/accent/muted`，幻灯片 13.333×7.5in）写：

```python
def note_bar(slide, note, top=6.72):
    if not note: return
    ln = slide.shapes.add_shape(1, Inches(0.8), Inches(top), Inches(11.5), Inches(0.02))
    ln.fill.solid(); ln.fill.fore_color.rgb = C(THEME["muted"]); ln.line.fill.background()
    txt(slide, "▸  " + note, 0.8, top + 0.08, 11.5, 0.5, 11, "muted", False)

def kpi(slide, title, items):
    bg(slide)
    txt(slide, title, 0.8, 0.7, 11.5, 1.0, 30, "title", True)
    n = max(1, min(4, len(items))); colw = 11.5 / n
    for i, it in enumerate(items[:n]):
        num, _, lab = str(it).partition("|")
        x = 0.8 + i * colw
        ln = slide.shapes.add_shape(1, Inches(x), Inches(2.7), Inches(colw * 0.8), Inches(0.04))
        ln.fill.solid(); ln.fill.fore_color.rgb = C(THEME["accent"]); ln.line.fill.background()
        txt(slide, num.strip(), x, 2.9, colw * 0.9, 1.2, 40, "title", True)
        txt(slide, lab.strip(), x, 4.2, colw * 0.9, 0.9, 14, "muted", False)

def timeline(slide, title, items):
    bg(slide)
    txt(slide, title, 0.8, 0.7, 11.5, 1.0, 30, "title", True)
    n = max(1, len(items)); colw = 11.5 / n
    ln = slide.shapes.add_shape(1, Inches(0.8), Inches(3.1), Inches(11.5), Inches(0.02))
    ln.fill.solid(); ln.fill.fore_color.rgb = C(THEME["accent"]); ln.line.fill.background()
    for i, it in enumerate(items):
        when, _, what = str(it).partition("|")
        x = 0.8 + i * colw
        dot = slide.shapes.add_shape(9, Inches(x), Inches(3.03), Inches(0.16), Inches(0.16))
        dot.fill.solid(); dot.fill.fore_color.rgb = C(THEME["accent"]); dot.line.fill.background()
        txt(slide, when.strip(), x, 2.4, colw * 0.9, 0.5, 13, "accent", True)
        txt(slide, what.strip(), x, 3.35, colw * 0.92, 2.6, 13, "text", False)

def compare(slide, title, items):
    bg(slide)
    txt(slide, title, 0.8, 0.7, 11.5, 1.0, 30, "title", True)
    ln = slide.shapes.add_shape(1, Inches(6.62), Inches(2.1), Inches(0.02), Inches(3.6))
    ln.fill.solid(); ln.fill.fore_color.rgb = C(THEME["muted"]); ln.line.fill.background()
    for i, it in enumerate(items[:2]):
        head, _, body = str(it).partition("|")
        x = 0.8 if i == 0 else 7.0
        txt(slide, head.strip(), x, 1.95, 5.4, 0.6, 20, "title", True)
        hb = slide.shapes.add_shape(1, Inches(x), Inches(2.6), Inches(5.2), Inches(0.03))
        hb.fill.solid()
        hb.fill.fore_color.rgb = C(THEME["accent"] if i == 0 else THEME["muted"])
        hb.line.fill.background()
        body = body.replace(";", "；")
        bullets(slide, [t for t in body.split("；") if t.strip()],
                color="text", size=14, top=2.85, left=x)
        # 注意：bullets 的宽度是写死的 11.2in，这里会超出右栏，需给它加个 w 参数
```

> ⚠️ **一个必须改的地方**：`bullets()` 的宽度写死 `Inches(11.2)`（#864），
> 在 `compare` 的右栏（宽约 5.2in）里会溢出到页外。
> 给它加个宽度参数即可：`def bullets(slide, items, color="text", size=18, top=1.8, left=1.0, w=11.2)`，
> 并把 `Inches(11.2)` 换成 `Inches(w)`。

```python
def quote_(slide, title, items, note):
    bg(slide)
    q = (items[0] if items else title) or ""
    txt(slide, q, 1.6, 2.4, 10.1, 2.4, 32, "title", True, PP_ALIGN.CENTER)
    if note:
        txt(slide, "—— " + note, 1.6, 5.0, 10.1, 0.6, 12, "muted", False, PP_ALIGN.CENTER)

def list_(slide, title, items, note):
    bg(slide)
    txt(slide, title, 0.8, 0.7, 11.5, 1.0, 30, "title", True)
    bullets(slide, items, size=16, top=1.9)
```

派发处（#893-899）改为：

```python
NOTE = s.get("note") or ""
if   lay == "cover":    cover(slide, s.get("title") or TITLE, s.get("subtitle") or SUB or "")
elif lay == "closing":  closing(slide, s.get("title") or "谢谢", s.get("content") or ["星星之火，可以燎原"])
elif lay == "kpi":      kpi(slide, s.get("title") or "", s.get("content") or [])
elif lay == "timeline": timeline(slide, s.get("title") or "", s.get("content") or [])
elif lay == "compare":  compare(slide, s.get("title") or "", s.get("content") or [])
elif lay == "quote":    quote_(slide, s.get("title") or "", s.get("content") or [], NOTE)
else:                   list_(slide, s.get("title") or "", s.get("content") or [], NOTE)
if lay not in ("cover", "closing", "quote"):
    note_bar(slide, NOTE)
```

并让 `spec` 带上 note（#815-816）：

```js
slides:state.slides.map(s=>({title:s.title,layout:normLayout(s.layout),content:s.content,note:s.note||""}))
```

> 注意同时把 `layout` 过一遍 `normLayout()` —— 现在传的是原始值，
> 如果 AI 返回了 `hero` / `cards` 之类的别名，python 侧认不出，又会掉进 `else`。

---

## ✅ 验证（补完跑这几条）

```js
// ① 导出 CSS 覆盖度：每个新版式类都必须在导出 CSS 里出现
const need=["kpi-row","kpi-num","tl-item","tl-h","step-n","cmp-rule","cmp-col",
            "lgrid","lcell","tbl","zz-row","zz-h","qk","qt","pnote"];
const css=buildExportCSS();
const miss=need.filter(c=>css.indexOf("."+c)<0);
console.assert(!miss.length,"导出 CSS 缺类名：",miss);

// ② 版式覆盖：≥4 种
console.assert(new Set(state.slides.map(s=>normLayout(s.layout))).size>=4,"版式过于单调");

// ③ 字阶比值 2.3~2.5
const el=document.querySelector("#stage .page");
const fs=n=>parseFloat(getComputedStyle(el.querySelector(n)).fontSize);
const r=fs(".pt")/fs(".ulist li");
console.assert(r>=2.3&&r<=2.5,`标题/正文 ${r.toFixed(2)}×，应 2.3~2.5`);

// ④ 行长：正文一行不超过 28 字
const li=document.querySelector("#stage .ulist li")||document.querySelector("#stage .lcell p");
if(li) console.assert(li.getBoundingClientRect().width/parseFloat(getComputedStyle(li).fontSize)<=28,
  "行长超过 28 字");

// ⑤ 无溢出
document.querySelectorAll("#stage .page").forEach((p,i)=>{
  if(p.scrollHeight>p.clientHeight+1)console.warn(`第 ${i+1} 页溢出`,p.scrollHeight,p.clientHeight);
});
```

**导出链路必测**（P0 的验收）：生成一份 ≥6 页、含 `kpi`+`timeline`+`quote` 的 deck →
**先看网页预览，再点「导出独立 HTML」，打开导出的文件逐页对比**。
两张截图一致才算过。这是唯一能证明 P0 修好的方法。

---

## 优先级

| 顺序 | 事项 | 为什么 |
|---|---|---|
| 1 | **导出 CSS 改 `collectSlideCSS()`** | P0，预览好导出崩最伤用户信任；且是结构性修复 |
| 2 | 字阶 31→35 + 标题 `max-width:20ch` | 一个数值改动，视觉提升最明显 |
| 3 | `.ulist` 行长 800px→26em | 「文字不工整」的主因 |
| 4 | `.lgrid` 改非均分 | 兑现「禁止均分」 |
| 5 | 正文字号统一到 `--ts-body` | 「不工整」的第二来源 |
| 6 | `tabular-nums` + padding 归 8 倍数 | 细节 |
| 7 | `.pptx` 补 5 种版式 + note | 导出链路的第二处失真 |

> 一句话：**你网页端已经做对了，现在的风险全在「导出两条链路」上 ——
> 独立 HTML 的 CSS 漏了 8 个版式，.pptx 只认 3 个分支。
> 先堵这两处，boss 才不会碰到「预览好看、导出变样」。**
