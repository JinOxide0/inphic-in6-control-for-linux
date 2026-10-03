"""轻量多语言支持 (gettext 风格: 中文原文为 key, 英文查表).

- 配置文件 `language` 可选 "auto" / "zh" / "en"
- auto: 读取 LC_ALL / LC_MESSAGES / LANG 环境变量, zh* -> 中文, 其他 -> 英文
- 未收录的字符串原样返回, 漏翻不会报错
"""
from __future__ import annotations

import os

SUPPORTED = ("auto", "zh", "en")
DEFAULT_LANGUAGE = "zh"

_current = DEFAULT_LANGUAGE


def detect_language() -> str:
    """按系统环境推断语言."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var) or ""
        if not value:
            continue
        code = value.split(".")[0].split("_")[0].strip().lower()
        if code:
            return "zh" if code == "zh" else "en"
    return "en"


def set_language(preference: str | None) -> str:
    """设置当前语言, 返回生效的语言代码."""
    global _current
    if preference in ("zh", "en"):
        _current = preference
    else:
        _current = detect_language()
    return _current


def get_language() -> str:
    return _current


def _(message: str) -> str:
    """把中文原文翻译为当前语言."""
    if _current == "en":
        return TRANSLATIONS.get(message, message)
    return message


# ---------------------------------------------------------------- 英文词典
TRANSLATIONS: dict[str, str] = {
    # ---------------- widgets / 通用
    "已充满": "Full",
    "充电中": "Charging",
    "使用中": "In use",
    "未检测到设备": "No device detected",
    "请将 8K 接收器插入 USB 端口": "Plug the 8K receiver into a USB port",
    "未连接": "Not connected",
    "Inphic 设备": "Inphic device",
    "8K 接收器": "8K receiver",
    "USB 有线连接": "USB wired connection",
    "已连接": "Connected",
    "请使用 8K 接收器或有线连接（蓝牙模式不支持配置）":
        "Use the 8K receiver or a wired connection (Bluetooth mode cannot be configured)",
    "设置键盘快捷键": "Set Keyboard Shortcut",
    "捕获按键": "Capture Key",
    "取消": "Cancel",
    "确定": "OK",
    "请直接按下想要绑定的按键组合": "Press the key combination you want to bind",
    "该按键不支持，请换一个": "This key is not supported, try another one",
    "请先按下一个按键": "Press a key first",
    "按下": "Down",
    "抬起": "Up",

    # ---------------- 主窗口
    "显示/隐藏侧边栏": "Toggle sidebar",
    "鼠标电量": "Mouse battery",
    "重新应用全部设置": "Re-apply all settings",
    "设置": "Settings",
    "概览": "Overview",
    "性能": "Performance",
    "灯光": "Lighting",
    "按键": "Buttons",
    "关于": "About",
    "鼠标可能休眠中，已安排自动重试（唤醒后自动应用）":
        "The mouse may be asleep; a retry was scheduled (applied automatically on wake)",
    "已连接 {label}": "Connected: {label}",
    "设备未连接": "Device not connected",
    "已重新应用全部设置": "All settings re-applied",

    # ---------------- 概览页
    "当前 DPI": "Current DPI",
    "轮询率": "Polling rate",
    "按键映射": "Button mapping",
    "应用全部设置": "Apply all settings",
    "恢复默认": "Restore defaults",
    "设置会立即写入鼠标; 修改后自动保存到本地配置。":
        "Changes are written to the mouse immediately and saved to the local config.",
    "档位 {stage} / 共 {enabled} 档": "Stage {stage} of {enabled} enabled",
    "竞技模式": "Esports mode",
    "游戏模式": "Gaming mode",
    "省电模式": "Power-saving mode",
    "关闭": "Off",
    "常亮": "Static",
    "呼吸": "Breathing",
    "霓虹": "Neon",
    "循环呼吸": "Cycle breathing",
    "DPI 常亮": "DPI static",
    "DPI 呼吸": "DPI breathing",
    "#{color} · 亮度 {brightness}": "#{color} · Brightness {brightness}",
    "{count} 个自定义": "{count} customized",
    "共 18 个动作槽位": "18 action slots in total",
    "已恢复默认设置": "Defaults restored",

    # ---------------- DPI 页
    "当前档位": "Active stage",
    "按鼠标底部的 DPI 键可在启用的档位间切换":
        "Press the DPI button on the bottom of the mouse to cycle through enabled stages",
    "DPI 档位": "DPI stages",
    "范围 {minimum} - {maximum}, 步进 {step}": "Range {minimum} - {maximum}, step {step}",
    "档位 {index}": "Stage {index}",
    "该档位的指示灯颜色": "Indicator color for this stage",
    "至少需要启用一个 DPI 档位": "At least one DPI stage must stay enabled",
    "当前: 档位 {stage} · {dpi} DPI": "Active: stage {stage} · {dpi} DPI",

    # ---------------- 性能页
    "8K 接收器支持最高 8000 Hz; 高轮询率会增加 CPU 占用":
        "The 8K receiver supports up to 8000 Hz; higher rates increase CPU usage",
    "传感器": "Sensor",
    "波纹控制 (Ripple Control)": "Ripple Control",
    "降低无线传输带来的抖动": "Reduces jitter caused by wireless transmission",
    "角度捕捉 (Angle Snapping)": "Angle Snapping",
    "让直线移动更平稳": "Keeps straight-line movement steady",
    "运动同步 (Motion Sync)": "Motion Sync",
    "传感器采样与 USB 上报同步": "Synchronizes sensor sampling with USB reports",
    "抬起高度 (LOD)": "Lift-off distance (LOD)",
    "电源管理": "Power management",
    "休眠时间": "Sleep timer",
    "无操作后进入浅睡的时间 (0.5 - 30 分钟)": "Time before light sleep when idle (0.5 - 30 min)",
    "深度休眠": "Deep sleep",
    "进入深度省电的时间 (1 - 60 分钟)": "Time before deep sleep (1 - 60 min)",
    "按键响应": "Button response",
    "按键去抖": "Debounce",
    "数值越低响应越快 (4 - 50 ms)": "Lower values respond faster (4 - 50 ms)",

    # ---------------- 灯光页
    "灯光模式": "Lighting mode",
    "「DPI 常亮 / DPI 呼吸」会显示当前 DPI 档位的颜色":
        '"DPI static / DPI breathing" shows the color of the active DPI stage',
    "模式": "Mode",
    "颜色": "Color",
    "灯光颜色": "Light color",
    "仅常亮 / 呼吸模式使用": "Only used by static / breathing modes",
    "亮度与速度": "Brightness and speed",
    "亮度": "Brightness",
    "1 (最暗) - 8 (最亮)": "1 (dimmest) - 8 (brightest)",
    "呼吸速度": "Breathing speed",
    "1 (最慢) - 8 (最快)": "1 (slowest) - 8 (fastest)",

    # ---------------- 按键页
    "无功能": "Disabled",
    "鼠标左键": "Left click",
    "鼠标右键": "Right click",
    "鼠标中键": "Middle click",
    "后退": "Back",
    "前进": "Forward",
    "双击": "Double click",
    "DPI 循环": "DPI cycle",
    "DPI +": "DPI +",
    "DPI -": "DPI -",
    "向上滚动": "Scroll up",
    "向下滚动": "Scroll down",
    "滚轮左倾": "Tilt wheel left",
    "滚轮右倾": "Tilt wheel right",
    "狙击键 (Easy Aim)": "Sniper button (Easy Aim)",
    "播放 / 暂停": "Play / Pause",
    "上一曲": "Previous track",
    "下一曲": "Next track",
    "停止播放": "Stop playback",
    "打开播放器": "Open media player",
    "音量 +": "Volume +",
    "音量 -": "Volume -",
    "静音": "Mute",
    "计算器": "Calculator",
    "邮件": "Email",
    "浏览器后退": "Browser back",
    "浏览器前进": "Browser forward",
    "刷新浏览器": "Refresh browser",
    "浏览器主页": "Browser home",
    "浏览器搜索": "Browser search",
    "复制": "Copy",
    "粘贴": "Paste",
    "剪切": "Cut",
    "撤销": "Undo",
    "重做": "Redo",
    "全选": "Select all",
    "保存": "Save",
    "查找": "Find",
    "打印": "Print",
    "切换窗口": "Switch window",
    "关闭窗口": "Close window",
    "显示桌面": "Show desktop",
    "锁定电脑": "Lock PC",
    "运行": "Run",
    "截图": "Screenshot",
    "收藏夹": "Favorites",
    "配置循环": "Profile cycle",
    "上一配置": "Previous profile",
    "下一配置": "Next profile",
    "键盘快捷键…": "Keyboard shortcut…",
    "宏…": "Macro…",
    "鼠标按键": "Mouse buttons",
    "修改后立即写入鼠标": "Changes are written to the mouse immediately",
    "说明": "Notes",
    "宏": "Macro",
    "选择「宏…」即可为按键录制键盘/移动宏":
        'Choose "Macro…" to record a keyboard / movement macro for the button',
    "其余 13 个功能槽位保持默认": "The other 13 function slots keep their defaults",
    "DPI 键 / 模式键 / 滚轮等由固件固定处理":
        "DPI button / mode button / scroll wheel are handled by firmware",
    "键盘: {shortcut}": "Keyboard: {shortcut}",
    "宏: {count} 个动作": "Macro: {count} actions",
    "宏: 未编辑": "Macro: not edited",

    # ---------------- 宏对话框
    "循环次数播放": "Play N times",
    "任意键按下停止": "Stop on any key press",
    "按住播放，松开停止": "Hold to play, release to stop",
    "当前宏键按下停止": "Stop on macro key press",
    "按下要录制的按键（A-Z、0-9、F1-F24 等）":
        "Press the key to record (A-Z, 0-9, F1-F24, etc.)",
    "鼠标移动": "Mouse move",
    "水平移动 X": "Horizontal move X",
    "垂直移动 Y": "Vertical move Y",
    "-32768 ~ 32767 (像素)": "-32768 to 32767 (pixels)",
    "编辑宏 — {button}": "Edit macro — {button}",
    "保存并应用": "Save and apply",
    "触发方式": "Trigger",
    "循环次数": "Loop count",
    "触发方式为「循环次数播放」时生效": 'Only applies to the "Play N times" trigger',
    "动作列表（每条动作的间隔 = 与上一动作的时间）":
        "Action list (each delay = time since the previous action)",
    "＋ 按键": "+ Key",
    "＋ 鼠标移动": "+ Mouse move",
    "还没有动作，点击上方按钮添加": "No actions yet — add one with the buttons above",
    "与上一动作的间隔 (毫秒)": "Delay since previous action (ms)",
    "删除此动作": "Delete this action",
    "移动 ({x}, {y})": "Move ({x}, {y})",
    "宏至少需要一个动作": "A macro needs at least one action",

    # ---------------- 关于页
    "设备": "Device",
    "设备名称": "Device name",
    "USB ID": "USB ID",
    "命令接口": "Command interface",
    "电量": "Battery",
    "协议": "Protocol",
    "IN6 配置协议": "IN6 configuration protocol",
    "Report ID 4 · 厂商接口 · 命令类型 4/5/6/8/9":
        "Report ID 4 · vendor interface · command types 4/5/6/8/9",
    "支持功能": "Features",
    "DPI · 轮询率 · 灯光 · 性能 · 按键映射 · 宏 (两页分包)":
        "DPI · polling rate · lighting · performance · button mapping · macros (two-page packets)",
    "协议来源": "Protocol source",
    "由官方 Web 驱动物理分析 + 社区逆向文档交叉验证":
        "Derived from the official Web driver and cross-checked with community reverse-engineering docs",
    "感谢": "Credits",
    "权限": "Permissions",
    "hidraw 访问权限": "hidraw access",
    "RPM 已安装 udev 规则, 重新插拔接收器后生效":
        "The udev rule is installed by the package; re-plug the receiver to apply",
    "版本 {version} · GTK4 / libadwaita": "Version {version} · GTK4 / libadwaita",
    "支持的设备": "Supported devices",
    "Inphic IN6 / IN6SE · 8K 接收器 (1d57:fa65)":
        "Inphic IN6 / IN6SE · 8K receiver (1d57:fa65)",
    "界面语言": "Interface language",
    "语言": "Language",
    "跟随系统": "System default",
    "语言已切换": "Language switched",

    # ---------------- 设备名称
    "左键": "Left button",
    "右键": "Right button",
    "中键": "Middle button",
    "IN6 8K 接收器": "IN6 8K receiver",
    "IN6 (有线)": "IN6 (wired)",
    "IN6 接收器": "IN6 receiver",

    # ---------------- 命令行诊断
    "未发现可配置的 Inphic 设备 (1d57:* 且带厂商接口)":
        "No configurable Inphic device found (1d57:* with vendor interface)",
    "可访问": "accessible",
    "无权限 (需要 udev 规则)": "no permission (udev rule required)",
    "    接口 {interface} · HID 名 {name} · {status}":
        "    iface {interface} · HID name {name} · {status}",
    "没有访问权限。临时授权:": "No access permission. Temporary fix:",
    "或安装软件包后重新插拔接收器 (包含 udev 规则)。":
        "Or install the package and re-plug the receiver (includes the udev rule).",
    "已发送 {length:>2} 字节: {data} ...": "Sent {length:>2} bytes: {data} ...",
    "监听设备事件 {seconds:.0f} 秒 (Ctrl+C 退出)...":
        "Listening for device events for {seconds:.0f}s (Ctrl+C to quit)...",
    "原始: {data}": "raw: {data}",
    "电量: {level}% (状态 {status})": "Battery: {level}% (status {status})",
    "ACK: 成功": "ACK: OK",
    "ACK: 失败": "ACK: FAIL",
    "DPI 切换到档位 {stage}": "DPI switched to stage {stage}",
    "其他事件: {data}": "Other event: {data}",
    "监听时长": "listen duration",
    "先写入一次本地配置再监听": "apply the local config once before listening",
}
