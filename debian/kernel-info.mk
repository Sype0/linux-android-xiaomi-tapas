# Kernel variant. For mainline-like kernels use "mainline", for
# Android kernels use "android".
VARIANT = android

# VERSION/PATCHLEVEL/SUBLEVEL come from debian/android-kernel-info.mk, which
# scripts/prepare-kernel.sh extracts from the fetched kernel sources.
KERNEL_BASE_VERSION = $(VERSION).$(PATCHLEVEL).$(SUBLEVEL)-android13

# The bootloader takes the cmdline from the stock vendor_boot; Droidian
# additions are set through CONFIG_CMDLINE (droidian.config).
KERNEL_BOOTIMAGE_CMDLINE =

DEVICE_VENDOR = xiaomi
DEVICE_MODEL = tapas
DEVICE_FULL_NAME = Xiaomi Redmi Note 12 4G

KERNEL_CONFIG_USE_FRAGMENTS = 1
KERNEL_CONFIG_USE_DIFFCONFIG = 0
KERNEL_DEFCONFIG = gki_defconfig

# GKI: dtb and dtbo are kept from the stock vendor_boot/dtbo partitions
KERNEL_IMAGE_WITH_DTB = 0
KERNEL_IMAGE_WITH_DTB_OVERLAY = 0
KERNEL_IMAGE_WITH_DTB_OVERLAY_IN_KERNEL = 0

KERNEL_BOOTIMAGE_PAGE_SIZE = 4096
KERNEL_BOOTIMAGE_BASE_OFFSET =
KERNEL_BOOTIMAGE_KERNEL_OFFSET =
KERNEL_BOOTIMAGE_INITRAMFS_OFFSET =
KERNEL_BOOTIMAGE_SECONDIMAGE_OFFSET =
KERNEL_BOOTIMAGE_TAGS_OFFSET =
KERNEL_BOOTIMAGE_DTB_OFFSET =
KERNEL_BOOTIMAGE_PATCH_LEVEL = 2026-09
KERNEL_BOOTIMAGE_OS_VERSION = 13.0.0
KERNEL_BOOTIMAGE_VERSION = 4
KERNEL_INITRAMFS_COMPRESSION = lz4

# tapas loads the generic ramdisk from init_boot; vendor_boot stays stock
DEVICE_HAS_INIT_BOOT = 1
KERNEL_BOOTIMAGE_GENERATE_VENDOR_BOOT = 0

DEVICE_VBMETA_REQUIRED = 0
DEVICE_VBMETA_IS_SAMSUNG = 0

# Do not flash anything automatically from the package postinst (yet)
FLASH_ENABLED = 0
FLASH_IS_AONLY = 0
FLASH_IS_LEGACY_DEVICE = 0
FLASH_IS_EXYNOS = 0
FLASH_INFO_MANUFACTURER = Xiaomi
FLASH_INFO_MODEL = 23021RAAEG
FLASH_INFO_CPU = Qualcomm Technologies, Inc KHAJE
FLASH_INFO_DEVICE_IDS = tapas topaz

BUILD_CROSS = 1
BUILD_TRIPLET = aarch64-linux-gnu-
BUILD_CLANG_TRIPLET = aarch64-linux-gnu-
BUILD_CC = clang
BUILD_LLVM = 1
BUILD_SKIP_MODULES = 0

CLANG_VERSION = 14.0-r450784d
CLANG_CUSTOM = 0
BUILD_PATH = /usr/lib/llvm-android-$(CLANG_VERSION)/bin

DEB_TOOLCHAIN = linux-initramfs-halium-generic:arm64, binutils-aarch64-linux-gnu, gcc-4.9-aarch64-linux-android, g++-4.9-aarch64-linux-android, libgcc-4.9-dev-aarch64-linux-android-cross, libelf-dev, pahole | dwarves
DEB_BUILD_ON = amd64
DEB_BUILD_FOR = arm64
KERNEL_ARCH = arm64
# The stock boot image carries an uncompressed Image
KERNEL_BUILD_TARGET = Image
