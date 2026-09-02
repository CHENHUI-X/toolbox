#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""企查查 MCP 每日积分自动补跑 (2026-08-05)
用法: python3 qcc_mcp_topup.py [每日预算积分=100]
读 数据/qcc_mcp_0_184.json, 找出权威字段缺失的公司, 按积分预算跑(默认约11家),
结果回填写回原 JSON, 供最终合并使用。
"""
import json, sys, time, os, re, urllib.request

import glob
DATA = sys.argv[2] if len(sys.argv) > 2 else None
if not DATA:
    _cands = sorted(glob.glob("/Users/didi/Desktop/yy工作/2026-08-01/数据/qcc_mcp_*.json"), key=os.path.getmtime, reverse=True)
    DATA = _cands[0] if _cands else None
if not DATA:
    print("未找到累计JSON, 请指定: python3 qcc_mcp_topup.py [预算积分] [累计json]"); sys.exit(1)
KEY_FILE = "/Users/didi/Desktop/yy工作/密钥"
KEY = json.load(open(KEY_FILE, encoding="utf-8"))["mcpServers"]["qcc-company"]["headers"]["Authorization"].replace("Bearer ", "")
SERVERS = {
    "company": "https://agent.qcc.com/mcp/company/stream",
    "risk":    "https://agent.qcc.com/mcp/risk/stream",
}

class MCPClient:
    def __init__(self, url):
        self.url = url; self.sid = None; self._id = 0
    def _call(self, payload):
        headers = {"Authorization": "Bearer " + KEY, "Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream"}
        if self.sid: headers["Mcp-Session-Id"] = self.sid
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            if r.headers.get("Mcp-Session-Id"): self.sid = r.headers["Mcp-Session-Id"]
            body = r.read().decode()
        if not body.strip(): return None
        datas = [line[6:] for line in body.splitlines() if line.startswith("data: ")]
        return json.loads("".join(datas)) if datas else json.loads(body)
    def connect(self):
        self._call({"jsonrpc":"2.0","id":self._nid(),"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"topup","version":"1.0"}}})
        self._call({"jsonrpc":"2.0","method":"notifications/initialized","params":{}})
    def _nid(self):
        self._id += 1; return self._id
    def invoke(self, tool, args):
        res = self._call({"jsonrpc":"2.0","id":self._nid(),"method":"tools/call","params":{"name":tool,"arguments":args}})
        if not res: return None
        if "error" in res: return {"_error": res["error"]}
        text = "".join(c.get("text","") for c in res.get("result",{}).get("content",[]) if c.get("type")=="text")
        try: return json.loads(text)
        except Exception: return {"_raw": text[:200]}

def extract_exception(exc):
    if not exc or "_error" in exc: return "", ""
    infos = exc.get("经营异常信息") or []
    if infos:
        i0 = infos[0]
        return "是", (i0.get("列入日期","") + " " + i0.get("列入经营异常名录原因","")).strip()
    s = exc.get("搜索结果","")
    if "未发现" in s: return "否", ""
    return "", json.dumps(exc, ensure_ascii=False)[:120]

def phone_str(ct):
    if not ct or "_error" in ct: return ""
    out = []
    for p in ((ct.get("联系方式信息") or {}).get("电话", []) or []):
        num = p.get("电话号码","").strip()
        if num:
            tags = "/".join(p.get("标签", []) or [])
            out.append(num + (f"({tags})" if tags else ""))
    return "; ".join(out)

def main():
    budget = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    per = 9  # 每家完整查询约9积分
    quota = max(1, budget // per)
    data = json.load(open(DATA, encoding="utf-8"))
    missing = [d for d in data if not (d["法人"] and d["登记状态"])]
    if not missing:
        print("没有待补公司, 全部完成"); return
    print(f"待补 {len(missing)} 家, 今日预算 {budget} 积分 -> 本次跑 {min(quota, len(missing))} 家", flush=True)
    cc = MCPClient(SERVERS["company"]); cc.connect()
    cr = MCPClient(SERVERS["risk"]); cr.connect()
    done = 0
    for d in missing[:quota]:
        name = d["公司"]; args = {"searchKey": name}
        reg = cc.invoke("get_company_registration_info", args)
        # 积分不足立即停止, 避免无效调用
        if isinstance(reg, dict) and reg.get("_error", {}).get("code") == 300008:
            print("积分不足(300008), 今日额度已用完, 停止本轮补跑", flush=True)
            break
        if reg and "_error" not in reg:
            d["法人"] = reg.get("法定代表人",""); d["注册地址"] = reg.get("注册地址","")
            d["登记状态"] = reg.get("登记状态",""); d["信用代码"] = reg.get("统一社会信用代码","")
            d["成立日期"] = reg.get("成立日期","")
        time.sleep(0.3)
        ct = cc.invoke("get_contact_info", args)
        if ct and "_error" not in ct:
            d["联系方式"] = phone_str(ct)
        time.sleep(0.3)
        exc = cr.invoke("get_business_exception", args)
        if exc and "_error" not in exc:
            abn, reason = extract_exception(exc)
            d["是否异常"] = abn; d["异常原因"] = reason
        d["源"] = [s for s in d.get("源", []) if "err" not in s] + ["qcc-topup"]
        done += 1
        print(f"[topup] {name[:16]} | 法人={d['法人'] or '-'} | 状态={d['登记状态'] or '-'} | 电话={'Y' if d['联系方式'] else '-'} | 异常={d['是否异常'] or '-'}", flush=True)
        time.sleep(0.5)
    json.dump(data, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ok = sum(1 for d in data if d["法人"] and d["登记状态"])
    print(f"本次补 {done} 家, 累计完成 {ok}/{len(data)}", flush=True)

if __name__ == "__main__":
    main()
