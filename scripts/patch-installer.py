#!/usr/bin/env python3
"""Adapt Droidian's generic recovery installer for tapas/topaz.

Takes the directory of an unpacked Droidian rootfs zip and patches:
 - update-binary: refuse to install on other devices or on a vendor that is
   not Android 13, before anything is written;
 - setup.sh: also flash init_boot (the generic script only knows boot).

With --stock (see make-full-zip.sh) the zip carries the stock base itself:
setup.sh then flashes it first and the vendor check is dropped.
"""
import os
import sys

root = sys.argv[1]


def patch(relpath, anchor, addition):
    path = os.path.join(root, relpath)
    src = open(path).read()
    if src.count(anchor) != 1:
        sys.exit("%s: expected exactly one match for: %s" % (relpath, anchor))
    open(path, "w").write(src.replace(anchor, addition + anchor))
    print("%s: patched" % relpath)


DEVICE_CHECK = r'''# tapas: only install on the right device and firmware
device_names="$(getprop ro.product.device) $(getprop ro.build.product) $(getprop ro.product.vendor.device)";
case "${device_names}" in
  *tapas*|*topaz*) ;;
  *) ui_print "This package is for Redmi Note 12 4G (tapas/topaz)."; ui_print "Detected: ${device_names}"; ui_print "Aborting, nothing was changed."; exit 1;;
esac;

slot_suffix=$(grep -oE 'androidboot\.slot_suffix[[:space:]]*=[[:space:]]*"_[ab]"' /proc/bootconfig 2>/dev/null | grep -oE '_[ab]');
[ -n "${slot_suffix}" ] || slot_suffix=$(grep -oE 'androidboot\.slot_suffix=_[ab]' /proc/cmdline | grep -oE '_[ab]$');
if [ ! -e "/dev/block/by-name/init_boot${slot_suffix}" ]; then
  ui_print "init_boot${slot_suffix} partition not found."; ui_print "Aborting, nothing was changed."; exit 1;
fi;

'''

VENDOR_CHECK = r'''# Droidian api33 needs the stock Android 13 (MIUI 14) vendor
vendor_release="";
mkdir -p /tmp/droidian-vendor;
if mount -o ro "/dev/block/mapper/vendor${slot_suffix}" /tmp/droidian-vendor 2>/dev/null; then
  vendor_release=$(grep -m1 '^ro.vendor.build.version.release=' /tmp/droidian-vendor/build.prop | cut -d= -f2);
  umount /tmp/droidian-vendor;
fi;
if [ -z "${vendor_release}" ]; then
  ui_print "WARNING: could not read the vendor Android version.";
  ui_print "Droidian needs the stock MIUI 14 (Android 13) firmware.";
elif [ "${vendor_release}" != "13" ]; then
  ui_print "The installed vendor is Android ${vendor_release}.";
  ui_print "Droidian needs the stock MIUI 14 (Android 13) firmware.";
  ui_print "Flash it first. Aborting, nothing was changed."; exit 1;
else
  ui_print "Device: tapas/topaz, vendor: Android 13, slot: ${slot_suffix}";
fi;

'''

INIT_BOOT = r'''# tapas: the Halium initramfs is embedded in the kernel; flash the stub
# init_boot so the bootloader does not load Android's ramdisk on top of it
if [ -e "$(ls /r/boot/init_boot.img*)" ]; then
    ui_print "init_boot found, flashing"
    get_partitions
    partition=$(find /dev/block/by-name -name "init_${target_boot_partition}" | head -n 1)
    if [ -z "${partition}" ]; then
        ui_print "init_boot partition not found, aborting"
        exit 1
    fi
    ui_print "Found init_boot partition for current slot ${partition}"
    if ! dd if="$(find /r/boot -name 'init_boot.img*')" of="${partition}"; then
        ui_print "Unable to flash init_boot"
        exit 1
    fi
    ui_print "init_boot flashed"
fi

'''

