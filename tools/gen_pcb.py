"""Create the Bolty Mood Module board: 40 mm round outline, every footprint from the
schematic netlist placed, nets assigned, GND pours on both layers. Routing is left
to do by hand in KiCad.

Run with KiCad's Python after gen_schematic.py and a netlist export:
    kicad-cli sch export netlist -o ../kicad/bolty-mood-module.net ../kicad/bolty-mood-module.kicad_sch
    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" gen_pcb.py

WARNING: overwrites ../kicad/bolty-mood-module.kicad_pcb (refuses if it exists,
unless --force is given), so hand placement/routing would be lost.
"""
import json
import math
import os
import sys

import pcbnew

import kisym
from kisym import child, children

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.normpath(os.path.join(HERE, "..", "kicad"))
NAME = "bolty-mood-module"
FP_ROOT = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"

CX, CY, R = 100.0, 100.0, 20.0  # board centre and radius (mm)

# ------------------------------------------------------------------ placement
# ref: (x, y, rotation_deg, side). Coordinates are seen from the FRONT (the face).
# Position = courtyard centre. side "B" = back (flipped).
PLACE = {}

# Eyes: 3 columns x 2 rows per eye, LED long axis vertical, caps between the rows.
COLS = (-4.3, 0.0, 4.3)
EYE_Y = 95.0
ROW_DY = 4.7
# data chain snakes down/up the columns: D1 top-left of the left eye ... D12
order = []
for eye_x in (93.0, 107.0):
    for ci, dx in enumerate(COLS):
        rows = (-ROW_DY, ROW_DY)
        # left eye: col0 down, col1 up, col2 down; right eye: col0 up, col1 down, col2 up
        down = (ci % 2 == 0) if eye_x < 100 else (ci % 2 == 1)
        for dy in (rows if down else rows[::-1]):
            order.append((eye_x + dx, EYE_Y + dy))
for n, (x, y) in enumerate(order, start=1):
    PLACE[f"D{n}"] = (x, y, 90, "B")
cap_refs = [f"C{k}" for k in range(3, 9)]
cap_pos = [(ex + dx, EYE_Y) for ex in (93.0, 107.0) for dx in COLS]
for ref, (x, y) in zip(cap_refs, cap_pos):
    PLACE[ref] = (x, y, 0, "B")

PLACE.update({
    "J1": (100.0, 83.4, 0, "B"),     # I2C connector, top edge
    "C1": (90.0, 85.3, 0, "B"),      # 10u bulk next to J1
    "H1": (83.5, 95.0, 0, "B"),
    "H2": (116.5, 95.0, 0, "B"),
    "BZ1": (100.0, 111.0, 0, "B"),
    "U1": (88.6, 107.6, 0, "B"),
    "C2": (84.5, 102.6, 90, "B"),    # U1 decoupling, near VCC
    "R1": (88.0, 112.0, 0, "B"),
    "R3": (92.0, 112.0, 0, "B"),
    "R4": (89.0, 114.2, 0, "B"),
    "R5": (92.6, 114.2, 0, "B"),
    "J2": (109.8, 109.0, 0, "B"),    # ISP pads
    "Q1": (115.6, 106.5, 0, "B"),
    "R2": (114.4, 110.4, 0, "B"),
    "D13": (100.0, 117.6, 0, "B"),
    "SW1": (100.0, 112.5, 0, "F"),   # pat button on the face ("chin")
})


def mm(v):
    return pcbnew.FromMM(v)


