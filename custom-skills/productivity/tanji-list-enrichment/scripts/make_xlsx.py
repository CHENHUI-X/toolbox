#!/usr/bin/env python3
"""手写 xlsx（zipfile，无需 openpyxl）— 供探迹名单经营内容补全使用"""
import zipfile, os, sys

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
    print(f"已生成: {path} ({os.path.getsize(path)} bytes)")

if __name__ == "__main__":
    # 用法: python3 make_xlsx.py <输出路径> <JSON文件(含headers和rows)>
    out = sys.argv[1]
    import json
    with open(sys.argv[2]) as f:
        data = json.load(f)
    make_xlsx(out, data["headers"], data["rows"])
