"""Autoroute the Bolty Mood Module board with Freerouting.

    python autoroute.py export   -> strips tracks, adds LED cut-out keep-outs, writes work/board.dsn
                                    (zones left out so GND is routed as a normal net)
    python autoroute.py import   -> strips tracks, adds keep-outs, imports work/board.ses,
                                    refills GND pours, saves the board

Run with KiCad's Python. Freerouting itself runs in between:
    freerouting.exe --gui.enabled=false -de work/board.dsn -do work/board.ses
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.normpath(os.path.join(HERE, "..", "kicad", "bolty-mood-module.kicad_pcb"))
WORK = r"H:\Tools\Freerouting\work"
KEEPOUT_MARGIN = 0.21  # mm around each LED light cut-out (pads sit 0.25 mm away)


def zones(board):
    return [board.GetArea(i) for i in range(board.GetAreaCount())]


def clear_tracks(board):
    for t in list(board.GetTracks()):
        board.Delete(t)


def add_cutout_keepouts(board):
    for z in zones(board):
        if z.GetIsRuleArea() and z.GetZoneName().startswith("cutout_"):
            board.Delete(z)  # Remove() here crashes the next GetFootprints() call
    m = pcbnew.FromMM(KEEPOUT_MARGIN)
    for fp in board.GetFootprints():
        cuts = [g for g in fp.GraphicalItems() if g.GetLayer() == pcbnew.Edge_Cuts]
        if not cuts:
            continue
        box = cuts[0].GetBoundingBox()
        for g in cuts[1:]:
            box.Merge(g.GetBoundingBox())
        box.Inflate(m)
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetZoneName(f"cutout_{fp.GetReference()}")
        ls = pcbnew.LSET()
        ls.AddLayer(pcbnew.F_Cu)
        ls.AddLayer(pcbnew.B_Cu)
        z.SetLayerSet(ls)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowZoneFills(False)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        ol = z.Outline()
        ol.NewOutline()
        x0, y0, x1, y1 = box.GetLeft(), box.GetTop(), box.GetRight(), box.GetBottom()
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            ol.Append(pcbnew.VECTOR2I(x, y))
        board.Add(z)


def main(mode):
    board = pcbnew.LoadBoard(PCB)
    clear_tracks(board)
    add_cutout_keepouts(board)
    if mode == "export":
        for z in zones(board):
            if not z.GetIsRuleArea():
                board.Remove(z)
        ok = pcbnew.ExportSpecctraDSN(board, os.path.join(WORK, "board.dsn"))
        print("exported DSN:", ok)  # board itself is not saved
    elif mode == "import":
        ok = pcbnew.ImportSpecctraSES(board, os.path.join(WORK, "board.ses"))
        print("imported SES:", ok)
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        pcbnew.SaveBoard(PCB, board)
        tr = list(board.GetTracks())
        print("tracks", sum(t.GetClass() == "PCB_TRACK" for t in tr), "vias", sum(t.GetClass() == "PCB_VIA" for t in tr))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
