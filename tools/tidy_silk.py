"""Silkscreen tidy-up for assembly. Run with KiCad's Python while the board is closed.

- LED and LED-cap references (D1-D12, C3-C8) have no room on silk between the
  packed LEDs: hide them on silk; they stay on the Fab layer for the assembly drawing.
- Remaining back-side references shrink to 0.8 mm text.
"""
import os

import pcbnew

PCB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kicad",
                                    "bolty-mood-module.kicad_pcb"))
HIDE = {f"D{n}" for n in range(1, 13)} | {f"C{n}" for n in range(3, 9)} | {"R2", "J2"}

b = pcbnew.LoadBoard(PCB)
for fp in b.GetFootprints():
    ref = fp.Reference()
    if fp.GetReference() in HIDE:
        ref.SetVisible(False)
    else:
        ref.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.8), pcbnew.FromMM(0.8)))
        ref.SetTextThickness(pcbnew.FromMM(0.12))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print("hidden refs:", sorted(HIDE))
