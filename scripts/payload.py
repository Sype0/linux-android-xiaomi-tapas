#!/usr/bin/env python3
"""Minimal Android OTA payload.bin reader (full payloads only).

  payload.py list ZIP_OR_PAYLOAD
  payload.py extract ZIP_OR_PAYLOAD OUTDIR part [part...]
"""
import bz2, lzma, struct, sys, zipfile, os, hashlib

def varint(b, p):
    r = s = 0
    while True:
        c = b[p]; p += 1
        r |= (c & 0x7F) << s; s += 7
        if not c & 0x80: return r, p

def fields(b):
    p = 0
    while p < len(b):
        k, p = varint(b, p); f, w = k >> 3, k & 7
        if w == 0: v, p = varint(b, p)
        elif w == 2:
            n, p = varint(b, p); v = b[p:p+n]; p += n
        elif w == 1: v = b[p:p+8]; p += 8
        elif w == 5: v = b[p:p+4]; p += 4
        else: raise ValueError("wire type %d" % w)
        yield f, v

def openpayload(path):
    if zipfile.is_zipfile(path):
        z = zipfile.ZipFile(path); i = z.getinfo("payload.bin")
        assert i.compress_type == 0, "payload.bin must be stored"
        f = open(path, "rb"); f.seek(i.header_offset)
        h = f.read(30); n, e = struct.unpack("<HH", h[26:30])
        return f, i.header_offset + 30 + n + e
    return open(path, "rb"), 0

def manifest(path):
    f, base = openpayload(path)
    f.seek(base); assert f.read(4) == b"CrAU"
    ver, msize = struct.unpack(">QQ", f.read(16)); sigsize, = struct.unpack(">I", f.read(4))
    m = f.read(msize); data = base + 24 + msize + sigsize
    parts = []; block = 4096
    for fn, v in fields(m):
        if fn == 3: block = v
        if fn == 13:
            name = None; ops = []; size = None
            for a, b in fields(v):
                if a == 1: name = b.decode()
                elif a == 7:
                    for c, d in fields(b):
                        if c == 1: size = d
                elif a == 8:
                    op = {"type": 0, "off": 0, "len": 0, "dst": []}
                    for c, d in fields(b):
                        if c == 1: op["type"] = d
                        elif c == 2: op["off"] = d
                        elif c == 3: op["len"] = d
                        elif c == 6:
                            st = nb = 0
                            for e, g in fields(d):
                                if e == 1: st = g
                                elif e == 2: nb = g
                            op["dst"].append((st, nb))
                        elif c == 8: op["hash"] = d
                    ops.append(op)
            parts.append((name, size, ops))
    return f, data, block, parts

def main():
    cmd, path = sys.argv[1], sys.argv[2]
    f, data, block, parts = manifest(path)
    if cmd == "list":
        for name, size, ops in parts: print("%-20s %12d  ops=%d" % (name, size, len(ops)))
        return
    out = sys.argv[3]; want = set(sys.argv[4:]); os.makedirs(out, exist_ok=True)
    for name, size, ops in parts:
        if name not in want: continue
        with open(os.path.join(out, name + ".img"), "wb") as o:
            for op in ops:
                f.seek(data + op["off"]); raw = f.read(op["len"])
                if "hash" in op and op["len"]: assert hashlib.sha256(raw).digest() == op["hash"], "hash mismatch in " + name
                t = op["type"]
                if t == 0: buf = raw
                elif t == 1: buf = bz2.decompress(raw)
                elif t == 8: buf = lzma.decompress(raw)
                elif t == 6: buf = None
                else: raise ValueError("%s: unsupported op %d (not a full payload?)" % (name, t))
                pos = 0
                for st, nb in op["dst"]:
                    o.seek(st * block)
                    if buf is None: o.write(b"\0" * (nb * block))
                    else: o.write(buf[pos:pos + nb * block]); pos += nb * block
            o.truncate(size)
        print("extracted %s (%d bytes)" % (name, size)); sys.stdout.flush()
main()
