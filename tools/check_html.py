#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
星火三部曲 · HTML 结构检查

为什么需要它：
    单纯数「开标签数 == 闭标签数」是拦不住嵌套错误的。
    `<b>甲<b>乙</b>丙</b>` 里 <b> 开 2 闭 2，配平算法判定通过，
    但它是非法标记，浏览器解析会错乱。

    所以本脚本用真的 HTML 解析器，维护一个开启标签栈，
    逐标签比对——嵌套、错配、未闭合，一个都跑不掉。

用法：
    python check_html.py                 # 检查仓库内所有页面
    python check_html.py a.html b.html   # 只检查指定文件
退出码：
    0 = 全部通过；1 = 发现问题
"""
import sys
import os
from html.parser import HTMLParser

# 自闭合标签，不需要配对
VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# 这些标签不允许直接嵌套自身（`<b><b>` 是错的）
NO_SELF_NEST = {
    "b", "i", "u", "em", "strong", "span", "a", "p",
    "h1", "h2", "h3", "h4", "h5", "h6", "title", "button",
    "table", "thead", "tbody", "ul", "ol",
}

# 遇到这些开标签时，若栈顶是同类（或表中指定的），视为隐式闭合
IMPLICIT_CLOSE = {
    "li": {"li"},
    "p": {"p"},
    "tr": {"tr", "td", "th"},
    "td": {"td", "th"},
    "th": {"td", "th"},
    "option": {"option"},
    "dt": {"dt", "dd"},
    "dd": {"dt", "dd"},
}

# 换行/格式化时不算问题的标签（浏览器会宽容处理）
LENIENT = {"html", "head", "body"}


class StructureChecker(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=False)
        self.path = path
        self.stack = []          # [(tag, lineno)]
        self.errors = []         # [(lineno, message)]

    # ---------- 工具 ----------
    def _top(self):
        return self.stack[-1] if self.stack else (None, None)

    def _pop_until(self, tags):
        """弹出到指定标签集合（用于隐式闭合）"""
        while self.stack and self.stack[-1][0] in tags:
            self.stack.pop()

    # ---------- 事件 ----------
    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        if tag in VOID:
            return

        # 1) 隐式闭合：<li> 紧跟 <li> 等
        if tag in IMPLICIT_CLOSE:
            top = self._top()[0]
            if top in IMPLICIT_CLOSE[tag]:
                self.stack.pop()

        # 2) 不允许自嵌套的标签
        if tag in NO_SELF_NEST:
            open_same = [t for t, _ in self.stack if t == tag]
            if open_same:
                prev_line = next(ln for t, ln in reversed(self.stack) if t == tag)
                self.errors.append((
                    line,
                    f"嵌套 <{tag}>：第 {line} 行又开了 <{tag}>，而第 {prev_line} 行的 <{tag}> 还没闭合"
                ))

        self.stack.append((tag, line))

    def handle_startendtag(self, tag, attrs):
        # <br/> <img/> 这类，忽略
        return

    def handle_endtag(self, tag):
        line = self.getpos()[0]
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append((line, f"多余的 </{tag}>：没有任何未闭合的 <{tag}> 与之对应"))
            return
        top, top_line = self.stack[-1]
        if top == tag:
            self.stack.pop()
            return
        # 栈顶不是它 —— 错配
        if tag in [t for t, _ in self.stack]:
            # 它在栈里但不在栈顶，说明中间有标签没关
            inner = [t for t, _ in self.stack[self.stack.index((tag, next(ln for t, ln in self.stack if t == tag)))+1:]]
            self.errors.append((
                line,
                f"错配 </{tag}>：它对应第 "
                f"{next(ln for t, ln in self.stack if t == tag)} 行的 <{tag}>，"
                f"但中间这些还没闭合 → {'、'.join('<' + t + '>' for t in inner)}"
            ))
        else:
            self.errors.append((line, f"错配 </{tag}>：栈顶是 <{top}>（第 {top_line} 行）"))

    def close(self):
        super().close()
        for tag, line in self.stack:
            self.errors.append((line, f"未闭合 <{tag}>：到文件结束都没有对应的 </{tag}>"))


def check(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    parser = StructureChecker(path)
    try:
        parser.feed(src)
        parser.close()
    except Exception as exc:                       # 解析器自身异常也算问题
        return [(0, f"解析失败：{exc}")]
    return sorted(set(parser.errors))


def collect_targets(argv):
    if argv:
        return argv
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, ".."))
    found = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith((".", "_"))]
        for name in files:
            if name.endswith(".html"):
                found.append(os.path.join(base, name))
    return sorted(found)


def main():
    targets = collect_targets(sys.argv[1:])
    if not targets:
        print("没有找到要检查的 HTML 文件")
        return 1

    total_errors = 0
    root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    for path in targets:
        errors = check(path)
        try:
            shown = os.path.relpath(path, root)
        except ValueError:
            shown = path
        if errors:
            total_errors += len(errors)
            print(f"[问题] {shown}")
            for line, msg in errors:
                print(f"       第 {line} 行  {msg}")
        else:
            print(f"[通过] {shown}")

    print()
    if total_errors:
        print(f"共发现 {total_errors} 处结构问题。")
        return 1
    print(f"全部通过（{len(targets)} 个文件，无嵌套 / 无错配 / 无未闭合）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
