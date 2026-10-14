#!/usr/bin/env bash
set -e

# Project root directory where the script is located
cd "$(dirname "$0")"

CONTROL_FILE="DEBIAN/control"

if [ ! -f "$CONTROL_FILE" ]; then
    echo "Error: File $CONTROL_FILE not found." >&2
    exit 1
fi

# Extract the version defined in the DEBIAN/control file
VERSION=$(awk -F': ' '/^Version:/ {print $2}' "$CONTROL_FILE" | tr -d '[:space:]')

if [ -z "$VERSION" ]; then
    echo "Error: Could not retrieve 'Version' field from $CONTROL_FILE." >&2
    exit 1
fi

OUTPUT="ubuntu-app-uninstaller_${VERSION}.deb"
BUILD_DIR=$(mktemp -d)
trap 'rm -rf "$BUILD_DIR"' EXIT

echo "==> Preparing packaging structure..."
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr"

cp -r DEBIAN/* "$BUILD_DIR/DEBIAN/"
cp -r usr/* "$BUILD_DIR/usr/"

echo "==> Setting permissions..."
chmod 755 "$BUILD_DIR"
chmod 755 "$BUILD_DIR/DEBIAN"
chmod 644 "$BUILD_DIR/DEBIAN/control"
find "$BUILD_DIR/usr" -type d -exec chmod 755 {} +
find "$BUILD_DIR/usr" -type f -exec chmod 644 {} +
chmod 755 "$BUILD_DIR/usr/local/bin/uninstaller"
chmod 755 usr/local/bin/uninstaller

echo "==> Generating package ${OUTPUT}..."
dpkg-deb --root-owner-group --build "$BUILD_DIR" "${OUTPUT}"

echo "==> Package successfully created: ${OUTPUT}"
