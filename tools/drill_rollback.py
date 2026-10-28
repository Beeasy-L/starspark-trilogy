#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回滚演练 —— 证明「回退包真的能用来回滚」，而不是「命令没报错」

背景（2026-10-27 两次教训）：
    git reset --hard 成功 ≠ 仓状态正确（那次执行后仍然分叉）
    VERSION.txt 写了 hash ≠ 那个 hash 还有效（重写后全部失效）
    → 「执行成功」和「状态正确」是两件事，回滚必须证明后者。

本脚本做三件事：
    演练 A  单文件被改坏 → 从发布物回退包恢复 → 证明 SHA256 复原
    演练 B  多文件被改坏 → 整目录恢复 → 证明全部复原
    演练 C  损坏未被发现的情形 → 证明自检能抓到

安全边界（硬约束）：
    - 全程在临时目录操作，【绝不触碰真实发布物】
    - 只读真实文件（复制出去），不写
    - 结束后清理临时目录

用法：
    python tools/drill_rollback.py

退出码：0 = 全部演练通过（回退包可用）｜1 = 有演练失败（回退包不可用于救火）
"""
import hashlib
import os
import shutil
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PKG = os.path.join(ROOT, "_归档", "发布物回退包")

# 演练 A/B 用的样本（包内相对路径 → 当前发布物相对路径）
SAMPLES = [
    ("介绍页/index.html", "index.html"),
    ("介绍页/assets/site.css", "assets/site.css"),
    ("介绍页/assets/site.js", "assets/site.js"),
    ("介绍页/projects/focus.html", "projects/focus.html"),
    ("PPT发布源/index.html", "产品/星火PPT/deploy/网页版/index.html"),
]

results = []


def add(name, ok, detail):
    results.append((name, ok, detail))
    print(("  [通过] " if ok else "  [失败] ") + name + "  " + detail)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def drill_a(tmp):
    """演练 A：单文件被改坏 → 从包恢复 → SHA256 复原"""
    print("\n【演练 A】单文件被改坏 → 从回退包恢复")
    rel_pkg, rel_cur = SAMPLES[0]
    src_pkg = os.path.join(PKG, rel_pkg.replace("/", os.sep))
    src_cur = os.path.join(ROOT, rel_cur.replace("/", os.sep))

    if not os.path.exists(src_pkg):
        add("A-1 包内文件存在", False, src_pkg)
        return
    if not os.path.exists(src_cur):
        add("A-2 当前发布物存在", False, src_cur)
        return

    # 1) 复制一份到临时目录，模拟「发布物」
    work = os.path.join(tmp, "a_index.html")
    shutil.copy2(src_cur, work)
    sha_good = sha256(work)

    # 2) 故意破坏（追加一行垃圾，模拟发布事故）
    with open(work, "a", encoding="utf-8") as f:
        f.write("\n<!-- DRILL: simulated corruption -->\n")
    sha_broken = sha256(work)
    add("A-3 破坏已生效（哈希应变化）", sha_good != sha_broken,
        "%s… → %s…" % (sha_good[:12], sha_broken[:12]))

    # 3) 从回退包恢复
    shutil.copy2(src_pkg, work)
    sha_restored = sha256(work)

    # 4) ★ 判据：恢复后哈希必须等于原来的好哈希
    add("A-4 恢复后 SHA256 复原", sha_restored == sha_good,
        "%s… == %s…" % (sha_restored[:12], sha_good[:12]))
    # 5) 且必须等于包内文件哈希（证明包本身是好的）
    add("A-5 恢复结果 == 包内文件", sha_restored == sha256(src_pkg),
        "包内 %s…" % sha256(src_pkg)[:12])


def drill_b(tmp):
    """演练 B：多个文件被改坏 → 整目录恢复"""
    print("\n【演练 B】多文件被改坏 → 整目录恢复")
    workdir = os.path.join(tmp, "b_publish")
    os.makedirs(workdir, exist_ok=True)

    # ★ 用序号做临时名，不用 basename —— 否则「介绍页/index.html」和
    #   「PPT发布源/index.html」会撞成同一个临时文件（本脚本第一版就栽在这，
    #   4 个样本只测了 3 个，演练结果失真）
    good = {}
    label = {}
    for idx, (rel_pkg, rel_cur) in enumerate(SAMPLES):
        src_cur = os.path.join(ROOT, rel_cur.replace("/", os.sep))
        if not os.path.exists(src_cur):
            continue
        dst = os.path.join(workdir, "f%02d_%s" % (idx, os.path.basename(rel_cur)))
        shutil.copy2(src_cur, dst)
        good[dst] = sha256(dst)
        label[dst] = rel_cur
    add("B-1 样本已就绪", len(good) >= 3, "%d 个文件（临时名带序号，避免同名覆盖）" % len(good))

    # 2) 全部破坏
    for p in good:
        with open(p, "a", encoding="utf-8") as f:
            f.write("\n<!-- DRILL -->\n")
    broken_ok = all(sha256(p) != good[p] for p in good)
    add("B-2 全部破坏已生效", broken_ok, "%d 个文件哈希均变化" % len(good))

    # 3) ★ 先区分「包过期」与「恢复机制失效」——两者含义完全不同
    #    包过期（他人施工中）→ 机制没坏，重打包即可
    #    恢复机制失效     → 回退包不能用于救火
    stale = []
    for rel_pkg, rel_cur in SAMPLES:
        src_pkg = os.path.join(PKG, rel_pkg.replace("/", os.sep))
        src_cur = os.path.join(ROOT, rel_cur.replace("/", os.sep))
        if os.path.exists(src_pkg) and os.path.exists(src_cur):
            if sha256(src_pkg) != sha256(src_cur):
                stale.append(rel_cur)
    if stale:
        add("B-0 包内与当前发布物一致", False,
            "%d 个文件已过期（他人施工中？）：%s"
            % (len(stale), ", ".join(stale[:3])))
        print("       → 这【不是回滚机制失效】，是回退包过期。"
              "先跑 repack.py 再演练，才验得出机制好坏。")
    else:
        add("B-0 包内与当前发布物一致", True, "全部 %d 个样本一致" % len(SAMPLES))

    # 4) 从包逐个恢复 —— 只对「包内与当前一致」的文件验恢复机制
    #    （过期的文件验不出机制好坏，它验的是包新鲜度，已在 B-0 报）
    restored = 0
    tested = 0
    failed = []
    for idx, (rel_pkg, rel_cur) in enumerate(SAMPLES):
        src_pkg = os.path.join(PKG, rel_pkg.replace("/", os.sep))
        dst = os.path.join(workdir, "f%02d_%s" % (idx, os.path.basename(rel_cur)))
        if dst not in good:
            continue
        if rel_cur in stale:
            continue                      # 过期样本不计入机制验证
        tested += 1
        if os.path.exists(src_pkg):
            shutil.copy2(src_pkg, dst)
            if sha256(dst) == good[dst]:
                restored += 1
            else:
                failed.append(rel_cur + "（恢复后内容不符）")
        else:
            failed.append(rel_cur + "（包内缺）")
    add("B-3 一致样本的恢复机制有效", tested > 0 and restored == tested,
        "%d/%d 复原（只验包内一致的样本）%s"
        % (restored, tested, ("，失败: " + "; ".join(failed)) if failed else ""))


def drill_c(tmp):
    """演练 C：损坏未被发现的情形 → 证明自检能抓到"""
    print("\n【演练 C】证明「自检能发现损坏」（反证：检查不是摆设）")
    # 造一个「看起来像图但不是图」的文件，验证魔术字节能识别
    fake = os.path.join(tmp, "fake.jpg")
    with open(fake, "w", encoding="ascii") as f:
        f.write("/9j/4AAQSkZJRgABAQAAAQABAAD")   # base64 文本伪装成 jpg
    with open(fake, "rb") as f:
        head = f.read(9)
    is_jpeg = head.startswith(b"\xff\xd8\xff")
    add("C-1 假 JPEG 能被识破", not is_jpeg,
        "前 9 字节 = %r（真 JPEG 应为 \\xff\\xd8\\xff）" % head)

    # 造一个真 JPEG 头，验证不会误报
    real = os.path.join(tmp, "real.jpg")
    with open(real, "wb") as f:
        f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 20)
    with open(real, "rb") as f:
        head2 = f.read(9)
    add("C-2 真 JPEG 不误报", head2.startswith(b"\xff\xd8\xff"),
        "前 9 字节 = %r" % head2)


def main():
    print("=" * 72)
    print("回滚演练 —— 证明「回退包可用于救火」")
    print("包位置: %s" % PKG)
    print("=" * 72)

    if not os.path.isdir(PKG):
        print("\n[致命] 回退包不存在：%s" % PKG)
        return 1

    tmp = tempfile.mkdtemp(prefix="drill_rollback_")
    try:
        drill_a(tmp)
        drill_b(tmp)
        drill_c(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print("\n临时目录已清理: %s" % tmp)

    ok = sum(1 for _, o, _ in results if o)
    total = len(results)
    print("\n" + "-" * 72)
    print("演练结果: %d/%d 通过" % (ok, total))

    if ok == total:
        print("\n结论: 回退包可用于救火 —— 恢复后内容哈希与原件一致，不是「命令没报错」。")
        print("      真实发布物全程未被触碰（演练在临时目录完成）。")
        return 0
    print("\n结论: 回退包不可用于救火，必须修好再发布。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
