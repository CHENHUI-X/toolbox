# HY2 Brutal 与服务端提速榨干实录（2026-09-24 QQG）

## AI 纯净出口（2026-09-25 两机部署）

灵感源 = yding-git/personal-edge-proxy：**入口层（REALITY/端口伪装）与出口层（WARP/固定 SOCKS）解耦** —— 提速卷的是入口，出口身份同样重要（机房 IP 段易被 AI 服务风控）。

实现：两机 sb.json 的 `route.rules` 在 sniff 规则后插一条 `{"domain_suffix":[22个AI域名],"outbound":"warp-out"}`（warp-out 端点两机早已存在，当初给 Telegram 配的）。

- AI 域名表：openai.com/chatgpt.com/oaistatic.com/oaiusercontent.com/anthropic.com/claude.ai/claude.com/gemini.google.com/generativelanguage.googleapis.com/aistudio.google.com/copilot.microsoft.com/githubcopilot.com/perplexity.ai/pplx.ai/x.ai/grok.com/api.openai.com/api.anthropic.com/api.x.ai 等
- **验证方法**：经节点 `curl https://chatgpt.com/cdn-cgi/trace` → `warp=on` + Cloudflare IP（104.28.x）= 出口已换；非 AI 域名（ipinfo）仍显机房 IP = 分流正确
- 备份：两机 `/etc/s-box/sb.json.bak-ai-warp`（回退=cp 回去+restart）
- 客户端/订阅侧零改动（出口路由是服务端的事）
- 终端工具限制：前台命令禁 `&`/nohup 后台化，测试实例用 terminal 的 `background=true` 参数起

用户「还是太慢了，有什么邪修方法」时的完整提速路径。前提：tcp-boost 四件套已落地（见 tcp-boost-four-pack.md）。

## 诊断顺序（先证明瓶颈不在服务器）

1. 服务器直连测速：`curl -x none https://speed.cloudflare.com/__down?bytes=10000000` —— QQG 实测 24.3MB/s（194Mbps），服务器满血
2. sysctl 现状核对（bbr+fq / 32MB 缓冲 / notsent_lowat / mtu_probing / slow_start_after_idle=0 全在）
3. 单核 load 0.00 → **结论：剩余瓶颈 100% 在用户↔VPS 国际段线路**，服务端仍可榨的只有下面两项

## 邪修 1：HY2 brutal 暴力模式（最大杠杆，回环实测 6 倍）

sing-box 服务端 hy2 inbound 默认走 BBR；声明带宽后客户端（mihomo/Stash）才用 brutal 按带宽硬发——专为高丢包线路设计。

**服务端** `/etc/s-box/sb.json` hysteria2 inbound 加：

```json
"up_mbps": 100,
"down_mbps": 100,
"ignore_client_bandwidth": false
```

先备份 → `/etc/s-box/sing-box check` → `systemctl restart sing-box`。

**订阅侧**（mihomo wiki 官方格式，⚠️ 必须带单位字符串）：

```yaml
up: "100 Mbps"
down: "100 Mbps"
alpn:
  - h3
```

纯数字 `up: 100` 老解析器不认。效果：同机回环下载 1.85MB/s → 10.98MB/s（**6 倍**）。

## 邪修 2：tcp_fastopen 1→3

`net.ipv4.tcp_fastopen=1` 只开客户端方向，服务端要 3（收发双向）：

```bash
sysctl -w net.ipv4.tcp_fastopen=3
# 持久化进 /etc/sysctl.d/99-tcp-boost.conf（已有该文件就 sed 改值）
```

## 客户端侧开关（告知用户手点）

- Stash VLESS 节点开 mux（网页/聊天场景减握手，小包丢包线路明显）
- HY2 重拉订阅自动继承 up/down=100
- 晚 8-11 点国内 QoS 高峰，大下载错峰

## 天花板要诚实

以上做完后服务端已无可榨（直连 194Mbps 跑满、单核 0.00）。剩余瓶颈 = 家宽↔国际段，唯一质变方案 = 国内入口中转小鸡（9929/CN2，$1-2/月）。用户问「套 CF / WARP 提速？」→ 不提速反慢（CF 免费版中国无节点绕美西 + 只能跑 WS 类协议把 REALITY/HY2/TUIC 全废；WARP 不改变用户↔VPS 段），判定口径详见 qos-evasion-port-migration.md。

## 双机同步纪律（本次踩坑）

- GCP 侧同款改动走 peer dm 下发，但 **必须独立实拉验证**——peer 自报「rule url 仍是 jsdelivr」实为 yaml 重写后回退成 raw 18 条（jsdelivr=0）。自报≠事实，curl 目标机分发端点数 jsdelivr/raw 计数
- **各机订阅 key 不同**（QQG 与 GCP 的 /etc/s-box/sub-key 各自独立），跨机拉订阅用目标机自己的 key，拿 QQG 的 key 拉 GCP 端点 = 401
- GCP 端口**有意不迁**：迁端口要同步动 gcloud 防火墙规则，且 GCP 走 Google 骨干本就少被 QoS，收益不抵风险——跨机同步改动时允许合理的范围裁剪，但要明说
- **peer dm 超时的含义（2026-09-30 补）**：GCP hermes LLM 崩（pydantic_core 损坏）期间 peer dm 直接 timeout 120s——不是网络问题，是 agent turn 起不来。此时跨机同步只能走 SSH 直连（等 GCP 侧 QQG 公钥到位），或把 QQG 分发端点给用户临时替代
