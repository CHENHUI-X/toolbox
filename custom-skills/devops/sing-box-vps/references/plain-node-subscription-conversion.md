# 纯节点订阅（供外部订阅转换）与 mihomo 字段对齐（2026-09-24）

用户：「把订阅改成最普通的订阅，不要自带规则，我再拿去做订阅转换」。

## 生成纯节点版

```python
import yaml
d = yaml.safe_load(open('/etc/s-box/merged-sub.yaml'))
yaml.dump({"proxies": d['proxies']}, open('/etc/s-box/merged-sub.yaml','w'),
          allow_unicode=True, sort_keys=False, default_flow_style=False)
```

- **先备份完整版**：`cp merged-sub.yaml merged-sub.yaml.bak-full-rules` —— 用户转换方案跑通前后随时一键还原
- subscription-server 每请求现读文件，**无需重启**，改完 curl 实拉验证：节点数齐、proxy-groups=0、规则=0
- 两台机的分发文件（merged-sub / aws-sub）同步处理

## mihomo 官方字段对齐（wiki.metacubex.one 逐协议核对）

机场原始订阅的标准长相，转换器识别率最高：

| 类型 | 关键字段（官方格式） |
|---|---|
| hysteria2 | `up: "100 Mbps"` / `down: "100 Mbps"`（**带单位字符串**）、`alpn: [h3]`、sni、skip-cert-verify |
| tuic (v5) | `uuid`+`password`、`alpn: [h3]`、`udp-relay-mode: native`、`reduce-rtt: true`、`congestion-controller: bbr` |
| anytls | `password`、`client-fingerprint: chrome`、`alpn: [h2, http/1.1]`、sni |
| vless | `uuid`+`flow: xtls-rprx-vision`、`client-fingerprint: chrome`、`reality-opts{public-key,short-id}`、`servername`、`packet-encoding: xudp`、alpn |
| vmess | `uuid`+`alterId: 0`+`cipher: auto`、ws-opts{path,headers.Host,max-early-data,early-data-header-name} |

全类型 `udp: true`。改完 `yaml.safe_load` 逐节点打印抽查断言（防止 sed 串字段）。

## 「只有 vmess」症状 = 转换端的锅

用户转换后只见 vmess：订阅侧实拉 10 节点俱在 → 老版订阅转换后端不认 anytls / tuic-v5 / 新字段写法，**静默丢节点**。

- 处置：让用户换带 `target=clashmeta`（mihomo）的新转换后端/模板
- **转换后数节点数**（本例应 10）作为交付验收，少=换后端
- ⚠️ 转换模板的规则源必须仍是 jsdelivr 镜像——模板若指回 raw.githubusercontent，微信走代理的老 bug 会原样复发