def vec(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def load_netlist(path):
    tree = kisym.parse(open(path, encoding="utf-8").read())
    comps = {}
    for c in children(child(tree, "components"), "comp"):
        ref = child(c, "ref")[1]
        comps[ref] = {
            "value": child(c, "value")[1],
            "footprint": child(c, "footprint")[1] if child(c, "footprint") else "",
            "uuid": child(c, "tstamps")[1],
            "dnp": any(child(p, "name")[1] == "dnp" for p in children(c, "property")),
            "fields": {child(f, "name")[1]: (f[2] if len(f) > 2 else "")
                       for f in children(child(c, "fields") or [], "field")},
        }
    nets = {}
    for n in children(child(tree, "nets"), "net"):
        name = child(n, "name")[1]
        for node in children(n, "node"):
            nets[(child(node, "ref")[1], child(node, "pin")[1])] = name
    return comps, nets


def load_fp(fpid):
    lib, name = fpid.split(":")
    path = os.path.join(PRJ, lib + ".pretty") if lib == "Bolty" else os.path.join(FP_ROOT, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit(f"footprint not found: {fpid}")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    # some library footprints carry a literal "REF**" silk text on top of the real reference
    for g in list(fp.GraphicalItems()):
        if isinstance(g, pcbnew.PCB_TEXT) and g.GetText() == "REF**":
            fp.Remove(g)
    return fp


def courtyard_box(fp):
    layer = pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd
    poly = fp.GetCourtyard(layer)
    if poly.OutlineCount() == 0:
        return fp.GetBoundingBox(False)
    return poly.BBox()


def circle_poly(r, n=96):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        pts.append(vec(CX + r * math.cos(a), CY + r * math.sin(a)))
    return pts


def main():
    out = os.path.join(PRJ, NAME + ".kicad_pcb")
    if os.path.exists(out) and "--force" not in sys.argv:
        raise SystemExit(f"{out} exists; re-run with --force to overwrite it")
    comps, pinnets = load_netlist(os.path.join(PRJ, NAME + ".net"))
    missing = set(comps) - set(PLACE)
    if missing:
        raise SystemExit(f"no placement for: {sorted(missing)}")

    board = pcbnew.NewBoard(out)
    board.SetCopperLayerCount(2)

    netinfo = {}
    for name in sorted(set(pinnets.values())):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni

    for ref, c in sorted(comps.items()):
        fp = load_fp(c["footprint"])
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH("/" + c["uuid"]))
        fp.SetSheetname("/")
        fp.SetSheetfile(NAME + ".kicad_sch")
        for fname, ftype in (("Datasheet", pcbnew.FIELD_T_DATASHEET),
                             ("Description", pcbnew.FIELD_T_DESCRIPTION)):
            if fname in c["fields"]:
                fp.GetField(ftype).SetText(c["fields"][fname])
        if c["dnp"]:
            fp.SetDNP(True)
        board.Add(fp)
        x, y, rot, side = PLACE[ref]
        fp.SetPosition(vec(x, y))
        fp.SetOrientationDegrees(rot)
        if side == "B":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        # shift so the courtyard centre lands on the requested point
        box = courtyard_box(fp)
        c_now = box.GetCenter()
        fp.Move(pcbnew.VECTOR2I(vec(x, y).x - c_now.x, vec(x, y).y - c_now.y))
        for pad in fp.Pads():
            net = pinnets.get((ref, pad.GetNumber()))
            if net:
                pad.SetNet(netinfo[net])

    # board outline
    edge = pcbnew.PCB_SHAPE(board)
    edge.SetShape(pcbnew.SHAPE_T_CIRCLE)
    edge.SetCenter(vec(CX, CY))
    edge.SetEnd(vec(CX + R, CY))
    edge.SetLayer(pcbnew.Edge_Cuts)
    edge.SetWidth(mm(0.1))
    board.Add(edge)

    # GND pour on both copper layers
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(netinfo["GND"])
        z.SetLocalClearance(mm(0.25))
        z.SetMinThickness(mm(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.3))
        z.SetThermalReliefSpokeWidth(mm(0.3))
        ol = z.Outline()
        ol.NewOutline()
        for p in circle_poly(R - 0.3):
            ol.Append(p)
        board.Add(z)

    # back silkscreen
    def silk(text_s, x, y, size=1.0, layer=pcbnew.B_SilkS):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text_s)
        t.SetPosition(vec(x, y))
        t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        t.SetTextThickness(mm(size * 0.15))
        if layer == pcbnew.B_SilkS:
            t.SetMirrored(True)
        board.Add(t)

    silk("BOLTY", 110.0, 84.6, 0.8)
    silk("0x42", 91.4, 83.0, 0.8)

    ds = board.GetDesignSettings()
    ds.m_TrackMinWidth = mm(0.1524)
    ds.m_MinClearance = mm(0.1524)
    ds.m_MinThroughDrill = mm(0.254)
    ds.m_ViasMinSize = mm(0.5)
    ds.m_CopperEdgeClearance = mm(0.3)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(out, board)
    set_netclasses(os.path.join(PRJ, NAME + ".kicad_pro"))
    print("wrote", out)


def set_netclasses(pro_path):
    with open(pro_path, encoding="utf-8") as fh:
        pro = json.load(fh)
    ns = pro.setdefault("net_settings", {})
    classes = ns.setdefault("classes", [])
    default = next((c for c in classes if c.get("name") == "Default"), None)
    if default is None:
        default = {"name": "Default"}
        classes.append(default)
    default.update({"track_width": 0.25, "clearance": 0.1524, "via_diameter": 0.6, "via_drill": 0.3})
    power = next((c for c in classes if c.get("name") == "Power"), None)
    if power is None:
        power = dict(default, name="Power")
        classes.append(power)
    power.update({"track_width": 0.5, "clearance": 0.1524, "via_diameter": 0.8, "via_drill": 0.4})
    ns["netclass_patterns"] = [{"netclass": "Power", "pattern": "+5V"}, {"netclass": "Power", "pattern": "GND"}]
    # SK6812MINI-E reverse-mount pads sit 0.25 mm from their own light cut-out
    rules = pro.setdefault("board", {}).setdefault("design_settings", {}).setdefault("rules", {})
    rules.update({"min_copper_edge_clearance": 0.2, "min_track_width": 0.1524, "min_clearance": 0.1524,
                  "min_through_hole_diameter": 0.254, "min_via_diameter": 0.5, "min_hole_clearance": 0.25})
    with open(pro_path, "w", encoding="utf-8") as fh:
        json.dump(pro, fh, indent=2)


if __name__ == "__main__":
    main()
