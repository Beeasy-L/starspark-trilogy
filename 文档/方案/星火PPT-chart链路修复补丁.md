# 星火PPT · chart 字段链路修复补丁（可直接套用）

> 出具：解读星火PPT项目并对比设想差距（只读分析方）
> 日期：2026-10-26
> 目标文件：`产品\星火PPT\static\index.html`、`产品\星火PPT\server.py`
> **本补丁不含任何我方改动——只是把四处改动的「改前/改后」写清楚，由 @星火PPT 自己动手。**
>
> **可信度标注**：本补丁每一处的「改前」行号与内容，均为我**在当前文件（2026-10-26 18:10:38 版，SHA256 f2782a890cf93c0f）里实际读到的原文**；
> 「改后」是建议代码，**尚未落地、未经运行验证**——落地后请按文末验收清单实测。

---

## 〇、先看这条链路（断点在哪一目了然）

```
AI 返回 JSON
   ↓  ❌断点1  buildDeck 的 map 丢 chart            index.html:6767-6770
state.slides[].chart
   ↓  ❌断点2  persist 的 lightSlides 丢 chart       index.html:7375-7378
localStorage 历史
   ↓
state.slides[].chart
   ├→ 网页预览   pageHTML → chartHTML(s,pts)  读 s.chart    index.html:6991
   ├→ 导出 HTML  pageHTML(s,i,...)            读 s.chart    index.html:7286
   └→ 导出 pptx  XH_PPTX.build → chartData(s) 读 s.chart    dev/pptx.js:1432
```

**断点1、2 修好后，三条下游路径同时恢复**——因为它们读的是同一个 `state.slides[].chart`。

另有一个「上游断点」：

```
后端 server.py 的 LAYOUT_DOC 列了 12 种版式，**没有 chart**   server.py:769-781
→ 走后端时模型根本不知道有 chart 版式，永远选不到 → 图表能力 0 触发
前端 index.html:1983 的 LAYOUT_DOC_JS **有** chart
```

**前后端提示词不一致：前端有、后端没有。**

---

## 改动 1 · `buildDeck` 补 chart 透传（断点 1）

**文件**：`产品\星火PPT\static\index.html`
**位置**：第 6767–6770 行（函数 `buildDeck`）

**改前**
```js
  const slides=(doctor.slides||[]).map(s=>({
    title:s.title||"",layout:(s.layout||"bullets").toLowerCase(),note:s.note?String(s.note):"",
    content:Array.isArray(s.content)?s.content.filter(x=>x!==null&&x!==undefined).map(x=>String(x)):(s.content?[String(s.content)]:[])
  }));
```

**改后**
```js
  const slides=(doctor.slides||[]).map(s=>({
    title:s.title||"",layout:(s.layout||"bullets").toLowerCase(),note:s.note?String(s.note):"",
    content:Array.isArray(s.content)?s.content.filter(x=>x!==null&&x!==undefined).map(x=>String(x)):(s.content?[String(s.content)]:[]),
    /* chart 必须透传：网页预览 / 导出 HTML / 导出 pptx 三条路都读这个字段 */
    chart:(s.chart&&typeof s.chart==="object")?s.chart:undefined
  }));
```

**为什么这样写**
- 与导出侧已有的写法保持一致（`index.html:7345` 就是 `chart:(s.chart&&typeof s.chart==="object")?s.chart:undefined`）——**同一份契约，两处写法统一**
- `typeof s.chart==="object"` 排除字符串/数字等脏值；`undefined` 而非 `null`，避免下游 `Array.isArray(ch.items)` 判断混淆
- **不要**在这里做深拷贝或裁剪：`chart.items` 已在 `chartData()`（pptx.js:1431）里 `slice(0,6)`，`chartItems()`（index.html:6984）里也 `slice(0,6)`，两处都有限长

---

## 改动 2 · `persist` 补 chart（断点 2）

**文件**：`产品\星火PPT\static\index.html`
**位置**：第 7375–7378 行（函数 `persist`）

**改前**
```js
    /* 配图是 base64 大字符串，存进历史会撑爆 localStorage —— 落库前剥离，只留文字 */
    const lightSlides=state.slides.map(s=>{
      const o={title:s.title,layout:s.layout,content:s.content,note:s.note||""};
      return o;
    });
```

