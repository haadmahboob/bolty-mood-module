"""8-pin grant prep:
 1. Swap SW1 to the C&K PTS645 footprint (DigiKey stocks it; the HYP 1TS009 is LCSC-only).
 2. Add "Part Number" + "Manufacturer" fields to every schematic symbol and PCB footprint,
    so the KiCad BOM export can be uploaded to DigiKey.
Run with KiCad's python:  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" tools/add_part_numbers.py
"""
import os
import re

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
KDIR = os.path.join(HERE, "..", "kicad")
SCH = os.path.join(KDIR, "bolty-mood-module.kicad_sch")
PCB = os.path.join(KDIR, "bolty-mood-module.kicad_pcb")

OLD_SW = "Button_Switch_SMD:SW_Push_1TS009xxxx-xxxx-xxxx_6x6x5mm"
NEW_SW_LIB, NEW_SW_NAME = "Button_Switch_SMD", "SW_SPST_PTS645Sx43SMTR92"

# reference prefix / exact ref -> (manufacturer, MPN)
PARTS = {
    "U1": ("Microchip", "ATTINY85-20SU"),
    "D13": ("Diodes Inc.", "1N4148W-7-F"),
    "D": ("Adafruit", "4960"),  # SK6812MINI-E reverse-mount, sold in 10-packs on DigiKey
    "Q1": ("onsemi", "MMBT3904LT1G"),
    "BZ1": ("Same Sky", "CMT-8504-100-SMT-TR"),
    "SW1": ("C&K", "PTS645SM43SMTR92 LFS"),
    "J1": ("JST", "B4B-PH-K-S(LF)(SN)"),
    "C1": ("Samsung", "CL21A106KAYNNNE"),
    "C": ("Samsung", "CL10B104KB8NNNC"),
    "R1": ("Yageo", "RC0603FR-0710KL"),
    "R2": ("Yageo", "RC0603FR-071KL"),
    "R3": ("Yageo", "RC0603FR-07330RL"),
    "R4": ("Yageo", "RC0603FR-074K7L"),
    "R5": ("Yageo", "RC0603FR-074K7L"),
}


def part_for(ref):
    if ref in PARTS:
        return PARTS[ref]
    prefix = re.match(r"[A-Z]+", ref).group(0)
    return PARTS.get(prefix)


def prop_block(name, value, at):
    return (f'\t\t(property "{name}" "{value}"\n\t\t\t(at {at})\n\t\t\t(effects\n\t\t\t\t(font\n'
            f'\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n')


def do_schematic():
    text = open(SCH, encoding="utf-8").read()
    text = text.replace(OLD_SW, f"{NEW_SW_LIB}:{NEW_SW_NAME}")
    out, pos, added = [], 0, 0
    # each placed symbol: "(symbol\n\t\t(lib_id ...)\n\t\t(at X Y R)" ... "(property "Reference" "REF""
    for m in re.finditer(r'\n\t\(symbol\n\t\t\(lib_id "[^"]+"\)\n\t\t\(at ([^)]+)\)', text):
        start = m.start()
        ref_m = re.compile(r'\n\t\t\(property "Reference" "([^"]+)"').search(text, start)
        ref = ref_m.group(1)
        if ref.startswith("#"):
            continue
        part = part_for(ref)
        if not part:
            continue
        seg_end = text.find('\n\t(symbol\n', start + 1)
        seg = text[start: seg_end if seg_end > 0 else len(text)]
        if '"Part Number"' in seg:
            continue
        at = m.group(1)
        ins = ref_m.start() + 1
        out.append(text[pos:ins])
        out.append(prop_block("Manufacturer", part[0], at) + prop_block("Part Number", part[1], at))
        pos = ins
        added += 1
    out.append(text[pos:])
    open(SCH, "w", encoding="utf-8", newline="\n").write("".join(out))
    print("schematic: fields added to", added, "symbols")


def set_field(fp, name, value):
    fp.SetField(name, value)  # creates the field if missing
    f = fp.GetField(name)
    f.SetVisible(False)
    f.SetLayer(pcbnew.B_Fab if fp.GetLayer() == pcbnew.B_Cu else pcbnew.F_Fab)


def do_pcb():
    board = pcbnew.LoadBoard(PCB)
    old = board.FindFootprintByReference("SW1")
    if old.GetFPID().GetLibItemName() != NEW_SW_NAME:
        lib_dir = os.path.join(os.environ.get("KICAD10_FOOTPRINT_DIR",
                               r"C:\Program Files\KiCad\10.0\share\kicad\footprints"), NEW_SW_LIB + ".pretty")
        new = pcbnew.FootprintLoad(lib_dir, NEW_SW_NAME)
        new.SetFPID(pcbnew.LIB_ID(NEW_SW_LIB, NEW_SW_NAME))
        board.Add(new)
        if old.GetLayer() == pcbnew.B_Cu:
            new.Flip(new.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        new.SetOrientation(old.GetOrientation())
        new.SetPosition(old.GetPosition())
        new.SetReference("SW1")
        new.SetValue(old.GetValue())
        new.Reference().SetPosition(old.Reference().GetPosition())
        new.Reference().SetVisible(old.Reference().IsVisible())
        new.Value().SetVisible(False)
        new.SetPath(old.GetPath())
        new.SetSheetname(old.GetSheetname())
        new.SetSheetfile(old.GetSheetfile())
        for name in ("Datasheet", "Description"):
            if old.HasField(name):
                set_field(new, name, old.GetFieldText(name))
        nets = {p.GetNumber(): p.GetNet() for p in old.Pads()}
        for p in new.Pads():
            p.SetNet(nets[p.GetNumber()])
        board.Remove(old)
        print("SW1 swapped at", new.GetPosition(), "layer", new.GetLayerName())
    n = 0
    for fp in board.GetFootprints():
        part = part_for(fp.GetReference())
        if part:
            set_field(fp, "Manufacturer", part[0])
            set_field(fp, "Part Number", part[1])
            n += 1
    board.BuildConnectivity()
    for z in board.Zones():
        z.UnFill()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)
    print("pcb: fields set on", n, "footprints")


if __name__ == "__main__":
    do_schematic()
    do_pcb()
