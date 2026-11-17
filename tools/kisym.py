"""Tiny S-expression helpers for reading KiCad symbol libraries."""
import copy
import os
import re

KICAD_SYMBOLS = r"C:\Program Files\KiCad\10.0\share\kicad\symbols"

_TOKEN = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')


class Sym(str):
    """Bare (unquoted) atom."""


def parse(text):
    stack, cur = [], []
    for tok in _TOKEN.findall(text):
        if tok == "(":
            stack.append(cur)
            cur = []
        elif tok == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif tok.startswith('"'):
            cur.append(re.sub(r'\\(.)', lambda m: "\n" if m.group(1) == "n" else m.group(1), tok[1:-1]))
        else:
            cur.append(Sym(tok))
    return cur[0]


def dump(node, indent=0):
    pad = "\t" * indent
    if not isinstance(node, list):
        if isinstance(node, Sym):
            return str(node)
        if isinstance(node, (int, float)):
            return fmt_num(node)
        return '"' + str(node).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    simple = all(not isinstance(x, list) for x in node)
    if simple:
        return pad + "(" + " ".join(dump(x) for x in node) + ")"
    out = pad + "(" + " ".join(dump(x) for x in node if not isinstance(x, list))
    for x in node:
        if isinstance(x, list):
            out += "\n" + dump(x, indent + 1)
    return out + "\n" + pad + ")"


def fmt_num(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def head(node):
    return node[0] if isinstance(node, list) and node else None


def children(node, name):
    return [x for x in node if isinstance(x, list) and x and x[0] == name]


def child(node, name):
    c = children(node, name)
    return c[0] if c else None


_lib_cache = {}


def load_lib(lib):
    if lib not in _lib_cache:
        path = os.path.join(KICAD_SYMBOLS, lib + ".kicad_sym")
        with open(path, encoding="utf-8") as fh:
            tree = parse(fh.read())
        _lib_cache[lib] = {s[1]: s for s in children(tree, "symbol")}
    return _lib_cache[lib]


def get_symbol(lib_id):
    """Return a flattened copy of the symbol named 'Lib:Name' ready to embed in lib_symbols."""
    lib, name = lib_id.split(":")
    syms = load_lib(lib)
    sym = copy.deepcopy(syms[name])
    ext = child(sym, "extends")
    if ext is not None:
        parent = copy.deepcopy(syms[ext[1]])
        pname = ext[1]
        props = {p[1]: p for p in children(sym, "property")}
        flat = [Sym("symbol"), name]
        for item in parent[2:]:
            if head(item) == "property" and item[1] in props:
                flat.append(props.pop(item[1]))
            elif head(item) == "symbol":
                item[1] = name + item[1][len(pname):]
                flat.append(item)
            else:
                flat.append(item)
        # child-only properties go before the first unit sub-symbol
        idx = next(i for i, x in enumerate(flat) if head(x) == "symbol")
        for p in props.values():
            flat.insert(idx, p)
            idx += 1
        sym = flat
    sym[1] = lib_id
    return sym


def pins(sym, unit=1):
    """Pins of a flattened symbol: {number: (x, y, angle, name, type)} in library coords (Y up)."""
    name = sym[1].split(":")[1]
    out = {}
    for sub in children(sym, "symbol"):
        m = re.match(re.escape(name) + r"_(\d+)_(\d+)$", sub[1])
        if not m or int(m.group(1)) not in (0, unit):
            continue
        for p in children(sub, "pin"):
            at = child(p, "at")
            num = child(p, "number")[1]
            pname = child(p, "name")[1]
            out[num] = (float(at[1]), float(at[2]), int(float(at[3])), pname, str(p[1]))
    return out
