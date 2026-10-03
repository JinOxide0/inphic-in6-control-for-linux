# 打包指南

本目录包含各发行版的打包配置。所有打包方式共用根目录 `Makefile`
的安装规则，安装布局完全一致：

| 路径 | 内容 |
| --- | --- |
| `/usr/bin/inphic-control` | 启动器（自动推导前缀，兼容 `/app`） |
| `/usr/share/inphic-control/inphic_control/` | Python 包源码（含 `style.css`、`ui/`） |
| `/usr/share/applications/inphic-control.desktop` | 桌面入口 |
| `/usr/share/icons/hicolor/scalable/apps/inphic-control.svg` | 图标 |
| `/usr/lib/udev/rules.d/70-inphic-in6.rules` | hidraw `uaccess` 权限规则 |

手动安装（开发时也可用）：

```bash
make install DESTDIR=/tmp/pkg PREFIX=/usr     # 打包暂存
sudo make install                             # 直接安装
sudo make uninstall                           # 卸载
```

运行依赖：`python3` (>= 3.10)、PyGObject (`python3-gi` / `python3-gobject`)、
GTK4、libadwaita（含对应的 GObject Introspection typelib）。

## Fedora / RHEL / openSUSE（RPM）

```bash
./packaging/build-rpm.sh        # 产物在 ~/rpmbuild/RPMS/noarch/
sudo dnf install ~/rpmbuild/RPMS/noarch/inphic-control-*.rpm
```

- 配置：`packaging/inphic-control.spec`
- 构建依赖：`rpm-build`、`make`
- 发布：
  - **Fedora / EPEL**：[Copr](https://copr.fedorainfracloud.org/)（注册后
    `copr-cli build` 上传 spec 与源码包，自动出多版本仓库）
  - **openSUSE / 通用 RPM**：[OBS](https://build.opensuse.org/) 可直接用同一
    spec 构建 openSUSE、Fedora、RHEL 乃至 Debian/Arch 的包。

## Debian / Ubuntu（DEB）

```bash
./packaging/build-deb.sh        # 产物在 dist/deb/
sudo apt install ./dist/deb/inphic-control_*_all.deb
```

- 配置：`packaging/debian/`（`control`、`rules`、`install`、`postinst` 等）
- 构建依赖：`dpkg-dev`、`debhelper (>= 13)`、`make`
- 发布：
  - **Ubuntu**：[Launchpad PPA](https://help.launchpad.net/Packaging/PPA) 只接受
    源码包：在 `build-deb.sh` 的暂存目录中额外执行 `dpkg-buildpackage -S -sa`
    （脚本已生成 `.orig.tar.gz`），然后
    `dput ppa:<用户>/<PPA名> inphic-control_<版本>_source.changes`
  - **Debian**：[mentors.debian.net](https://mentors.debian.net/) → 走 ITP/NEW 流程

## Arch Linux

```bash
./packaging/build-arch.sh       # 需在 Arch 环境运行, 产物在 packaging/arch/
sudo pacman -U packaging/arch/inphic-control-*.pkg.tar.zst
```

- 配置：`packaging/arch/PKGBUILD`、`inphic-control.install`（udev 重载）
- 非 Arch 系统可用容器（`makepkg` 不能以 root 运行）：
  `podman run --rm -v "$PWD:/src:ro" archlinux bash -c 'pacman -Sy --noconfirm --needed base-devel >/dev/null && cp -r /src /tmp/build && useradd -m b && chown -R b /tmp/build && su b -c "cd /tmp/build && ./packaging/build-arch.sh" && cat /tmp/build/packaging/arch/*.pkg.tar.zst' > inphic-control.pkg.tar.zst`
- 发布 **AUR**：
  1. 将源码发布到 GitHub Release，并把 `source` 改为
     `("$pkgname-$pkgver.tar.gz::https://github.com/JinOxide0/inphic-in6-control-for-linux/archive/refs/tags/v$pkgver.tar.gz")`
  2. `updpkgsums` 写入真实校验和
  3. `makepkg --printsrcinfo > .SRCINFO`，连同 `PKGBUILD`、`.install` 推送到 AUR

## Flatpak（跨发行版单文件包）

```bash
./packaging/build-flatpak.sh              # 产物 dist/inphic-control.flatpak
./packaging/build-flatpak.sh --install    # 构建并安装到当前用户
flatpak install --user dist/inphic-control.flatpak
flatpak run io.github.inphic.InphicControl
```

- 配置：`packaging/flatpak/io.github.inphic.InphicControl.yml`
- 依赖：`flatpak`、`flatpak-builder`、`org.gnome.Platform/Sdk`（版本号需与
  manifest 中的 `runtime-version` 一致，用 `flatpak list` 查看）
- 发布 [Flathub](https://docs.flathub.org/)：以 git tag 作为 source 提交 manifest
  到 `flathub/flathub` 仓库走审核。
- **注意**：Flatpak 沙箱内无法安装 udev 规则，宿主机需另外安装
  `70-inphic-in6.rules`（例如安装本项目的 DEB/RPM，或把规则手动放到
  `/etc/udev/rules.d/` 后 `sudo udevadm control --reload-rules`）。
  临时方案：`sudo setfacl -m u:$USER:rw /dev/hidrawN`。

## 其他形式

| 形式 | 说明 |
| --- | --- |
| **AppImage** | 可行但成本高：需用 [appimage-builder](https://appimage-builder.readthedocs.io/) 或 linuxdeploy 打包 PyGObject/GTK4 typelib，且与宿主 glibc/显卡驱动耦合。跨发行版建议优先 Flatpak。 |
| **Snap** | 不推荐：`strict` 沙箱无法访问 `/dev/hidraw*`，需 `classic` 或自定义 `custom-device` 接口与商店审核，成本高于收益。 |
| **Nix / NixOS** | 可用 `pkgs.python3Packages.buildPythonApplication` 编写 `default.nix`，把 `inphic_control` 装进 site-packages，并 `services.udev.extraRules` 添加权限规则；适合提 PR 到 nixpkgs。 |

## 版本号维护位置

发布新版本时需要同步修改：

- `inphic_control/__init__.py` — `__version__`（Makefile 与 DEB/Arch 构建脚本会读取）
- `inphic_control/ui/window.py` — `APP_VERSION`
- `inphic_control/ui/about_page.py` — 关于页版本文案
- `packaging/build-rpm.sh` — `VERSION`
- `packaging/inphic-control.spec` — `Version`
- `packaging/debian/changelog` — 新版本条目
- `packaging/arch/PKGBUILD` — `pkgver`（并执行 `updpkgsums`）
