"""Generate the Bolty Mood Module KiCad project (schematic + project-local symbol lib).

Run with KiCad's Python:
    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" gen_schematic.py

Every component pin is joined with a short wire stub to a net label or power
symbol, so the netlist is defined entirely by the CONNECTIONS below. Source of
truth for the circuit: ../DESIGN.md.
"""
import copy
import json
import math
import os
import uuid

import kisym
from kisym import Sym, child, children, dump

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "kicad")
NAME = "bolty-mood-module"
SCH_VERSION = 20250610
STUB = 2.54

ROOT_UUID = str(uuid.uuid5(uuid.NAMESPACE_URL, "bolty-mood-module/root"))
_uid_n = 0


def uid():
    global _uid_n
    _uid_n += 1
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"bolty-mood-module/{_uid_n}"))


FP = {
    "R": "Resistor_SMD:R_0603_1608Metric",
    "C": "Capacitor_SMD:C_0603_1608Metric",
    "C0805": "Capacitor_SMD:C_0805_2012Metric",
    "LED": "LED_SMD:LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount",
    "U": "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm",
    "Q": "Package_TO_SOT_SMD:SOT-23",
    "D": "Diode_SMD:D_SOD-123",
    "SW": "Button_Switch_SMD:SW_Push_1TS009xxxx-xxxx-xxxx_6x6x5mm",
    "J1": "Connector_JST:JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical",
    "ISP": "Bolty:ISP_Pads_2x3_P2.54mm",  # bare pads for a pogo-pin ISP clip, bottom side
    "BZ": "Buzzer_Beeper:MagneticBuzzer_CUI_CMT-8504-100-SMT",  # pad 1 +, pad 2 -, pads 3/4 dummy (datasheet)
}

# ---------------------------------------------------------------- symbols

def make_sk6812mini_e():
    """SK6812MINI-E: same body as LED:SK6812MINI, but pin numbers follow the
    MINI-E datasheet (1 VDD, 2 DOUT, 3 VSS, 4 DIN), which is what KiCad's
    LED_SK6812MINI-E footprint pads use."""
    sym = kisym.get_symbol("LED:SK6812MINI")
    renumber = {"1": "2", "2": "3", "3": "4", "4": "1"}

    def walk(node):
        for x in node:
            if isinstance(x, list):
                if kisym.head(x) == "symbol" and isinstance(x[1], str):
                    x[1] = x[1].replace("SK6812MINI", "SK6812MINI-E")
                if kisym.head(x) == "pin":
                    num = child(x, "number")
                    num[1] = renumber[num[1]]
                walk(x)

    walk(sym)
    sym[1] = "SK6812MINI-E"
    for p in children(sym, "property"):
        if p[1] == "Value":
            p[2] = "SK6812MINI-E"
        elif p[1] == "Footprint":
            p[2] = FP["LED"]
        elif p[1] == "Datasheet":
            p[2] = "https://www.lcsc.com/datasheet/C5149201.pdf"
        elif p[1] == "Description":
            p[2] = "RGB LED with integrated driver, reverse-mount, 3.2x2.8 mm"
        elif p[1] == "ki_fp_filters":
            p[2] = "LED*SK6812MINI*E*"
    return sym


LIB_SYMBOLS = {}  # lib_id -> flattened symbol (named with lib_id)


def lib_symbol(lib_id):
    if lib_id not in LIB_SYMBOLS:
        if lib_id == "Bolty:SK6812MINI-E":
            sym = make_sk6812mini_e()
            sym[1] = lib_id
        else:
            sym = kisym.get_symbol(lib_id)
        LIB_SYMBOLS[lib_id] = sym
    return LIB_SYMBOLS[lib_id]


# ---------------------------------------------------------------- schematic items

ITEMS = []
_pwr_n = 0


def snap(v):
    return round(v / 1.27) * 1.27


def eff(size=1.27, justify=None, hide=False, bold=False):
    font = [Sym("font"), [Sym("size"), size, size]]
    if bold:
        font.append([Sym("bold"), Sym("yes")])
    e = [Sym("effects"), font]
    if justify:
        e.append([Sym("justify")] + [Sym(j) for j in justify.split()])
    if hide:
        e.append([Sym("hide"), Sym("yes")])
    return e


