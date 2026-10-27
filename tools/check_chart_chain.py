#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
星火PPT · 字段透传链路自检
=========================

为什么需要它（2026-10-26 事故）：
    V2.0~V2.8 整整三个版本，「图表进导出」一直被验收官报为「已通过」。
    真因不是图表没做，是 **chart 字段在 buildDeck() 这一环被丢掉**：
        AI JSON  →  buildDeck()  →  state.slides[].chart  →  {网页 / 导出 HTML / 导出 pptx}
                                  ^ 断在这里，下游全部拿到 undefined
    而下游三处（chartHTML / pageHTML / chartData）都是**正确的**——
    **测了零件，没测那条路。**

    这类 bug 是**结构性漏的**：字段在 schema 里声明了，在消费处读得到，
    中间的搬运环节少写一个字段名，谁看代码都看不出来。
    所以必须有一条**自动的、按链路逐环核对**的门禁。

本脚本做什么：
    把 slide 的字段逐个核对「声明 → 生产 → 搬运 → 消费」四个环节：
      1. 必带字段（title / layout / content / note）——任何一环漏了就是断链
      2. 数据字段（chart）——AI 会返回、渲染器会读，必须全程透传
      3. 图片字段（img）——**有意只在部分环节存在**（存历史时剥离），
         本脚本单独检查「该有的地方有、不该有的地方没有」

用法：
    python check_chart_chain.py                    # 查默认路径
    python check_chart_chain.py --ppt <路径>       # 指定 index.html
    python check_chart_chain.py --strict           # 有问题以非 0 退出（挂 CI / 门禁）

退出码：
    0 = 链路完整
    1 = 发现断链
    2 = 文件缺失

设计约束：
    - 零第三方依赖，只用标准库
    - **只读**：绝不修改任何文件
    - 输出可读表格 + 明确的处置建议
