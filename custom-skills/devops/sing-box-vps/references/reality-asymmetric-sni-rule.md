# 不对称 REALITY 配置的 sni 一致性铁律（2026-09-06 二次事故）

## 事故链

1. 上午：握手目标被阻断，上了不对称配置（server_name=apple.com，handshake.server=itunes.apple.com），用户旧参数立刻能用 ✅
2. 但同时把订阅文件的 sni 也同步成了 itunes.apple.com（当时以为是"顺手保持一致"）
3. 用户重拉订阅 → 客户端改发 sni=itunes.apple.com → 服务端校验名仍是 apple.com → REALITY 秒拒
4. 用户报"还是超时"（vmess/anytls 一直好、就 vless 修完反而挂）→ 二次暴怒（原话"你是真傻逼，在排查排查？"）

## 不变式

**`订阅 sni ≡ tls.server_name（校验名）`，两者必须同改或同不改。`handshake.server` 是服务端借证书的内部目标，与客户端/订阅完全无关。**

三种自洽状态（任选其一，禁混搭）：

| 状态 | server_name | handshake.server | 订阅 sni | 效果 |
|---|---|---|---|---|
| A 不对称 ✅ | 旧 | 新(实测通) | 旧 | 所有人立即可用 |
| B 对称 | 新(实测通) | 新(实测通) | 新 | 重拉后可用，旧客户端挂到重拉 |
| ❌ 混搭(事故) | 旧 | 新 | 新 | 重拉用户全挂 |

事故后落地的修复 = 状态 B（校验名也改成 itunes.apple.com，与订阅一致，全对称）。

## 验证规则（防复发）

**修复后的端到端测试必须用订阅现行输出做客户端参数**——curl 拉订阅 → 解出 sni/pbk/sid/uuid 填进测试客户端。你用"记忆里的参数"测通 ≠ 用户能用，用户手里的参数可能已经变了（重拉过订阅）：

```bash
grep QQG-VLESS /etc/s-box/sub-links-plain.txt   # 逐参数对照 sb.json
```

**报"还是超时"时先看服务端日志的拒绝时间分布**：`journalctl -u sing-box | grep <用户IP>`——用户连接"有到达但秒拒 invalid"且你上一次修复自测通过 = 你的修复没覆盖到用户手里的参数版本，逐字对比订阅输出 vs sb.json。

## 2026-09-14 复发提醒

同样的 invalid 被拒又出现（用户出口 IP 已换成 218.12.x）——但这次服务端/订阅/sni 三方全一致、本地用订阅参数实测 204/50ms 通，被拒的是用户端**缓存的旧参数**（Stash 没重拉订阅）。区别方法：**服务端三方一致 + 本地订阅参数实测通 + 用户持续被拒 = 客户端缓存问题**，直接让用户强制重拉订阅，不要再去改服务端。详见 `subscription-outage-diagnosis.md` 的 2026-09-14 案例与判定表。