def to_sch(x, y, lx, ly):
    return (x + lx, y - ly)


def place(ref, lib_id, value, x, y, footprint="", nets=None, nc=(), dnp=False,
          in_bom=True, on_board=True, fields_hidden=False):
    """Place a symbol (no rotation) and stub every pin listed in nets."""
    sym = lib_symbol(lib_id)
    lib_props = {p[1]: p for p in children(sym, "property")}
    is_power = child(sym, "power") is not None

    node = [Sym("symbol"), [Sym("lib_id"), lib_id], [Sym("at"), x, y, 0], [Sym("unit"), 1],
            [Sym("exclude_from_sim"), Sym("no")],
            [Sym("in_bom"), Sym("yes" if in_bom else "no")],
            [Sym("on_board"), Sym("yes" if on_board else "no")],
            [Sym("dnp"), Sym("yes" if dnp else "no")],
            [Sym("uuid"), uid()]]
    values = {"Reference": ref, "Value": value,
              "Footprint": footprint or lib_props.get("Footprint", [0, 0, ""])[2],
              "Datasheet": lib_props.get("Datasheet", [0, 0, ""])[2],
              "Description": lib_props.get("Description", [0, 0, ""])[2]}
    for key, val in values.items():
        lp = lib_props.get(key)
        fang = 0
        if lib_id == "Device:R" and key in ("Reference", "Value"):
            px, py = x + 2.54, y + (-1.27 if key == "Reference" else 1.27)
            e = eff(justify="left")
        elif lp is not None:
            at = child(lp, "at")
            px, py = to_sch(x, y, float(at[1]), float(at[2]))
            fang = int(float(at[3])) if len(at) > 3 else 0
            e = copy.deepcopy(child(lp, "effects"))
        else:
            px, py, e = x, y, eff(hide=True)
        if fields_hidden and key == "Reference" and e is not None:
            e = [i for i in e if kisym.head(i) != "hide"] + [[Sym("hide"), Sym("yes")]]
        if key in ("Footprint", "Datasheet", "Description"):
            e = [i for i in (e or eff()) if kisym.head(i) != "hide"] + [[Sym("hide"), Sym("yes")]]
        node.append([Sym("property"), key, val, [Sym("at"), px, py, fang], e])
    pins = kisym.pins(sym)
    for num in pins:
        node.append([Sym("pin"), num, [Sym("uuid"), uid()]])
    node.append([Sym("instances"), [Sym("project"), NAME,
                 [Sym("path"), "/" + ROOT_UUID, [Sym("reference"), ref], [Sym("unit"), 1]]]])
    ITEMS.append(node)

    for num, net in (nets or {}).items():
        stub = STUB
        if isinstance(net, tuple):
            net, stub = net
        lx, ly, ang, _, _ = pins[num]
        px, py = to_sch(x, y, lx, ly)
        attach(px, py, (ang + 180) % 360, net, stub)
    for num in nc:
        lx, ly, _, _, _ = pins[num]
        px, py = to_sch(x, y, lx, ly)
        ITEMS.append([Sym("no_connect"), [Sym("at"), px, py], [Sym("uuid"), uid()]])
    return pins


def wire(x1, y1, x2, y2):
    ITEMS.append([Sym("wire"), [Sym("pts"), [Sym("xy"), x1, y1], [Sym("xy"), x2, y2]],
                  [Sym("stroke"), [Sym("width"), 0], [Sym("type"), Sym("default")]],
                  [Sym("uuid"), uid()]])


def label(name, x, y, angle):
    just = {0: "left bottom", 90: "left bottom", 180: "right bottom", 270: "right bottom"}[angle]
    ITEMS.append([Sym("label"), name, [Sym("at"), x, y, angle],
                  [Sym("fields_autoplaced"), Sym("yes")], eff(justify=just),
                  [Sym("uuid"), uid()]])


