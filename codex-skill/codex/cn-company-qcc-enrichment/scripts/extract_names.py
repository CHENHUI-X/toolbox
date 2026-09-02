#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从任意Excel提取公司名称列 (自动识别"公司名称/企业名称/客户名称/单位名称/名称"列)
用法: python3 extract_names.py <xlsx> [sheet名] [输出.txt]
"""
import sys, openpyxl

def main():
    xlsx = sys.argv[1]
    sheet = sys.argv[2] if len(sys.argv) > 2 else None
    out = sys.argv[3] if len(sys.argv) > 3 else None
    wb = openpyxl.load_workbook(xlsx, read_only=True)
    ws = wb[sheet] if sheet else wb.active
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0] if rows else []
    name_col = 0
    for i, h in enumerate(header):
        if h and any(k in str(h) for k in ("公司名称", "企业名称", "客户名称", "单位名称", "名称")):
            name_col = i
            break
    names = []
    for r in rows[1:]:
        v = r[name_col] if name_col < len(r) else None
        if v and str(v).strip():
            names.append(str(v).strip())
    text = "\n".join(names)
    if out:
        open(out, "w", encoding="utf-8").write(text)
        print(f"提取 {len(names)} 家 -> {out}")
    else:
        print(text)
    wb.close()

if __name__ == "__main__":
    main()
