> ⚠️ **本文件已大部分过时（2026-10-24 18:30 标注）。**
> 星火PPT 已自行实现 12 种版式、`note` 渲染、`checkRenderer()` 自检。
> **请以 `星火PPT-残留问题核对与补丁.md` 为准** —— 那份只列仍未解决的问题（含一个 P0 导出 CSS 断档）。
> 本文件保留价值：第一节的三个量化诊断（行长 53 字 / 字阶 1.68× / 46px 不在网格）与第五节断言。

---

# 星火PPT · 排版内核补丁（可直接粘贴）

> 由 星火专注Pro 提供。验收官已给出「11 种版式只实现 4 种」的架构诊断，本文件不重复，
> 只补三件他还没说的：**可量化的排版缺陷** + **可直接粘贴的 CSS/JS 补丁** + **自检断言**。
>
> 使用方式：整段替换/新增，改完跑最后一节的三条断言。

---

## 一、先看三个可量化的缺陷（「不合理 / 不工整 / 对不齐」的机械原因）

### 缺陷 1：正文行长超标 2 倍 —— 这是「文字不工整」的直接原因

```
.stage            max-width:940px, aspect-ratio:16/9   →  940 × 528.75
.page             padding:46px 56px                    →  内容区 828 × 436.75
.ulist            max-width:820px, font-size:15.5px    →  820 / 15.5 ≈ 52.9 字/行
```

中文舒适行长是 **20–28 字**。现在一行塞 53 个字，读者眼睛要横扫整屏再折返，
「工整」从何谈起？而且 `820px` 几乎等于内容区宽度 `828px`，**这个 max-width 等于没设**。

**但注意——不能简单把 max-width 改小就完事**：单栏正文收窄到 24 字后，右侧会空出 460px。
这恰恰说明 **16:9 宽屏上的单栏列表页本身就是错的版式**，正确的解法是收窄 + 两栏（见下面 CSS）。

### 缺陷 2：标题字阶只有 1.68 倍 —— 这是「排版不合理」的机械原因

```
.page .pt         font-size:26px   （页标题）
.ulist li         font-size:15.5px （正文）
                  →  26 / 15.5 = 1.68×
```

排版纪律要求标题是正文的 **2.3–2.5 倍**。现在 1.68 倍，标题压不住正文，
一页里所有文字「分量」差不多，读者找不到入口 → 视觉上就是「乱」。

（注释档其实是合格的：`.pno` 11px / 15.5px = 0.71，符合 0.65–0.8。所以只缺标题这一档。）

### 缺陷 3：`46px` 不在 8px 网格上

```
.page padding:46px 56px   →  56 = 8×7 ✓      46 = 8×5.75 ✗
```

单个 46px 不致命，但它意味着**没有网格约束**。一旦各处 padding/margin 自由取值，
「对不齐」就会从各处渗出来。统一到 `calc(var(--u)*n)` 之后，对齐是自动成立的。

### 顺带：均分是「写死」的，不是模型选的

```css
.cards-grid{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
```

`auto-fit + 1fr` 的语义就是「永远等分」。3 个卡片必然三等分，4 个必然四等分。
**只要这个类还在被用，「禁止均分」的提示词就永远赢不了 CSS。**

---

## 二、CSS 补丁：排版内核

替换 `.page` 那一段（原 #160-161），并新增版式样式。整段可粘贴。

