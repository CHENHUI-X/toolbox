# 国内 App 分流覆盖：GEOIP 穿透机制、诊断法与规则库对照

## 机制：为什么 GEOIP,CN 兜不住国内 App 的 CDN 流量

国内大厂（腾讯/阿里/字节等）把大量 CDN 接入点部署在自家国际云上（腾讯云 HK/SG、阿里云国际 SG/US、Cloudflare）。这些域名即使解析也常返回海外 IP，实测例：

- 微信图片/头像：`mmbiz.qpic.cn` → 43.146.x（SG）；`wx.qlogo.cn` → 43.156.x / 101.32.x（SG/HK）；小程序 `servicewechat.com` → HK
- 网易云图床 `neteasemusic.com` → Cloudflare（US）；小米统计 `mistat.com` → US；苏宁云 `snyun.com` → HK
- 注意：同一域名不同 DNS 返回不同节点——本机（海外）查国内 DNS 得海外调度；用户手机（国内）多数时候得国内 IP。所以「别人用着没事」和「用户看日志炸了」可以同时为真

穿透链条：域名规则没接住 → 落到 GEOIP,CN → 库判定（正确地）说是 HK/SG/US → 不中 → MATCH 兜底走代理。Meta 官方 geoip 库判定没错——这些 IP 真不在国内。唯一稳的解法是**域名规则直接命中直连**（域名命中不看 IP 归属）。

用户日志形如 `[DPC] <TCP> connect [IP]:443 via 漏网之鱼 match MATCH` 时，`[IP]` 表示 App 拿着 IP 硬连、根本没有域名——这是 Clash 机制死角，任何订阅规则都救不了，唯一解是客户端 TUN 排除应用（安卓 Clash Meta：`tun.exclude-package: [com.tencent.mm]`，微信整个不进代理栈）。其他 App 同理换包名。

## 诊断流程：某个 App 流量走代理了

1. **先判定是域名路径还是纯 IP 路径**：用户日志里是 `[域名]:443` 还是 `[IP]:443`。后者直接给客户端 exclude-package，别在订阅上找补
2. **模拟命中链**：拿该 App 的核心域名（主域 + 图片/头像/统计 CDN 域——主域在规则里≠CDN 域在），按订阅规则顺序逐条模拟 DOMAIN-SUFFIX/DOMAIN/KEYWORD 匹配，看落在哪条
3. **域名未命中时查 IP 归属**：`dig +short <domain> @223.5.5.5` 再用 ip-api.com batch 查国家。海外 IP = 穿透实锤，需要域名规则接住；国内 IP = GEOIP 能兜住，低风险
4. **批量排查时**：把 33 个 App 族 130+ 域名做成清单跑同样的模拟（脚本化，禁止凭感觉）。注意性能：ChinaMax 12 万条 × 130 域名的暴力双层循环会超时——先把 ruleset 拆成 suffix/domain/keyword 三个 set（suffix 用逐级父域查表，O(1)），秒级完成
5. **修复后重跑同一模拟**：未命中清单 15→8 才算收敛；剩余 8 个（bytedapm/neteasemusic/mistat/qyimgs/beike/snyun/huyacdn/cmcc）全球无库收录，多为统计上报/按需 CDN 长尾，其中 beike 解析国内 IP（GEOIP 兑住）、qyimgs/huyacdn 解析失败（按需调度）——**不为这几个开洞，不值得**

## 冗余判定：哪些「看着重复」的规则能删、哪些不能

删之前先回答「这条规则的条目是否被后续规则 100% 覆盖、且目的地相同」：

- **可删**：SukkaChinaIP（3900 条中国 CIDR）——被 ChinaMax 内嵌 IP 段（12472 条 IP-CIDR）+ GEOIP,CN 双重完全覆盖，删了还省掉 3900 条线性匹配
- **不能删（看着像重复）**：
  - `ChinaCompanyIp`：ACL4SSR 专门收录中国公司**国际段**（203.205.x 微信 HK 接入等 12 条腾讯云国际 CIDR）——GEOIP 判这些是 HK，它是纯 IP 穿透的唯一防线
  - `ChinaDomain`：625 条中 551 条被 ChinaMax 覆盖，但 74 条独有（playstation.net 国服、epicgames.dev 等），且有官方模板成分
  - `ChinaMedia`：目的地是「国内媒体」组（组内可切节点），与「全球直连」组不是一回事——目的地不同不算重复
  - `ChinaMax` 的 IP-CIDR 部分：与 GEOIP 重复但它是 12 万行主体库的顺带部分，不拆

