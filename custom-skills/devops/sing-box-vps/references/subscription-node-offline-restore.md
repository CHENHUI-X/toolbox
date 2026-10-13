# 订阅节点下架/恢复与凭据克隆（2026-09-06 实战）

场景：QQG(DDoS 防护线路) 中国方向 UDP 被机房洗掉，用户同意把 QQG-HY2/QQG-TUIC 从订阅下架；后又要求恢复原样。

## 下架/恢复订阅节点的坑

**订阅有 4 种格式，改一处必须同步其余**：`sub-links-plain.txt` / `sub-links-b64.txt`（改完 plain 后**必须重新 base64 编码**）/ `sub-singbox.json` / `aws-sub.yaml`（Clash/Stash，字段名是 `servername:` 不是 `server_name`）/ `sub-surfboard.ini`。端到端验证 = 用真实 key `curl` 本机订阅端点数节点数。

**从零重建节点链接的正确姿势：以同协议另一台机器的现成链接为模板做字符串替换**（域名/端口/密码/uuid/sni/#名字），不要手写 URL 参数——hy2 的 obfs-password、tuic 的 uuid+password 双字段很容易漏。

**Clash yaml 的 proxy-groups 引用是独立陷阱**：删了 proxies 里的块，groups 里的 `- 🇺🇸 洛杉矶 | HY2` 引用还在 → 客户端解析报错或组内空引用。删块后必须核对 groups 引用无缺失；恢复时同理，新增块要插在 `proxy-groups:` 之前，并确认组里名字能对上。

**GCP 节点不在 aws-sub.yaml 里**（该文件只有 QQG 节点，desc 还写着"自建5节点"）——各订阅文件的覆盖范围不一致，改前先 `cat` 确认每个文件实际含什么，别按假设批量替换。

## 已验证的下架/恢复操作（可复用）

下架 plain 行：`sed -i '/#QQG-HY2$/d; /#QQG-TUIC$/d' sub-links-plain.txt`；singbox 删 outbound 按 `(type, server域名)` 过滤；yaml 按块切分 `re.split(r'(?m)^(?=- type:)', s)` 后按端口+域名过滤。

恢复 = 从 GCP 对应块克隆改参数；yaml 新块直接 f-string 手写比字符串替换稳（`port: %d` 全局替换会误伤）。恢复后 `grep -c '^#QQG-HY2' sub-links-plain.txt` 和端点实拉双验。

## 用户偏好（本次学到的）

- 用户中途推翻方案（"不不不"）→ 立即停手，不要继续执行被打断的操作，先确认用户要什么
- "先恢复原样"= 最小恢复，别顺手做其他"优化"
- 用户最终说"超时就超时吧"= 接受现状收尾，把状态恢复干净、简短汇报即可

## 2026-09-11 用户反转实录（与 09-06 同构）

用户否定"GCP 中继修 UDP"方案（"这个方法也不好，你先给我把节点都恢复，超时就超时吧"）→ 撤销中继构想，把订阅恢复到改动前原样。与 09-06 的"下架→否决→恢复"完全同构。**恢复操作**：drop-qqg-udp.sh 删掉的节点用 restore 脚本按协议重建（从 sb.json 取真值 + 克隆现成块模板），aws-sub.yaml 的恢复最麻烦——块被删后 proxy-groups 引用残留，恢复时从 GCP 对应块克隆改端口，改完全格式端点实拉验证节点数。**教训**：用户说"能不要 UDP 吗"是在发泄，不是决策——他马上会反悔，删订阅节点这类用户可见变更尽量缓一步。