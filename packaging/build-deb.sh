#!/usr/bin/env bash
# 构建 inphic-control 的 Debian / Ubuntu 软件包 (.deb)
#
# 依赖: dpkg-dev, debhelper (>= 13), make
# 用法: ./packaging/build-deb.sh
# 产物: dist/deb/inphic-control_<版本>_all.deb
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="inphic-control"
VERSION="$(make -s -C "$ROOT" print-version)"
OUTDIR="${OUTDIR:-$ROOT/dist/deb}"

for tool in dpkg-buildpackage dh make; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "缺少 $tool, 请安装: sudo apt install dpkg-dev debhelper make" >&2
        exit 1
    }
done

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
SRCDIR="$STAGE/$NAME-$VERSION"
mkdir -p "$SRCDIR"

echo "==> 准备源码树 $NAME-$VERSION"
tar -C "$ROOT" \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' \
    --exclude='dist' --exclude='build' --exclude='*.rpm' --exclude='*.deb' \
    -cf - . | tar -C "$SRCDIR" -xf -

# 上游 tarball (供 dpkg-buildpackage -S 使用, 不含 debian/)
tar -C "$SRCDIR" --exclude='./packaging/debian' --exclude='./packaging/debian/*' \
    -czf "$STAGE/${NAME}_${VERSION}.orig.tar.gz" .

cp -r "$ROOT/packaging/debian" "$SRCDIR/debian"
chmod +x "$SRCDIR/debian/rules" "$SRCDIR/debian/postinst" "$SRCDIR/debian/postrm"

echo "==> dpkg-buildpackage"
cd "$SRCDIR"
dpkg-buildpackage -us -uc -b

mkdir -p "$OUTDIR"
cp "$STAGE"/*.deb "$OUTDIR/"
cp "$STAGE"/*.buildinfo "$STAGE"/*.changes "$OUTDIR/" 2>/dev/null || true

echo
echo "==> 产物:"
ls -1 "$OUTDIR"
