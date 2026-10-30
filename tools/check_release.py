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
import time
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

REPOS = [
    ("介绍页", ROOT),
    ("专注Pro", os.path.join(ROOT, "产品", "星火专注Pro", "_gitrepo")),
    ("PPT deploy", os.path.join(ROOT, "产品", "星火PPT", "deploy", "网页版")),
]

ONLINE = [
    ("介绍页首页", "https://beeasy-l.github.io/starspark-trilogy/", 9000, 20000, "星火三部曲"),
    ("第二部入口", "https://beeasy-l.github.io/starspark-trilogy/projects/focus.html", 5000, 40000, "星火专注"),
    ("第三部入口", "https://beeasy-l.github.io/starspark-trilogy/projects/ppt.html", 5000, 40000, "星火PPT"),
    ("第一部入口", "https://beeasy-l.github.io/starspark-trilogy/projects/streak.html", 3000, 40000, "续火花"),
    ("星火PPT 站点", "https://beeasy-l.github.io/starspark-ppt/", 100000, 900000, None),
    ("星火专注Pro 站点", "https://beeasy-l.github.io/starspark-focus/", 50000, 600000, None),
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
skipped = []  # 因网络不可达而未验证的项（≠ 失败）
infos = []    # 已知取舍：看起来是问题，但已裁定接受（≠ 失败，也 ≠ 通过）


def add(level, name, ok, detail=""):
    results.append((level, name, ok, detail))


def add_skip(name, reason):
    """网络不可达：不能判定，也不该算失败"""
    skipped.append((name, reason))


def add_info(name, detail):
    """已知取舍：已由主公/验收官裁定接受，不列为缺陷

    规矩十第④条（2026-10-27 群管立）：
        对于「看起来是问题但已决定接受」的情况，
        不用删检查、也不用强判 PASS，而用 [INFO] 单独登记：
        位置 + 现状 + 裁定 + 理由 + 日期
        目的是阻止后来人重复发现、重复修、重复争论
    """
    infos.append((name, detail))


# 网络不可达的错误特征（我的机器连不上 ≠ 站点坏了）
NETWORK_ERROR_MARKERS = (
    "getaddrinfo failed",
    "Name or service not known",
    "Temporary failure in name resolution",
    "Connection was reset",
    "Connection refused",
    "WinError 10051",
    "WinError 10060",
    "WinError 11001",
    "timed out",
    "No route to host",
    "Network is unreachable",
)


def is_network_error(exc) -> bool:
    s = str(exc)
    return any(m.lower() in s.lower() for m in NETWORK_ERROR_MARKERS)


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

        # fsck —— ★ 单次失败不直接判 P0（2026-10-28 19:10 实测修正）
        #   实测：PPT deploy 仓在 @星火PPT 施工写入期间，fsck 报了 1 次
        #   「missing/broken」，1 秒后连测 3 次全部干净、门禁 P0 自动消失。
        #   → 那是读到了「他人写入中的瞬时状态」，不是真的对象库损坏。
        #   判据应能区分「瞬时」与「稳定」：失败必须复测 2 次仍失败才算 P0。
        bad = False
        attempts = 0
        for attempt in range(3):
            attempts = attempt + 1
            code, out, err = run_git(repo, ["fsck", "--no-progress"], timeout=60)
            bad = bool(re.search(r"missing|broken link", (out or "") + (err or "")))
            if not bad:
                break
            if attempt < 2:
                time.sleep(1.0)
        if bad:
            add("P0", "%s fsck" % label, False,
                "连续 %d 次报 missing/broken — 对象库真损坏，需用远端 clone 替换 .git" % attempts)
        elif attempts > 1:
            add("P0", "%s fsck" % label, True,
                "第 1 次报错、第 %d 次干净 —— 疑似他人写入的瞬时状态，非真损坏" % attempts)
        else:
            add("P0", "%s fsck" % label, True, "对象库完好")

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

        # 未提交改动 —— 两路都查（2026-10-27 18:20 采纳 @星火专注Pro 的发现 + @群管理 补的缺口）
        #
        # 旧判据（已废弃）：git status --porcelain 非空 → 有未提交改动
        #   废弃原因：迁移/复制改 mtime + core.autocrlf=true 会让索引 stat 缓存与磁盘对不上，
        #            status 报 M 但 git diff 说无差异（git 的 "racy clean"）→ 假阳性
        #
        # 新判据（两路都查，各查各的）：
        #   git diff --quiet          → 只看「已跟踪文件」的内容有没有真变化
        #   git ls-files --others     → 只看「未跟踪新文件」（git diff 看不见这类！）
        #   两条缺一：只用 diff 会漏掉忘记 add 的新文件；只用 status 会误报幻影 M
        code_tracked, _, _ = run_git(repo, ["diff", "--quiet"])
        dirty_tracked = (code_tracked != 0)   # 0 = 无差异

        code_cached, _, _ = run_git(repo, ["diff", "--cached", "--quiet"])
        dirty_staged = (code_cached != 0)

        _, untracked_raw, _ = run_git(repo, ["ls-files", "--others", "--exclude-standard"])
        untracked = [x for x in untracked_raw.splitlines() if x.strip()]

        # 再看 status，仅用于诊断「stat 过期」这种幻影
        _, status_raw, _ = run_git(repo, ["status", "--porcelain"])
        status_lines = [x for x in status_raw.splitlines() if x.strip()]
        # status 里有 M/A/D 但 diff 无差异的，就是幻影
        phantom = (not dirty_tracked) and (not dirty_staged) and bool(status_lines) and not untracked

        if dirty_tracked or dirty_staged:
            parts = []
            if dirty_tracked:
                parts.append("工作区有真实改动")
            if dirty_staged:
                parts.append("暂存区有未提交")
            if untracked:
                parts.append("另有 %d 个未跟踪新文件" % len(untracked))
            add("P1", "%s 工作区干净" % label, False, "；".join(parts))
        elif untracked:
            names = ", ".join(untracked[:5]) + (" …" if len(untracked) > 5 else "")
            add("P1", "%s 工作区干净" % label, False,
                "%d 个未跟踪新文件（git diff 看不见这类）：%s" % (len(untracked), names))
        elif phantom:
            # 内容没变，只是索引 stat 过期 —— 报出来但不当作「未提交」
            add("P1", "%s 索引 stat" % label, False,
                "索引 stat 过期（迁移/复制 + autocrlf 导致），实际零改动；"
                "建议 git add 刷新，非真改动")
        else:
            add("P1", "%s 工作区干净" % label, True, "无未提交改动，无未跟踪文件")


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

        # ★ 不只 grep 符号：符号存在 ≠ 真的调用了
        #   按「定义 / 实例化 / 调用」三级判定
        has_def = "function createAnim" in content
        has_call = bool(re.search(r"createAnim\s*\(", content))
        has_mount = bool(re.search(r"\.mount\s*\(", content))
        has_duck_hook = "onPageEnter" in content

        if has_def and has_call and has_mount:
            level = "已接入（定义+实例化+mount 三级齐全）"
            if has_duck_hook:
                level += "，且含 onPageEnter 回调"
            add("P1", "anim.js 接入", True, level)
        elif has_def:
            # 只找到定义：可能是内联了模块但没接线
            print("       ⚠ 找到 createAnim 定义，但缺实例化或 mount 调用")
            print("         → 模块可能已内联但未接线；发布说明不能写「动画已完成」")
            add("P1", "anim.js 接入", True,
                "仅内联未接线（定义有，调用/mount 缺）")
        else:
            print("       ⚠ 未找到 createAnim —— 模块已交付但未启用")
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


# ---------------- P0-4 线上可访问（验内容，不只验状态码） ----------------
def check_online():
    print("\n【P0-4】线上站点：状态码 + 体积 + **内容特征**")
    for name, url, lo, hi, must_contain in ONLINE:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "xh-release-check/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                code = resp.status
                body = resp.read()
            size = len(body)

            if code != 200:
                add("P0", name, False, "HTTP %d" % code)
                continue

            if not (lo <= size <= hi):
                add("P1", name, False,
                    "HTTP 200 但体积 %s 超出期望 %s–%s"
                    % (human(size), human(lo), human(hi)))
                continue

            # ★ 关键：验内容，不只看状态码 + 体积
            try:
                text = body.decode("utf-8", errors="replace")
            except Exception:
                text = ""

            has_html = ("<html" in text.lower()) or ("<!doctype" in text.lower())
            has_title = "<title" in text.lower()

            if not has_html:
                add("P0", name, False,
                    "HTTP 200 + %s 但**不是 HTML**（可能是错误页）" % human(size))
                print("       → 状态码和体积都能骗人，这一条是本轮新增的内容检查")
                continue
            if not has_title:
                add("P1", name, False, "是 HTML 但无 <title>，页面可能不完整")
                continue

            # 特征串校验（可选）
            if must_contain:
                if must_contain in text:
                    add("P0", name, True,
                        "HTTP 200, %s, HTML+title ✅（含「%s」）"
                        % (human(size), must_contain))
                else:
                    add("P1", name, False,
                        "HTTP 200 且是 HTML，但**未含特征串「%s」**——可能是旧版或错误页"
                        % must_contain)
            else:
                add("P0", name, True, "HTTP 200, %s, HTML+title ✅" % human(size))

        except Exception as e:
            if is_network_error(e):
                add_skip(name, "网络不可达：%s" % str(e)[:70])
            else:
                add("P0", name, False, "不可访问: %s" % str(e)[:80])
                print("       → 若刚 push，等 2 分钟再试")


# ---------------- P0-5 分享卡：URL + 图片内容双重检查 ----------------
# magic bytes：只看 HTTP 200 不够，必须验内容是图片
MAGIC = {
    b"\xff\xd8\xff": "JPEG",
    b"\x89PNG\r\n\x1a\n": "PNG",
    b"GIF87a": "GIF",
    b"GIF89a": "GIF",
    b"RIFF": "WebP(RIFF)",
}


def sniff_image(head_bytes):
    """返回 (是否图片, 类型名或误判说明)"""
    for magic, name in MAGIC.items():
        if head_bytes.startswith(magic):
            return True, name
    head = head_bytes[:12]
    # base64 文本的典型开头：/9j/4AAQ（JPEG 的 base64）
    if head.startswith(b"/9j/") or head.startswith(b"iVBOR") or head.startswith(b"R0lGOD"):
        return False, "是 base64 文本，不是图片二进制"
    try:
        text = head.decode("ascii", errors="replace")
        if all(32 <= ord(c) < 127 for c in text):
            return False, "是文本内容，不是图片二进制"
    except Exception:
        pass
    return False, "未知格式（前 %d 字节: %r）" % (len(head), head[:8])


def fetch_head(url, nbytes=16, timeout=20):
    """只读前 nbytes 字节 + 状态码 + content-type + 总长"""
    req = urllib.request.Request(url, headers={"User-Agent": "xh-release-check/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = resp.status
        ctype = resp.headers.get("Content-Type", "")
        clen = resp.headers.get("Content-Length")
        head = resp.read(nbytes)
    return status, ctype, (int(clen) if clen and clen.isdigit() else None), head


def check_share_card():
    print("\n【P0-5】分享卡：og:image 指向 + 图片内容双重检查")
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
        print("       og:image = %s" % url)

        # ① 协议与主机检查
        #    2026-10-27 18:12 群管理经测速改判：接受服务端托管（方案 B）
        #    实测：服务器 58–86 ms vs Pages 1099–1385 ms，Pages 慢 15 倍
        #    2026-10-27 18:41 群管进一步裁定：这是「已知取舍」，用 [INFO] 登记，
        #    不列为缺陷（否则每次门禁都红，会逼人删掉检查）
        is_ip_http = bool(re.match(r"http://\d+\.\d+\.\d+\.\d+", url))
        is_http_nonip = url.startswith("http://")
        if is_ip_http:
            add_info("og:image 主机",
                     "裸 IP + HTTP（自建服务器）｜接受（验收官测速改判 2026-10-27）"
                     "｜服务器 58-86ms vs Pages 1099-1385ms；已登记外部依赖 + 有 Pages 兜底")
        elif is_http_nonip:
            add("P1", "og:image 主机", False, "HTTP 非 HTTPS —— 微信可能拒绝抓取")
        else:
            add("P0", "og:image 主机", True, "HTTPS 域名")

        # ② ★ 图片内容检查（本轮新增，正是先前判错的原因）
        #    只看 HTTP 200 不够：坏文件也能返回 200
        try:
            status, ctype, clen, head = fetch_head(url, 16, 25)
            ok_img, kind = sniff_image(head)
            size_note = human(clen) if clen else "未知"
            if status != 200:
                add("P0", "og:image 内容", False, "HTTP %d" % status)
            elif not ok_img:
                add("P0", "og:image 内容", False,
                    "**坏文件**：HTTP 200 但 %s（%s）" % (kind, size_note))
                print("       → 状态码 200 不代表内容是图片。这正是 2026-10-27 判错两次的根因")
                print("       → 修复：换真图后重新推送，再验前 2 字节 == FF D8")
            elif "image" not in ctype.lower():
                add("P1", "og:image 内容", False,
                    "是 %s 但 content-type=%s" % (kind, ctype))
            else:
                add("P0", "og:image 内容", True,
                    "%s, %s, %s ✅（magic bytes 正确）" % (kind, size_note, ctype))
        except Exception as e:
            if is_network_error(e):
                add_skip("og:image 内容", "网络不可达：%s" % str(e)[:70])
            else:
                add("P0", "og:image 内容", False, "取不到: %s" % str(e)[:70])

        # ③ twitter:image 一致性
        mt = re.search(r'name="twitter:image"\s+content="([^"]+)"', content)
        if mt:
            same = mt.group(1) == url
            add("P1", "twitter:image 一致", same,
                "与 og:image 相同" if same else "与 og:image 不同: %s" % mt.group(1))
    except Exception as e:
        add("P0", "og:image", False, str(e))


# ---------------- P1-5 版本口径一致性 ----------------
def read_first(pattern, path, group=1, flags=0):
    """从文件里读第一个匹配，返回捕获组或 None（只读）"""
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        m = re.search(pattern, content, flags)
        return m.group(group).strip() if m else None
    except Exception:
        return None


def check_version_consistency():
    """版本口径：产品源码 logver == 介绍页声明值

    设计原则（《发布操作方案》3-④）：
        真值取自【产品源码】，不取自【介绍页文案】。
        文案是人工登记的，会忘会错；源码是构建产物，是唯一真相。
        群管 2026-10-28 11:59 定同一口径（方案甲：以源码 logver 为准）。

    重要：本检查【只读不写】。发现不一致只报 P1，不代改文案 ——
          文案归属各产品作者（群管 12:09 明确 L87 归介绍页开发）。
    """
    print("\n【P1-5】版本口径三处一致（真值取自产品源码，只读不改）")

    svc = os.path.join(ROOT, "产品")
    rows = [
        # (名称, 真值来源路径, 真值正则, 文案来源路径, 文案正则)
        ("第一部 续火花",
         os.path.join(svc, "星火续火花", "②程序文件", "core", "backup.py"),
         r'APP_VERSION\s*=\s*"([^"]+)"',
         os.path.join(ROOT, "index.html"),
         r'第一部[^<]*?V([0-9][0-9.]*)'),
        ("第二部 专注Pro",
         os.path.join(svc, "星火专注Pro", "_gitrepo", "index.html"),
         r'<div class="logver">\s*(v[0-9][0-9.]*)',
         os.path.join(ROOT, "projects", "focus.html"),
         r'第二部[^<]*?[vV]([0-9][0-9.]*)'),
        ("第三部 星火PPT",
         os.path.join(svc, "星火PPT", "deploy", "网页版", "index.html"),
         r'<div class="logver">\s*(V[0-9][0-9.]*)',
         os.path.join(ROOT, "projects", "ppt.html"),
         r'第三部[^<]*?V([0-9][0-9.]*)'),
    ]

    # ★ 2026-10-28 18:35 补全（群管 R15 指出「只覆盖介绍页」）：
    #   上面 3 项只查了「首页第一部徽章 + 两个子页头部」，
    #   漏了 index.html 的第二/三部徽章、以及 focus-start.html 的版本声明。
    #   全部「只读不改」。
    rows.append((
        "首页徽章·第二部",
        os.path.join(svc, "星火专注Pro", "_gitrepo", "index.html"),
        r'<div class="logver">\s*(v[0-9][0-9.]*)',
        os.path.join(ROOT, "index.html"),
        r'第二部[^<]*?[vV]([0-9][0-9.]*)'))
    rows.append((
        "首页徽章·第三部",
        os.path.join(svc, "星火PPT", "deploy", "网页版", "index.html"),
        r'<div class="logver">\s*(V[0-9][0-9.]*)',
        os.path.join(ROOT, "index.html"),
        r'第三部[^<]*?V([0-9][0-9.]*)'))
    rows.append((
        "专注Pro启动页",
        os.path.join(svc, "星火专注Pro", "_gitrepo", "index.html"),
        r'<div class="logver">\s*(v[0-9][0-9.]*)',
        os.path.join(ROOT, "projects", "focus-start.html"),
        r'第二部[^<]*?[vV]([0-9][0-9.]*)'))
    # ★ 第 3 个覆盖漏洞（2026-10-28 19:00 补，由 @介绍页开发 18:23 的补充暴露）
    #   focus-app/index.html:955 也是版本声明位置，此前完全没被扫到。
    #   它是「零入口但线上 200 可达」的陈旧副本（v1.2.2 vs 真值 v1.3.2）。
    rows.append((
        "专注Pro内嵌版",
        os.path.join(svc, "星火专注Pro", "_gitrepo", "index.html"),
        r'<div class="logver">\s*(v[0-9][0-9.]*)',
        os.path.join(ROOT, "projects", "focus-app", "index.html"),
        r'<div class="logver">\s*(v[0-9][0-9.]*)'))

    for name, real_path, real_re, site_path, site_re in rows:
        real = read_first(real_re, real_path)
        site = read_first(site_re, site_path)
        if not real:
            add("P1", "%s 版本真值" % name, False,
                "读不到源码版本（%s）" % os.path.basename(real_path))
            continue
        if not site:
            add("P1", "%s 介绍页版本" % name, False,
                "读不到介绍页声明（%s）" % os.path.basename(site_path))
            continue
        if real.lstrip("vV") == site.lstrip("vV"):
            add("P1", "%s 版本口径" % name, True, "源码 %s = 文案 %s ✅" % (real, site))
        else:
            add("P1", "%s 版本口径" % name, False,
                "源码 %s ≠ 文案 %s —— 文案没跟上产品（归属产品作者改）" % (real, site))
            print("       → 「人工登记会忘会错」的典型。只报不改，改由文案作者做")


# ---------------- INFO 已知取舍登记 ----------------
def check_known_tradeoffs():
    """看起来是问题、但已裁定接受的情况 —— 用 [INFO] 登记，不判 PASS/FAIL

    目的（规矩十第④条）：阻止后来人重复发现、重复修、重复争论。
    """
    print("\n【INFO】已知取舍登记（不列缺陷，修改前须经主公/验收官同意）")

    # ① streak.html 后台按钮 → HTTP 裸 IP
    p = os.path.join(ROOT, "projects", "streak.html")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                content = f.read()
            m = re.search(r"http://(\d+\.\d+\.\d+\.\d+)(:\d+)?", content)
            if m:
                add_info("streak.html 后台按钮",
                         "指向 HTTP 裸 IP（%s:%s）｜保持现状（主公 2026-10-27）"
                         "｜性质：部署者自用入口，非访客功能；"
                         "访客误入遇「不安全+令牌错误」为已知代价，不列为缺陷"
                         % (m.group(1), (m.group(2) or "").lstrip(":") or "80"))
        except Exception:
            pass
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
        check_version_consistency()
        check_known_tradeoffs()
    if not offline_only:
        # og:image 检查要联网拉图验 magic bytes，因此归 online 分支
        # （offline-only 时跳过，避免误报"取不到"）
        check_share_card()
        check_online()

    # ---- 汇总 ----
    print("\n" + "=" * 72)
    p0_fail = [r for r in results if r[0] == "P0" and not r[2]]
    p1_fail = [r for r in results if r[0] == "P1" and not r[2]]
    total = len(results)

    for level, name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        print("  [%s][%s] %-38s %s" % (mark, level, name, detail))

    # 网络不可达的项单独列出 —— 它们既不是通过，也不是失败
    if skipped:
        print()
        print("  ── 未验证（网络不可达，不判定通过/失败）──")
        for name, reason in skipped:
            print("  [SKIP]    %-38s %s" % (name, reason))

    # 已知取舍单独列出 —— 看起来是问题，但已裁定接受
    if infos:
        print()
        print("  ── 已知取舍（非缺陷，修改前须经主公/验收官同意）──")
        for name, detail in infos:
            print("  [INFO]    %-38s %s" % (name, detail))

    print("-" * 72)
    print("合计 %d 项：P0 阻塞 %d 项未过 / P1 应有 %d 项未过 / 未验证 %d 项 / 已知取舍 %d 项"
          % (total, len(p0_fail), len(p1_fail), len(skipped), len(infos)))

    if skipped:
        print()
        print("⚠️  有 %d 项因网络不可达未验证。" % len(skipped))
        print("   这些项**不能算通过**，也**不是失败** —— 是「没量到」。")
        print("   发布前请在网络正常时重跑一次，确认它们真的通过。")
        print("   判据依据：我连不上 ≠ 站点坏了。把前者当后者报，会制造假阻塞。")

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
    if skipped:
        # 全绿但有未验证项 → 不能宣称「全部通过」
        print("\n✅ 已检查项全部通过，但有 %d 项未验证（网络）。" % len(skipped))
        print("   网络恢复后请重跑，再宣布「门禁全绿」。")
        return 2

    print("\n✅ 全部通过，可发布。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