**改后**
```js
    /* 配图是 base64 大字符串，存进历史会撑爆 localStorage —— 落库前剥离，只留文字。
       注意：只剥配图（img），**不要**剥 chart —— chart 只有几十字节，剥了刷新历史就丢图。 */
    const lightSlides=state.slides.map(s=>{
      const o={title:s.title,layout:s.layout,content:s.content,note:s.note||"",
        chart:(s.chart&&typeof s.chart==="object")?s.chart:undefined};
      return o;
    });
```

**为什么这样写**
- 原注释说「只留文字」，但 `chart` 不是「图」而是**数据**（几十字节的 JSON），剥它没有体积收益，只有信息损失
- `img` 字段本来就没在 `o` 里（所以配图确实被剥掉了，行为正确）；这里**不要顺手加 `img`**
- `openHistory()`（index.html:7407）直接 `state.slides=r.slides`，恢复时不需要额外改动——**只要存进去的就是完整的**

---

## 改动 3 · 后端 `LAYOUT_DOC` 补 chart 版式

**文件**：`产品\星火PPT\server.py`
**位置**：第 781 行末尾（`LAYOUT_DOC` 三引号字符串的最后一行）

**改前**（第 781 行）
```python
- zigzag　 交错图文。4~6 条，格式「小标题|说明」，左右交替排布。"""
```

**改后**
```python
- zigzag　 交错图文。4~6 条，格式「小标题|说明」，左右交替排布。
- chart　　数据图。**只有在内容里真的有可比较的数字时才用**。除 title/content 外，再给一个 chart 字段：{"type":"bar|progress|ring","unit":"%","items":[{"label":"指标名","value":68}]}；type=bar 横向条形（最常用），progress 纵向进度条组，ring 占比环（items 只给一条，value 为 0~100）。content 给空数组即可，note 照常。"""
```

**这一行是直接从前端抄的**
- 前端 `LAYOUT_DOC_JS`（index.html:1983）已有完整的 chart 说明，两边**字面一致**，避免「同一件事在两处各规定一次」
- 只改 `server.py` 一处，**前端不用动**（前端那行已经是对的）
- 改完后**前后端都能选到 chart 版式**，图表能力才真正可达

---

## 改动 4 · `LAYOUT_RULE.chart` 与提示词对齐

**文件**：`产品\星火PPT\static\index.html`
**位置**：第 6892 行

**改前**
```js
  chart:    {min:1, max:6, pipe:0},
```

**改后**
```js
  chart:    {min:0, max:0, pipe:0},
```

**为什么**
- 提示词（index.html:1983）明确写「**content 给空数组即可**」，但契约表要求 `min:1` —— **两处规定不一致**
- 现状下 chart 页**侥幸没塌**：`normalizeSlide` 的降级白名单（index.html:6915）是 `compare||table||timeline||steps||kpi||zigzag`，**不含 chart**，所以 `pts.length < rule.min` 这条分支对 chart 不生效
- 但这是**运气，不是设计**。任何人以后往白名单里加 chart，图表页就会集体降级成列表
- `min:0 / max:0` 表示「chart 页的 content 不参与条数契约」——`max:0` 不会裁切，因为裁切分支是 `pts.length > rule.max`，`pts.length=0` 不满足

**⚠️ 一处必须同步检查**：`normalizeSlide` 的降级分支（index.html:6913-6917）里，
**chart 目前不在白名单中**。改成 `min:0` 后这条路径依然不触发，**行为不变**——但请顺手在
`LAYOUT_RULE` 旁加一行注释，说明「chart 的数据在 chart 字段里，content 可空」。

---

## 五、这四处改完后，图表的完整链路

| 环节 | 读什么 | 现在 |
|---|---|---|
| AI 返回 | `slides[].chart` | ✅ 模型能返回（前端提示词已教它格式） |
| 后端提示词 | `LAYOUT_DOC` 含 chart | ❌ **改动 3 修** |
| `buildDeck` | 透传 chart | ❌ **改动 1 修** |
| `state.slides[].chart` | — | ✅ 三条下游路径的唯一真相源 |
| 网页预览 | `chartHTML(s,pts)` | ✅（拿到 chart 就能画） |
| 导出 HTML | `pageHTML(s,i,…)` | ✅ |
| 导出 pptx | `chartData(s)` → `layChart` | ✅（`Ch*` 真形状） |
| localStorage 历史 | `persist` | ❌ **改动 2 修** |

---

## 六、验收清单（改完请逐条跑，并把输出贴群）

### A. 静态断言（最快，5 秒）

