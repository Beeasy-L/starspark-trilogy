#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回退包自检 —— 判定「回退包是否还与当前发布物一致」

背景（2026-10-26 15:44 事故）：
    我 15:33 打包发布物回退包并验证 9/9 一致；
    4 分钟后星火PPT 交付新构建，回退包立刻变成 8/9；
    回退包【不会自己叫】——不主动比对就发现不了它已经过期。

这个脚本就是让它会叫。

用法：
    python check_rollback.py            # 检查并报告
    python check_rollback.py --strict   # 不一致时以非 0 退出（可挂 CI / 钩子）

退出码：
    0 = 全部一致（回退包可用）
    1 = 有不一致（回退包已过期，需重打包）
    2 = 包或发布物缺失

设计：
    - 零第三方依赖，只用标准库
    - 只读：绝不修改任何文件
    - 输出可读表格 + 明确的处置建议
"""
import hashlib
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PKG = os.path.join(ROOT, "_归档", "发布物回退包")

# (包内相对路径, 当前发布物相对路径, 说明)
PAIRS = [
    ("介绍页/index.html", "index.html", "介绍页首页"),
    ("介绍页/assets/site.css", "assets/site.css", "介绍页样式"),
    ("介绍页/assets/site.js", "assets/site.js", "介绍页脚本"),
    ("介绍页/projects/focus.html", "projects/focus.html", "第二部入口页"),
    ("介绍页/projects/ppt.html", "projects/ppt.html", "第三部入口页"),
    ("介绍页/projects/streak.html", "projects/streak.html", "第一部入口页"),
    ("介绍页/projects/focus-start.html", "projects/focus-start.html", "专注Pro 启动页"),
    ("介绍页/projects/focus-app/index.html", "projects/focus-app/index.html", "专注Pro 内嵌版"),
    ("PPT发布源/index.html", "产品/星火PPT/deploy/网页版/index.html", "PPT Pages 源"),
    ("PPT发布源/music.mp3", "产品/星火PPT/deploy/网页版/music.mp3", "PPT 背景音乐"),
    ("专注Pro发布源/index.html", "产品/星火专注Pro/_gitrepo/index.html", "专注Pro Pages 源"),
    ("专注Pro发布源/sw.js", "产品/星火专注Pro/_gitrepo/sw.js", "专注Pro Service Worker"),
    ("专注Pro发布源/manifest.webmanifest", "产品/星火专注Pro/_gitrepo/manifest.webmanifest", "专注Pro PWA 清单"),
]

# 发布物所属的 git 仓（用于报 commit）
REPO_FOR = [
    ("介绍页/", ROOT, "主仓"),
    ("PPT发布源/", os.path.join(ROOT, "产品", "星火PPT", "deploy", "网页版"), "PPT deploy 独立仓"),
    ("专注Pro发布源/", os.path.join(ROOT, "产品", "星火专注Pro", "_gitrepo"), "专注Pro 仓"),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head(repo):
    try:
        out = subprocess.run(
            ["git", "-C", repo, "log", "-1", "--format=%h %s"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "(取不到)"


def main():
    strict = "--strict" in sys.argv

    if not os.path.isdir(PKG):
        print("[错误] 回退包不存在: %s" % PKG)
        print("       可能已被删除。若需重建，见 _归档\\README.md 的说明。")
        return 2

    print("回退包自检")
    print("包位置: %s" % PKG)
    print("=" * 78)

    same, diff, missing = [], [], []

    for pkg_rel, cur_rel, desc in PAIRS:
        p1 = os.path.join(PKG, pkg_rel.replace("/", os.sep))
        p2 = os.path.join(ROOT, cur_rel.replace("/", os.sep))
        if not os.path.exists(p1):
            missing.append((pkg_rel, cur_rel, desc, "包内缺失"))
            continue
        if not os.path.exists(p2):
            missing.append((pkg_rel, cur_rel, desc, "当前发布物缺失"))
            continue
        if sha256(p1) == sha256(p2):
            same.append((pkg_rel, desc))
        else:
            diff.append((pkg_rel, cur_rel, desc))

    # ---- 结果表 ----
    for pkg_rel, desc in same:
        print("  [一致] %-44s %s" % (pkg_rel, desc))
    for pkg_rel, cur_rel, desc in diff:
        print("  [过期] %-44s %s" % (pkg_rel, desc))
    for pkg_rel, cur_rel, desc, why in missing:
        print("  [缺失] %-44s %s（%s）" % (pkg_rel, desc, why))

    print("-" * 78)
    print("合计: 一致 %d | 过期 %d | 缺失 %d" % (len(same), len(diff), len(missing)))

    # ---- 各发布仓当前版本 ----
    print()
    print("当前发布版本（重打包时应与包内版本对应）:")
    for prefix, repo, label in REPO_FOR:
        print("  %-18s %s" % (label, git_head(repo)))

    # ---- 结论 ----
    print()
    if not diff and not missing:
        print("结论: 回退包与当前发布物完全一致 —— 可用于回滚。")
        return 0

    print("结论: 回退包已过期，不能直接用于回滚。")
    print()
    print("处置（按顺序）:")
    print("  1. 确认过期原因：上面 [过期] 的文件是否是你刚交付的新构建？")
    print("     - 是 → 正常现象，重打包即可")
    print("     - 否 → 查是否有意外改动")
    print("  2. 重打包：")
    print("     python _归档/发布物回退包/repack.py")
    print("  3. 重打包后复验：")
    print("     python check_rollback.py")
    print()
    print("  注: 重打包会覆盖包内文件，但不会动任何线上/产品文件。")
    return 1


if __name__ == "__main__":
    code = main()
    sys.exit(code if (code != 0 or "--strict" not in sys.argv) else code)
