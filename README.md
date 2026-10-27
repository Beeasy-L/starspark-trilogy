# 星火三部曲

> 一个产品，三部曲。**从续火花（收官）到专注 Pro，再到星火 PPT。**
> 记录思考、专注当下、整理表达——「星火三部曲」系统介绍页。

## 目录结构

```
星火三部曲\                    ← 本仓库（git，GitHub Pages 发布根）
├── index.html                 介绍页首页
├── assets\                    页面资源（截图、音频、样式、脚本）
├── projects\                  三个子项目入口页
│   ├── streak.html            第一部 · 星火续火花
│   ├── focus.html             第二部 · 星火专注Pro
│   ├── ppt.html               第三部 · 星火PPT
│   └── focus-app\             专注Pro 内嵌版（构建产物）
├── tools\                     检查工具
│   └── check_html.py          HTML 结构检查（抓嵌套错配）
├── 产品\                      ← 各产品源码（不进 git）
│   ├── 星火续火花\             第一部（收官版）
│   ├── 星火专注Pro\            第二部
│   └── 星火PPT\               第三部
├── 共用\                      ← 跨产品公用资产
│   ├── 设计令牌\               design-tokens.js（PPT dev/ 为真源）
│   ├── 动画规范\               emil-motion 6 份 Skill 文档
│   ├── 字体\                   Noto Serif SC 子集（198 个 woff2）
│   ├── 音频\                   静场 / 环境音
│   └── 工具\                   check_html.py
├── 文档\                      ← 方案 / 报告 / 规范
│   ├── 方案\
│   ├── 报告\
│   └── 规范\
└── _归档\                     ← 临时物、产物、旧备份、重复副本
```

## 三个产品

| 位置 | 产品 | 定位 | 技术形态 |
|---|---|---|---|
| `产品\星火续火花\` | 第一部 · 续火花 | 已收官，仅保留交付物 | Python + 单文件 Web |
| `产品\星火专注Pro\` | 第二部 · 专注Pro | 专注计时、铸星、写复盘信 | PWA，离线可用 |
| `产品\星火PPT\` | 第三部 · 星火PPT | 网页原生 AI PPT 生成器 | 单文件 HTML + Python 标准库 server |

## 底层原则（三部曲共同遵守）

1. **数据只在本机** —— localStorage 存储，不做云账号、不做跨设备同步
2. **不上传用户原稿** —— 星火PPT 的 API Key 仅存本机浏览器
3. **不催促** —— 无推送、无打卡、无排行榜、不做社交分享
4. **零外部依赖** —— 全部可离线运行，字体与音频自带

## Git 与发布

- 远端：`github.com/Beeasy-L/starspark-trilogy.git`（分支 `main`）
- GitHub Pages 发布根即仓库根：`index.html` / `assets\` / `projects\`
- `产品\`、`共用\字体\`、`共用\音频\`、`_归档\` 由 `.gitignore` 排除，**不入仓**——避免仓膨胀导致 Pages 部署超时

### ⚠️ 外部依赖登记（2026-10-27，主公定「服务端托管」方案）

**介绍页首页的分享卡图片，依赖一台外部服务器：**

| 项 | 值 |
|---|---|
| 地址 | `http://8.137.60.56:8000/static/social-card.jpg?v=3` |
| 服务 | 星火续火花 ②程序文件（自带令牌门禁，`/static` 为公开路径） |
| 失效影响 | 微信 / Twitter / QQ 分享首页时，分享卡退化为纯文字，**页面本身不受影响** |
| 兜底 | `index.html` 的 `<body>` 内有一个 `display:none` 的 `<img>`，同样指向该地址，用于促使微信抓图 |
| 回复方案 | 若该服务器长期下线，改回 `https://beeasy-l.github.io/starspark-trilogy/assets/social-card.jpg`（产品页目前用的就是这个 Pages 地址） |

**注意**：`assets/social-card.jpg` 曾是**被写坏的 base64 文本**（7036 字节，解出来是截断的 5276 字节残图，PIL 无法读取）。2026-10-27 已用有效 1200×630 JPEG 覆盖（82 KB）。若再有人「用 PowerShell 改图」，请确认写入的是二进制而不是 base64 字符串。


## 常用命令

```bash
# 启动星火PPT（默认 127.0.0.1:8577）
cd 产品/星火PPT && python server.py

# 检查介绍页 HTML 结构
python tools/check_html.py

# 部署（介绍页开发负责）
git push origin main
```

## 文档索引

| 位置 | 内容 |
|---|---|
| `文档\规范\星火网页动效规范.md` | **★ 网页动效语言 v1.0**（曲线族 / 时长表 / 出场时序 / 禁用清单 / 落地清单） |
| `文档\报告\星火三部曲-架构分析报告.md` | 全项目架构测绘与改进路线 |
| `文档\报告\验收报告_星火PPT.md` / `验收报告_专注Pro.md` | 验收官验收结论 |
| `文档\规范\项目经验总结.md` | 跨项目经验沉淀 |
| `产品\星火PPT\设计规范.md` | 星火PPT 设计规范（12 套设计系统实测值） |
| `共用\动画规范\emil-motion\` | 动画 Skill 文档（animate / improve / review / mobile-native） |
| `共用\设计令牌\design-tokens.js` | 设计令牌（`window.XH_DESIGN` 数据表，含 src 出处） |

---

*合并整理：星火架构师 ｜ 2026-10-26*
