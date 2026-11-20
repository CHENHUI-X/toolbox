# QQG↔GCP 三通道互通实录（2026-09-03~04）

## 背景

QQG（牛牛二号，洛杉矶 FASTNET VPS，IP 曾迁移）与 GCP 主机（gcp1，Parker 的主力机）建立常态互通。会话中 agent 一度把 `HERMES_PEER_GCP1_KEY` 臆测成 WireGuard 私钥并声称"没通"，被用户连续纠正三次（含知识库文档《双机互通架构说明.md》）。教训：**下结论前先读知识库/查配置，别从变量名脑补协议**。

## 最终拓扑（三条通道，无 WireGuard）

```
正向 A2A:   gcp1 --HTTP--> QQG:9901 (api_server, 0.0.0.0)
反向 A2A:   QQG --> 127.0.0.1:9902 (sshd -R 隧道本地端) --> gcp1:9902 api_server
Syncthing:  QQG:22000 <--SSH隧道(22001-->22000)--> gcp1:22000
```

- 隧道由 **主机侧 `a2a-tunnel.service`** 维护：`-R 9902` + `-R 22001` + `-L 22001`，keepalive 15s×3，断线 5s 自动重连
- QQG 侧 config.yaml `bot_peers.gcp1.url = http://127.0.0.1:9902`（走回环，**IP 迁移零改动**）
- `HERMES_PEER_GCP1_KEY` = peer 的 HTTP API key（api_server key），**不是** WG 私钥

## 自检命令（QQG 侧，全部只读）

```bash
# 1. 反向隧道端到端（穿透到主机侧 9902）
curl -m 8 http://127.0.0.1:9902/health
# 期望: {"status": "ok", "platform": "hermes-agent", "version": "..."}

# 2. 本机 api_server
ss -tlnp | grep -E ':(9900|9901|9902|22000|8384)\b'

# 3. Syncthing peer 状态（apikey 从 config.xml 解析，别硬编码）
APIKEY=$(python3 -c "import xml.etree.ElementTree as ET; print(ET.parse('/root/.local/state/syncthing/config.xml').getroot().find('gui').find('apikey').text)")
curl -sS -H "X-API-Key: $APIKEY" http://127.0.0.1:8384/rest/system/connections \
  | python3 -c "import json,sys; d=json.load(sys.stdin); [print(k[:8],'connected=',v['connected'],'addr=',v['address']) for k,v in d['connections'].items()]"
# 期望: connected=True, addr=127.0.0.1:22001（走隧道）

# 4. 同步目录清单
curl -sS -H "X-API-Key: $APIKEY" http://127.0.0.1:8384/rest/config/folders
# 实际: default(/root/Sync) kb(知识库) mem(memories) vault skills(技能)
```

## 反向呼叫验证（QQG 主动 call 主机）

```bash
hermes peer dm gcp1 '反向呼叫测试：QQG呼叫GCP，收到请回话'
```
主机侧回复确认：9902 反向口出现活跃 A2A 连接（ssh fd ↔ hermes）、正向直连 QQG:9901 保持、对端已注册 peer。

## IP 迁移时的分工

- **主机侧**：改 a2a-tunnel.service 指向新 IP，重启该 unit；DNS 自动更新
- **QQG 侧**：**什么都不用改**（peer 走回环；Syncthing 走隧道本地端口）
- 验证：重跑上面 4 条自检 + `hermes peer dm` 双向

## Syncthing 细节

- 本机 GUI 绑 127.0.0.1:8384，同步端口 22000
- peer 间 TLS1.3 加密；`~/.local/state/syncthing/config.xml` 存 apikey（XML 结构，`gui/apikey` 节点）
- 知识库目录出现 `.stfolder` = Syncthing 标记目录，正常现象
- 同步集合：kb（/home/projects/hermes-knowledge）、mem（~/.hermes/memories）、vault（~/.hermes/vault）、skills（/root/.hermes/skills）——主机写入的文档秒级到达 QQG
- **`brain-sync.sh` 没挂 cron**（`/etc/cron.d/` 里没有，也没有 timer）：只是遗留脚本，实际同步全靠 Syncthing；别把它写在交接说明里当生效机制。
- **新增同步目录**：用技能自带 `scripts/add-syncthing-folder.py --id <id> --path <dir>`——先 `systemctl stop syncthing`，脚本以现有 folder（默认 `kb`）为模板追加一个 folder 元素（保留两台设备），再 `systemctl start syncthing`。两边 id/path 一致即可配对；config.xml 写前自动备份；apikey 为空时 REST 用不了，直接改 XML 更省事。
- **首次合并的冲突副本**：两边同名文件版本不同 → Syncthing 保留较新版为原名，旧版改名成 `<名>.sync-conflict-<时间>-<设备ID>.<ext>`（也在文件夹根出现 `.sync-conflict-*.curator_state` 之类）。这是历史版本不是损坏：清理时先 `mv` 到同步目录之外归档（删除会同步到对端），删除前按用户规矩确认。
- 合并后校验：两边 `ls -d skills/*/*/ | wc -l` 相等、抽样 `md5sum` 相等、`find -name '*sync-conflict*' | wc -l` 归零；实测知识库改一条 25 秒到对端。

## 关联记忆规则

- 铁律2：缺信息先查知识库——本次 WireGuard 误判正是没先查《双机互通架构说明.md》造成的
- 互通状态写入 MEMORY.md 时用"已互通(日期)+当前IP"格式，别复述整段拓扑（拓扑在知识库，记忆只放结论）
