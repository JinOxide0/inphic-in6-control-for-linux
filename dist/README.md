# 构建产物（v0.3.0）

| 文件 | 适用发行版 | 安装命令 |
| --- | --- | --- |
| `rpm/inphic-control-0.3.0-1.fc44.noarch.rpm` | Fedora / RHEL / openSUSE | `sudo dnf install ./rpm/inphic-control-*.rpm` |
| `deb/inphic-control_0.3.0-1_all.deb` | Debian / Ubuntu | `sudo apt install ./deb/inphic-control_*.deb` |
| `arch/inphic-control-0.3.0-1-any.pkg.tar.zst` | Arch Linux | `sudo pacman -U ./arch/inphic-control-*.pkg.tar.zst` |

校验完整性：

```bash
cd dist && sha256sum -c SHA256SUMS
```

安装后重新插拔一次接收器（或注销重登），udev 规则才会对 hidraw 生效。

## 说明

- 三种包内容一致（`/usr` 前缀），均为纯 Python + GTK4/libadwaita，无编译产物。
- RPM 里带 `fc44` 标签是构建环境的 release 后缀，`noarch` 内容在其他 Fedora 版本同样可用。
- Flatpak 包未在本机生成：需要 `flatpak-builder` 与 `org.gnome.Platform/Sdk` 运行时，
  请按 `packaging/README.md` 的说明构建：

  ```bash
  sudo dnf install flatpak-builder            # 或 apt install flatpak-builder
  ./packaging/build-flatpak.sh
  ```

## 重新构建

```bash
./packaging/build-rpm.sh        # → ~/rpmbuild/RPMS/noarch/
./packaging/build-deb.sh        # → dist/deb/（需 Debian/Ubuntu 或容器）
./packaging/build-arch.sh       # → packaging/arch/（需 Arch 或容器）
```
