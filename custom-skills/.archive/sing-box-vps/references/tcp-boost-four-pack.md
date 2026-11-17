# TCP 吞吐优化四件套（2026-09-11 两机落地，用户批准）

背景：9/5 的 X 帖 16 项调优因用户要求 9/6 全部撤回出厂（有前科）；9/11 用户主动问"TCP 系还能不能再加速"→ clarify 列明改动范围+回退方式，用户点头后只上 4 项实锤收益项。**内核调优必须先问再动。**

## 内容（QQG 与 GCP 同套）

`/etc/sysctl.d/90-tcp-boost.conf`：
- `net.core.default_qdisc = fq`、`net.ipv4.tcp_congestion_control = bbr`
- `net.core.rmem_max = wmem_max = 33554432`（tcp_rmem/tcp_wmem 中值 131072/16384，max 32MB）
- `tcp_slow_start_after_idle = 0`、`tcp_mtu_probing = 1`

`/etc/sysctl.d/91-tcp-extra.conf`：`tcp_max_syn_backlog = 4096`、`tcp_notsent_lowat = 131072`

fq 持久化：`/etc/systemd/system/set-fq-qdisc.service`（oneshot，`tc qdisc replace dev <iface> root fq`；QQG=eth0，GCP=ens4）。

回退：两台各 `/root/rollback_tune2.sh` 一键回规格值（cubic/pfifo_fast/212992 缓冲/回删两个 conf 和 service）。

## 为什么是这四项

| 项 | 治什么 |
|---|---|
| cubic→BBR | cubic 丢包驱动，高丢包线路上吞吐崩；BBR 顶着丢包跑（收益窗口=晚高峰丢包多时） |
| fq | BBR 官方搭档 |
| 缓冲 212KB→32MB | 200ms RTT 下单流上限从 ~8.5Mbps 解锁到 Gb 级 |
| slow_start_after_idle=0 | 代理长连接空闲后不重新慢启动（刷视频场景） |

## GCP 出厂值差异（回退脚本按"规格值"写）

GCP 真出厂与 QQG 不同：qdisc=mq+fq_codel（非 pfifo_fast）、slow_start_after_idle 本来=0、tcp_rmem 中值 7101984。**真要一比一还原出厂，以 /root/net-tune/tune2-before.txt 快照为准**（脚本注释两头都记了）。GCP 施工走 peer dm（`hermes peer dm gcp1 '<任务>'`，输出 tee /tmp/*.txt，后台+notify）。

## A/B 实测教训

- **tcp_no_metrics_save=1**（X 帖吹"带宽立刻打上去"）：本机交替 A/B 两轮**无统计学差异**——中国方向 0.07~3MB/s、美国方向的波动全由 CDN 单源限速主导。零副作用保留（90-no-metrics-save.conf），但须如实告知用户"未复现帖子效果"。帖子结论≠真值。
- 单次前后对比无效：CDN 波动远大于参数差异。交替轮法 + 多源测速见 `china-line-quality-diagnosis.md`。

## LimitNOFILE 陷阱

给 sing-box 加 fd 上限前先 `systemctl show sing-box | grep LimitNOFILE`——unit 原本就 `LimitNOFILE=infinity`，drop-in 写 65535 反而是**收窄**（已踩：drop-in 已删）。

## 流程纪律

- 两台服务器成对改、成对验证（用户硬性要求"你修的话，2个服务器一起修"）。
- 改前后都留快照（tune2-before.txt），回退脚本跟着改动同步追加（本次 91-tcp-extra.conf 的回退就是事后补进 rollback 脚本的）。