```powershell
# A1 buildDeck 已透传 chart
Select-String -Path "产品\星火PPT\static\index.html" -Pattern 'chart:\(s\.chart&&typeof s\.chart==="object"\)'
#   期望：至少 3 处（buildDeck / persist / 导出 deck）

# A2 server.py 已补 chart 版式
Select-String -Path "产品\星火PPT\server.py" -Pattern '^\- chart'
#   期望：1 处

# A3 LAYOUT_RULE.chart 已改 min:0
Select-String -Path "产品\星火PPT\static\index.html" -Pattern 'chart:\s*\{min:0'
#   期望：1 处
```

### B. 运行时断言（node 沙箱跑**原函数**，不依赖浏览器）

把 `buildDeck` / `chartItems` / `chartHTML` 从 index.html 里原样抠出来跑，断言：

```
buildDeck 后 slides[0].chart.type  === "ring"      （改前是 undefined）
chartItems 返回 [{label:"转化率", value:75}]         （改前是 [{label:"", value:0}]）
```

### C. 端到端断言（这条链**从来没跑通过**，务必实测）

```
1. 用一段含可比较数字的文案生成（如「转化率提升到 75%」）
2. 确认网页预览出现「数据图」版式，且是**环图**（不是条形）
3. 导出 .pptx → 解包 → 数 ppt/slides/slideN.xml 里 name="Ch* 的形状数
   期望：Ch* > 0（改前恒为 0）
4. 用真 PowerPoint 打开 → 不弹修复对话框
5. 刷新页面 → 打开「本机历史」→ 该 deck 的图表**还在**
   （这一步专查改动 2；改前这里必丢）
6. 导出独立 HTML → 双击打开 → 图表还在
```

### D. 回归断言（防止这四处改动踩坏别的）

```
D1 13 种版式自检仍全过（控制台「版式自检通过」）
D2 导出样例里 Deco* 仍是每页 11 个、越界形状 = 0
D3 static/index.html 与 deploy/网页版/index.html 的 SHA256 一致
D4 线上 https://beeasy-l.github.io/starspark-ppt/ 的 SHA256 与本地一致
```

---

## 七、两条必须一起做的说明

**改动 1 与改动 2 必须同时做。**
只做 1 不做 2 → 现象是「刚生成时有图，刷新历史就没了」，比原来更难解释。

**改动 3 与改动 4 建议一起做。**
- 只做 3（后端能选 chart）不做 4 → 模型给 chart 页、content 给空 → 契约表要求 min:1 → 侥幸不降级，但契约与提示词长期不一致
- 只做 4 不做 3 → 后端模式永远选不到 chart，改动 4 毫无意义

---

## 八、另外三件不在这四处之内、但请一并考虑的事

> 这三条**不在本次 P0 范围内**，不要求周二做，只是别忘了它们存在。

### ① `deploy\网页版` 的改动还没 commit
```
git status → M index.html
```
现在两份 SHA256 一致，但**只要有人从 git 重新 checkout 部署，P0-1 的修复就会消失、线上重新变成废的**。
**建议今晚补一个 commit。**

### ② 流式中途预览「跳页」
用户设定 8 页、模型出到第 9 页时，`buildDeck` 的页数硬约束（index.html:6776-6784）会把中间页裁掉：

```
已完成 8 页 → 预览 8 页（P8）
已完成 9 页 → 预览 7 页（P7）   ← 倒退
已完成10 页 → 预览 8 页（封底）
```
**用户会看到已出现的页面凭空消失。** 建议：流式进行中**不做页数裁剪**，等 JSON 完整闭合后再裁。

### ③ `quote` 版式丢页标题
```js
// index.html:7038-7042
if(L==="quote"){
  const q=pts[0]||s.title||"";
  ...
  return `<div class="qk">...</div><div class="qt">${esc(q)}</div>...`;
}
```
`quote` 分支**提前 return**，不走 `head()`，所以**页标题（AI 认真写的结论句）被丢弃**；
并且 `s.eyebrow` 这个字段 **schema 里没有、编辑面板也没有输入框**（面板只有 s-title / s-layout / s-content / s-note），
所以 `qk` 永远走兜底字面量「一句话」。
> 这两条是 10-24 那份质量提升方案里 0-3 项的老问题，**至今未修**。

---

## 九、我这边的状态

- **本补丁不含我的任何改动**——`产品\星火PPT\` 下我一个字节没动
- 验收清单 A/B 两条（静态断言 + node 沙箱跑原函数）**我可以直接帮你跑**，跑完贴群；要我跑就说一声
- 我建的临时探针脚本已全部删除并核验「残留 0」

**本文件位置**：`文档\方案\星火PPT-chart链路修复补丁.md`
