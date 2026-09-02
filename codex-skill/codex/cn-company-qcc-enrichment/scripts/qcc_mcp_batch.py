#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""企查查 MCP 批量补全脚本 (2026-08-05)
用法: python3 qcc_mcp_batch.py <名单.txt> <起始> <结束> [输出.json]
对每家公司调用: 工商信息 + 联系方式 + 经营异常 (company/risk 两个 server)
输出字段: 公司|法人|联系方式|注册地址|登记状态|是否异常|异常原因|信用代码|成立日期
"""
import json, sys, os, time, urllib.request

KEY_FILE = "/Users/didi/Desktop/yy工作/密钥"
KEY = json.load(open(KEY_FILE, encoding="utf-8"))["mcpServers"]["qcc-company"]["headers"]["Authorization"].replace("Bearer ", "")

SERVERS = {
    "company": "https://agent.qcc.com/mcp/company/stream",
    "risk":    "https://agent.qcc.com/mcp/risk/stream",
}

class MCPClient:
    def __init__(self, url):
        self.url = url
        self.sid = None
        self._rpc_id = 0
    def _call(self, payload):
        headers = {"Authorization": "Bearer " + KEY, "Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream"}
        if self.sid:
            headers["Mcp-Session-Id"] = self.sid
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            sid2 = r.headers.get("Mcp-Session-Id")
            if sid2:
                self.sid = sid2
            body = r.read().decode()
        if not body.strip():
            return None
        datas = [line[6:] for line in body.splitlines() if line.startswith("data: ")]
        if datas:
            return json.loads("".join(datas))
        return json.loads(body)
    def connect(self):
        self._call({"jsonrpc": "2.0", "id": self._nid(), "method": "initialize",
                    "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                               "clientInfo": {"name": "qcc-batch", "version": "1.0"}}})
        self._call({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    def _nid(self):
        self._rpc_id += 1
        return self._rpc_id
    def invoke(self, tool, args):
        res = self._call({"jsonrpc": "2.0", "id": self._nid(), "method": "tools/call",
                          "params": {"name": tool, "arguments": args}})
        if not res:
            return None
        if "error" in res:
            return {"_error": res["error"]}
        text = ""
        for c in res.get("result", {}).get("content", []):
            if c.get("type") == "text":
                text += c.get("text", "")
        try:
            return json.loads(text)
        except Exception:
            return {"_raw": text}


def extract_phone(contact):
    """从 get_contact_info 结果提取电话字符串"""
    phones = []
    info = (contact or {}).get("联系方式信息") or {}
    for p in info.get("电话", []) or []:
        num = p.get("电话号码", "").strip()
        if num:
            tags = "/".join(p.get("标签", []) or [])
            phones.append(num + (f"({tags})" if tags else ""))
    return "; ".join(phones)


def extract_exception(exc):
    """解析 get_business_exception: 返回 (是否异常, 原因)"""
    if not exc:
        return "", ""
    s = exc.get("搜索结果") or json.dumps(exc, ensure_ascii=False)
    if "未发现" in s and "经营异常" in s:
        return "否", ""
    if "未发现" in s:
        return "否", ""
    # 有记录: 尝试提取列入原因
    return "是", s[:200]


def process(client_c, client_r, name):
    row = {"公司": name, "法人": "", "联系方式": "", "注册地址": "", "登记状态": "",
           "是否异常": "", "异常原因": "", "信用代码": "", "成立日期": "", "源": []}
    args = {"searchKey": name}
    # 工商信息
    reg = client_c.invoke("get_company_registration_info", args)
    if reg and "_error" not in reg:
        row["法人"] = reg.get("法定代表人", "")
        row["注册地址"] = reg.get("注册地址", "")
        row["登记状态"] = reg.get("登记状态", "")
        row["信用代码"] = reg.get("统一社会信用代码", "")
        row["成立日期"] = reg.get("成立日期", "")
        row["源"].append("qcc-company")
    else:
        row["源"].append(f"reg_err:{json.dumps(reg, ensure_ascii=False)[:100] if reg else 'none'}")
    time.sleep(0.3)
    # 联系方式
    ct = client_c.invoke("get_contact_info", args)
    if ct and "_error" not in ct:
        row["联系方式"] = extract_phone(ct)
        row["源"].append("qcc-contact")
    else:
        row["源"].append(f"contact_err:{json.dumps(ct, ensure_ascii=False)[:100] if ct else 'none'}")
    time.sleep(0.3)
    # 经营异常
    exc = client_r.invoke("get_business_exception", args)
    if exc and "_error" not in exc:
        abn, reason = extract_exception(exc)
        row["是否异常"] = abn
        row["异常原因"] = reason
        row["源"].append("qcc-exception")
    else:
        row["源"].append(f"exc_err:{json.dumps(exc, ensure_ascii=False)[:100] if exc else 'none'}")
    return row


def main():
    listfile = sys.argv[1]
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    end = int(sys.argv[3]) if len(sys.argv) > 3 else start + 10
    out = sys.argv[4] if len(sys.argv) > 4 else f"/Users/didi/Desktop/yy工作/2026-08-01/数据/qcc_mcp_{start}_{end}.json"
    with open(listfile, encoding="utf-8") as f:
        names = [l.strip() for l in f if l.strip()]
    print(f"QCC-MCP 批量 [{start}:{end}] 共{len(names)}家 -> {out}", flush=True)
    client_c = MCPClient(SERVERS["company"]); client_c.connect()
    client_r = MCPClient(SERVERS["risk"]); client_r.connect()
    results = []
    for i in range(start, min(end, len(names))):
        n = names[i]
        try:
            row = process(client_c, client_r, n)
        except Exception as e:
            row = {"公司": n, "法人": "", "联系方式": "", "注册地址": "", "登记状态": "",
                   "是否异常": "", "异常原因": "", "信用代码": "", "成立日期": "", "源": [f"err:{str(e)[:100]}"]}
        results.append(row)
        missing = [k for k in ("法人", "联系方式", "注册地址", "是否异常") if not row[k]]
        print(f"[{i}] {n[:16]} | 法人={row['法人'] or '-'} | 状态={row['登记状态'] or '-'} | 电话={'Y' if row['联系方式'] else '-'} | 异常={row['是否异常'] or '-'} | 缺:{' '.join(missing) or '无'}", flush=True)
        time.sleep(0.5)
        if (i - start + 1) % 10 == 0:
            with open(out, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=1)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print(f"\n完成 {len(results)} 条 -> {out}", flush=True)


if __name__ == "__main__":
    main()
