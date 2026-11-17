"""Post-route fixes. Run with KiCad's Python while no KiCad window has the board open.

1. Widen track pieces Freerouting necked below 0.1524 mm (OSH Park 6 mil minimum).
2. Set the Power net class clearance to 0.1524 mm in the project file. This runs
   AFTER pcbnew has released the project, because pcbnew rewrites .kicad_pro on exit.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.normpath(os.path.join(HERE, "..", "kicad"))
PCB = os.path.join(PRJ, "bolty-mood-module.kicad_pcb")
PRO = os.path.join(PRJ, "bolty-mood-module.kicad_pro")

WIDEN = r'''
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
mn = pcbnew.FromMM(0.1524)
n = 0
for t in b.GetTracks():
    if t.GetClass() == "PCB_TRACK" and t.GetWidth() < mn:
        t.SetWidth(mn); n += 1
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(sys.argv[1], b)
print("widened", n)
'''

subprocess.run([sys.executable, "-c", WIDEN, PCB], check=True)

with open(PRO, encoding="utf-8") as fh:
    pro = json.load(fh)
for c in pro["net_settings"]["classes"]:
    if c.get("name") in ("Default", "Power"):
        c["clearance"] = 0.1524
with open(PRO, "w", encoding="utf-8") as fh:
    json.dump(pro, fh, indent=2)
print("clearances:", {c["name"]: c["clearance"] for c in pro["net_settings"]["classes"]})