判定方法：把每条规则的目的地组、list 内容并集、被覆盖比例三样摆出来对比，不要凭直觉「好像重复」。

## 社区规则库对照（覆盖谁、坑在哪）

| 库 | 规模/构建 | 覆盖特点 | 坑 |
|---|---|---|---|
| ACL4SSR 官方 list（ChinaDomain 等） | 精选 635 条 | 主流大厂主域 | **不含 qpic/qlogo 等长尾 CDN 域**——官方五个主流 ini 都没引用 Wechat/Tencent.list，别以为引用了官方模板就万事大吉 |
| Sukka `ruleset.skk.moe` | 每日构建 | domestic.txt 879 行，**含 qpic/qlogo/weixin/xhscdn**，热门模板（WC-Dream 等）都在用 | 必须用 `/Clash/` 专用路径（Clash 预处理格式）；`/List/` 通用路径是 Surge 格式，其 IP 库混 DOMAIN 签名行，ipcidr behavior 加载有风险 |
| blackmatrix7 ChinaMax | 12.4 万行，每 6h | 覆盖面最大的中国域名聚合库（服务小程序/京东京喜/贝壳/vivo/bbk 等 9+ 长尾） | 仍有盲区：neteasemusic.com/mistat.com/qyimgs.com/huyacdn.com/snyun.com/cmcc.com 全球无库收录 |
| v2fly geosite (GEOSITE 规则) | 内核原生 | tencent 分类含 qpic/qlogo | Meta 内核特性；GEOSITE,cn 有 `@!cn` 剔除机制，部分国内域会被剔出分类 |
| Loyalsoldier clash-rules | 每日构建 | direct.txt 11 万行 | 同样缺 qpic/qlogo（@-!cn 剔除）；cncidr 是纯 CN 库，腾讯云 HK 段不在内 |

**规则源 URL 必须实测 curl 200 且抽查内容格式**：Sukka 的 `/List/` vs `/Clash/` 路径差异（ Surge 格式 vs Clash 预处理格式）就是靠打开文件看内容发现的——签名行、注释头、DOMAIN 混入 IP 库这类问题 curl 状态码看不出来，必须看内容。

## RULE-SET 引用数 ≠ 规则条数

用户看到订阅里 17 个 RULE-SET 会以为「规则只有十几条，别人好几万」。实际：每个 RULE-SET 背后是几千条的 list 文件（实测 ACL4SSR 精选流合计 10165 条 + GEOIP 全量库兜底 ≈ 客户端显示 1 万+）。Loyalsoldier 全量流 ~15 万条是另一流派（v2fly 全量导出，没被墙的国外站也逐条列）。两流派功能等价（国内直连/国外代理），解释清楚即可，不要因此加规则。

## 零自造铁律（用户红线，多次暴怒确认）

- 订阅 rules 里禁止手写内联域名/IP-CIDR 规则（唯一例外 = 订阅域名自身 DIRECT 一条）
- 禁止自造 IP 段 list（RIPEstat 拉 ASN 全段生成直连库 = 被否定并回滚）
- 往官方模板上加任何东西（哪怕社区权威库 cncidr/sniffer/GEOSITE）都要先问用户
- 加社区规则源前先查「人家热门模板怎么配」（bianyuan.xyz 等转换站的前端 JS 里有它家模板清单，拆开看就知道主流用法——其清单里 WC-Dream 等热门模板挂的就是 Sukka domestic + skk china_ip），照抄人家的 provider 声明（url/behavior/format/interval），不要自己发明组合
- 每次改动后全量复验：两份订阅逐规则逐 provider 对比 + 模拟命中链重跑 + 端到端 TCP

## 交付模式：用户用转换站自套模板（现行主模式）

用户对订阅端反复调规则的耐心已耗尽，现从 bianyuan.xyz 等转换站自套模板为主，成品订阅降为备份。响应口径：

- 给 raw 订阅链接（纯 proxies 无规则，`/raw` 路由，同步脚本自动维护），一句话说明转换站怎么填（后端默认 + 远程配置选 ACL4SSR_Online_Full），完事
- 不要再主动替用户调规则/加源/修分流——他要的是「节点给你，规则我自己套」
- 转换站只是 subconverter 前端壳，内置模板全是 ACL4SSR 系；它的价值在「用户自己选模板」，不在技术比订阅服务端生成更先进
- 用户问「别人为什么用着没事」这类质疑，用本文件的机制解释（海 CDN 调度 + 纯 IP 路径死角），不要又开一轮规则改造
