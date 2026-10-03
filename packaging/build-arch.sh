#!/usr/bin/env bash
# 构建 inphic-control 的 Arch Linux 软件包
#
# 依赖: Arch 环境 + base-devel (makepkg, make)
# 用法: ./packaging/build-arch.sh
# 产物: packaging/arch/inphic-control-<版本>-<pkgrel>-any.pkg.tar.zst
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(make -s -C "$ROOT" print-version)"
PKGDIR="$ROOT/packaging/arch"

command -v makepkg >/dev/null 2>&1 || {
    echo "未找到 makepkg: 请在 Arch Linux 上构建 (或使用 docker run archlinux)。" >&2
    exit 1
}

if [ "$(id -u)" -eq 0 ]; then
    echo "makepkg 不能以 root 运行; 请用普通用户构建。" >&2
    echo "容器示例: podman run --rm -v \"\$PWD:/src:ro\" archlinux bash -c '" >&2
    echo "  pacman -Sy --noconfirm --needed base-devel && cp -r /src /tmp/build &&" >&2
    echo "  useradd -m b && chown -R b /tmp/build &&" >&2
    echo "  su b -c \"cd /tmp/build && ./packaging/build-arch.sh\" &&" >&2
    echo "  cat /tmp/build/packaging/arch/*.pkg.tar.zst' > inphic-control.pkg.tar.zst" >&2
    exit 1
fi

echo "==> 准备源码 tarball inphic-control-$VERSION.tar.gz"
tar -C "$ROOT" \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' \
    --exclude='dist' --exclude='build' --exclude='*.rpm' --exclude='*.deb' \
    --exclude='packaging/arch/*.tar.gz' --exclude='packaging/arch/pkg' \
    -czf "$PKGDIR/inphic-control-$VERSION.tar.gz" .

echo "==> makepkg"
cd "$PKGDIR"
makepkg -f --skipchecksums --noconfirm

echo
echo "==> 产物:"
find "$PKGDIR" -maxdepth 1 -name '*.pkg.tar.*' -printf '   %p\n'
