Name:           inphic-control
Version:        0.4.0
Release:        1%{?dist}
Summary:        Inphic IN6 (8K) gaming mouse control panel for Linux
Summary(zh_CN): Inphic IN6 (8K) 游戏鼠标 Linux 控制面板
License:        MIT
URL:            https://github.com/JinOxide0/inphic-in6-control-for-linux
BuildArch:      noarch
BuildRequires:  make

Requires:       python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita

Source0:        %{name}-%{version}.tar.gz

%description
A modern dark-themed GTK4/libadwaita control panel for the Inphic IN6
tri-mode gaming mouse on Linux. Configure DPI stages, polling rate
(up to 8000 Hz), RGB lighting, sleep and debounce, plus button remapping
over the vendor HID interface (Report ID 4). No Windows software needed.

%description -l zh_CN
为 Inphic IN6 三模游戏鼠标打造的 Linux 控制面板（GTK4 / libadwaita，
深色界面）。支持 DPI 档位、轮询率（最高 8000 Hz）、RGB 灯光、
休眠/去抖参数以及按键重映射，直接通过厂商 HID 接口（Report ID 4）
通信，无需 Windows 驱动。

%prep
%setup -q

%build
# 纯 Python, 无需构建

%install
%make_install

%post
/usr/bin/udevadm control --reload-rules >/dev/null 2>&1 || :
/usr/bin/udevadm trigger --subsystem-match=hidraw >/dev/null 2>&1 || :

%postun
/usr/bin/udevadm control --reload-rules >/dev/null 2>&1 || :

%files
%license LICENSE
%doc README.md README.en.md docs
%{_bindir}/inphic-control
%{_datadir}/inphic-control
%{_datadir}/applications/inphic-control.desktop
%{_datadir}/icons/hicolor/scalable/apps/inphic-control.svg
%{_prefix}/lib/udev/rules.d/70-inphic-in6.rules

%changelog
* Sat Oct 03 2026 Inphic Control contributors <noreply@example.com> - 0.4.0-1
- 界面中英双语: 新增语言选项 (跟随系统 / 简体中文 / English), 英文翻译
- Bilingual UI: language selector (system / Chinese / English) with English translation

* Fri Oct 02 2026 Inphic Control contributors <noreply@example.com> - 0.3.0-1
- 新增宏功能: 键盘/移动动作, 四种触发方式, 两页分包写入
- 宏协议逆向自官方 Windows 驱动 (宏动作编码 + 页校验和)

* Fri Oct 02 2026 Inphic Control contributors <noreply@example.com> - 0.2.0-1
- 修正写入协议: 官方帧格式 + 校验和, 鼠标侧 ACK 与自动重试
- 载荷长度对齐官方驱动 (DPI 56 / 灯光 15 / 轮询 9 / 按键 59)
