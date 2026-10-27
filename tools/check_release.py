#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
星火三部曲 · 发布检查（自动化部分）

配套文档：文档/规范/发布检查清单.md
用法：
    python tools/check_release.py                # 全量检查
    python tools/check_release.py --online-only  # 只查线上
    python tools/check_release.py --offline-only # 只查本地（不联网）

退出码：
    0 = P0 全过，可发布
    1 = 有 P0 阻塞项，不能发
    2 = 有 P1 问题，可发但需记录

设计原则：
    - 只读，不修改任何文件、不 push、不 commit
    - 联网项失败不影响本地项结论（分节报告）
    - 每项输出「期望 vs 实测」，便于他人复核
"""
import os
import re
import subprocess
import sys
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

REPOS = [
    ("介绍页", ROOT),
    ("专注Pro", os.path.join(ROOT, "产品", "星火专注Pro", "_gitrepo")),
    ("PPT deploy", os.path.join(ROOT, "产品", "星火PPT", "deploy", "网页版")),
]

ONLINE = [
    ("介绍页首页", "https://beeasy-l.github.io/starspark-trilogy/", 9000, 20000),
    ("第二部入口", "https://beeasy-l.github.io/starspark-trilogy/projects/focus.html", 5000, 40000),
    ("第三部入口", "https://beeasy-l.github.io/starspark-trilogy/projects/ppt.html", 5000, 40000),
    ("第一部入口", "https://beeasy-l.github.io/starspark-trilogy/projects/streak.html", 3000, 40000),
    ("星火PPT 站点", "https://beeasy-l.github.io/starspark-ppt/", 100000, 900000),
    ("星火专注Pro 站点", "https://beeasy-l.github.io/starspark-focus/", 50000, 600000),
]

# 本地发布物：路径 -> 允许的体积区间（字节）
LOCAL_FILES = [
    ("index.html", 5000, 60000),
    ("projects/focus.html", 5000, 60000),
    ("projects/ppt.html", 5000, 60000),
    ("projects/streak.html", 3000, 60000),
    ("projects/focus-start.html", 3000, 60000),
    ("projects/focus-app/index.html", 100000, 600000),
    ("assets/site.css", 10000, 60000),
    ("assets/site.js", 10000, 60000),
    ("产品/星火PPT/static/index.html", 200000, 2000000),
    ("产品/星火PPT/deploy/网页版/index.html", 200000, 2000000),
    ("产品/星火PPT/deploy/网页版/music.mp3", 5000000, 20000000),
    ("产品/星火专注Pro/_gitrepo/index.html", 100000, 600000),
]

results = []  # (level, name, ok, detail)


def add(level, name, ok, detail=""):
    results.append((level, name, ok, detail))


def run_git(repo, args, timeout=20):
    try:
        out = subprocess.run(
            ["git", "-C", repo] + args,
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        return out.returncode, (out.stdout or "").strip(), (out.stderr or "").strip()
    except Exception as e:
        return -1, "", str(e)


def human(n):
    if n >= 1024 * 1024:
        return "%.1f MB" % (n / 1024 / 1024)
    return "%.1f KB" % (n / 1024)


# ---------------- P0-1 git 健康与同步 ----------------
def check_git():
    print("\n【P0-1】三个 git 仓：健康 + 不分叉")
    for label, repo in REPOS:
        if not os.path.isdir(os.path.join(repo, ".git")):
            add("P0", "%s 仓存在" % label, False, "找不到 .git")
            continue

        # fsck
        code, out, err = run_git(repo, ["fsck", "--no-progress"], timeout=60)
        bad = bool(re.search(r"missing|broken link", (out or "") + (err or "")))
        add("P0", "%s fsck" % label, not bad,
            "对象库完好" if not bad else "出现 missing/broken — 需用远端 clone 替换 .git")

        # 同步状态
        run_git(repo, ["fetch", "origin"], timeout=60)
        code, out, _ = run_git(repo, ["rev-list", "--left-right", "--count", "HEAD...origin/main"])
        if code != 0 or not out:
            add("P0", "%s 同步检查" % label, False, "无法取得 origin/main（可能无远端）")
            continue
        parts = out.split()
        if len(parts) == 2:
            ahead, behind = int(parts[0]), int(parts[1])
            if ahead == 0 and behind == 0:
                add("P0", "%s 同步" % label, True, "0/0 已同步")
            elif behind > 0 and ahead > 0:
                add("P0", "%s 同步" % label, False,
                    "**分叉** 本地领先 %d / 远端领先 %d —— 先判断哪边是最终版" % (ahead, behind))
            elif ahead > 0:
                add("P1", "%s 同步" % label, False, "本地领先 %d 未推送" % ahead)
            else:
                add("P1", "%s 同步" % label, False, "远端领先 %d，需 pull --ff-only" % behind)
        else:
            add("P0", "%s 同步检查" % label, False, "输出异常: %s" % out)

        # 未提交改动
        code, out, _ = run_git(repo, ["status", "--short"])
        n = len([l for l in out.splitlines() if l.strip()])
        add("P1", "%s 工作区干净" % label, n == 0,
            "无未提交改动" if n == 0 else "%d 项未提交" % n)


# ---------------- P0-2 回退包一致 ----------------
def check_rollback():
    print("\n【P0-2】发布物与回退包一致")
    script = os.path.join(ROOT, "tools", "check_rollback.py")
    if not os.path.exists(script):
        add("P0", "回退包自检脚本", False, "tools/check_rollback.py 不存在")
        return
    try:
        out = subprocess.run(
            [sys.executable, script],
            capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",
        )
        txt = (out.stdout or "") + (out.stderr or "")
        m = re.search(r"合计:\s*一致\s*(\d+)\s*\|\s*过期\s*(\d+)\s*\|\s*缺失\s*(\d+)", txt)
        if m:
            same, expired, miss = map(int, m.groups())
            ok = (expired == 0 and miss == 0)
            add("P0", "回退包一致", ok,
                "一致 %d / 过期 %d / 缺失 %d" % (same, expired, miss))
            if not ok:
                print("       → 处置: python _归档/发布物回退包/repack.py")
        else:
            add("P0", "回退包自检", out.returncode == 0, "exit=%d" % out.returncode)
    except Exception as e:
        add("P0", "回退包自检", False, str(e))


# ---------------- P0-3 本地发布物存在且体积合理 ----------------
def check_local_files():
    print("\n【P0-3】本地发布物：存在 + 体积合理")
    for rel, lo, hi in LOCAL_FILES:
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.exists(p):
            add("P0", rel, False, "文件不存在")
            continue
        size = os.path.getsize(p)
        ok = lo <= size <= hi
        add("P0" if ok else "P1", rel, ok,
            "%s（期望 %s–%s）" % (human(size), human(lo), human(hi)))


# ---------------- P1-1 HTML 结构 ----------------
def check_html():
    print("\n【P1-1】介绍页 HTML 结构")
    script = os.path.join(ROOT, "tools", "check_html.py")
    if not os.path.exists(script):
        add("P1", "HTML 检查脚本", False, "tools/check_html.py 不存在")
        return
    try:
        out = subprocess.run(
            [sys.executable, script],
            capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",
        )
        txt = (out.stdout or "") + (out.stderr or "")
        ok = out.returncode == 0
        summary = ""
        for line in txt.splitlines():
            if "全部通过" in line or "问题" in line:
                summary = line.strip()
        add("P1", "HTML 结构", ok, summary or ("exit=%d" % out.returncode))
    except Exception as e:
        add("P1", "HTML 结构", False, str(e))


# ---------------- P1-2 动画模块接入状态（信息项） ----------------
def check_anim():
    print("\n【P1-2】动画模块接入状态（信息项，不算失败）")
    ppt = os.path.join(ROOT, "产品", "星火PPT", "static", "index.html")
    if not os.path.exists(ppt):
        add("P1", "anim.js 接入", False, "PPT 主页面不存在")
        return
    try:
        with open(ppt, encoding="utf-8", errors="replace") as f:
            content = f.read()
        connected = "createAnim" in content
        if connected:
            add("P1", "anim.js 接入", True, "已接入主页面")
        else:
            print("       ⚠ createAnim 0 命中 —— 模块已交付但未启用")
            print("         → 发布说明必须写明「已就绪未启用」，不能写「动画已完成」")
            add("P1", "anim.js 接入", True, "未接入（已知状态，非故障）")
    except Exception as e:
        add("P1", "anim.js 接入", False, str(e))


# ---------------- P1-4 无外部依赖 ----------------
def check_external_deps():
    print("\n【P1-4】发布物无外部依赖（离线承诺）")
    targets = [
        os.path.join(ROOT, "index.html"),
        os.path.join(ROOT, "assets", "site.css"),
        os.path.join(ROOT, "assets", "site.js"),
    ]
    pattern = re.compile(r"fonts\.googleapis|cdn\.|unpkg|jsdelivr|cdnjs", re.I)
    hits = []
    for p in targets:
        if not os.path.exists(p):
            continue
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    if pattern.search(line):
                        hits.append("%s:%d" % (os.path.basename(p), i))
        except Exception:
            pass
    add("P1", "无 CDN 外链", len(hits) == 0, "无" if not hits else "命中: " + ", ".join(hits))


# ---------------- P0-4 线上可访问 ----------------
def check_online():
    print("\n【P0-4】线上站点可访问")
    for name, url, lo, hi in ONLINE:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "xh-release-check/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                code = resp.status
                body = resp.read()
            size = len(body)
            ok = (code == 200) and (lo <= size <= hi)
            add("P0" if ok else "P1", name, ok,
                "HTTP %d, %s（期望 %s–%s）" % (code, human(size), human(lo), human(hi)))
        except Exception as e:
            add("P0", name, False, "不可访问: %s" % str(e)[:80])
            print("       → 若刚 push，等 2 分钟再试")


# ---------------- P0-5 分享卡 ----------------
def check_share_card():
    print("\n【P0-5】分享卡 og:image（待确认项）")
    p = os.path.join(ROOT, "index.html")
    if not os.path.exists(p):
        add("P0", "og:image", False, "index.html 不存在")
        return
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            content = f.read()
        m = re.search(r'property="og:image"\s+content="([^"]+)"', content)
        if not m:
            add("P0", "og:image 存在", False, "未找到 og:image")
            return
        url = m.group(1)
        is_ip_http = bool(re.match(r"http://\d+\.\d+\.\d+\.\d+", url))
        print("       og:image = %s" % url)
        if is_ip_http:
            print("       ⚠ 裸 IP + HTTP 协议 —— 需 @介绍页开发 确认：")
            print("         ① 微信分享能否正常出图（微信通常要求 HTTPS）")
            print("         ② 该服务器下线后分享卡即失效，需要兜底")
            add("P1", "og:image 协议", False, "裸 IP + HTTP，待确认微信兼容性与长期可用性")
        else:
            add("P1", "og:image 协议", True, "非裸 IP")
    except Exception as e:
        add("P0", "og:image", False, str(e))


# ---------------- 主流程 ----------------
def main():
    online_only = "--online-only" in sys.argv
    offline_only = "--offline-only" in sys.argv

    print("=" * 72)
    print("星火三部曲 · 发布检查")
    print("工作根: %s" % ROOT)
    print("=" * 72)

    if not online_only:
        check_git()
        check_rollback()
        check_local_files()
        check_html()
        check_anim()
        check_external_deps()
        check_share_card()
    if not offline_only:
        check_online()

    # ---- 汇总 ----
    print("\n" + "=" * 72)
    p0_fail = [r for r in results if r[0] == "P0" and not r[2]]
    p1_fail = [r for r in results if r[0] == "P1" and not r[2]]
    total = len(results)

    for level, name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        print("  [%s][%s] %-38s %s" % (mark, level, name, detail))

    print("-" * 72)
    print("合计 %d 项：P0 阻塞 %d 项未过 / P1 应有 %d 项未过"
          % (total, len(p0_fail), len(p1_fail)))

    if p0_fail:
        print("\n❌ 有 P0 阻塞项，**不能发布**：")
        for _, name, _, detail in p0_fail:
            print("   - %s：%s" % (name, detail))
        print("\n处置见 文档/规范/发布检查清单.md")
        return 1
    if p1_fail:
        print("\n⚠️  P0 全部通过，可发布；下列 P1 项需记录：")
        for _, name, _, detail in p1_fail:
            print("   - %s：%s" % (name, detail))
        return 2

    print("\n✅ 全部通过，可发布。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