def power(net, x, y, outward):
    """Power symbol whose body points in the outward direction (math angle, Y up)."""
    global _pwr_n
    _pwr_n += 1
    lib_id = {"+5V": "power:+5V", "GND": "power:GND", "PWR_FLAG": "power:PWR_FLAG"}[net]
    natural = 270 if net == "GND" else 90
    rot = (outward - natural) % 360
    sym = lib_symbol(lib_id)
    lib_props = {p[1]: p for p in children(sym, "property")}
    ref = f"#{'FLG' if net == 'PWR_FLAG' else 'PWR'}{_pwr_n:02d}"
    node = [Sym("symbol"), [Sym("lib_id"), lib_id], [Sym("at"), x, y, rot], [Sym("unit"), 1],
            [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")],
            [Sym("on_board"), Sym("yes")], [Sym("dnp"), Sym("no")], [Sym("uuid"), uid()]]
    # value text sits just beyond the symbol body and always reads horizontally
    dist = 3.81 if net != "PWR_FLAG" else 3.556
    vx = x + dist * round(math.cos(math.radians(outward)))
    vy = y - dist * round(math.sin(math.radians(outward)))
    just = {0: "left", 180: "right"}.get(outward)
    fang = (-rot) % 360
    for key, val in (("Reference", ref), ("Value", net),
                     ("Footprint", ""), ("Datasheet", ""), ("Description", lib_props["Description"][2])):
        node.append([Sym("property"), key, val, [Sym("at"), vx, vy, fang],
                     eff(justify=just if key == "Value" else None, hide=key != "Value")])
    node.append([Sym("pin"), "1", [Sym("uuid"), uid()]])
    node.append([Sym("instances"), [Sym("project"), NAME,
                 [Sym("path"), "/" + ROOT_UUID, [Sym("reference"), ref], [Sym("unit"), 1]]]])
    ITEMS.append(node)


def attach(px, py, outward, net, stub=STUB):
    """Wire stub from a pin end, then a label or power symbol."""
    dx = round(math.cos(math.radians(outward)))
    dy = -round(math.sin(math.radians(outward)))
    ex, ey = px + dx * stub, py + dy * stub
    wire(px, py, ex, ey)
    if net in ("+5V", "GND"):
        power(net, ex, ey, outward)
    else:
        label(net, ex, ey, outward)


def text(s, x, y, size=1.8, bold=True):
    ITEMS.append([Sym("text"), s, [Sym("exclude_from_sim"), Sym("no")], [Sym("at"), x, y, 0],
                  eff(size=size, justify="left bottom", bold=bold), [Sym("uuid"), uid()]])


def pwr_flag(net, x, y):
    """Power symbol + PWR_FLAG joined by a short wire (tells ERC the net is driven)."""
    power(net, x, y, 90 if net == "+5V" else 270)
    wire(x, y, x + 7.62, y)
    power("PWR_FLAG", x + 7.62, y, 90)


# ---------------------------------------------------------------- the circuit

def build():
    # --- MCU + I2C connector ------------------------------------------------
    text("MCU + I2C  (address 0x42)", 25.4, 30.48)
    Y1 = 58.42
    place("U1", "MCU_Microchip_ATtiny:ATtiny85-20S", "ATtiny85-20SU", 63.5, Y1, FP["U"],
          nets={"1": "RST", "2": "BTN", "3": "BUZ", "4": "GND",
                "5": "SDA", "6": "LED_RAW", "7": "SCL", "8": "+5V"})
    place("C2", "Device:C", "100n", 40.64, Y1, FP["C"], nets={"1": "+5V", "2": "GND"})
    place("R1", "Device:R", "10k", 106.68, Y1, FP["R"], nets={"1": "+5V", "2": "RST"})
    place("R4", "Device:R", "4.7k", 119.38, Y1, FP["R"], nets={"1": "+5V", "2": "SDA"}, dnp=True)
    place("R5", "Device:R", "4.7k", 132.08, Y1, FP["R"], nets={"1": "+5V", "2": "SCL"}, dnp=True)
    place("R3", "Device:R", "330", 144.78, Y1, FP["R"], nets={"1": "LED_RAW", "2": "LED_DIN"})
    place("J1", "Connector_Generic:Conn_01x04", "I2C (JST-PH 4)", 182.88, Y1, FP["J1"],
          nets={"1": ("GND", 15.24), "2": ("+5V", 10.16), "3": "SCL", "4": "SDA"})
    place("C1", "Device:C", "10u", 203.2, Y1, FP["C0805"], nets={"1": "+5V", "2": "GND"})
    pwr_flag("+5V", 215.9, 48.26)
    pwr_flag("GND", 215.9, 68.58)

    # --- buzzer, button, ISP -------------------------------------------------
    text("Buzzer driver / pat button / ISP", 25.4, 88.9)
    place("R2", "Device:R", "1k", 27.94, 104.14, FP["R"], nets={"1": "BUZ", "2": "Q1_B"})
    place("Q1", "Transistor_BJT:MMBT3904", "MMBT3904", 50.8, 104.14, FP["Q"],
          nets={"1": "Q1_B", "2": "GND", "3": "BUZ_N"})
    place("D13", "Diode:1N4148W", "1N4148W", 83.82, 104.14, FP["D"], nets={"1": "+5V", "2": "BUZ_N"})
    place("BZ1", "Device:Buzzer", "CMT-8504-100-SMT", 114.3, 104.14, FP["BZ"],
          nets={"1": "+5V", "2": "BUZ_N"})
    place("SW1", "Switch:SW_Push", "Pat", 144.78, 104.14, FP["SW"], nets={"1": "BTN", "2": "GND"})
    place("J2", "Connector:AVR-ISP-6", "ISP", 185.42, 104.14, FP["ISP"],
          nets={"1": "LED_RAW", "2": "+5V", "3": "SCL", "4": "SDA", "5": "RST", "6": "GND"})
    text("Unplug J1 while programming:\nSDA/SCL share the ISP pins.", 139.7, 119.38, size=1.27, bold=False)

    # --- eyes ------------------------------------------------------------------
    text("Eyes: D1-D6 left eye, D7-D12 right eye (3x2 grids, one data chain)", 25.4, 124.46)
    step, x0 = 22.86, 45.72
    for row, (y, first) in enumerate(((139.7, 1), (172.72, 7))):
        for i in range(6):
            n = first + i
            x = x0 + i * step
            nets = {"1": "+5V", "3": "GND"}
            nc = ()
            if i == 0:
                nets["4"] = "LED_DIN" if row == 0 else "EYE_LINK"
            if i == 5:
                if row == 0:
                    nets["2"] = "EYE_LINK"
                else:
                    nc = ("2",)
            pins = place(f"D{n}", "Bolty:SK6812MINI-E", "SK6812MINI-E", x, y, FP["LED"],
                         nets=nets, nc=nc)
            if i < 5:  # DOUT -> next DIN
                dout = to_sch(x, y, *pins["2"][:2])
                din = to_sch(x + step, y, *pins["4"][:2])
                wire(dout[0], dout[1], din[0], din[1])

    # --- LED decoupling -------------------------------------------------------
    text("LED decoupling, 1 per LED pair", 236.22, 30.48)
    for k in range(6):
        x = 241.3 + (k % 4) * 12.7
        y = 50.8 + (k // 4) * 27.94
        place(f"C{k + 3}", "Device:C", "100n", x, y, FP["C"], nets={"1": "+5V", "2": "GND"})

    # --- mechanical -------------------------------------------------------------
    text("Mounting", 236.22, 106.68)
    for i, hx in enumerate((241.3, 254.0)):
        place(f"H{i + 1}", "Mechanical:MountingHole", "M2", hx, 116.84,
              "MountingHole:MountingHole_2.2mm_M2", in_bom=False)


# ---------------------------------------------------------------- output

def write_all():
    os.makedirs(OUT, exist_ok=True)
    build()

    sch = [Sym("kicad_sch"), [Sym("version"), SCH_VERSION], [Sym("generator"), "eeschema"],
           [Sym("generator_version"), "9.99"], [Sym("uuid"), ROOT_UUID], [Sym("paper"), "A4"],
           [Sym("title_block"), [Sym("title"), "Bolty Mood Module"], [Sym("date"), "2026-11-15"],
            [Sym("rev"), "0.1"], [Sym("comment"), 1, "Round 40 mm, 2-layer. ATtiny85 + 12x SK6812MINI-E + buzzer + button"],
            [Sym("comment"), 2, "I2C slave at 0x42 via JST-PH 4-pin (GND, +5V, SCL, SDA)"]],
           [Sym("lib_symbols")] + list(LIB_SYMBOLS.values())]
    sch += ITEMS
    sch += [[Sym("sheet_instances"), [Sym("path"), "/", [Sym("page"), "1"]]],
            [Sym("embedded_fonts"), Sym("no")]]
    with open(os.path.join(OUT, NAME + ".kicad_sch"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(dump(sch) + "\n")

    # project-local symbol library with the corrected SK6812MINI-E
    led = make_sk6812mini_e()
    lib = [Sym("kicad_symbol_lib"), [Sym("version"), 20251024], [Sym("generator"), "bolty_gen"],
           [Sym("generator_version"), "10.0"], led]
    with open(os.path.join(OUT, "Bolty.kicad_sym"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(dump(lib) + "\n")
    with open(os.path.join(OUT, "sym-lib-table"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write('(sym_lib_table\n\t(version 7)\n\t(lib (name "Bolty")(type "KiCad")'
                 '(uri "${KIPRJMOD}/Bolty.kicad_sym")(options "")(descr "Bolty project parts"))\n)\n')

    # project-local footprint: 2x3 bare ISP pads, AVR-ISP-6 numbering (1 top-left, 2 top-right ...)
    pretty = os.path.join(OUT, "Bolty.pretty")
    os.makedirs(pretty, exist_ok=True)
    pads = ""
    for n in range(6):
        px, py = (n % 2) * 2.54 - 1.27, (n // 2) * 2.54 - 2.54
        pads += (f'\t(pad "{n + 1}" smd {"rect" if n == 0 else "circle"} (at {px:.2f} {py:.2f}) (size 1.6 1.6) '
                 f'(layers "F.Cu" "F.Mask")\n\t)\n')
    silk_labels = ["MISO", "VCC", "SCK", "MOSI", "RST", "GND"]
    texts = ""
    for n, lab in enumerate(silk_labels):
        px = -1.27 - 1.6 if n % 2 == 0 else 1.27 + 1.6
        py = (n // 2) * 2.54 - 2.54
        just = "right" if n % 2 == 0 else "left"
        texts += (f'\t(fp_text user "{lab}" (at {px:.2f} {py:.2f} 0) (layer "F.SilkS")\n'
                  f'\t\t(effects (font (size 0.8 0.8) (thickness 0.12)) (justify {just}))\n\t)\n')
    with open(os.path.join(pretty, "ISP_Pads_2x3_P2.54mm.kicad_mod"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write('(footprint "ISP_Pads_2x3_P2.54mm"\n\t(version 20241229)\n\t(generator "bolty_gen")\n'
                 '\t(layer "F.Cu")\n\t(descr "AVR ISP 2x3 bare pads, 2.54 mm pitch, for pogo-pin programming clip")\n'
                 '\t(attr smd)\n'
                 '\t(property "Reference" "REF**" (at 0 -4.6 0) (layer "F.SilkS")\n'
                 '\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))\n\t)\n'
                 '\t(property "Value" "ISP_Pads" (at 0 4.6 0) (layer "F.Fab")\n'
                 '\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))\n\t)\n'
                 '\t(fp_rect (start -2.3 -3.57) (end 2.3 3.57) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))\n'
                 + texts + pads + ')\n')
    with open(os.path.join(OUT, "fp-lib-table"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write('(fp_lib_table\n\t(version 7)\n\t(lib (name "Bolty")(type "KiCad")'
                 '(uri "${KIPRJMOD}/Bolty.pretty")(options "")(descr "Bolty project footprints"))\n)\n')

    pro = os.path.join(OUT, NAME + ".kicad_pro")
    if not os.path.exists(pro):
        with open(pro, "w", encoding="utf-8") as fh:
            json.dump({"meta": {"filename": NAME + ".kicad_pro", "version": 3}}, fh, indent=2)
    print("wrote", os.path.abspath(OUT))


if __name__ == "__main__":
    write_all()
