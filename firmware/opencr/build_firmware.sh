#!/usr/bin/env bash
#
# build_firmware.sh -- MAINTAINER-ONLY. Recompiles the custom OpenCR firmware
# and drops the result in prebuilt/turtlebot3_burger_custom.opencr.
#
# You do NOT need this to flash a robot -- see flash_opencr.sh for that
# (it just uploads the file already sitting in prebuilt/). Run this script
# only when turtlebot3_burger_custom.ino or disable_test_drive.patch changes
# and prebuilt/ needs to be regenerated.
#
# Why this needs Docker at all: the OpenCR board package's compiler
# (opencr_gcc 5.4.0-2016q2) only ships prebuilt binaries for x86_64/i686
# Linux, Windows, and old 32-bit Intel macOS -- it does NOT run on the Pi
# (aarch64) or on Apple Silicon Macs (arm64). So we compile inside an
# emulated x86_64 (amd64) container instead (works via Docker Desktop's
# Rosetta/QEMU amd64 emulation on Apple Silicon, natively on an x86_64 host).
#
# The one dependency the compiler needs (the actual gcc-arm-none-eabi
# toolchain tarball) lives on an old, heavily-throttled Launchpad mirror
# (observed ~14 KB/s -- the 88 MB file can take 90+ minutes and doesn't
# support resuming). This script fetches it from archive.org's Wayback
# Machine cache instead, which mirrors the exact same bytes (checksum
# verified against ROBOTIS's own package index) at normal speed.
#
# Usage (from repo root or this directory):
#     ./build_firmware.sh
#
# Requires: Docker Desktop with amd64 emulation (works out of the box on
# Apple Silicon; nothing extra needed on an x86_64 host).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$HERE/prebuilt"
FW_NAME="turtlebot3_burger_custom"
FW_VERSION="V$(date +%Y%m%d)"
BOARD_URL="https://raw.githubusercontent.com/ROBOTIS-GIT/OpenCR/master/arduino/opencr_release/package_opencr_index.json"

GCC_ARCHIVE="gcc-arm-none-eabi-5_4-2016q2-20160622-linux.tar.bz2"
GCC_SHA256="9910b6b5df12efe564dbb3856bf1599d4c16178a6f28bd8a23c9e5c3edc219e4"
# Primary Launchpad URL is real but throttled to ~14 KB/s and doesn't support
# resume -- archive.org's cached copy of the exact same bytes is much faster.
GCC_URL_PRIMARY="https://launchpadlibrarian.net/268330503/${GCC_ARCHIVE}"
GCC_URL_MIRROR="https://web.archive.org/web/20251120025833/https://launchpadlibrarian.net/268330503/${GCC_ARCHIVE}"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "=== [1/4] fetch gcc-arm-none-eabi toolchain (staged so the container skips the slow mirror) ==="
GCC_TARBALL="$WORK/$GCC_ARCHIVE"
if ! curl -fSL --max-time 120 -o "$GCC_TARBALL" "$GCC_URL_MIRROR"; then
  echo "archive.org mirror failed, falling back to the slow Launchpad original..."
  curl -fSL --max-time 6000 -o "$GCC_TARBALL" "$GCC_URL_PRIMARY"
fi
echo "$GCC_SHA256  $GCC_TARBALL" | shasum -a 256 -c -

echo "=== [2/4] install OpenCR core + Dynamixel2Arduino in an amd64 container ==="
docker volume create opencr-arduino15 >/dev/null
docker run --rm --platform linux/amd64 \
  -v opencr-arduino15:/root/.arduino15 \
  -v "$GCC_TARBALL":/root/.arduino15/staging/packages/"$GCC_ARCHIVE":ro \
  ubuntu:22.04 bash -c "
    set -e
    apt-get update -qq && apt-get install -y -qq curl ca-certificates >/dev/null
    curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=/usr/local/bin sh >/dev/null
    mkdir -p /root/.arduino15/staging/packages
    arduino-cli config init --overwrite >/dev/null
    arduino-cli config set board_manager.additional_urls '$BOARD_URL'
    arduino-cli core update-index
    arduino-cli core install OpenCR:OpenCR
    arduino-cli lib install Dynamixel2Arduino
  "

echo "=== [3/4] apply the button patch + compile the sketch ==="
mkdir -p "$WORK/out"
docker run --rm --platform linux/amd64 \
  -v opencr-arduino15:/root/.arduino15 \
  -v "$HERE":/src:ro \
  -v "$WORK/out":/out \
  ubuntu:22.04 bash -c "
    set -e
    dpkg --add-architecture i386
    apt-get update -qq
    apt-get install -y -qq curl ca-certificates libc6:i386 libstdc++6:i386 libncurses5:i386 zlib1g:i386 >/dev/null
    curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=/usr/local/bin sh >/dev/null

    TB3_CPP=\$(find /root/.arduino15/packages/OpenCR -path '*turtlebot3_ros2/src/turtlebot3/turtlebot3.cpp' | head -n1)
    if grep -qE '^\s*test_motors_with_buttons\(' \"\$TB3_CPP\"; then
      sed -i -E 's|^([[:space:]]*)test_motors_with_buttons\(|\1// RobotKub: disabled (mission buttons) // test_motors_with_buttons(|' \"\$TB3_CPP\"
    fi

    mkdir -p /root/sketch
    cp -r /src/${FW_NAME} /root/sketch/
    arduino-cli compile --fqbn OpenCR:OpenCR:OpenCR /root/sketch/${FW_NAME} --output-dir /out/compiled
  "

echo "=== [4/4] wrap the .bin into the .opencr format update.sh/opencr_ld_shell expect ==="
docker run --rm --platform linux/amd64 \
  -v "$WORK/out":/out \
  -v "$HERE/tools/opencr_ld_shell_x86":/opencr_ld_shell_x86:ro \
  ubuntu:22.04 bash -c "
    cp /opencr_ld_shell_x86 /tmp/opencr_ld_shell_x86 && chmod +x /tmp/opencr_ld_shell_x86
    cd /out/compiled
    /tmp/opencr_ld_shell_x86 make ${FW_NAME}.ino.bin ${FW_NAME} ${FW_VERSION}
  "

mkdir -p "$OUT_DIR"
cp "$WORK/out/compiled/${FW_NAME}.opencr" "$OUT_DIR/${FW_NAME}.opencr"

cat > "$OUT_DIR/BUILD_INFO.txt" <<EOF
firmware:      ${FW_NAME}.opencr
built:         $(date -u +%Y-%m-%dT%H:%M:%SZ)
fw_version:    ${FW_VERSION}
sha256:        $(shasum -a 256 "$OUT_DIR/${FW_NAME}.opencr" | awk '{print $1}')
patch applied: disable_test_drive.patch (SW1/SW2 test-drive disabled, state reporting kept)
opencr core:   OpenCR:OpenCR (via board_manager url below)
board url:     ${BOARD_URL}
EOF

echo ""
echo "=== done: $OUT_DIR/${FW_NAME}.opencr ==="
cat "$OUT_DIR/BUILD_INFO.txt"
echo ""
echo "Commit prebuilt/${FW_NAME}.opencr and prebuilt/BUILD_INFO.txt, then flash with:"
echo "    ./flash_opencr.sh"