```css
/* ===== 排版内核：8px 网格 · 三档字阶 · 行长约束 ===== */
.page{
  --u:8px;                    /* 网格单位：所有间距必须是它的整数倍 */
  --gutter:56px;              /* 左右统一边距（同层级左边缘共线靠它） */
  --ts-title:36px;            /* 标题 = 正文 2.4× */
  --ts-sub:19px;
  --ts-body:15px;             /* 正文基准 */
  --ts-note:11px;             /* 注释 = 正文 0.73× */
  --rhythm:1.75;

  position:absolute;inset:0;font-family:var(--sans);background:var(--bg);
  display:flex;flex-direction:column;
  padding:calc(var(--u)*6) var(--gutter);   /* 48px 56px */
  overflow:hidden;
  line-break:strict;                        /* 避头尾：标点不进行首 */
  text-spacing-trim:space-first;
}
.page .pt{font-family:var(--serif);font-size:var(--ts-title);color:var(--th);
  font-weight:800;line-height:1.24;margin:0;letter-spacing:.01em}
.page .phr{width:40px;height:2px;background:linear-gradient(90deg,var(--tk),transparent);
  margin:calc(var(--u)*2) 0 calc(var(--u)*2)}

/* 底部收束条：兑现 DESIGN_RULES 第 3 条的 note 字段 */
.page .pnote{
  margin-top:auto;                          /* 永远吸底 */
  padding-top:calc(var(--u)*2);
  border-top:1px solid var(--tborder);
  font-size:var(--ts-note);color:var(--tsub);
  line-height:1.6;letter-spacing:.02em;
}
.page.cover .pnote,.page.closing .pnote{display:none}   /* 封面封底不收束 */

/* ---- 要点列表：行长 24 字，内容多时自动两栏 ---- */
.ulist{list-style:none;margin:0;padding:0;
  max-width:24em;                           /* 24 × 15px = 360px ≈ 24 字/行 */
  column-gap:calc(var(--u)*6)}
.ulist.two{column-count:2;max-width:none}   /* ≥5 条时加 .two，撑满两栏 */
.ulist li{position:relative;padding-left:calc(var(--u)*3);
  margin:0 0 calc(var(--u)*1.5);break-inside:avoid;
  font-size:var(--ts-body);color:var(--tp);line-height:var(--rhythm)}
.ulist li::before{content:"";position:absolute;left:2px;top:.62em;
  width:8px;height:8px;border-radius:2px;background:var(--tk);transform:rotate(45deg);opacity:.85}

/* ---- kpi：大数字页（视觉冲击最强，优先补） ---- */
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:calc(var(--u)*3);align-items:end;margin:calc(var(--u)*3) 0 0;flex:1}
.kpi{border-top:2px solid var(--tk);padding-top:calc(var(--u)*2)}
.kpi b{display:block;font-family:var(--serif);font-size:64px;line-height:1;
  color:var(--th);font-weight:900;letter-spacing:-.01em}
.kpi span{display:block;margin-top:calc(var(--u));font-size:var(--ts-body);color:var(--tsub)}

/* ---- timeline：竖线 + 节点 ---- */
.tl{list-style:none;margin:calc(var(--u)*3) 0 0;padding:0 0 0 calc(var(--u)*4);
  position:relative;flex:1}
.tl::before{content:"";position:absolute;left:5px;top:6px;bottom:6px;
  width:1px;background:linear-gradient(180deg,var(--tk),transparent)}
.tl li{position:relative;margin-bottom:calc(var(--u)*2.5)}
.tl .tl-dot{position:absolute;left:calc(var(--u)*-4 + 1px);top:.45em;
  width:9px;height:9px;border-radius:50%;background:var(--tk);
  box-shadow:0 0 0 4px color-mix(in srgb,var(--tk) 18%,transparent)}
.tl .tl-t{font-size:var(--ts-sub);color:var(--th);font-weight:700;line-height:1.4}
.tl .tl-d{font-size:var(--ts-body);color:var(--tp);line-height:var(--rhythm);margin-top:2px}

/* ---- steps：流程推进 ---- */
.steps{list-style:none;margin:calc(var(--u)*3) 0 0;padding:0;
  display:flex;flex-direction:column;gap:calc(var(--u)*2);flex:1}
.steps li{display:flex;gap:calc(var(--u)*2);align-items:flex-start}
.steps i{flex:none;width:28px;height:28px;border-radius:50%;
  border:1.5px solid var(--tk);color:var(--tk);font-style:normal;
  font-size:13px;display:flex;align-items:center;justify-content:center;font-weight:700}
.steps b{display:block;font-size:var(--ts-sub);color:var(--th);font-weight:700}
.steps p{margin:2px 0 0;font-size:var(--ts-body);color:var(--tp);line-height:var(--rhythm)}

/* ---- compare：左右对照（替代 two_col 的均分盒） ---- */
.cmp{display:grid;grid-template-columns:1fr 1fr;gap:0;
  margin:calc(var(--u)*3) 0 0;flex:1}
.cmp-c{padding:0 calc(var(--u)*3)}
.cmp-c:first-child{padding-left:0;border-right:1px solid var(--tborder)}   /* 一条细线，不用圆角盒 */
.cmp-c:last-child{padding-right:0}
.cmp-c h4{font-family:var(--serif);font-size:var(--ts-sub);color:var(--tcardh);
  margin:0 0 calc(var(--u)*1.5);font-weight:700}
.cmp-c ul{list-style:none;margin:0;padding:0}
.cmp-c li{position:relative;padding-left:calc(var(--u)*2);
  font-size:var(--ts-body);color:var(--tp);line-height:var(--rhythm);
  margin-bottom:calc(var(--u)*1.25)}
.cmp-c li::before{content:"";position:absolute;left:0;top:.65em;
  width:5px;height:1px;background:var(--tk)}

/* ---- quote：整页留白金句（最强的个性化武器） ---- */
.quote{margin:auto 0;padding:0;border:0;max-width:18em;
  font-family:var(--serif);font-size:38px;line-height:1.55;
  color:var(--th);font-weight:700;letter-spacing:.02em}
.quote::before{content:"";display:block;width:48px;height:3px;
  background:var(--tk);margin-bottom:calc(var(--u)*3)}

/* ---- table：无竖线表格 ---- */
.tbl{width:100%;border-collapse:collapse;margin:calc(var(--u)*3) 0 0;flex:1}
.tbl td{padding:calc(var(--u)*1.5) calc(var(--u)*2) calc(var(--u)*1.5) 0;
  border-bottom:1px solid var(--tborder);
  font-size:var(--ts-body);color:var(--tp);line-height:1.6;vertical-align:top}
.tbl td:first-child{color:var(--th);font-weight:700;width:30%}
.tbl td:last-child{color:var(--tsub);font-size:var(--ts-note);width:28%}
.tbl tr:last-child td{border-bottom:0}

/* ---- zigzag：左右交错（消灭均分的武器） ---- */
.zz{display:flex;flex-direction:column;gap:calc(var(--u)*2.5);
  margin:calc(var(--u)*3) 0 0;flex:1}
.zz-i{display:grid;grid-template-columns:1fr 1fr;gap:calc(var(--u)*3);align-items:baseline}
.zz-i .zz-t{font-family:var(--serif);font-size:var(--ts-sub);color:var(--th);
  font-weight:700;text-align:right;line-height:1.4}
.zz-i .zz-d{font-size:var(--ts-body);color:var(--tp);line-height:var(--rhythm);
  border-left:2px solid var(--tk);padding-left:calc(var(--u)*2)}
.zz-i.r .zz-t{order:2;text-align:left}
.zz-i.r .zz-d{order:1;border-left:0;border-right:2px solid var(--tk);
  padding-left:0;padding-right:calc(var(--u)*2);text-align:right}

/* ---- grid：细线网格（**不用圆角卡片**） ---- */
.gridl{list-style:none;margin:calc(var(--u)*3) 0 0;padding:0;
  display:grid;grid-template-columns:1fr 1fr;gap:0 calc(var(--u)*4);flex:1}
.gridl li{padding:calc(var(--u)*2) 0;border-top:1px solid var(--tborder);
  font-size:var(--ts-body);color:var(--tp);line-height:var(--rhythm);break-inside:avoid}

/* ---- 正文段落（zigzag/compare 之外的通用） ---- */
.page p{font-size:var(--ts-body);line-height:var(--rhythm);color:var(--tp)}
```

