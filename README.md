# linux-android-xiaomi-tapas

Droidian kernel packaging for the Xiaomi Redmi Note 12 4G (`tapas` / `topaz`,
Snapdragon 685 / SM6225, android13-5.15 GKI).

**Status: builds on GitHub Actions, not yet booted on a device.**

## How it works

tapas is a GKI device: the kernel `Image` lives in `boot`, the generic ramdisk
in `init_boot`, and every hardware driver is a vendor module in `vendor_boot`
and `vendor_dlkm`. Instead of rebuilding those ~320 modules, this follows the
approach of Droidian's `linux-android-common-*` kernels:

- build the GKI `Image` with the Halium/Droidian options enabled
  (`droidian/common_fragments/*.config`, `droidian/tapas.config`);
- keep the module ABI (KMI) unchanged so the stock vendor modules still load.
  `CONFIG_SYSVIPC` would shift `task_struct`, so `scripts/sysvipc-kabi.py`
  moves its fields into the Android KABI padding;
- embed the Halium initramfs into the kernel, because `init_boot` (8 MiB) is
  too small for it. The bootloader unpacks the `vendor_boot` and `init_boot`
  ramdisks on top of it: the stock `vendor_boot` provides the first stage
  modules and their `modules.load`, and `init_boot.img` is a stub so Android's
  `/init` does not replace Halium's;
- `vendor_boot`, `dtbo` and the vendor partitions stay stock.

Kernel sources are not stored here. `scripts/prepare-kernel.sh` fetches a
pinned commit of the community android13-5.15 tree for this device.

## CI

`.github/workflows/build.yml` builds with Droidian's `build-essential` image
and `releng-build-package`, then runs `scripts/check-kmi.py`, which compares
the symbol CRCs of the built kernel with what the prebuilt tapas vendor
modules expect. The job fails if any module would be rejected.

Artifact `droidian-kernel-tapas`:

| File | Purpose |
| --- | --- |
| `boot.img` | kernel with embedded Halium initramfs, for the `boot` partition |
| `init_boot.img` | stub ramdisk, for the `init_boot` partition |
| `recovery.img` | Droidian recovery-mode boot image (not needed for install) |
| `linux-*.deb` | Droidian kernel packages |
| `kmi-report.txt` | vendor module ABI check result |
| `kernel.config`, `Module.symvers`, `System.map` | build references |

## Installing (untested, wipes the phone)

The `package` job takes Droidian's generic `api33` rootfs, installs the
kernel packages into it and publishes a single recovery zip on the
[releases page](https://github.com/Sype0/linux-android-xiaomi-tapas/releases/tag/latest).

1. Unlocked bootloader, stock MIUI 14 (Android 13) firmware. The installer
   checks the device and the vendor version and refuses anything else before
   writing.
2. Back up `boot`, `init_boot`, `vendor_boot`, `dtbo` and `vbmeta`.
3. In a custom recovery: Format Data, then flash the zip.

The zip installs the rootfs to `userdata` and flashes `boot` and `init_boot`
of the active slot. To go back, flash the backed up images or the stock
firmware.