STOCK_FLASH = r'''# tapas: flash the bundled stock MIUI 14 base (vendor, vendor_boot, dtbo and
# firmware). Everything is checked before the first write, and every write is
# read back and compared.
STOCK="${DROIDIAN_STOCK_DIR:-/data/droidian/stock}"
if [ -f "${STOCK}/manifest" ]; then
    slot=$(grep -oE 'androidboot\.slot_suffix[[:space:]]*=[[:space:]]*"_[ab]"' /proc/bootconfig 2>/dev/null | grep -oE '_[ab]')
    [ -n "${slot}" ] || slot=$(grep -oE 'androidboot\.slot_suffix=_[ab]' /proc/cmdline | grep -oE '_[ab]$')
    stock_part() {
        case "$1" in
            super) echo /dev/block/by-name/super ;;
            *) echo "/dev/block/by-name/$1${slot}" ;;
        esac
    }
    stock_hash() { head -c "$2" "$1" | sha256sum | cut -d ' ' -f 1; }
    stock_fail() { ui_print "$1"; ui_print "Aborting."; exit 1; }

    ui_print "Checking the stock MIUI 14 images (slot ${slot})"
    [ -n "${slot}" ] || stock_fail "Unable to detect the active slot."
    while read -r name size sum; do
        img="${STOCK}/${name}.img"
        part=$(stock_part "${name}")
        [ -e "${part}" ] || stock_fail "Partition for ${name} not found. Nothing was changed."
        [ "$(stock_hash "${img}" "${size}")" = "${sum}" ] || stock_fail "${name}.img is corrupt. Nothing was changed."
        psize=$(blockdev --getsize64 "${part}" 2>/dev/null)
        if [ -n "${psize}" ] && [ "${size}" -gt "${psize}" ]; then
            stock_fail "${name}.img does not fit its partition. Nothing was changed."
        fi
    done < "${STOCK}/manifest"

    if [ -z "${DROIDIAN_DRY_RUN}" ]; then
        for mountpoint in /vendor /vendor_dlkm /odm /system /system_root /system_ext /product; do
            umount "${mountpoint}" 2>/dev/null
        done
    fi

    while read -r name size sum; do
        img="${STOCK}/${name}.img"
        part=$(stock_part "${name}")
        if [ "$(stock_hash "${part}" "${size}")" = "${sum}" ]; then
            ui_print "${name}: already up to date"
            continue
        fi
        if [ -n "${DROIDIAN_DRY_RUN}" ]; then
            ui_print "${name}: would flash ${part}"
            continue
        fi
        ui_print "Flashing ${name}"
        flashed=no
        for try in 1 2; do
            dd if="${img}" of="${part}" bs=1048576
            sync
            echo 3 > /proc/sys/vm/drop_caches
            if [ "$(stock_hash "${part}" "${size}")" = "${sum}" ]; then
                flashed=yes
                break
            fi
            ui_print "${name}: verification failed, retrying"
        done
        if [ "${flashed}" != "yes" ]; then
            ui_print "${name} could not be written correctly."
            ui_print "DO NOT REBOOT. Flash the stock firmware again first."
            exit 1
        fi
    done < "${STOCK}/manifest"
    [ -z "${DROIDIAN_DRY_RUN}" ] || exit 0
    ui_print "Stock base flashed"
    rm -rf "${STOCK}"
fi

'''

# --stock: the zip bundles its own stock base, so the installed vendor does
# not matter and gets replaced
bundles_stock = "--stock" in sys.argv[2:]

patch("META-INF/com/google/android/update-binary",
      "# mount vendor and data\n",
      DEVICE_CHECK if bundles_stock else DEVICE_CHECK + VENDOR_CHECK)
patch("setup.sh", "# If we should flash the dtbo, do it\n", INIT_BOOT)
if bundles_stock:
    patch("setup.sh", "## rootfs install\n", STOCK_FLASH)
