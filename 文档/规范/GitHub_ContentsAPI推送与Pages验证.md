# 规范 · GitHub Contents API 推送与 Pages 验证

> 适用场景：`github.com:443`（git 协议）不通，但 `api.github.com` 可达时，
> 仍需把发布物推上仓并让 GitHub Pages 生效。
> 实测来源：2026-10-28 星火PPT 全部 6 个提交（P0 修复、anim 接入、星河 v2 等）
> 均经此通道推送并线上验证生效。

---

## 一、判据：先确认走哪条路

```powershell
# 1. git 协议通不通（两条都要试）
git ls-remote --heads origin main                          # 裸 DNS
git -c "http.https://github.com/.proxy=" `
    -c http.curloptResolve=github.com:443:140.82.113.4 `
    ls-remote --heads origin main                          # 绕代理+指 IP

# 2. API 通道通不通
Invoke-WebRequest https://api.github.com/ -TimeoutSec 15   # 200 即可用
```

**2026-10-30 实测结论**：`github.com:443` 全断（代理死 + 直连 21s 超时），
`api.github.com` 200 / 0.64s 活着。**两通道互相独立，一条断不影响另一条。**

### ★ 判据（2026-10-30 18:47 群管栽过、架构师复证）：核远端一律读 api，不许拿 ls-remote FAIL 当证据

`git ls-remote` 走 `github.com:443`。**git 断时它必 FAIL**，此时：

```
✗ 错误推论：ls-remote FAIL  →  「对方没推上去」
✓ 正确做法：api.github.com 直读真实远端 HEAD，再判
```

**核远端一条命令（走活着的 api 通道）**：
```bash
curl -s https://api.github.com/repos/Beeasy-L/starspark-trilogy/branches/main \
  | grep -oE '"sha": "[a-f0-9]{40}"' | head -1
```
> 群管 18:43 就是拿 `ls-remote`（断的）查不到，误判介绍页开发「虚报推送」，
> 18:47 改用 api 直读才发现远端 `44113eef` 真在。**这是「验描述不验对象」的第 6 次**——
> ls-remote 的 FAIL 描述的是「我的通道」，不是「远端的状态」。

### ⚠️ Contents API 的代价：会造成平行历史（架构师 2026-10-30 实测）

API 推送**绕过本地 git**，别人 `fetch` 不到时用 API 推，会造出「内容相同、SHA 不同」的分叉链。

**2026-10-30 18:50 实测到的真实分叉**：
```
远端链  …e1b3a7f4 → 05d9b2b3 → c605e194 → 44113eef   （介绍页开发走 API 推的）
本地链  47dd800 → 75b0777 → 7e9a3c3                  （架构师 git 本地提交）
        ↑ 05d9b2b3/c605e194/44113eef  本地全没有
        ↑ 我的 75b0777「续火花报告」和远端 c605e194 是同内容不同 SHA = 平行
```
**后果**：git 恢复后本地直接 `push` 会被拒（non-fast-forward），`pull` 又会把平行提交合进来变双份。

**规避规则**：
1. **能用 git 等就等 git**（今天下午定的「文档类提交一律等 git」）；
2. **必须用 API 推前**，先 api 读远端 HEAD、确认本地基点 = 远端 HEAD（`curl …/branches/main` 的 sha 要能在本地 `git cat-file -t` 到）；
3. **git 恢复后第一次操作一律 `git fetch` + `git log HEAD..origin/main` 看分叉**，不要直接 push，也不要盲目 pull。


---

## 二、推送步骤（Contents API）

### 1) 取凭据

```powershell
$gitOut = "protocol=https`nhost=github.com`n`n" | git credential fill
$TOK = ($gitOut | Where-Object { $_ -match '^password=' }) -replace '^password=',''
```

- 凭据存在 **Windows 凭据管理器**里，PowerShell 侧的 git 取得到；
- **DSH 自带 bash 里的 git 凭据链是空的**（`credential.helper=` 被置空），
  别在它里面折腾，从外部调 `powershell.exe` 执行。

### 2) GET 拿当前文件 sha（乐观锁，必须）

```powershell
$api = "https://api.github.com/repos/<owner>/<repo>/contents/<path>"
$cur = Invoke-RestMethod -Uri $api -Headers @{
    Authorization = "Bearer $TOK"; Accept = "application/vnd.github+json"; "User-Agent" = "x"
} -Method Get
```

### 3) PUT 推新内容

```powershell
$b64  = [Convert]::ToBase64String([IO.File]::ReadAllBytes($localFile))
$body = @{ message = "提交说明"; content = $b64; branch = "main"; sha = $cur.sha } |
        ConvertTo-Json -Compress
$res = Invoke-RestMethod -Uri $api -Headers $headers -Method Put `
      -Body $body -ContentType "application/json"
$res.commit.sha    # 返回即成功
```

**要点**
- `sha` 不传 = 覆盖式新建，会撞 409；**必须先 GET 再 PUT**；
- 多人并发时 PUT 返回 **409**：说明别人先推了，重新走 GET→PUT；
- 一次请求一个文件；多文件多次，每次重新 GET 拿最新 sha；
- 大文件（>100MB base64 后）不适用，改用 git 通道。

---

## 三、Pages 生效验证（必须做，推完 ≠ 上线）

```powershell
# Pages 构建约 1~2 分钟。轮询 + 时间戳绕 CDN 缓存：
for($i=1;$i -le 8;$i++){
  $a = (Invoke-WebRequest "https://<user>.github.io/<site>/?v=$([DateTime]::Now.Ticks)"
        -UseBasicParsing).Content
  if($a -match "本次改动的特征串"){ "已生效"; break }
  Start-Sleep 12
}
```

**三个坑（都踩过）**：
1. **不加 `?v=` 会命中 CDN 旧缓存**，看半天以为没生效；
2. **只查 HTTP 200 不算过**——要查「本次改动的特征串」（新函数名/新日志标题）；
3. **最强验证是哈希**：下载线上全文算 sha256 与本地比，逐字节一致才算「线上=本地」。

```powershell
(Invoke-WebRequest $url -OutFile live.tmp)
(Get-FileHash live.tmp).Hash -eq (Get-FileHash $localFile).Hash   # True 才算数
```

---

## 四、什么时候用哪条

| 情况 | 用法 |
|---|---|
| `git push` 通 | 正常 git（保留完整提交历史，优先） |
| 443 断、API 通 | **本文的 Contents API**（每个文件一个提交） |
| 两个都断 | 停止推送，报网络故障；**不要**反复重试占时间 |

**Contents API 的代价**：每个文件一次提交，历史比 git 碎；
所以网络恢复后建议 `git fetch` + 对账一次，确认本地与远端内容一致。
