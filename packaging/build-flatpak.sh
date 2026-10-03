#!/usr/bin/env bash
# 构建 inphic-control 的 Flatpak (可跨发行版使用)
#
# 依赖: flatpak, flatpak-builder, org.gnome.Platform/Sdk (版本见 manifest)
# 用法: ./packaging/build-flatpak.sh [--install]
#         --install  构建后安装到当前用户 (~/.local/share/flatpak)
# 产物: dist/inphic-control.flatpak
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$ROOT/packaging/flatpak/io.github.inphic.InphicControl.yml"
BUILD_DIR="$ROOT/build/flatpak"
REPO_DIR="$ROOT/build/flatpak-repo"
BUNDLE="$ROOT/dist/inphic-control.flatpak"

for tool in flatpak flatpak-builder; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "缺少 $tool, 请安装后再运行 (如: sudo dnf install flatpak-builder)" >&2
        exit 1
    }
done

ARGS=(--force-clean --repo="$REPO_DIR")
if [ "${1:-}" = "--install" ]; then
    ARGS+=(--user --install)
fi

echo "==> flatpak-builder"
flatpak-builder "${ARGS[@]}" "$BUILD_DIR" "$MANIFEST"

echo "==> 导出 bundle"
mkdir -p "$ROOT/dist"
flatpak build-bundle "$REPO_DIR" "$BUNDLE" io.github.inphic.InphicControl

echo
echo "==> 产物: $BUNDLE"
echo "安装: flatpak install --user $BUNDLE"
