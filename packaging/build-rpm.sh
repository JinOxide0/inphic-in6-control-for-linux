#!/usr/bin/env bash
# 构建 inphic-control RPM
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="inphic-control"
VERSION="0.3.0"
TOPDIR="${HOME}/rpmbuild"

echo "==> 准备源码包"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/$NAME-$VERSION"
tar -C "$ROOT" \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' \
    --exclude='build' --exclude='*.rpm' \
    -cf - . | tar -C "$STAGE/$NAME-$VERSION" -xf -

mkdir -p "$TOPDIR/SOURCES" "$TOPDIR/SPECS" "$TOPDIR/BUILD" "$TOPDIR/RPMS" "$TOPDIR/SRPMS"
tar -C "$STAGE" -czf "$TOPDIR/SOURCES/$NAME-$VERSION.tar.gz" "$NAME-$VERSION"
cp "$ROOT/packaging/$NAME.spec" "$TOPDIR/SPECS/"

echo "==> rpmbuild"
rpmbuild -bb "$TOPDIR/SPECS/$NAME.spec"

echo
echo "==> 产物:"
find "$TOPDIR/RPMS" -name "$NAME-$VERSION*.rpm" -printf '   %p\n'
