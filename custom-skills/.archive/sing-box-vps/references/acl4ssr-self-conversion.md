# ACL4SSR 自建订阅转换（不依赖第三方转换站）

第三方订阅转换站大多已死或后端老旧——老 subconverter 后端会**静默丢弃** anytls / tuic-v5 / 新协议节点，用户侧表现就是「为什么只有 vmess」（2026-09-25 实锤）。订阅网站「分类规则」的真身 = ACL4SSR 官方转换配置 `Clash/config/ACL4SSR_Online_Full_MultiMode.ini`。自己解析它做转换 = 与转换网站同产物且完全可控。

## 流程
1. 拉官方 ini（raw 被墙，jsdelivr 镜像）：`https://testingcf.jsdelivr.net/gh/ACL4SSR/ACL4SSR@master/Clash/config/ACL4SSR_Online_Full_MultiMode.ini`
2. 解析两类行：`ruleset=<组名>,<url 或 []内联规则>` 与 `custom_proxy_group=<名>\`<类型>\`<成员...>`
3. 规则源全部 raw→testingcf jsdelivr 化；url→rule-provider 映射：behavior（`*Ip*.list`=ipcidr，其余=domain）、interval 86400、path `./ruleset/<名>.list`
4. 组构建：成员 `.*`→全部节点名；`(正则)`→re.search 匹配节点名；`[]X`→组引用；url-test/fallback 组补 `url`(gstatic 204)/`interval`/`tolerance`
5. 落盘后校验链：`yaml.safe_load` 回读 → 组引用无悬空 → 订阅实拉 curl 200 → 全部 provider HEAD 逐个 200

## 组精简：用户只要「国外走代理 / 国内直连」两分法
用户原话：不要 AI/油管之类的细分组，本质上就国外和国内两个。精简时的映射原则 = **按官方各组默认值归边**，不是全归代理：

- **直连侧**（官方组默认 DIRECT/全球直连）：哔哩哔哩、国内媒体、微软Bing/云盘/服务、苹果服务、谷歌FCM、游戏平台、网易音乐 + LocalAreaNetwork/UnBan/ChinaDomain/ChinaCompanyIp/ChinaIp/GoogleCN/Download/SteamCN/ChinaMedia
- **代理侧**（官方组默认节点选择/地区节点）：电报、AI、油管、奈飞、巴哈姆特、国外媒体、ProxyGFWlist
- 精简后 4 组：🚀节点选择(默认♻️自动选择→可切手动/DIRECT)、♻️自动选择(url-test)、🚀手动切换、🎯全球直连(默认DIRECT)
- **末条兜底规则 Stash 用 `MATCH` 不用 `FINAL`**——Stash 老 clash premium 核对 FINAL 直接报错（2026-09-25 用户实测）；`MATCH,🚀 节点选择` 与官方「漏网之鱼→节点选择」等价
- 规则保持官方 ini 原序：ProxyGFWlist(→代理) 在 ChinaDomain(→直连) 之前，google.com 先命中代理

## 坑
- **空地区组**：HK/JP/SG/TW/KR 的正则匹配不到 `[GCP]`/`[AWS]` 节点名 → 组为空。空 url-test 组会让 Stash 拉订阅报错 → 给空组补 `DIRECT` 兜底（组存在不报错；不被规则引用，不影响实际分流）
- **分流走查禁用子串匹配**：`baidu.com in BanProgramAD` 之类的假阳性（广告列表里有含 baidu 的统计域名）；要用 DOMAIN-SUFFIX 后缀匹配语义重查。且走查脚本拉不全大列表（ChinaIp/ChinaMax/ProxyGFWlist 常超时被跳过），走查结果只是参考，**规则顺序才是真相**
- **禁止 per-app 专项规则**（用户明确否决「微信专项」：「明天有其他 App 你还搞专项吗」）：官方库 ChinaDomain+ChinaMedia+GEOIP,CN 已覆盖国内应用，新 App 被 GEOIP,CN 自动兜住；手加专项 = 补丁思维，会被打回
- **微信覆盖实测（2026-09-25 逐条规则实 match）**：`sgshort.wechat.com` 在第 30 条命中 ChinaDomain 的 `DOMAIN-SUFFIX,wechat.com` → 直连；`weixin.qq.com`/`qpic.cn`/`qlogo.cn` 靠 `DOMAIN-SUFFIX,qq.com` 等；ProxyGFWlist 全量 7052 条无一命中微信域（只有 freewechat.com/wechatlawsuit.com 等无关站，且后缀匹配不误伤 wechat.com）→ **回答「微信走代理吗」直接给实 match 结论，别再猜**
- **PyYAML 重写分发 yaml 后必须 grep raw 残留**：GCP 侧用 PyYAML 重写 merged-sub.yaml 时把手工 jsdelivr 化的 rule-provider URL 回退成 raw（peer 自报「重写未回退」是假的，跨机独立实拉抓出 raw=18）。每次 yaml.dump 落盘后 `grep -c raw.githubusercontent` 必须=0
- 各机订阅 key 相互独立（QQG key ≠ GCP key），跨机拉对方订阅先取对方 `/etc/s-box/sub-key`

