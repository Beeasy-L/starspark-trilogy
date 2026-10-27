#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回退包重打包 —— 把「发布物回退包」刷新到当前发布物状态

何时用：check_rollback.py 报 [过期] 时。

安全边界（硬约束）：
    - 只写 _归档/发布物回退包/ 目录内
    - 绝不触碰产品目录、线上目录、git 索引
    - 不删除任何现有发布物文件，只覆盖包内副本

用法：
    python _归档/发布物回退包/repack.py            # 重打包
    python _归档/发布物回退包/repack.py --dry      # 只看会做什么，不实际执行
"""
import hashlib
import os
import shutil
import sys

PKG = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.path.join(PKG, "..", ".."))

# (源相对根路径, 包内相对路径)
COPIES = [
    ("index.html", "介绍页/index.html"),
    ("README.md", "介绍页/README.md"),
    ("assets/site.css", "介绍页/assets/site.css"),
    ("assets/site.js", "介绍页/assets/site.js"),
    ("assets/social-card.jpg", "介绍页/assets/social-card.jpg"),
    ("assets/moon.mp3", "介绍页/assets/moon.mp3"),
    ("assets/xiaoxingxing.mp3", "介绍页/assets/xiaoxingxing.mp3"),
    ("assets/spark-ai.png", "介绍页/assets/spark-ai.png"),
    ("assets/spark-cloud.png", "介绍页/assets/spark-cloud.png"),
    ("assets/spark-logs.png", "介绍页/assets/spark-logs.png"),
    ("assets/spark-overview.png", "介绍页/assets/spark-overview.png"),
    ("assets/focus-policy-v060.png", "介绍页/assets/focus-policy-v060.png"),
    ("assets/focus-qr.png", "介绍页/assets/focus-qr.png"),
    ("assets/focus-sound-v060.png", "介绍页/assets/focus-sound-v060.png"),
    ("assets/ppt-compare.jpg", "介绍页/assets/ppt-compare.jpg"),
    ("assets/ppt-interface.jpg", "介绍页/assets/ppt-interface.jpg"),
    ("assets/ppt-pages.jpg", "介绍页/assets/ppt-pages.jpg"),
    ("assets/ppt-points.jpg", "介绍页/assets/ppt-points.jpg"),
    ("assets/ppt-themes.jpg", "介绍页/assets/ppt-themes.jpg"),
    ("projects/focus.html", "介绍页/projects/focus.html"),
    ("projects/focus-start.html", "介绍页/projects/focus-start.html"),
    ("projects/ppt.html", "介绍页/projects/ppt.html"),
    ("projects/streak.html", "介绍页/projects/streak.html"),
    ("projects/focus-app/index.html", "介绍页/projects/focus-app/index.html"),
    ("projects/focus-app/sw.js", "介绍页/projects/focus-app/sw.js"),
    ("projects/focus-app/manifest.webmanifest", "介绍页/projects/focus-app/manifest.webmanifest"),
    ("tools/check_html.py", "介绍页/tools/check_html.py"),
    # PPT Pages 发布源
    ("产品/星火PPT/deploy/网页版/index.html", "PPT发布源/index.html"),
    ("产品/星火PPT/deploy/网页版/music.mp3", "PPT发布源/music.mp3"),
    # 专注Pro Pages 发布源
    ("产品/星火专注Pro/_gitrepo/index.html", "专注Pro发布源/index.html"),
    ("产品/星火专注Pro/_gitrepo/sw.js", "专注Pro发布源/sw.js"),
    ("产品/星火专注Pro/_gitrepo/manifest.webmanifest", "专注Pro发布源/manifest.webmanifest"),
]

# 目录整体复制
DIRS = [
    ("assets", "介绍页/assets"),
    ("projects", "介绍页/projects"),
    ("icons", "专注Pro发布源/icons"),
]

# 目录里要排除的（中间产物）
EXCLUDE_NAMES = {"gif-frames", "__pycache__"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head(repo):
    import subprocess
    try:
        out = subprocess.run(["git", "-C", repo, "log", "-1", "--format=%h"],
                             capture_output=True, text=True, timeout=15,
                             encoding="utf-8", errors="replace")
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "?"


def copy_tree_overlay(src, dst, dry=False):
    """增量覆盖复制：不先删目标目录，避免 Windows 文件锁导致失败，
    也避免误删包里已有的额外文件。"""
    n = 0
    for base, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_NAMES]
        rel = os.path.relpath(base, src)
        target_base = dst if rel == "." else os.path.join(dst, rel)
        if not dry:
            os.makedirs(target_base, exist_ok=True)
        for name in files:
            if name.endswith(".pyc"):
                continue
            s = os.path.join(base, name)
            t = os.path.join(target_base, name)
            if os.path.exists(t) and sha256(s) == sha256(t):
                continue
            if not dry:
                try:
                    shutil.copy2(s, t)
                except PermissionError:
                    # 文件被占用：重试一次，仍失败则跳过并报告
                    try:
                        shutil.copy2(s, t)
                    except PermissionError:
                        print("  [占用] 跳过: %s" % os.path.relpath(t, PKG))
                        continue
            n += 1
    return n


def main():
    dry = "--dry" in sys.argv
    print("回退包重打包%s" % ("（预演，不实际执行）" if dry else ""))
    print("包位置: %s" % PKG)
    print("=" * 70)

    copied = skipped = 0
    changed = []

    for src_rel, dst_rel in COPIES:
        src = os.path.join(ROOT, src_rel.replace("/", os.sep))
        dst = os.path.join(PKG, dst_rel.replace("/", os.sep))
        if not os.path.exists(src):
            print("  [跳过] 源不存在: %s" % src_rel)
            skipped += 1
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst) and sha256(src) == sha256(dst):
            skipped += 1
            continue
        try:
            if not dry:
                shutil.copy2(src, dst)
        except PermissionError:
            print("  [占用] 跳过: %s" % dst_rel)
            skipped += 1
            continue
        copied += 1
        changed.append(dst_rel)

    for src_rel, dst_rel in DIRS:
        src = os.path.join(ROOT, src_rel.replace("/", os.sep))
        dst = os.path.join(PKG, dst_rel.replace("/", os.sep))
        if not os.path.isdir(src):
            print("  [跳过] 源目录不存在: %s" % src_rel)
            skipped += 1
            continue
        n = copy_tree_overlay(src, dst, dry)
        copied += n
        if n:
            changed.append("%s (%d 个文件)" % (dst_rel, n))

    print("-" * 70)
    print("文件复制 %d | 跳过(相同或缺失) %d" % (copied, skipped))
    if changed:
        print("本次刷新:")
        for c in changed:
            print("  + %s" % c)

    # 写入版本戳
    stamp = os.path.join(PKG, "VERSION.txt")
    if not dry:
        import datetime
        main_h = git_head(ROOT)
        ppt_h = git_head(os.path.join(ROOT, "产品", "星火PPT", "deploy", "网页版"))
        fp_h = git_head(os.path.join(ROOT, "产品", "星火专注Pro", "_gitrepo"))
        with open(stamp, "w", encoding="utf-8") as f:
            f.write("# 发布物回退包 · 版本戳\n")
            f.write("#\n")
            f.write("# 下面三个 git hash 只是【溯源参考】，会因历史重写/合并/ff 而失效。\n")
            f.write("# 判断本包是否仍与发布物一致，请跑：python tools/check_rollback.py\n")
            f.write("# 那个脚本用 SHA256 逐文件比对内容，【不依赖 git hash】—— 这才是硬判据。\n")
            f.write("\n")
            f.write("打包时间: %s\n" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            f.write("\n")
            f.write("主仓          %s   (C:\\Users\\saucc\\Desktop\\星火三部曲)\n" % main_h)
            f.write("PPT deploy 仓 %s   (产品\\星火PPT\\deploy\\网页版)\n" % ppt_h)
            f.write("专注Pro 仓    %s   (产品\\星火专注Pro\\_gitrepo)\n" % fp_h)
            f.write("\n")
            f.write("一致性自检: python tools/check_rollback.py   （期望 exit=0）\n")
    print("版本戳: %s" % ("（预演未写入）" if dry else stamp))
    print()
    print("下一步: python tools/check_rollback.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