"""
import argparse
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DEFAULT_PPT = os.path.join(ROOT, "产品", "星火PPT", "static", "index.html")
DEFAULT_SERVER = os.path.join(ROOT, "产品", "星火PPT", "server.py")


# ---------------------------------------------------------------- 读文件
def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def grab_function(src, name):
    """抠出一个函数的完整源码（按大括号配对，跳过字符串与注释里的花括号）。"""
    m = re.search(r"function\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{", src)
    if not m:
        return ""
    start = m.start()
    i = m.end() - 1
    depth = 0
    in_str = None
    esc = False
    while i < len(src):
        ch = src[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in "\"'`":
            in_str = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1
    return ""


def grab_block(src, start_pat):
    """从 start_pat 匹配处开始，抠出一段配平大括号的内容。"""
    m = re.search(start_pat, src)
    if not m:
        return ""
    i = src.find("{", m.start())
    if i < 0:
        return ""
    depth = 0
    in_str = None
    esc = False
    while i < len(src):
        ch = src[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in "\"'`":
            in_str = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():i + 1]
        i += 1
    return ""


# ---------------------------------------------------------------- 链路定义
# scope 说明：
#   ("func", 名称)  → 只在该函数体内找
#   ("whole", "")   → 在整个文件里找
CHAIN = [
    {
        "field": "title",
        "kind": "必带",
        "hops": [
            ("AI schema 声明", ("func", "buildSystemPromptJS"), [r'"title"\s*:\s*"页标题']),
            ("buildDeck 搬运", ("func", "buildDeck"), [r"title\s*:\s*s\.title"]),
            ("state.slides 消费", ("func", "pageHTML"), [r"esc\(s\.title"]),
        ],
    },
    {
        "field": "layout",
        "kind": "必带",
        "hops": [
            ("AI schema 声明", ("func", "buildSystemPromptJS"), [r'"layout"\s*:\s*"版式名"']),
            ("buildDeck 搬运", ("func", "buildDeck"), [r"layout\s*:\s*\(s\.layout"]),
            ("state.slides 消费", ("func", "normalizeSlide"), [r"normLayout\(s\.layout\)"]),
        ],
    },
    {
        "field": "content",
        "kind": "必带",
        "hops": [
            ("AI schema 声明", ("func", "buildSystemPromptJS"), [r'"content"\s*:\s*\[.*\]']),
            ("buildDeck 搬运", ("func", "buildDeck"), [r"content\s*:\s*Array\.isArray\(s\.content\)"]),
            ("state.slides 消费", ("func", "pageHTML"), [r"\bpts\b"]),
        ],
    },
    {
        "field": "note",
        "kind": "必带",
        "hops": [
            ("AI schema 声明", ("func", "buildSystemPromptJS"), [r'"note"\s*:\s*"这一页的收束句"']),
            ("buildDeck 搬运", ("func", "buildDeck"), [r"note\s*:\s*s\.note"]),
            ("state.slides 消费", ("func", "pageHTML"), [r"s\.note\s*\?"]),
        ],
    },
    {
        "field": "chart",
        "kind": "数据",
        "hops": [
            ("AI schema 声明", ("whole", ""), [r"chart\s+字段"]),
            ("buildDeck 搬运", ("func", "buildDeck"), [r"chart\s*:\s*\(s\.chart\s*&&\s*typeof s\.chart===\"object\"\)",
                                                      r"\.\.\.\(s\.chart\s*&&\s*typeof s\.chart===\"object\"\s*\?\s*\{chart\s*:",]),
            ("网页预览消费", ("func", "chartHTML"), [r"const\s+ch\s*=\s*s\.chart\s*\|\|\s*\{\}"]),
            ("导出 HTML 消费", ("func", "pageHTML"), [r"chartHTML\(s,\s*pts\)"]),
            ("导出 pptx 搬运", ("block", r'\$\("#btn-export-pptx"\)\.onclick'), [r"chart\s*:\s*\(s\.chart\s*&&\s*typeof s\.chart===\"object\"\)"]),
        ],
    },
    {
        "field": "img",
        "kind": "图片（有意只在部分环节存在）",
        "hops": [
            ("AI 生图入口", ("whole", ""), [r"async\s+function\s+aiImage\("]),
            ("state.slides 存放", ("func", "pageHTML"), [r"s\.img"]),
            ("导出 pptx 搬运", ("block", r'\$\("#btn-export-pptx"\)\.onclick'), [r"img\s*:\s*s\.img\s*\|\|"]),
        ],
    },
]

# 有意「不出现」的环节：存历史时必须剥离 img（base64 撑爆 localStorage）
MUST_NOT = [
    {
        "field": "img",
        "where": "persist（存历史）",
        "func": "persist",
        "why": "配图是 base64 大字符串，存进 localStorage 会撑爆配额——必须剥离",
    },
]


def collect(src):
    parts = {"__all__": src}
    for name in ("buildDeck", "persist", "pageHTML", "chartHTML", "chartItems",
                 "buildSystemPromptJS", "buildUserPromptJS", "blueprintText",
                 "normLayout", "normalizeSlide", "openHistory"):
        parts["func:" + name] = grab_function(src, name)
    parts["block:EXPORT"] = grab_block(src, r'\$\("#btn-export-pptx"\)\.onclick')
    return parts


def blob_for(parts, scope):
    kind, name = scope
    if kind == "whole":
        return parts["__all__"]
    if kind == "func":
        return parts.get("func:" + name, "")
    if kind == "block":
        return parts.get("block:EXPORT", "")
    return ""


def check(ppt_path, server_path):
    if not os.path.exists(ppt_path):
        print("找不到 PPT 前端文件: %s" % ppt_path)
        return 2
    src = read(ppt_path)
    parts = collect(src)

    print("=" * 78)
    print("星火PPT · 字段透传链路自检")
    print("文件: %s" % ppt_path)
    print("大小: %d B   行数: %d" % (len(src.encode("utf-8")), src.count("\n") + 1))
    print("=" * 78)

    problems = []
    rows = []

    for spec in CHAIN:
        for hop_name, scope, pats in spec["hops"]:
            blob = blob_for(parts, scope)
            if not blob:
                rows.append((spec["field"], spec["kind"], hop_name, "MISS", "找不到该环节"))
                problems.append("[%s] %s：找不到环节（%s:%s）" % (spec["field"], hop_name, scope[0], scope[1]))
                continue
            hit = any(re.search(p, blob) for p in pats)
            rows.append((spec["field"], spec["kind"], hop_name,
                         "OK" if hit else "BROKEN",
                         "命中" if hit else "未找到透传证据"))
            if not hit:
                problems.append("[%s] %s（%s:%s）：未找到字段透传证据"
                                % (spec["field"], hop_name, scope[0], scope[1]))

    # 有意「不出现」的环节
    for spec in MUST_NOT:
        blob = parts.get("func:" + spec["func"], "")
        # 去掉注释后再找，避免注释里的字样被误判
        code_only = re.sub(r"/\*.*?\*/", "", blob, flags=re.S)
        code_only = re.sub(r"//[^\n]*", "", code_only)
        real_hit = bool(re.search(r"img\s*:\s*s\.img", code_only))
        rows.append((spec["field"], "图片", spec["where"],
                     "BROKEN" if real_hit else "OK",
                     "仍在写入 localStorage" if real_hit else "已按预期剥离"))
        if real_hit:
            problems.append("[%s] %s：配图没有被剥离，会撑爆 localStorage 配额" % (spec["field"], spec["where"]))

    # ---- 后端提示词版式清单 ----
    if os.path.exists(server_path):
        s = read(server_path)
        server_note = "有" if re.search(r"^- chart\u3000", s, re.M) else "无"
    else:
        server_note = "（未找到 server.py）"

    # ---- 输出 ----
    print()
    print("%-8s %-24s %-22s %-6s %s" % ("字段", "类别", "环节", "结果", "备注"))
    print("-" * 78)
    for field, kind, hop, res, note in rows:
        mark = {"OK": "✅", "MISS": "⚠️", "BROKEN": "❌"}[res]
        print("%-8s %-24s %-22s %s %-6s %s" % (field, kind, hop, mark, res, note))

    print("-" * 78)
    print("后端 LAYOUT_DOC 是否含 chart 版式: %s" % server_note)
    if server_note == "无":
        problems.append("[chart] 后端 LAYOUT_DOC 没有 chart 版式 → 走后端时模型选不到图表")

    print()
    if problems:
        print("发现 %d 处断链 / 不一致：" % len(problems))
        for p in problems:
            print("  ❌ " + p)
        print()
        print("处置建议：")
        print("  · chart 相关 → 见 文档\\方案\\星火PPT-chart链路修复补丁.md（4 处改动的改前/改后全文）")
        print("  · 必带字段断链 → 检查对应环节的 map / 赋值是否漏了字段名")
        print("  · 一条铁律：字段在 schema 里声明了，就必须在这条链的每一环都能找到它")
    else:
        print("✅ 链路完整：schema → 生产 → 搬运 → 消费，每一环都对得上。")

    return 1 if problems else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ppt", default=DEFAULT_PPT, help="index.html 路径")
    ap.add_argument("--server", default=DEFAULT_SERVER, help="server.py 路径")
    ap.add_argument("--strict", action="store_true", help="有问题以非 0 退出")
    args = ap.parse_args()

    code = check(args.ppt, args.server)
    if code == 2:
        return 2
    return 1 if (args.strict and code == 1) else 0


if __name__ == "__main__":
    sys.exit(main())
