#!/usr/bin/env python3
"""Move the SYSVIPC task_struct fields into the Android KABI padding.

Same change as Halium's "GKI: use Android ABI padding for SYSVIPC task_struct
fields" (TheKit), applied by content rather than by line context. It lets
CONFIG_SYSVIPC=y be enabled without shifting task_struct, so that the stock
vendor modules keep working.
"""
import sys

path = sys.argv[1]
src = open(path).read()

fields = (
    "\tstruct sysv_sem\t\t\tsysvsem;\n"
    "\tstruct sysv_shm\t\t\tsysvshm;\n"
)
padding = (
    "\tANDROID_KABI_RESERVE(6);\n"
    "\tANDROID_KABI_RESERVE(7);\n"
    "\tANDROID_KABI_RESERVE(8);\n"
)
for needle in (fields, padding):
    if src.count(needle) != 1:
        sys.exit("%s: expected exactly one match for:\n%s" % (path, needle))

src = src.replace(
    fields,
    "\t/* sysvsem and sysvshm live in the ANDROID_KABI padding below */\n",
)
src = src.replace(
    padding,
    "#if defined(CONFIG_SYSVIPC)\n"
    "\tANDROID_KABI_USE(6, struct sysv_sem sysvsem);\n"
    "\t_ANDROID_KABI_REPLACE(ANDROID_KABI_RESERVE(7); ANDROID_KABI_RESERVE(8),\n"
    "\t\t\t      struct sysv_shm sysvshm);\n"
    "#else\n" + padding + "#endif\n",
)
open(path, "w").write(src)
print("%s: SYSVIPC fields moved to KABI padding" % path)
