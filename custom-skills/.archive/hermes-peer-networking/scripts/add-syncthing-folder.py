#!/usr/bin/env python3
"""给 Syncthing 增加共享文件夹（以现有 folder 为模板复制设备列表）。

用法（必须先停服务，避免运行中的 Syncthing 回写覆盖）：
  systemctl stop syncthing
  python3 add-syncthing-folder.py --id skills --path /root/.hermes/skills
  systemctl start syncthing

两边机器用同样的 --id/--path；启动后目录会出现 .stfolder 并开始对传。
config.xml 写盘前自动备份到同目录 *.bak-<时间戳>。
"""
import argparse
import shutil
import sys
import time
import xml.etree.ElementTree as ET

CFG = "/root/.local/state/syncthing/config.xml"

ap = argparse.ArgumentParser()
ap.add_argument("--id", default="skills")
ap.add_argument("--label", default="skills")
ap.add_argument("--path", default="/root/.hermes/skills")
ap.add_argument("--template", default="kb", help="用作模板的现有 folder id（复制其设备列表）")
args = ap.parse_args()

tree = ET.parse(CFG)
root = tree.getroot()

for f in root.findall("folder"):
    if f.get("id") == args.id:
        print("ALREADY_EXISTS", f.get("id"), f.get("path"))
        sys.exit(0)
    if f.get("path") == args.path:
        print("PATH_ALREADY_SHARED_AS", f.get("id"), f.get("path"))
        sys.exit(0)

tpl = None
for f in root.findall("folder"):
    if f.get("id") == args.template:
        tpl = f
if tpl is None:
    print("NO_TEMPLATE", args.template)
    sys.exit(1)

new = ET.fromstring(ET.tostring(tpl))
new.set("id", args.id)
new.set("label", args.label)
new.set("path", args.path)
root.append(new)

backup = CFG + ".bak-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy2(CFG, backup)
tree.write(CFG, encoding="utf-8", xml_declaration=True)
print("ADDED", args.id, args.path, "| devices:", [d.get("id", "")[:12] for d in new.findall("device")], "| backup:", backup)
