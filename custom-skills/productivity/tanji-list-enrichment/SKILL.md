---
name: tanji-list-enrichment
description: "Use when mom sends an Excel list needing 经营内容 per company."
version: 1.0.0
author: Hermes
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [excel, xlsx, 探迹, 名单, 经营内容, 陌拜, 易盘点, weixin]
---

# 探迹名单经营内容补全

## 触发条件

用户（Parker）或妈妈通过微信发来一个 **Excel/CSV 名单文件**（探迹名单），列通常含：公司名称、法人、电话、地址等。要求：**在"经营内容"列填入每个公司的经营内容**，然后返回填好的文件。

## 核心规则（用户明确要求）

1. **保留名单原有列，不新增列、不拆列** —— 公司名称、法人、电话等保持原样
2. **所有内容全部填进"经营内容"这一列** —— 一格里塞进陌拜 md 文件（如 `/home/projects/hermes-knowledge/易盘点客户/辽宁北软.md`）的全部要点，用换行分块：
   - 【公司概况】成立时间、注册主体、地址、规模
   - 【主营业务】分点列举（这公司是干什么的）
   - 【行业地位】龙头/客户量/市场占有率/资质荣誉（干得怎么样）
   - 【相关人员/对接】法定代表人、董事长/实控人、关键联系人、对接渠道（总机、企业QQ、供应商平台、销售邮箱等）
   - 【结合易盘点的切入话术】这家公司业务怎么跟固定资产管理（易盘点）结合——客户群是否重资产、有无资产盘点/维保/审计需求、适合什么合作方式（方案打包/渠道分润/生态平台入驻/免费试点），写一段可直接用的切入话术
3. **逐公司 web_search** 搜真实信息（官网、企查查/爱企查、年报、新闻），不要编造
4. 找不到信息的公司，经营内容填"⚠️ 未检索到公开经营信息"
5. 如果名单里缺法人/电话等列，只填经营内容即可，其它空着不用补

## 执行步骤

### 1. 读取名单文件
- `.xlsx`：优先 `read_file`（Hermes 自动提取）；若提取为空，用 terminal python3 + zipfile 解析
- `.csv`：read_file 直接读
- 识别列名：找到公司名称列（"公司"/"公司名称"/"企业名称"）、"经营内容"列（可能为空或不存在，需新增）

### 2. 逐公司搜索 + 填内容
对每个公司：
- `web_search` 查询：`<公司名> 主营业务 经营范围 简介`
- 必要时再补一条：`<公司名> 官网 行业地位`
- 提炼成一段：分点主营业务 + 行业地位/亮点
- 填入该行"经营内容"列

### 3. 生成新 Excel
- 用 zipfile 手写 xlsx（openpyxl 在 Hermes sandbox 不可用），见下方脚本模板
- 文件名：`探迹名单经营内容_YYYYMMDD.xlsx`，存 `/tmp/`
- 验证：zip 完整性 + XML 可解析

### 4. 交付
- **Telegram 端**：直接 `MEDIA:/tmp/xxx.xlsx` 发送
- **微信端（妈妈）**：
  1. 先试 `hermes send --to "weixin:<邮箱/ID>" "MEDIA:路径"` 直接发文件
  2. 发不了（iLink 不支持文件/限流）→ **传临时网盘**：
     - `curl -F "file=@/tmp/xxx.xlsx" https://file.io`（返回 link 字段）
     - 或 `curl -F "file=@/tmp/xxx.xlsx" https://0x0.st`
     - 或 `curl --upload-file /tmp/xxx.xlsx https://transfer.sh/探迹名单.xlsx`
  3. 把**下载链接**发给妈妈，提示"点开链接下载即可"

## xlsx 生成脚本模板（zipfile 手写，无需 openpyxl）

```python
import zipfile, os

def make_xlsx(path, headers, rows):
    all_strs = list(headers)
    for row in rows:
        for v in row:
            if isinstance(v, str) and v not in all_strs:
                all_strs.append(v)
    ss_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    ss_xml += '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="%d" uniqueCount="%d">' % (len(all_strs), len(all_strs))
    for s in all_strs:
        ss_xml += '<si><t>%s</t></si>' % s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
    ss_xml += '</sst>'

    def cell_ref(col, row):
        col_letter = ''; c = col
        while c > 0:
            c, rem = divmod(c-1, 26)
            col_letter = chr(65+rem) + col_letter
        return f'{col_letter}{row}'

    data = '<sheetData><row r="1">'
    for ci, h in enumerate(headers, 1):
        data += f'<c r="{cell_ref(ci,1)}" t="s"><v>{all_strs.index(h)}</v></c>'
    data += '</row>'
    for ri, row in enumerate(rows, 2):
        data += f'<row r="{ri}">'
        for ci, v in enumerate(row, 1):
            if isinstance(v, str):
                data += f'<c r="{cell_ref(ci,ri)}" t="s"><v>{all_strs.index(v)}</v></c>'
            else:
                data += f'<c r="{cell_ref(ci,ri)}"><v>{v}</v></c>'
        data += '</row>'
    data += '</sheetData>'

    sheet_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<dimension ref="A1:D{len(rows)+1}"/>
<sheetViews><sheetView workbookViewId="0"/></sheetViews>
<sheetFormatPr defaultRowHeight="15"/>
{data}
</worksheet>'''

    workbook_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="探迹名单" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''
    rels_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>
</Relationships>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>'''

    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', content_types)
        z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml', workbook_xml)
        z.writestr('xl/_rels/workbook.xml.rels', rels_xml)
        z.writestr('xl/worksheets/sheet1.xml', sheet_xml)
        z.writestr('xl/sharedStrings.xml', ss_xml)
```

## 陷阱与注意

- ⚠️ 文件名含中文时 transfer.sh 可能报错，改用 file.io 或 0x0.st，或先改英文名
- ⚠️ openpyxl 在 Hermes sandbox 不可用 —— 用 zipfile 手写 xlsx（见上方模板）
- ⚠️ 妈妈发的 xlsx 可能是空模板（openpyxl 生成无数据）—— 先确认有行数据再动手，没有就找用户要
- ⚠️ 批量公司（20+）时：分批搜索，先做完一批再下一批，避免单次超时
- 微信发送注意 iLink 限流：文件发送失败不要重试轰炸，直接转网盘链接方案
