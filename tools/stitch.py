"""Add GND stitching vias on a grid wherever both GND pours are solid copper.
Run with KiCad's Python while the board is closed in KiCad."""
import math
import os

import pcbnew

PCB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kicad",
                                    "bolty-mood-module.kicad_pcb"))
CX, CY = 100.0, 100.0
PITCH = 2.5        # candidate grid (mm); keep vias >= ~5 mm apart
MIN_SPACING = 4.5
VIA_D, VIA_DRILL = 0.6, 0.3
MARGIN = 0.5       # extra solid copper required around the via (mm)

b = pcbnew.LoadBoard(PCB)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
gnd = b.FindNet("GND")
pours = [b.GetArea(i) for i in range(b.GetAreaCount())]
pours = [z for z in pours if not z.GetIsRuleArea() and z.GetNetname() == "GND"]
existing = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
placed = [(pcbnew.ToMM(v.GetPosition().x), pcbnew.ToMM(v.GetPosition().y)) for v in existing
          if v.GetNetname() == "GND"]

r_check = VIA_D / 2 + MARGIN
ring = [(r_check * math.cos(a), r_check * math.sin(a)) for a in [i * math.pi / 4 for i in range(8)]] + [(0, 0)]


def solid(x, y):
    for z in pours:
        for dx, dy in ring:
            if not z.HitTestFilledArea(z.GetLayer(), pcbnew.VECTOR2I(pcbnew.FromMM(x + dx), pcbnew.FromMM(y + dy))):
                return False
    return True


added = 0
steps = int(18 / PITCH)
for i in range(-steps, steps + 1):
    for j in range(-steps, steps + 1):
        x, y = CX + i * PITCH, CY + j * PITCH
        if math.hypot(x - CX, y - CY) > 17.5:
            continue
        if any(math.hypot(x - px, y - py) < MIN_SPACING for px, py in placed):
            continue
        if not solid(x, y):
            continue
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        v.SetWidth(pcbnew.FromMM(VIA_D))
        v.SetDrill(pcbnew.FromMM(VIA_DRILL))
        v.SetNet(gnd)
        b.Add(v)
        placed.append((x, y))
        added += 1

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print("stitching vias added:", added)