## Stash 测速「超时」与 UDP 协议诊断口径（2026-09-25）
用户报「AWS 三个端口超 12（秒）」：服务端 5 协议回环全 204、防火墙全放行、UDP 监听正常，但 sing-box 日志 30 分钟内 **0 个来自用户 IP 的 UDP 包**（仅测试自连记录）= 家宽/运营商对国际 UDP 的 QoS 掐死，是客户端路径问题不是配置问题。

- 诊断手法：按协议 grep `inbound/<type>` 计数对比（vless/vmess 有大量成功 vs hy2/tuic 零到达）
- HY2/TUIC 留作备胎（换网络环境可能恢复），主力 = VLESS(443/tcp) + VMESS(2053/tcp)
- ANYTLS(8443/tcp) 也超时 → 可能是 Stash 版本不认 anytls 节点类型（协议较新）
- **「能不能干掉 QoS」的口径**：QoS 在运营商路由器上，服务端/客户端都碰不到，别接这个活；已做的（443 区端口+brutal+TFO）是「绕」，GCP 节点是「绕得更彻底」（Google 骨干被 QoS 程度轻），真质变只有国内入口中转小鸡（9929/CN2 GIA，用户预算极紧未买）。QoS 实测特征：连接 0 错误全天可用（24h 3000+ 连接全成功、中位延迟 242ms），掐的是高峰期带宽不是连通性

## 订阅分发通道与稳定性（2026-09-25）
- **明文 HTTP 订阅在中国↔美西线路上会被运营商/GFW 干扰重置**（服务端 ConnectionReset 日志为证，用户拉订阅请求 24h 零到达服务器）→ QQG 订阅服务本身 1ms 响应无懈可击，是线路问题
- **解法：订阅分发迁到 GCP**（Google 骨干中国直连质量好）——QQG 的 merged-sub 同步到 GCP 的订阅服务，用户 Stash 改拉 GCP URL。**拉订阅走 GCP ≠ 上网走 GCP**：订阅只是菜单，节点流量仍按 server 字段直连各机（用户问过「那我连qqg的节点会走gcp流量吗」——不会）
- 跨机传订阅文件：`hermes peer dm` 传 base64 会被对端打码拒绝 → 改让对端自己 `curl http://QQG订阅URL` 拉取（对端在美西，拉 QQG 的 80 口无障碍），md5 对账
- GCP 分发入口：`http://gcp.eosphor.dpdns.org/merged9k2m?key=<GCP的sub-key>`，现役给用户的就是这条

## AI 纯净出口（2026-09-25 两机部署，灵感源 yding-git/personal-edge-proxy）
核心思想：**入口层（REALITY/端口伪装）与出口层（WARP/固定 SOCKS5）解耦**——前期提速全在卷入口，该仓库提醒出口身份同样重要（机房 IP 段易被 AI 服务风控）。

实现：两机 sb.json `route.rules` 在 sniff 规则后插 `{"domain_suffix":[22个AI域名],"outbound":"warp-out"}`（warp-out 端点两机早已存在，当初给 Telegram 配的）。备份 `/etc/s-box/sb.json.bak-ai-warp`（回退=cp 回去+restart）。客户端/订阅侧零改动。

- AI 域名表：openai.com/chatgpt.com/oaistatic.com/oaiusercontent.com/anthropic.com/claude.ai/claude.com/gemini.google.com/generativelanguage.googleapis.com/aistudio.google.com/copilot.microsoft.com/githubcopilot.com/perplexity.ai/pplx.ai/x.ai/grok.com/api.openai.com/api.anthropic.com/api.x.ai 等
- **验证**：经节点 `curl https://chatgpt.com/cdn-cgi/trace` → `warp=on` + Cloudflare IP（104.28.x）= 出口已换；非 AI 域名（ipinfo.io/json）仍显机房 IP = 分流正确。实测 QQG：104.28.195.192/warp=on vs 直连 50.114.172.17；GCP：104.28.205.253/warp=on。api.ip.sb 经 WARP 会被挡（空响应），换 chatgpt 的 /cdn-cgi/trace
- 用户对 AI 出口的要求：US + 干净（IP 信誉），WARP 出口满足两者
- 终端工具限制：前台命令禁 `&`/nohup 后台化，测试实例用 terminal 的 `background=true` 参数起，测完 ss 确认 0 残留
