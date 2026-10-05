#!/bin/bash
#
# Builds a recovery zip that also carries the stock MIUI 14 (Android 13) base
# Droidian needs: vendor, odm and vendor_dlkm (as a super image), vendor_boot,
# dtbo and the firmware partitions.
#
# The stock images are Xiaomi's and are not redistributed by this repository;
# run this locally with a recovery ROM you downloaded yourself.
#
# Usage: make-full-zip.sh STOCK_RECOVERY_ROM.zip DROIDIAN_TAPAS.zip OUTPUT.zip [WORKDIR]
#
# Needs: python3, lpmake, simg2img, unzip, zip

set -euo pipefail

STOCK_ROM="$(realpath "${1}")"
DROIDIAN_ZIP="$(realpath "${2}")"
OUTPUT="$(realpath "${3}")"
WORKDIR="${4:-$(mktemp -d)}"
SCRIPTS="$(dirname "$(realpath "${0}")")"

# Size of the super partition and name of its group on tapas
SUPER_SIZE=7516192768
SUPER_GROUP=xiaomi_dynamic_partitions_a
SUPER_PARTITIONS="odm vendor vendor_dlkm"
# Flash order: what Droidian needs first, bootloader stages last
PHYSICAL="vendor_boot dtbo modem dsp bluetooth featenabler qupfw imagefv uefisecapp keymaster devcfg rpm hyp tz xbl_config xbl abl"

mkdir -p "${WORKDIR}/images" "${WORKDIR}/zip"
cd "${WORKDIR}"

echo "Extracting the stock images"
# shellcheck disable=SC2086
python3 "${SCRIPTS}/payload.py" extract "${STOCK_ROM}" images ${SUPER_PARTITIONS} ${PHYSICAL}

echo "Unpacking ${DROIDIAN_ZIP}"
unzip -q -o "${DROIDIAN_ZIP}" -d zip
grep -q 'tapas: flash the bundled stock' zip/setup.sh && { echo "E: ${DROIDIAN_ZIP} already bundles a stock base" >&2; exit 1; }
mkdir -p zip/stock

echo "Building super.img"
args=()
for part in ${SUPER_PARTITIONS}; do
	size=$(stat -c %s "images/${part}.img")
	args+=(--partition "${part}_a:readonly:${size}:${SUPER_GROUP}" --image "${part}_a=images/${part}.img")
done
lpmake --metadata-size 65536 --metadata-slots 3 --device-size "${SUPER_SIZE}" \
	--super-name super --group "${SUPER_GROUP}:$(( SUPER_SIZE - 4194304 ))" \
	"${args[@]}" --sparse --output super.sparse
simg2img super.sparse super.raw
rm super.sparse
# Only the used part has to be written to the device
python3 - super.raw <<'PY'
import os, sys
path = sys.argv[1]
step = 1 << 20
with open(path, "r+b") as f:
    pos = os.path.getsize(path)
    while pos > 0:
        pos -= step
        f.seek(pos)
        if f.read(step).strip(b"\0"):
            break
    f.truncate(pos + step)
PY
mv super.raw zip/stock/super.img
for part in ${PHYSICAL}; do
	mv "images/${part}.img" "zip/stock/${part}.img"
done

for name in super ${PHYSICAL}; do
	echo "${name} $(stat -c %s "zip/stock/${name}.img") $(sha256sum "zip/stock/${name}.img" | cut -d ' ' -f 1)"
done > zip/stock/manifest
cat zip/stock/manifest

# The released zip checks for an Android 13 vendor; this one brings its own.
# Start again from the generic installer and patch it for the bundled base.
python3 - zip <<'PY'
import sys
root = sys.argv[1]
for rel, start, end in (
    ("META-INF/com/google/android/update-binary", "# tapas: only install", "# mount vendor and data\n"),
    ("setup.sh", "# tapas: the Halium initramfs", "# If we should flash the dtbo, do it\n"),
):
    path = "%s/%s" % (root, rel)
    src = open(path).read()
    a, b = src.index(start), src.index(end)
    open(path, "w").write(src[:a] + src[b:])
PY
python3 "${SCRIPTS}/patch-installer.py" zip --stock

rm -f "${OUTPUT}"
(cd zip && zip -q -r "${OUTPUT}" META-INF tools setup.sh stock data)
ls -la "${OUTPUT}"
