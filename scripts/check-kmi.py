#!/usr/bin/env python3
"""Check a built kernel against prebuilt (stock) vendor modules.

Compares the symbol CRCs every prebuilt .ko expects (its __versions section)
with the ones the freshly built kernel exports (Module.symvers). A mismatch
or a missing symbol means that module will refuse to load, i.e. the build
broke the GKI module ABI.

Usage: check-kmi.py Module.symvers MODULES_DIR [MODULES_DIR...]
"""
import os
import struct
import sys


def sections(data):
    shoff, = struct.unpack_from("<Q", data, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 0x3A)
    raw = []
    for i in range(shnum):
        name, typ, _, _, off, size, link = struct.unpack_from(
            "<IIQQQQI", data, shoff + i * shentsize)
        raw.append((name, typ, off, size, link))
    stroff = raw[shstrndx][2]
    out = {}
    for name, typ, off, size, link in raw:
        end = data.index(b"\0", stroff + name)
        out[data[stroff + name:end].decode()] = (typ, off, size, link, raw)
    return out


def parse_module(path):
    """Returns (required {sym: crc}, exported {sym: crc or None})"""
    data = open(path, "rb").read()
    if data[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    secs = sections(data)

    required = {}
    if "__versions" in secs:
        _, off, size, _, _ = secs["__versions"]
        for pos in range(off, off + size, 64):
            crc, = struct.unpack_from("<Q", data, pos)
            name = data[pos + 8:pos + 64].split(b"\0", 1)[0].decode()
            required[name] = crc & 0xFFFFFFFF

    exported, crcs = {}, {}
    if ".symtab" in secs:
        _, off, size, link, raw = secs[".symtab"]
        stroff = raw[link][2]
        for pos in range(off, off + size, 24):
            st_name, _, _, _, value = struct.unpack_from("<IBBHQ", data, pos)
            end = data.index(b"\0", stroff + st_name)
            name = data[stroff + st_name:end].decode(errors="replace")
            if name.startswith("__ksymtab_"):
                exported[name[len("__ksymtab_"):]] = None
            elif name.startswith("__crc_"):
                crcs[name[len("__crc_"):]] = value & 0xFFFFFFFF
    for name in exported:
        exported[name] = crcs.get(name)
    return required, exported


def main():
    symvers_path, module_dirs = sys.argv[1], sys.argv[2:]

    kernel = {}
    for line in open(symvers_path):
        fields = line.rstrip("\n").split("\t")
        if len(fields) >= 3 and fields[2] == "vmlinux":
            kernel[fields[1]] = int(fields[0], 16)

    modules = {}
    for module_dir in module_dirs:
        for root, _, files in os.walk(module_dir):
            for name in files:
                if name.endswith(".ko") and name not in modules:
                    try:
                        modules[name] = parse_module(os.path.join(root, name))
                    except Exception as e:
                        print("W: skipping %s: %s" % (name, e))

    from_modules = {}
    for name, (_, exported) in modules.items():
        for sym, crc in exported.items():
            from_modules.setdefault(sym, (name, crc))

    mismatches, missing, checked = [], [], 0
    for name in sorted(modules):
        for sym, crc in sorted(modules[name][0].items()):
            checked += 1
            if sym in kernel:
                if kernel[sym] != crc:
                    mismatches.append((name, sym, crc, kernel[sym]))
            elif sym not in from_modules:
                missing.append((name, sym))

    print("Kernel exports: %d symbols" % len(kernel))
    print("Prebuilt modules: %d, symbol references checked: %d"
          % (len(modules), checked))
    print("CRC mismatches: %d (in %d modules, %d distinct symbols)" % (
        len(mismatches), len({m[0] for m in mismatches}),
        len({m[1] for m in mismatches})))
    print("Missing symbols: %d (in %d modules, %d distinct symbols)" % (
        len(missing), len({m[0] for m in missing}),
        len({m[1] for m in missing})))

    if mismatches:
        print("\nMismatching symbols (expected by modules -> built kernel):")
        seen = set()
        for name, sym, want, have in mismatches:
            if sym not in seen:
                seen.add(sym)
                users = sorted({m[0] for m in mismatches if m[1] == sym})
                print("  %s: 0x%08x -> 0x%08x (%d modules, e.g. %s)"
                      % (sym, want, have, len(users), users[0]))
    if missing:
        print("\nSymbols no longer exported:")
        seen = set()
        for name, sym in missing:
            if sym not in seen:
                seen.add(sym)
                users = sorted({m[0] for m in missing if m[1] == sym})
                print("  %s (%d modules, e.g. %s)" % (sym, len(users), users[0]))

    if not modules or not kernel:
        print("\nRESULT: nothing to compare")
        return 2
    if mismatches or missing:
        print("\nRESULT: KMI BROKEN")
        return 1
    print("\nRESULT: KMI OK - every prebuilt module matches the built kernel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
