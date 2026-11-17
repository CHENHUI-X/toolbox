# 中国方向线路质量诊断：延迟低但速度慢（2026-09-06 / 2026-09-14 两次实战）

**症状**：节点连得上、延迟低，但视频/网页加载极慢。用户会先怀疑协议/UDP/服务端配置——都不一定。

## ⚠️ 先读：单源测速会骗人（09-14 对 09-06 结论的重大纠正）

09-06 曾据"服务器→qq.com CDN 仅 0.27~0.57 MB/s"定性"QQG 线路中国方向天花板 ≈3MB/s，服务端无解"。**09-14 多源复测推翻了它**——同一条线、同一时刻：

| 中国源 | 服务器直连 | 走 vless 代理（用户真实路径） |
|---|---|---|
| 华为云镜像 mirrors.huaweicloud.com（ubuntu iso） | **49 MB/s** | **37 MB/s** |
| 清华 TUNA（ubuntu iso） | 11 MB/s | 11.7 MB/s |
| 腾讯 dldir1.qq.com（微信安装包） | 2.9 MB/s | — |
| 中科大 / 阿里云 OSS | 0（对海外限速/拒） | — |

**结论修正**：QQG→中国干线实际能力 **11~49 MB/s**；0.27~3MB/s 的读数是腾讯该 CDN **对海外 IP 的单源限速**，不是线路天花板。

**方法论铁律**：任何"线路限速"结论必须 **≥3 个中国源交叉验证，且必含华为云镜像**（对海外最慷慨）。美国方向同理——09-11 CF `__down`、cachefly 对本机 IP 也降到 1~5 MB/s（平时 100+），thinkbroadband 100MB 却有 39.5 MB/s。CDN 对单个 VPS IP 的动态限速双向存在，单基准源会得出"服务器出口坏了"的假象。

## 时段性拥塞
晚高峰国际出口拥塞造成"白天快晚上堵"，与节点/协议/服务端无关，无解。体感对比必须同时段做。

## 测量方法
```bash
# 服务器→中国方向吞吐：多源、多次（缺一不可）
for url in \
  "https://mirrors.huaweicloud.com/ubuntu-releases/22.04/ubuntu-22.04.5-live-server-amd64.iso" \
  "https://mirrors.tuna.tsinghua.edu.cn/ubuntu-releases/22.04/ubuntu-22.04.5-live-server-amd64.iso" \
  "https://dldir1.qq.com/weixin/Windows/WeChatSetup.exe"; do
  curl -s -o /dev/null -w "%{speed_download}B/s  $url\n" --max-time 10 "$url"
done
# 走节点代理复测（用户真实路径；本地测试客户端搭法见 reality-handshake-target-blocked.md）
curl -x socks5h://127.0.0.1:17897 "$url" -w "%{speed_download}B/s\n"
# 对照：服务器→美国（也要多源：CF __down 会被限速，加 thinkbroadband）
```

## 优化前后对比的正确姿势（09-11 BBR 落地时验证）
- CDN 波动远大于参数差异，**单次 A/B 无效**；用交替轮：关参数测 2 次 → 开参数测 2 次，循环 ≥2 轮，比分布不比单点。
- 给用户的体感对比法：同一时段 `sysctl -w net.ipv4.tcp_congestion_control=cubic` 切回旧算法再切回 bbr，用户立即重测。
- BBR 的收益窗口在**丢包多的时段**（晚高峰）；线路好时无差别——不要在线路好时宣布"优化无效"，也不要在线路差时归功参数。

## "怎么保证出口是华为云"——用户概念纠偏（09-14）
方向反了：出口 IP = 代理服务器 IP（QQG=50.114.172.17），目标网站看到的是它；"华为云"只是被访问的目标，与出口无关。验证用户是否真走节点：Stash 选中节点后手机开 ip-api.com，显示服务器 IP = 在走。

## 排查陷阱
1. **用户出口 IP 会中途变**（已见 60.8.100.50→124.126.139.210→115.171.48.81→218.12.29.95）。先 `journalctl -u sing-box --since today | grep -oE "from [0-9.]+" | sort | uniq -c` 确认当前 IP 再分析，grep 旧 IP 一无所获会误判"没流量/没修好"。
2. **UDP 通不通随用户网络变**：同一服务器，A 出口 UDP 全丢，用户换网络后 hy2/tuic 握手包双向飞（1280 字节大包来回）。"UDP 好了"可能是用户换了网络，不是谁修好了——反过来说 UDP 问题也可能自愈，别急着下架节点。
3. **UDP 入站到达 ≠ 可用**：QUIC 握手包到了、日志无 ERROR 也无转发 = 认证没过/卡住。判断可用性看 outbound 转发记录或实测代理吞吐，别只看"有包到达"。
4. **单向包流 ≠ 服务端故障**：tcpdump 只见服务端→用户的回包、没有用户→服务端的包 = 中国方向入包被丢（服务端在重传等待），是路径问题，不是本机问题。

## 协议速度排名（给用户选节点的口径）
HY2 ≈ TUIC（QUIC，抗丢包，高延迟线路最快）> VLESS-Reality（TCP 系最快，无双重封装）> AnyTLS > VMess-ws（最慢，多层封装，只当备胎）。
推荐口径：日常主力 TCP 系（VLESS），要速度切 UDP 系（HY2/TUIC）——前提是该线路 UDP 没被洗、回程没被限速。

## 缓解手段（提速类问题的出口）
诊断先定位瓶颈段，再谈提速。服务端可做：全协议端口迁入 443 区（流程/坑/代价见 `qos-evasion-port-migration.md`）。客户端可做：mux、错峰。治本：9929/CN2 中转跳板。套 CF/WARP 不解决用户↔服务器段——CF 仅代理 HTTP(S)/WS，会废掉 REALITY/TUIC/HY2；WARP 不改变用户↔服务器段。