> **注意 `.cards-grid` 的处理**：不要留着它。要么删掉 `cards` 版式，要么把
> `cards` 重映射到 `.gridl`（细线网格）。**圆角卡片 + auto-fit 均分是 skill 明令禁止的组合**，
> 它俩同时存在一天，「不用均分」就一天不可能实现。

---

## 三、JS 补丁：`pageHTML()` 补齐 8 种版式 + 渲染 note

替换 `pageHTML()` 整个函数（原 #576-594）。与 `LAYOUT_DOC`（server.py #334-346）**逐字对齐**。

```js
/* "数字|标签" / "阶段|说明" 通用拆分 */
function split2(t){
  const s=String(t),i=s.indexOf("|");
  return i<0?[s,""]:[s.slice(0,i).trim(),s.slice(i+1).trim()];
}
function pageHTML(s,i,total){
  const L=(s.layout||"bullets").toLowerCase();
  if(L==="cover")return coverHTML(s);
  if(L==="closing")return closingHTML(s);
  const pts=(s.content||[]).map(t=>String(t)).filter(x=>x.trim());
  let body="";

  switch(L){
    case "two_col":{                       // 4~6 条，前两条作左右小标题
      const mid=Math.max(1,Math.ceil(pts.length/2));
      const c1=pts.slice(0,mid),c2=pts.slice(mid);
      body=`<div class="cmp">
        <div class="cmp-c"><h4>${esc(c1[0]||"")}</h4><ul>${c1.slice(1).map(p=>`<li>${esc(p)}</li>`).join("")}</ul></div>
        <div class="cmp-c"><h4>${esc(c2[0]||"")}</h4><ul>${c2.slice(1).map(p=>`<li>${esc(p)}</li>`).join("")}</ul></div>
      </div>`;break;
    }
    case "compare":{                       // 恰好 2 条：「大标题|要点①；要点②；要点③」
      const two=pts.slice(0,2);
      body=`<div class="cmp">${two.map(p=>{
        const [h,b]=split2(p);
        const items=b.split(/[；;]/).map(x=>x.trim()).filter(Boolean);
        return `<div class="cmp-c"><h4>${esc(h)}</h4><ul>${items.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>`;
      }).join("")}</div>`;break;
    }
    case "kpi":{                           // 2~4 条：「数字|标签」
      body=`<div class="kpi-row">${pts.map(p=>{
        const [n,l]=split2(p);
        return `<div class="kpi"><b>${esc(n)}</b><span>${esc(l)}</span></div>`;
      }).join("")}</div>`;break;
    }
    case "timeline":{                      // 3~5 条：「阶段|说明」
      body=`<ol class="tl">${pts.map(p=>{
        const [t,d]=split2(p);
        return `<li><span class="tl-dot"></span><div class="tl-t">${esc(t)}</div><div class="tl-d">${esc(d)}</div></li>`;
      }).join("")}</ol>`;break;
    }
    case "steps":{                         // 3~5 条：「步骤名|说明」
      body=`<ol class="steps">${pts.map((p,ii)=>{
        const [t,d]=split2(p);
        return `<li><i>${ii+1}</i><div><b>${esc(t)}</b><p>${esc(d)}</p></div></li>`;
      }).join("")}</ol>`;break;
    }
    case "quote":{                         // 恰好 1 条引文，出处写在 note
      body=`<blockquote class="quote">${esc(pts[0]||"")}</blockquote>`;break;
    }
    case "table":{                         // 3~6 条：「指标|数值|备注」
      body=`<table class="tbl"><tbody>${pts.map(p=>
        `<tr>${String(p).split("|").map(c=>`<td>${esc(c.trim())}</td>`).join("")}</tr>`
      ).join("")}</tbody></table>`;break;
    }
    case "zigzag":{                        // 4~6 条：「小标题|说明」，左右交替
      body=`<div class="zz">${pts.map((p,ii)=>{
        const [t,d]=split2(p);
        return `<div class="zz-i${ii%2?" r":""}"><div class="zz-t">${esc(t)}</div><div class="zz-d">${esc(d)}</div></div>`;
      }).join("")}</div>`;break;
    }
    case "grid":{                          // 3~6 条：细线网格，非卡片
      body=`<ul class="gridl">${pts.map(p=>`<li>${esc(p)}</li>`).join("")}</ul>`;break;
    }
    default:{                              // bullets（唯一的兜底）
      body=`<ul class="ulist${pts.length>=5?" two":""}">${pts.map(p=>`<li>${esc(p)}</li>`).join("")}</ul>`;
    }
  }
  // 兑现 note：底部收束条（cover/closing 由 CSS 隐藏）
  const note=s.note?`<div class="pnote">${esc(s.note)}</div>`:"";
  return `<div class="pt">${esc(s.title||"")}</div><div class="phr"></div>${body}${note}`;
}
```

