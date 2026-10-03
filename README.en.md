# Inphic Control

[简体中文](README.md) | [English](README.en.md)

A Linux control panel for the **Inphic IN6 (tri-mode / 8K receiver)** gaming mouse.
Modern dark UI (GTK4 + libadwaita) that talks directly to the vendor HID interface —
no Windows driver required. A community, vibe-coded project.

The UI is **bilingual (English / Simplified Chinese)**: it follows the system
language by default and can be switched in **About → Interface language**.

![preview](docs/preview.png)

## Features

| Feature | Description |
| --- | --- |
| DPI | 8 stages, 50–26000, enable/disable each stage, per-stage indicator color, switch the active stage |
| Polling rate | 125 / 250 / 500 / 1000 / 2000 / 4000 / 8000 Hz |
| Sensor | Ripple Control, Angle Snapping, Motion Sync, lift-off distance (1 / 2 mm) |
| Power | Sleep timer (0.5–30 min), deep sleep (1–60 min) |
| Buttons | Debounce time (4–50 ms) |
| Lighting | Off / Static / Breathing / Neon / Cycle breathing / DPI static / DPI breathing, with color and brightness/speed |
| Button mapping | Left, right, middle, forward, back — mouse actions, multimedia keys, system shortcuts, custom key combos |
| Macros | Key press/release + mouse movement, 4 trigger modes (play N times / stop on any key / hold to play / stop on macro key), one macro per button |
| Battery | Live battery level and charging status |
| Config persistence | Saved to `~/.config/inphic-control/config.json` |
| Sleep retry | Commands are retried at 1s/6s/21s while the mouse is asleep and applied on wake |
| UI language | English / Simplified Chinese, follows the system by default, switchable in the About page |

## Install

```bash
sudo dnf install ./inphic-control-0.4.0-1.*.noarch.rpm
```

After installing, **re-plug the receiver** (or log out and back in) so the udev
rule grants the current user access to the hidraw device. Then open
“Inphic Control” from the application menu.

Prebuilt packages for each distribution are attached to
[GitHub Releases](https://github.com/JinOxide0/inphic-in6-control-for-linux/releases):
RPM (Fedora / RHEL / openSUSE), DEB (Debian / Ubuntu) and Arch packages.

## Usage

```bash
inphic-control                    # GUI
inphic-control --probe            # CLI diagnostics: list devices, watch battery/events
inphic-control --probe --apply    # write the current config once, then watch
```

If you see a permission error, grant temporary access:

```bash
sudo setfacl -m u:$USER:rw /dev/hidrawN
```

## Packaging

All distributions share the install rules in the top-level `Makefile`;
build scripts live in `packaging/`:

| Target | Command | Output |
| --- | --- | --- |
| Fedora / RHEL / openSUSE (RPM) | `./packaging/build-rpm.sh` | `~/rpmbuild/RPMS/noarch/*.rpm` |
| Debian / Ubuntu (DEB) | `./packaging/build-deb.sh` | `dist/deb/*.deb` |
| Arch Linux | `./packaging/build-arch.sh` (Arch environment) | `packaging/arch/*.pkg.tar.zst` |
| Flatpak (cross-distro) | `./packaging/build-flatpak.sh` | `dist/inphic-control.flatpak` |

RPM builds need `rpm-build`, DEB needs `dpkg-dev` + `debhelper`, Flatpak needs
`flatpak-builder`. Runtime dependencies everywhere: `python3-gobject`, `gtk4`,
`libadwaita`. See [packaging/README.md](packaging/README.md) for COPR / OBS /
PPA / AUR / Flathub publishing instructions.

## Protocol

The receiver (`1d57:fa65`) is a composite HID device. USB interface 3 is the
vendor-defined interface (Usage Page `0xFF00`, Report ID `4`). Configuration
commands are sent as Output Reports on that interface.

**Write frame format** (reverse-engineered from the official Windows driver):

```
[0x04] [total length + 5] [0x00] <command payload> [checksum high] [checksum low]
checksum = sum of bytes 0..end of payload (16 bit)
```

The first byte of the payload is the command type:

| Type | Length | Purpose |
| --- | --- | --- |
| `0x04` | 56 | DPI / sensor |
| `0x05` | 15 | Lighting / sleep / debounce |
| `0x06` | 9 | Polling rate |
| `0x08` | 59 | Button mapping |
| `0x09` | 111 | Macros (two pages: `04 40` page 0 = 59 bytes + `04 39` page 1 = 52 bytes, each with checksum) |

**Device responses** (Input Report, Report ID 4):

- `06 c0 01 00 xx` — receiver ACK (checksum passed, ~30 ms)
- `06 c1 01 00 xx` — mouse confirmed the settings (~0.7 s)
- `06 c1 00 00 xx` — mouse did not confirm (~2.1 s, usually because it is asleep)
- `03 41 40 <status> <battery>` — battery report (~every 2 s)

The protocol was reverse-engineered from the official Web driver
(`hub.inphic.cn`) and the official Windows driver (INPHIC YU Setup,
`hiddriver.dll` / `INPHIC.exe`), and cross-checked against these community
projects:

- [HarukaYamamoto0/attack-shark-x11-driver](https://github.com/HarukaYamamoto0/attack-shark-x11-driver) (MIT)
- [D3m0nZOnFire/mousectl](https://github.com/D3m0nZOnFire/mousectl) (MIT)

## Known limitations

- **Macros support single keys and mouse movement only**: macro actions can
  record a single keyboard key (down/up) and mouse movement; modifier combos
  (Ctrl+X, etc.) cannot be used inside macros yet — use “Keyboard shortcut…”
  binding instead.
- **The app cannot read the current settings from the mouse**: the official Web
  driver is write-only as well; the UI shows the locally saved configuration.
- Some settings (e.g. DPI) apply immediately — no save button needed.

## Disclaimer

This software is not affiliated with Inphic. It is a community
reverse-engineering effort; writing unknown settings involves risk, use at your
own. If the device stops responding, switch to Bluetooth mode for a few seconds
and back.

## License

MIT
