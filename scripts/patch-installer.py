#!/usr/bin/env python3
"""Adapt Droidian's generic recovery installer for tapas/topaz.

Takes the directory of an unpacked Droidian rootfs zip and patches:
 - update-binary: refuse to install on other devices or on a vendor that is
   not Android 13, before anything is written;
 - setup.sh: also flash init_boot (the generic script only knows boot).
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

# Droidian api33 needs the stock Android 13 (MIUI 14) vendor
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

patch("META-INF/com/google/android/update-binary",
      "# mount vendor and data\n", DEVICE_CHECK)
patch("setup.sh", "# If we should flash the dtbo, do it\n", INIT_BOOT)