同时给 `renderSlide` 的容器补上 layout 类名（供 `.page.quote` 等选择器命中）：

```js
// renderSlide() 内，原 #572 那行改为：
$("#stage").innerHTML=`<div class="page ${tpl.cls} ${(s.layout||"bullets").toLowerCase()}">
  ${pageHTML(s,state.current,state.slides.length)}<span class="pno">${state.current+1} / ${state.slides.length}</span></div>`;
```

> `renderSlideInOverlay()`（#636）和导出（#654）用的是同一个 `pageHTML`，
> 所以补齐后**网页/放映/HTML 导出三处同时生效**。但 `.pptx` 走的是
> `buildPptxScript()`（#766 起）的 python 分支，**要另外补**，否则导出仍全是要点列表。

---

## 四、编辑器下拉框同步（原 #612）

```js
const ls=["cover","closing","bullets","two_col","compare","kpi","timeline","steps","quote","table","zigzag","grid"];
```

并同步 `layoutName()`（#617）：

```js
function layoutName(l){return{
  cover:"封面",closing:"封底",bullets:"要点列表",two_col:"两栏说明",
  compare:"左右对照",kpi:"大数字",timeline:"时间轴",steps:"流程推进",
  quote:"金句",table:"无竖线表格",zigzag:"交错图文",grid:"细线网格"
}[l]||l;}
```

