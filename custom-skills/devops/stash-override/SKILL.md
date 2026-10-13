---
name: stash-override
description: "Use when creating or debugging Stash .stoverride files."
version: 1.0.0
author: Hermes Agent
tags: [stash, override, proxy, subscription, ios, stoverride]
---

# Stash 覆写（.stoverride）：把自建节点/规则附加到任意订阅

## When to Use

- 把自建节点 + 指定分流规则（例：PayPal 走自建）"贴"到别的订阅上（订阅之间不能合并，覆写是唯一手段）
- 覆写导入失败（"下载失败" / `RequestManager 错误 -1`）
- 覆写导入成功但"规则看起来没生效"

## 覆写机制（官方 + 实测）

- 文件 = YAML 片段，后缀 `.stoverride`；`name`/`desc` 仅用于展示（建议都写）
- 合并语义（官方文档）：
  - 简单类型 → 直接覆盖
  - 字典 → 递归合并
  - **数组 → 覆写数组插到原数组最前面** ⇒ 覆写里的 `rules` 优先级最高、先命中
  - 加 `#!replace` → 整段替换（慎用，会清掉订阅原有内容）
- 可同时启用多个覆写，按列表从上到下依次合并
- 覆写独立于订阅文件，订阅更新不会丢

## 已验证的坑（实测）

- ✅ **手机上"规则"列表页不显示覆写层规则** —— 别用它判断是否生效！
- ✅ 验证生效唯一可靠办法：**工具 → 检视 HTTP 请求**，看连接行 `match <规则> via <组>[<节点>]`
  - 例：`connect i.paypal.com:443 via 自建节点[[GCP] VLESS] match DOMAIN-SUFFIX/paypal.com`
- ✅ 导入报 `RequestManager 错误 -1` = 请求没到达服务器（连接层失败）：
  1. 先在服务器 curl 自测（200 ⇒ 文件/服务没问题）
  2. 让用户**断开 Stash 的 VPN 开关**再导入（开着会把请求塞进自身隧道）
  3. 换手机能连的域名（实测：GCP 域名手机直连不通；QQG/AWS 洛杉矶域名可用）
  4. `http://` 80 端口完全可用于导入，不是必须 https
- ⛔ 覆写不要用 GitHub gist 托管：含节点凭据（UUID/密码），用户明确在意安全 ⇒ 用自家订阅服务器 + sub-key
- ⚠️ 疑未证实：带 `rule-providers` + `path:` 的覆写从 URL 导入可能失败（排查期怀疑，未复测）⇒ 覆写尽量只用 proxies / proxy-groups / rules

## 最小模板（自建节点 + PayPal 规则）

```yaml
name: 自建节点追加
desc: 把自建10节点追加到当前订阅，PayPal走自建节点，其余流量不受影响
proxies:
- name: '[GCP] VLESS'
  type: vless
  # ...节点字段照 /etc/s-box/merged-sub.yaml 抄，与服务器保持一致
proxy-groups:
- name: 自建节点
  type: select
  proxies: ['[GCP] VLESS', '[GCP] VMESS']
rules:
- DOMAIN-SUFFIX,paypal.com,自建节点
- DOMAIN-SUFFIX,paypalobjects.com,自建节点
- DOMAIN-KEYWORD,paypal,自建节点
```

- 只放**增量**（新节点/新组/新规则），不要塞整份订阅
- **不要**加 MATCH 兜底 ⇒ 会接管订阅其他流量
- 规则目标 = 自建组的名字（组名可自定义，如"自建节点"）

## 制作 → 托管 → 交付

1. **生成+校验**：python3（`yaml.safe_dump(..., allow_unicode=True)`）写 `/tmp/xxx.stoverride`，再 `yaml.safe_load` 复查 keys/rules
2. **上传**到订阅服务器 `/etc/s-box/xxx.stoverride`
   - QQG（本机/洛杉矶）直接放；GCP 用 `ssh -p 22022 -i /root/.ssh/id_ed25519_gcp_admin root@127.0.0.1`
3. **挂路由**：`/root/.hermes/scripts/subscription-server.py` 的 PATH_MAP 加一行
   `'/xxx.stoverride': '/etc/s-box/xxx.stoverride',` → `systemctl restart subscription-server`
   （只重启订阅服务，别动 sing-box / gateway）
4. **验证**：`curl -s "http://<域名>/xxx.stoverride?key=$(cat /etc/s-box/sub-key)" | head -3`，YAML 可解析、规则在
5. **交付 URL**：`http://aws.eosphor.dpdns.org/<文件名>?key=<读 /etc/s-box/sub-key，禁硬编码>`（手机可达）；GCP 域名手机不通，仅作备份

> 现行文件：`/etc/s-box/qqg-attach.stoverride`（自建节点追加），路由 `/qqg-attach.stoverride`

## 变更纪律

- 改 subscription-server.py 前先 `cp -a` 备份；只重启对应 unit
- 交付前自测：HTTP 200 + YAML 合法 + 目标规则存在
- sub-key 从 `/etc/s-box/sub-key` 读取，禁止硬编码到文档里

## 参考

- 官方覆写文档：https://stash.wiki/configuration/override
- 本机相关文件：`/etc/s-box/qqg-attach.stoverride`、`/etc/s-box/qqg-rules.stoverride`
- 技能/知识库文件本身经 Syncthing 在两机间自动同步（folder `skills`），改完不需要手动 scp；同步机制见技能 `hermes-peer-networking`
