#!/bin/bash
#
# Fetches the kernel sources and prepares them for the Droidian build
#

set -euo pipefail

# android13-5.15 GKI tree used by the tapas/topaz community kernels. It
# carries the reverts the stock SM6225 vendor modules need.
KERNEL_REPO="${KERNEL_REPO:-https://github.com/SM6225-Android-Playground/kernel_common-android13-5.15-lts}"
KERNEL_COMMIT="${KERNEL_COMMIT:-7770b42210590781e12160fcb0375ec960cd8bb7}"
KERNEL_DIR="android_kernel_common"

cd "$(dirname "${0}")/.."

rm -rf "${KERNEL_DIR}"
git init -q "${KERNEL_DIR}"
git -C "${KERNEL_DIR}" remote add origin "${KERNEL_REPO}"
git -C "${KERNEL_DIR}" fetch -q --depth 1 origin "${KERNEL_COMMIT}"
git -C "${KERNEL_DIR}" checkout -q FETCH_HEAD
rm -rf "${KERNEL_DIR}/.git"

python3 scripts/sysvipc-kabi.py "${KERNEL_DIR}/include/linux/sched.h"

# Config fragments are looked up inside the kernel sources
cp -r droidian "${KERNEL_DIR}/droidian"

cat > debian/android-kernel-info.mk <<INFO
# Do not modify! These values have been extracted from the kernel
# sources by scripts/prepare-kernel.sh

INFO
head -n 6 "${KERNEL_DIR}/Makefile" >> debian/android-kernel-info.mk

echo "Kernel sources ready: ${KERNEL_REPO}@${KERNEL_COMMIT}"
cat debian/android-kernel-info.mk