删掉 `cards` —— 它与 `LAYOUT_DOC` 本就不一致（前端有、文档无），且是均分来源。

---

## 五、改完跑这三条断言（别靠肉眼）

```js
/* 粘到控制台，生成一份 ≥8 页的 deck 后执行 */

// ① 版式覆盖：不同 layout 数 ≥ 4
const L=new Set(state.slides.map(s=>(s.layout||"bullets").toLowerCase()));
console.assert(L.size>=4,`版式只用 ${L.size} 种，应 ≥4`,L);

// ② 静默降级检测：LAYOUT_DOC 声明的每种版式都必须有明确分支
const DECLARED=["cover","closing","bullets","two_col","grid","kpi","timeline","steps","compare","quote","table","zigzag"];
const missing=DECLARED.filter(l=>{
  const probe={title:"t",layout:l,content:["3|a","b|c","d|e","f|g"]};
  const html=pageHTML(probe,0,9);
  return html.includes('class="ulist') && l!=="bullets";   // 落到 bullets 兜底即视为缺失
});
console.assert(!missing.length,"以下版式被静默降级成列表:",missing);

// ③ 字阶比值 2.3~2.5 : 1
const el=document.querySelector("#stage .page");
const g=n=>parseFloat(getComputedStyle(el.querySelector(n)).fontSize);
const ratio=g(".pt")/g(".ulist li")||g(".gridl li");
console.assert(ratio>=2.3&&ratio<=2.5,`标题/正文字阶 ${ratio.toFixed(2)}×，应在 2.3~2.5`);
```

再加一条**几何自检**（比断言更彻底，能把「不合理」挡在给 boss 看之前）：

```js
// ④ 溢出检测：任一页 scrollHeight 超出 clientHeight 就该降档重排
document.querySelectorAll("#stage .page").forEach((p,i)=>{
  if(p.scrollHeight>p.clientHeight+1) console.warn(`第 ${i+1} 页内容溢出`,p.scrollHeight,p.clientHeight);
});
```

---

## 六、优先级建议

| 顺序 | 做什么 | 为什么是这个顺序 |
|---|---|---|
| 1 | 上 CSS 排版内核（第二节） | 字阶+行长+网格，**立刻**改善「不合理/不工整」，不依赖模型 |
| 2 | `pageHTML` 补 8 种版式（第三节） | 让提示词承诺的 12 种版式真的画得出来 |
| 3 | 渲染 `note` | 一行代码，兑现已有设计 |
| 4 | 同步 `buildPptxScript()` | 否则导出仍单调（网页好看、导出打回原形最伤） |
| 5 | 上几何自检（第五节④） | 自动拦截溢出/重叠 |
| 6 | 提示词再加「节奏」约束 | **最后做**——渲染器不支持时，再好的提示词也白搭 |

> 核心判断：**现在的问题不是审美，是渲染器断档 + 排版内核缺失。**
> 先让 12 种版式画得出来、让字阶行长立住，再谈 AI 自主编排。
