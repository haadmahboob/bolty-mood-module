"""Remux a fragmented MP4 (Chrome MediaRecorder output, single video track) into a
normal MP4 with a real duration and sample tables, so upload sites read it correctly.
Usage: python fix_mp4.py in.mp4 out.mp4"""
import struct
import sys

CONTAINERS = {b"moov", b"trak", b"mdia", b"minf", b"stbl", b"dinf", b"edts", b"moof", b"traf", b"mvex"}


def parse(d, o, e):
    out = []
    while o < e:
        sz, t = struct.unpack(">I4s", d[o:o + 8])
        h = 8
        if sz == 1:
            sz = struct.unpack(">Q", d[o + 8:o + 16])[0]
            h = 16
        elif sz == 0:
            sz = e - o
        kids = parse(d, o + h, o + sz) if t in CONTAINERS else None
        out.append({"t": t, "o": o, "h": h, "sz": sz, "raw": d[o:o + sz], "kids": kids})
        o += sz
    return out


def find(boxes, t):
    return next(b for b in boxes if b["t"] == t)


def ser(b):
    if b["kids"] is not None:
        body = b"".join(ser(k) for k in b["kids"])
        return struct.pack(">I4s", 8 + len(body), b["t"]) + body
    return b["raw"]


def box(t, body):
    return {"t": t, "kids": None, "raw": struct.pack(">I4s", 8 + len(body), t) + body}


def full(t, body, v=0, flags=0):
    return box(t, struct.pack(">I", (v << 24) | flags) + body)


def set_duration(b, off_v0, off_v1, value):
    raw = bytearray(b["raw"])
    if raw[8] == 0:
        struct.pack_into(">I", raw, off_v0, value)
    else:
        struct.pack_into(">Q", raw, off_v1, value)
    b["raw"] = bytes(raw)


def main(src, dst):
    d = open(src, "rb").read()
    top = parse(d, 0, len(d))
    moov = find(top, b"moov")
    trak = find(moov["kids"], b"trak")
    mdia = find(trak["kids"], b"mdia")
    stbl = find(find(mdia["kids"], b"minf")["kids"], b"stbl")
    mdhd = find(mdia["kids"], b"mdhd")
    v = mdhd["raw"][8]
    timescale = struct.unpack(">I", mdhd["raw"][28:32] if v else mdhd["raw"][20:24])[0]

    trex = find(find(moov["kids"], b"mvex")["kids"], b"trex")["raw"]
    _, _, def_dur, def_size, def_flags = struct.unpack(">IIIII", trex[12:32])

    samples = []  # (abs_offset, size, duration, flags, cto)
    for moof in (b for b in top if b["t"] == b"moof"):
        traf = find(moof["kids"], b"traf")
        tfhd = find(traf["kids"], b"tfhd")["raw"]
        tf_flags = struct.unpack(">I", tfhd[8:12])[0] & 0xFFFFFF
        p = 16
        base = moof["o"]
        if tf_flags & 0x1:
            base = struct.unpack(">Q", tfhd[p:p + 8])[0]; p += 8
        if tf_flags & 0x2:
            p += 4
        dur, size, flags = def_dur, def_size, def_flags
        if tf_flags & 0x8:
            dur = struct.unpack(">I", tfhd[p:p + 4])[0]; p += 4
        if tf_flags & 0x10:
            size = struct.unpack(">I", tfhd[p:p + 4])[0]; p += 4
        if tf_flags & 0x20:
            flags = struct.unpack(">I", tfhd[p:p + 4])[0]; p += 4
        for trun_b in (b for b in traf["kids"] if b["t"] == b"trun"):
            r = trun_b["raw"]
            ver = r[8]
            fl = struct.unpack(">I", r[8:12])[0] & 0xFFFFFF
            n = struct.unpack(">I", r[12:16])[0]
            p = 16
            data = base
            if fl & 0x1:
                data = base + struct.unpack(">i", r[p:p + 4])[0]; p += 4
            first_flags = None
            if fl & 0x4:
                first_flags = struct.unpack(">I", r[p:p + 4])[0]; p += 4
            for i in range(n):
                sd, ss, sf, sc = dur, size, flags, 0
                if fl & 0x100:
                    sd = struct.unpack(">I", r[p:p + 4])[0]; p += 4
                if fl & 0x200:
                    ss = struct.unpack(">I", r[p:p + 4])[0]; p += 4
                if fl & 0x400:
                    sf = struct.unpack(">I", r[p:p + 4])[0]; p += 4
                if i == 0 and first_flags is not None:
                    sf = first_flags
                if fl & 0x800:
                    sc = struct.unpack(">i" if ver else ">I", r[p:p + 4])[0]; p += 4
                samples.append((data, ss, sd, sf, sc))
                data += ss

    total = sum(s[2] for s in samples)
    n = len(samples)

    # sample tables
    stts, last = [], None
    for s in samples:
        if stts and stts[-1][1] == s[2]:
            stts[-1][0] += 1
        else:
            stts.append([1, s[2]])
    stss = [i + 1 for i, s in enumerate(samples) if not (s[3] & 0x00010000)]
    has_cto = any(s[4] for s in samples)

    new_tables = [
        full(b"stts", struct.pack(">I", len(stts)) + b"".join(struct.pack(">II", c, du) for c, du in stts)),
        full(b"stss", struct.pack(">I", len(stss)) + b"".join(struct.pack(">I", i) for i in stss)),
        full(b"stsc", struct.pack(">IIII", 1, 1, n, 1)),
        full(b"stsz", struct.pack(">II", 0, n) + b"".join(struct.pack(">I", s[1]) for s in samples)),
        full(b"stco", struct.pack(">II", 1, 0)),  # patched below
    ]
    if has_cto:
        new_tables.append(full(b"ctts", struct.pack(">I", n) + b"".join(struct.pack(">Ii", 1, s[4]) for s in samples), v=1))
    stbl["kids"] = [find(stbl["kids"], b"stsd")] + new_tables

    mvhd = find(moov["kids"], b"mvhd")
    mv_ts = struct.unpack(">I", mvhd["raw"][28:32] if mvhd["raw"][8] else mvhd["raw"][20:24])[0]
    mv_dur = total * mv_ts // timescale
    set_duration(mvhd, 24, 32, mv_dur)
    set_duration(find(trak["kids"], b"tkhd"), 28, 36, mv_dur)
    set_duration(mdhd, 24, 32, total)
    moov["kids"] = [k for k in moov["kids"] if k["t"] != b"mvex"]

    ftyp = box(b"ftyp", b"isom" + struct.pack(">I", 512) + b"isomiso2avc1mp41")
    mdat_body = b"".join(d[s[0]:s[0] + s[1]] for s in samples)
    head_len = len(ser(ftyp)) + len(ser(moov))
    stco = new_tables[4]
    stco["raw"] = stco["raw"][:16] + struct.pack(">I", head_len + 8)
    with open(dst, "wb") as f:
        f.write(ser(ftyp))
        f.write(ser(moov))
        f.write(struct.pack(">I4s", 8 + len(mdat_body), b"mdat"))
        f.write(mdat_body)
    print(f"{n} samples, {total / timescale:.2f} s, {len(stss)} keyframes -> {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
