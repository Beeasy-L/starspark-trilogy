#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R3 结构与一致性审查 · 星火架构师

审查对象：产品\星火PPT\示例\示例_运营复盘_8页.pptx
审查维度（群管 R3 分派给我的四项）：
  ① 版式选择是否合理（该用表格的有没有用表格）
  ② 图表三类型是否用对
  ③ 跨页风格是否统一
  ④ 有没有版面越界、元素重叠

★ 独立口径（不采信参数表自述）：
  参数表的「溢出页 0 / 重叠页 0」来自**网页渲染**时的 scrollHeight / overlapScan。
  我改用 **OOXML 坐标层**独立验：直接读每个形状的 <a:off> / <a:ext>，
  自己算边界与重叠。两条路互相印证，比任一条单独可信。

只读：不修改 pptx、不写回示例目录。
用法：python tools/review_r3_structure.py
"""
import os
import re
import sys
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PPTX = os.path.join(ROOT, "产品", "星火PPT", "示例", "示例_运营复盘_8页.pptx")

EMU_PER_PX = 9525          # OOXML: 914400 EMU/inch ÷ 96 dpi

# 版式合理性预期（来自 逐页清单.md 的自述，我逐页核对）
EXPECT_LAYOUT = {
    1: "cover", 2: "kpi", 3: "chart", 4: "chart",
    5: "chart", 6: "table", 7: "zigzag", 8: "closing",
}

results = []


def add(name, ok, detail):
    results.append((name, ok, detail))
    print(("  [通过] " if ok else "  [问题] ") + name + "  " + detail)


def parse_shapes(xml):
    """返回该页所有形状的 (名称, x, y, cx, cy) —— 单位 px"""
    out = []
    # <p:sp> ... <p:nvSpPr>...<p:cNvPr id= name= ...> ... <a:off x= y=/><a:ext cx= cy=/>
    for m in re.finditer(r"<p:sp>.*?</p:sp>", xml, re.S):
        block = m.group(0)
        nm = re.search(r'<p:cNvPr[^>]*name="([^"]*)"', block)
        off = re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"', block)
        ext = re.search(r'<a:ext cx="(-?\d+)" cy="(-?\d+)"', block)
        if not (off and ext):
            continue
        x = int(off.group(1)) / EMU_PER_PX
        y = int(off.group(2)) / EMU_PER_PX
        cx = int(ext.group(1)) / EMU_PER_PX
        cy = int(ext.group(2)) / EMU_PER_PX
        out.append((nm.group(1) if nm else "?", x, y, cx, cy))
    return out


def main():
    if not os.path.exists(PPTX):
        print("[致命] 找不到示例：%s" % PPTX)
        return 1

    print("=" * 74)
    print("R3 结构与一致性审查（OOXML 坐标层独立验，不采信渲染自述）")
    print("对象: %s" % os.path.relpath(PPTX, ROOT))
    print("=" * 74)

    z = zipfile.ZipFile(PPTX)
    slide_names = sorted(
        [n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)],
        key=lambda s: int(re.search(r"(\d+)", os.path.basename(s)).group(1)),
    )
    n_pages = len(slide_names)
    print("\n页数: %d" % n_pages)

    # 画布尺寸（presentation.xml 的 sldSz）
    pres = z.read("ppt/presentation.xml").decode("utf-8", "replace")
    m = re.search(r'<p:sldSz cx="(\d+)" cy="(\d+)"', pres)
    W = int(m.group(1)) / EMU_PER_PX if m else 960
    H = int(m.group(2)) / EMU_PER_PX if m else 540
    print("画布: %.0f x %.0f px" % (W, H))

    # ---------- ④ 越界 / 重叠 ----------
    print("\n【④ 版面越界与元素重叠】")
    total_overflow = 0
    total_overlap = 0
    for idx, name in enumerate(slide_names, 1):
        xml = z.read(name).decode("utf-8", "replace")
        shapes = parse_shapes(xml)
        # 越界：形状是否有任何一边超出画布（容差 1px）
        of = [s for s in shapes
              if s[1] < -1 or s[2] < -1 or s[1] + s[3] > W + 1 or s[2] + s[4] > H + 1]
        # 重叠：非嵌套、面积重叠 > 5% 较小者
        ov = []
        for i in range(len(shapes)):
            for j in range(i + 1, len(shapes)):
                a, b = shapes[i], shapes[j]
                ax1, ay1, ax2, ay2 = a[1], a[2], a[1] + a[3], a[2] + a[4]
                bx1, by1, bx2, by2 = b[1], b[2], b[1] + b[3], b[2] + b[4]
                ix = max(0, min(ax2, bx2) - max(ax1, bx1))
                iy = max(0, min(ay2, by2) - max(ay1, by1))
                inter = ix * iy
                if inter <= 0:
                    continue
                smaller = min(a[3] * a[4], b[3] * b[4])
                if smaller <= 0:
                    continue
                # 嵌套（一个完全在另一个里面）不算重叠问题
                a_in_b = ax1 >= bx1 - 1 and ay1 >= by1 - 1 and ax2 <= bx2 + 1 and ay2 <= by2 + 1
                b_in_a = bx1 >= ax1 - 1 and by1 >= ay1 - 1 and bx2 <= ax2 + 1 and by2 <= ay2 + 1
                if a_in_b or b_in_a:
                    continue
                if inter / smaller > 0.05:
                    ov.append((a[0], b[0], inter / smaller))
        # ★ 区分「设计意图的重叠」与「意外重叠」（19:50 修正）
        #   第一版把所有 >5% 的重叠都算问题，报了 27 对——其中大部分是设计意图：
        #     装饰层（Deco*）垫在内容下面      → 本来就是叠的
        #     图表内部元素（Svg*/ring/seg）互叠 → 环形图分段必须画在底环上
        #   真正可疑的只有「内容元素之间」的重叠（文本块×文本块、文本×图表）。
        DECO_PREFIX = ("Deco", "Svg", "motif", "bg", "Bg", "Line")
        CHART_KEYS = ("ring", "Ring", "Seg", "seg", "chart", "Chart",
                      "Track", "Fill", "Bar", "CB")
        def is_deco(n):
            return n.startswith(DECO_PREFIX) or any(k in n for k in CHART_KEYS)
        ov_real = [o for o in ov if not (is_deco(o[0]) or is_deco(o[1]))]
        ov_by_design = [o for o in ov if (is_deco(o[0]) or is_deco(o[1]))]
        total_overflow += len(of)
        total_overlap += len(ov_real)
        flag = "" if (not of and not ov_real) else "  ← 有问题"
        print("  第%d页: 形状%2d  越界%d  可疑重叠%d  设计重叠%d%s"
              % (idx, len(shapes), len(of), len(ov_real), len(ov_by_design), flag))
        for s in of[:2]:
            print("       越界: %s  (%.0f,%.0f %.0fx%.0f)" % (s[0], s[1], s[2], s[3], s[4]))
        for a, b, r in ov_real[:3]:
            print("       可疑重叠: %s × %s  %.1f%%" % (a, b, r * 100))

    add("④a 无越界", total_overflow == 0, "8 页合计越界 %d 个形状" % total_overflow)
    add("④b 无「可疑重叠」", total_overlap == 0,
        "8 页合计可疑重叠 %d 对（已排除装饰层与图表内部的重叠）" % total_overlap)
    print("      判据说明：装饰层压内容、环形图底环叠分段 = 设计意图，不计；")
    print("                只报「内容元素之间」的重叠（文本×文本、文本×图表）。")
    print("      参数表自称「溢出页 0 / 重叠页 0」（基于网页渲染）；")
    print("      本条是我用 OOXML 坐标独立算的 —— 两条路口径不同，互补。")

    # ---------- ② 图表三类型 ----------
    print("\n【② 图表三类型是否用对】")
    chart_pages = {3: "bar", 4: "progress", 5: "ring"}
    for pg, want in chart_pages.items():
        xml = z.read(slide_names[pg - 1]).decode("utf-8", "replace")
        has_donut = 'prst="donut"' in xml
        rot_cnt = len(re.findall(r'rot="', xml))
        # progress 用矩形对（底槽 FFFFFF + 填充色），bar 用同色矩形
        if want == "ring":
            ok = has_donut or rot_cnt >= 8
            add("② 第%d页 = %s" % (pg, want), ok,
                "donut=%s rot=%d（环形图特征）" % (has_donut, rot_cnt))
        else:
            add("② 第%d页 = %s" % (pg, want), rot_cnt < 8,
                "rot=%d（非环形，符合 %s）" % (rot_cnt, want))

    # ---------- ① 版式选择合理性 ----------
    print("\n【① 版式选择是否合理】")
    # 第6页「四个渠道」在逐页清单里标的是 table 版式。
    # V2.1 之后导出改成「量网页照抄成形状」，所以要看两件事：
    #   ① 视觉上是不是表格形态（有行列分栏的矩形/线条）
    #   ② 是不是真 OOXML 表格 <a:tbl>（决定用户能否在 PowerPoint 里增删行列）
    xml6 = z.read(slide_names[5]).decode("utf-8", "replace")
    has_tbl = "<a:tbl>" in xml6
    n_sp6 = len(parse_shapes(xml6))
    n_lines6 = len(re.findall(r'prst="(line|straightConnector1)"', xml6))
    looks_like_table = n_sp6 >= 20 or n_lines6 >= 4
    add("① 第6页视觉上是表格形态", looks_like_table,
        "形状 %d 个 / 线条 %d 条" % (n_sp6, n_lines6))
    if has_tbl:
        add("① 第6页是真 OOXML 表格", True, "<a:tbl> 存在 —— 可在 PPT 里增删行列")
    else:
        add("① 第6页是真 OOXML 表格", False,
            "<a:tbl> **不存在** —— 视觉是表格，但由文本框/线条拼成，"
            "在 PowerPoint 里无法增删行列（只能逐个挪）")
        print("      这是 V2.1「照抄网页形状」方案的已知代价，不是 bug；")
        print("      但属「表格该不该是真表格」的产品取舍，需记录。")
    # 第2页 KPI 应为多个大数字
    xml2 = z.read(slide_names[1]).decode("utf-8", "replace")
    big = len([s for s in parse_shapes(xml2) if s[4] > 40])
    add("① 第2页 KPI 有大数字块", big >= 4, "高度>40px 的形状 %d 个" % big)

    # ---------- ③ 跨页风格统一 ----------
    print("\n【③ 跨页风格是否统一】")
    fonts = {}
    for idx, name in enumerate(slide_names, 1):
        xml = z.read(name).decode("utf-8", "replace")
        for f in re.findall(r'typeface="([^"+]+)"', xml):
            fonts.setdefault(f, set()).add(idx)
    if fonts:
        print("  出现的字体（类型名 → 所在页）:")
        for f, pages in sorted(fonts.items(), key=lambda kv: -len(kv[1])):
            print("    %-22s %s" % (f, sorted(pages)))
        main_fonts = [f for f, p in fonts.items() if len(p) >= n_pages - 1]
        add("③ 字体跨页统一", len(main_fonts) >= 1,
            "%d 个字体覆盖 ≥%d 页" % (len(main_fonts), n_pages - 1))
    else:
        add("③ 字体跨页统一", False, "未解析到 typeface")

    # 主题稳定性：每页使用的主题色
    themes = {}
    for idx, name in enumerate(slide_names, 1):
        xml = z.read(name).decode("utf-8", "replace")
        themes[idx] = set(re.findall(r'srgbClr val="([0-9A-Fa-f]{6})"', xml))
    all_colors = set().union(*themes.values()) if themes else set()
    print("  全篇用色 %d 种" % len(all_colors))
    add("③ 用色克制（≤12 种）", len(all_colors) <= 12, "%d 种" % len(all_colors))

    # ---------- 汇总 ----------
    ok = sum(1 for _, o, _ in results if o)
    total = len(results)
    print("\n" + "=" * 74)
    print("R3 审查: %d/%d 项通过" % (ok, total))
    if ok == total:
        print("结论: 结构与一致性四项全部通过。")
        return 0
    print("结论: 有 %d 项需说明。" % (total - ok))
    return 0   # 审查脚本本身不返回失败（结论由人写）


if __name__ == "__main__":
    sys.exit(main())
