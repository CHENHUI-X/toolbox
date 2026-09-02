#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并企查查MCP结果(+可选浏览器结果) -> 规范Excel
用法: python3 merge_deliver.py <qcc.json> [baidu.json] <输出.xlsx>
输出列: 公司名称|法人|联系方式|注册地址|经营内容(空)|是否异常|异常原因|登记状态|数据来源
权威字段以qcc.json为准; 浏览器数据标"参考"
"""
import json, sys, openpyxl

def fix_exception(d):
    abn, reason = d.get("是否异常", ""), d.get("异常原因", "")
    for s in d.get("源", []):
        if "exc_err" in s:
            return "", "异常待权威补(积分不足)"
    if reason and str(reason).strip().startswith("{"):
        try:
            obj = json.loads(reason)
            infos = obj.get("经营异常信息") or []
            if infos:
                i0 = infos[0]
                reason = (str(i0.get("列入日期", "")) + " " + str(i0.get("列入经营异常名录原因", ""))).strip()
                abn = "是"
        except Exception:
            pass
    return abn, reason

def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print("用法: python3 merge_deliver.py <qcc.json> [baidu.json] <输出.xlsx>"); sys.exit(1)
    out = args[-1]
    qcc_path = args[0]
    baidu_path = args[1] if len(args) == 3 else None
    qcc = json.load(open(qcc_path, encoding="utf-8"))
    qcc_map = {d["公司"]: d for d in qcc if d.get("法人") and d.get("登记状态")}
    baidu_map = {}
    if baidu_path:
        baidu = json.load(open(baidu_path, encoding="utf-8"))
        baidu_map = {d["公司"]: d for d in baidu}
    names = []
    for d in qcc:
        if d["公司"] not in names:
            names.append(d["公司"])
    for n in baidu_map:
        if n not in names:
            names.append(n)
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Sheet1"
    ws.append(["公司名称", "法人", "联系方式", "注册地址", "经营内容", "是否异常", "异常原因", "登记状态", "数据来源"])
    auth = ref = 0
    for n in names:
        if n in qcc_map:
            d = qcc_map[n]
            abn, reason = fix_exception(d)
            ws.append([n, d.get("法人", ""), d.get("联系方式", ""), d.get("注册地址", ""), "", abn, reason, d.get("登记状态", ""), "企查查MCP(权威)"])
            auth += 1
        elif n in baidu_map:
            b = baidu_map[n]
            phones = "; ".join(b.get("电话", []) or [])
            abn = "是" if b.get("异常") else ""
            ws.append([n, b.get("法人", "") or "", phones, b.get("地址", "") or "", "", abn, b.get("异常", "") or "", b.get("状态", "") or "", "浏览器(参考, 法人/状态待权威补)"])
            ref += 1
        else:
            ws.append([n, "", "", "", "", "", "", "", "无数据"])
    wb.save(out)
    print(f"合并完成 -> {out}: 权威{auth} + 参考{ref} + 无数据{len(names)-auth-ref} = {len(names)}家")

if __name__ == "__main__":
    main()
