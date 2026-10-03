"""Inphic IN6 (8K 接收器) HID 协议实现.

协议来源: 官方 Web 驱动 (hub.inphic.cn) 的打包代码逆向,
并与 Attack Shark X11 (同一厂商 SDKT) 的公开文档交叉验证.

通信方式:
    hidraw 设备 (USB 接口 3, usage page 0xFF00), Report ID 0x04,
    输出/输入载荷 63 字节. 命令载荷第一个字节始终是"命令类型"
    (4=DPI, 5=灯光/性能, 6=轮询率, 8=按键, 9=宏).

本模块只负责"把设置编码成 63 字节以内的命令载荷", 不涉及 IO.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

# IN6 在官方驱动里的设备编号 (0x41)
DEVICE_ID = 0x41

REPORT_ID = 0x04

# 命令类型
CMD_DPI = 0x04
CMD_LIGHTING = 0x05
CMD_POLLING = 0x06
CMD_BUTTONS = 0x08
CMD_MACRO = 0x09

# 轮询率 -> 固件字节 (来自官方 Web 驱动 IN6 性能页)
POLLING_RATE_BYTES: dict[int, int] = {
    125: 32,
    250: 16,
    500: 8,
    1000: 4,
    2000: 2,
    4000: 1,
    8000: 64,
}

# 灯光模式 -> 高半字节 (官方 Web 驱动 lightMode = hex << 4)
LIGHT_MODES: dict[str, int] = {
    "off": 0x0,
    "static": 0x1,
    "breathing": 0x2,
    "neon": 0x3,
    "cycle_breathing": 0x4,
    "static_dpi": 0x5,
    "breathing_dpi": 0x6,
}

# 每个 DPI 档位的默认指示颜色 (官方 Fn.Dpi_level_*_indication_flag)
DEFAULT_DPI_COLORS: list[tuple[int, int, int]] = [
    (255, 255, 0),
    (0, 255, 255),
    (0, 255, 0),
    (255, 0, 255),
    (0, 0, 255),
    (255, 0, 0),
    (255, 64, 0),
    (255, 255, 255),
]

# 官方 Fn.Dpi_indication_type
DPI_INDICATION_TYPE = 1

# ---------------------------------------------------------------- DPI

def encode_dpi(value: int) -> tuple[int, int]:
    """官方 za(): DPI = 50 + 50 * 原始值, 小端 16 位."""
    if value <= 0:
        return (0, 0)
    raw = (value - 50) // 50
    if raw <= 255:
        return (raw, 0)
    return (raw & 0xFF, (raw >> 8) & 0xFF)


def decode_dpi(low: int, high: int) -> int:
    return 50 + 50 * (low | (high << 8))


def build_dpi_packet(
    values: Sequence[int],
    active_stage: int,
    *,
    active_mask: int = 0x3F,
    lift_off_distance: int = 0,      # 0 = 1mm, 1 = 2mm
    ripple: bool = True,
    angle_snap: bool = False,
    motion_sync: bool = True,
    colors: Sequence[tuple[int, int, int]] | None = None,
    profile_id: int = 1,
) -> bytes:
    """构造 DPI 命令 (60 字节).

    官方 web 驱动的 socketDpiDataIN6/Sde 完全等价实现.
    注意 IN6 固件把角度捕捉/运动同步复用到了 byte6/byte7.
    """
    buf = bytearray(56)
    buf[0] = CMD_DPI
    buf[1] = 56                      # sizeTotalData
    buf[2] = profile_id
    buf[3] = lift_off_distance & 0xFF
    buf[4] = 1 if ripple else 0
    buf[5] = active_mask & 0xFF
    buf[6] = 1 if angle_snap else 0
    buf[7] = 1 if motion_sync else 0

    vals = list(values)[:8] + [0] * max(0, 8 - len(values))
    for i in range(8):
        buf[8 + i], buf[16 + i] = encode_dpi(vals[i])

    buf[24] = max(1, min(8, active_stage))

    palette = list(colors or DEFAULT_DPI_COLORS)
    palette += [(255, 255, 255)] * max(0, 8 - len(palette))
    for i in range(8):
        r, g, b = palette[i]
        buf[25 + 3 * i] = r & 0xFF
        buf[26 + 3 * i] = g & 0xFF
        buf[27 + 3 * i] = b & 0xFF

    buf[49] = DPI_INDICATION_TYPE

    checksum = sum(buf[3:50]) & 0xFFFF
    buf[50] = (checksum >> 8) & 0xFF
    buf[51] = checksum & 0xFF
    return bytes(buf)


# ---------------------------------------------------------------- 轮询率

def build_polling_packet(rate: int, *, profile_id: int = 1) -> bytes:
    """官方 hn(): [6, 9, 1, rate, ~rate, 0, 0, 0, 0]."""
    if rate not in POLLING_RATE_BYTES:
        raise ValueError(f"不支持的轮询率: {rate}")
    raw = POLLING_RATE_BYTES[rate]
    buf = bytearray(9)
    buf[0] = CMD_POLLING
    buf[1] = 9
    buf[2] = profile_id
    buf[3] = raw
    buf[4] = (~raw) & 0xFF
    return bytes(buf)


# ---------------------------------------------------------------- 灯光 / 性能

def build_lighting_packet(
    *,
    light_mode: str = "off",
    brightness: int = 2,             # 1-8, 用于非呼吸模式
    speed: int = 3,                  # 1-8, 用于呼吸模式
    red: int = 0,
    green: int = 0,
    blue: int = 255,
    sleep_minutes: float = 0.5,      # 0.5 - 30
    deep_sleep_minutes: int = 10,    # 1 - 60
    debounce_ms: int = 8,            # 4 - 50, 偶数
    profile_id: int = 1,
) -> bytes:
    """官方 Vpe() + 性能/灯光页的组合编码 (20 字节).

    固件把浅睡/深睡/按键响应时间与灯光参数放在同一条命令里,
    所以每次修改其中任意一项都要带上其余项的当前值.
    """
    if light_mode not in LIGHT_MODES:
        raise ValueError(f"未知灯光模式: {light_mode}")
    mode_byte = LIGHT_MODES[light_mode] << 4

    # 深睡: 官方 M() -> 分钟数高/低半字节塞进 breathingSpeed / LightBrightness 的高半字节
    hi = (deep_sleep_minutes >> 4) & 0x0F
    lo = deep_sleep_minutes & 0x0F
    # breathingSpeed 低半字节 = (9 - speed), LightBrightness 低半字节 = brightness
    breathing_speed = (hi << 4) | ((9 - max(1, min(8, speed))) & 0x0F)
    light_brightness = (lo << 4) | (max(1, min(8, brightness)) & 0x0F)

    # 官方 Windows 驱动的灯光载荷 = 15 字节 (Vpe 的前 15 字节)
    buf = bytearray(15)
    buf[0] = CMD_LIGHTING
    buf[1] = 15
    buf[2] = profile_id
    buf[3] = mode_byte
    buf[4] = breathing_speed
    buf[5] = light_brightness
    buf[6] = red & 0xFF
    buf[7] = green & 0xFF
    buf[8] = blue & 0xFF
    buf[9] = int(round(sleep_minutes * 2)) & 0xFF
    buf[10] = debounce_ms & 0xFF

    checksum = sum(buf[3:11]) & 0xFFFF
    buf[11] = (checksum >> 8) & 0xFF
    buf[12] = checksum & 0xFF
    # buf[13], buf[14] = 0
    return bytes(buf)


# ---------------------------------------------------------------- 按键

# 官方 sC 表: 功能名 -> 3 字节动作
BUTTON_ACTIONS: dict[str, tuple[int, int, int]] = {
    "off": (1, 0, 0),
    "left": (2, 0, 0),
    "right": (3, 0, 0),
    "middle": (4, 0, 0),
    "backward": (5, 0, 0),
    "forward": (6, 0, 0),
    "double_click": (7, 0, 0),
    "fire": (8, 0, 0),
    "scroll_down": (9, 0, 0),
    "scroll_up": (10, 0, 0),
    "tilt_left": (11, 0, 0),
    "tilt_right": (12, 0, 0),
    "dpi_cycle": (13, 0, 0),
    "dpi_up": (14, 0, 0),
    "dpi_down": (15, 0, 0),
    "easy_aim": (16, 0, 3),
    "media_player": (21, 0, 0),
    "previous": (22, 0, 0),
    "next": (23, 0, 0),
    "play_pause": (24, 0, 0),
    "media_stop": (25, 0, 0),
    "mute": (26, 0, 0),
    "volume_up": (27, 0, 0),
    "volume_down": (28, 0, 0),
    "calculator": (29, 0, 0),
    "email": (30, 0, 0),
    "browser_back": (33, 0, 0),
    "browser_forward": (32, 0, 2),
    "browser_refresh": (36, 0, 0),
    "browser_home": (37, 0, 0),
    "browser_search": (38, 0, 0),
    "browser_favorites": (17, 3, 18),
    "show_desktop": (17, 8, 7),
    "lock_pc": (17, 8, 15),
    "run": (17, 8, 21),
    "screenshot": (17, 10, 22),
    "copy": (17, 1, 6),
    "paste": (17, 1, 25),
    "cut": (17, 1, 27),
    "undo": (17, 1, 29),
    "redo": (17, 1, 28),
    "select_all": (17, 1, 4),
    "save": (17, 1, 22),
    "find": (17, 1, 9),
    "print": (17, 1, 19),
    "close_window": (17, 4, 61),
    "swap_windows": (17, 4, 43),
    "profile_cycle": (52, 0, 0),
    "profile_up": (53, 0, 0),
    "profile_down": (54, 0, 0),
    "mode_key": (60, 0, 0),
}

# IN6 在按键命令里的 18 个槽位 (对应官方 Zce 顺序), 以及默认动作.
# 坐标槽位仅前 5 个可以在官方 Web UI 自定义, 其余保持默认.
BUTTON_SLOTS: list[tuple[str, str]] = [
    ("fun_click", "left"),
    ("fun_menu", "right"),
    ("fun_scrolling", "middle"),
    ("fun_dpi_cycle", "dpi_cycle"),
    ("fun_dpi_up", "dpi_up"),
    ("fun_dpi_down", "dpi_down"),
    ("fun_backward", "backward"),
    ("fun_forward", "forward"),
    ("fun_mode_key", "mode_key"),
    ("fun_off_1", "off"),
    ("fun_off_2", "off"),
    ("fun_off_3", "off"),
    ("fun_off_4", "off"),
    ("fun_off_5", "off"),
    ("fun_off_6", "off"),
    ("fun_off_7", "off"),
    ("fun_scroll_down", "scroll_down"),
    ("fun_scroll_up", "scroll_up"),
]

# 官方 Web UI 只允许自定义这 5 个物理按键: (槽位索引, 名称)
USER_BUTTONS: list[tuple[int, str]] = [
    (0, "左键"),
    (1, "右键"),
    (2, "中键"),
    (7, "前进"),
    (6, "后退"),
]

MOD_CTRL, MOD_SHIFT, MOD_ALT, MOD_WIN = 1, 2, 4, 8


def shortcut_action(mod_mask: int, usage: int) -> tuple[int, int, int]:
    """键盘快捷键动作: [17, 修饰键掩码, HID usage id]."""
    return (17, mod_mask & 0x3F, usage & 0xFF)


def macro_action(macro_id: int) -> tuple[int, int, int]:
    """宏动作: [18, 0, 宏编号]."""
    return (18, 0, macro_id & 0xFF)


def build_buttons_packet(
    actions: Sequence[tuple[int, int, int]],
    *,
    profile_id: int = 1,
) -> bytes:
    """官方 ide(): [8, 59, 1, 18*3 字节动作..., 校验和]."""
    if len(actions) != len(BUTTON_SLOTS):
        raise ValueError(f"需要 {len(BUTTON_SLOTS)} 个动作, 收到 {len(actions)}")
    buf = bytearray(59)
    buf[0] = CMD_BUTTONS
    buf[1] = 59
    buf[2] = profile_id
    pos = 3
    for action in actions:
        a, b, c = action
        buf[pos] = a & 0xFF
        buf[pos + 1] = b & 0xFF
        buf[pos + 2] = c & 0xFF
        pos += 3
    checksum = sum(buf[3:pos]) & 0xFFFF
    buf[pos] = (checksum >> 8) & 0xFF
    buf[pos + 1] = checksum & 0xFF
    return bytes(buf)


# ---------------------------------------------------------------- 宏

@dataclass
class MacroAction:
    """宏动作. kind: key(键盘) / move(鼠标移动)."""
    kind: str = "key"
    key: int = 4                    # HID usage (kind=key)
    down: bool = True               # True=按下 False=抬起 (kind=key)
    x: int = 0                      # 有符号 16 位 (kind=move)
    y: int = 0
    delay: int = 10                 # 毫秒


def _encode_actions(actions: list[MacroAction]) -> tuple[bytes, int]:
    """把动作编码进载荷 9..108 区域. 返回 (字节串, 计数).

    官方编码:
      按键(短,<=127ms): [delay|1 按下 / delay|0x80 抬起, key]
      移动(短):         [delay, 0xF6, x_hi, x_lo, y_hi, y_lo]
      长延时(>127ms): 末尾追加 [delay/100, 3], 延时字节用 delay%100 (至少1)
      计数 = Σ(按键+1, 移动+2, 长延时再+1)
    """
    out = bytearray()
    count = 0
    for act in actions:
        delay = max(1, min(25500, int(act.delay)))
        long = delay > 127
        if long:
            g, r = divmod(delay, 100)
            if r < 1:
                r = 1
            g = min(255, g)
        else:
            r = delay
        if act.kind == "key":
            flag = 0x01 if act.down else 0x80
            out.append((r | flag) & 0xFF)
            out.append(act.key & 0xFF)
            count += 1
            if long:
                out.append(g)
                out.append(3)
                count += 1
        else:  # move
            out.append(r & 0xFF)
            out.append(0xF6)
            x = max(-32768, min(32767, int(act.x)))
            y = max(-32768, min(32767, int(act.y)))
            out.append((x >> 8) & 0xFF)
            out.append(x & 0xFF)
            out.append((y >> 8) & 0xFF)
            out.append(y & 0xFF)
            count += 3
            if long:
                out.append(g)
                out.append(3)
                count += 1
        if len(out) > 100:
            raise ValueError("宏动作过多, 超过 100 字节")
    return bytes(out), count


def build_macro_payload(
    macro_id: int,
    trigger: int,
    loops: int,
    actions: list[MacroAction],
    color: tuple[int, int, int] = (0, 0, 0),
) -> bytes:
    """构造 111 字节宏载荷 (官方 Windows 驱动格式)."""
    data, count = _encode_actions(actions)
    buf = bytearray(111)
    buf[0] = CMD_MACRO
    buf[1] = 111
    buf[2] = macro_id & 0xFF
    buf[3] = trigger & 0xFF
    buf[4] = color[0] & 0xFF
    buf[5] = color[1] & 0xFF
    buf[6] = color[2] & 0xFF
    buf[7] = max(1, min(255, loops)) if trigger == 0 else 1
    buf[8] = count & 0xFF
    buf[9:9 + len(data)] = data
    checksum = sum(buf[3:109]) & 0xFFFF
    buf[109] = checksum >> 8
    buf[110] = checksum & 0xFF
    return bytes(buf)


def build_macro_pages(payload: bytes) -> list[bytes]:
    """把 111 字节宏载荷拆成两页输出报告 (官方分包格式).

    页0: [04, 0x40, 0x00, 数据0..58, 校验和16]  (64 字节, 校验和覆盖前 62 字节)
    页1: [04, 0x39, 0x01, 数据59..110, 校验和16, 补零到64]
         (校验和覆盖前 55 字节; 官方 Windows 驱动补零到定长写入)
    每页以 0x04 开头 (即 HID 报告 ID).
    """
    if len(payload) != 111:
        raise ValueError(f"宏载荷应为 111 字节, 收到 {len(payload)}")

    def page(index: int, size_byte: int, data: bytes, csum_len: int) -> bytes:
        chunk = bytearray(size_byte)
        chunk[0] = 0x04
        chunk[1] = size_byte
        chunk[2] = index
        chunk[3:3 + len(data)] = data
        checksum = sum(chunk[0:csum_len]) & 0xFFFF
        chunk[csum_len] = checksum >> 8
        chunk[csum_len + 1] = checksum & 0xFF
        return bytes(chunk)

    pages = [
        page(0, 0x40, payload[0:59], 62),
        page(1, 0x39, payload[59:111], 55),
    ]
    pages[1] += bytes(64 - len(pages[1]))
    return pages


# ---------------------------------------------------------------- 写帧

def frame_packet(payload: bytes) -> bytes:
    """构造官方驱动使用的输出报告帧.

    帧格式 (来自官方 Windows 驱动逆向):
        [0x04] [len+5] [0x00] <载荷...> [校验和高字节] [校验和低字节]
    校验和 = 从索引 0 到 len+2 的所有字节之和 (含报告 ID 与表头).
    设备收到后回包 `06 c0|c1 <状态> 00 <校验>` 其中状态 01=成功.
    """
    n = len(payload)
    buf = bytearray(n + 5)
    buf[0] = REPORT_ID
    buf[1] = n + 5
    buf[2] = 0x00
    buf[3:3 + n] = payload
    checksum = sum(buf[0:n + 3]) & 0xFFFF
    buf[n + 3] = checksum >> 8
    buf[n + 4] = checksum & 0xFF
    return bytes(buf)


def pad_payload(payload: bytes, size: int = 63) -> bytes:
    """(旧格式) 补齐到 Report ID 4 的输出报告长度."""
    if len(payload) > size:
        raise ValueError(f"命令载荷 {len(payload)} 字节超过 {size} 字节")
    return bytes(payload) + bytes(size - len(payload))


# ---------------------------------------------------------------- 事件解析

EVENT_BATTERY = 0x40
EVENT_BATTERY_ALT = 0x41
EVENT_ACK = 0x50
EVENT_DPI_CYCLE = 0x10
EVENT_VIBRATION = 0x11
EVENT_PROFILE = 0x80

_EVENT_CODES = {
    EVENT_BATTERY,
    EVENT_BATTERY_ALT,
    EVENT_ACK,
    EVENT_DPI_CYCLE,
    EVENT_VIBRATION,
    EVENT_PROFILE,
}

_COMMAND_IDS = {0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C}

# 电量状态字节
BATTERY_NORMAL = 1
BATTERY_FULL = 2
BATTERY_CHARGING = 3


@dataclass
class DeviceEvent:
    kind: str                  # battery | ack | dpi_cycle | vibration | profile
    raw: bytes
    battery_status: int | None = None
    battery_level: int | None = None
    ack_command: int | None = None
    ack_ok: bool | None = None
    stage: int | None = None


def parse_event(data: bytes) -> DeviceEvent | None:
    """解析厂商接口的输入报告.

    1) 写入确认 (官方格式): 06 c0|c1 <状态> 00 <校验>
       状态 0x01=成功, 0x00=失败; 校验和 = (报告ID4 + 前4字节和) & 0xFF.
    2) 事件包 (5 字节): 03 <设备编号> <事件码> <参数1> <参数2>
       (某些链路会在前面多一两个字节, 按偏移 2/3/4 依次探测.)
    """
    if len(data) < 5:
        return None

    # 写入确认响应
    if data[0] == 0x06 and data[1] in (0xC0, 0xC1, 0xC2, 0xC3):
        if data[2] in (0x00, 0x01) and (4 + sum(data[0:4])) & 0xFF == data[4]:
            return DeviceEvent(
                kind="ack",
                raw=bytes(data),
                ack_command=None,
                ack_ok=(data[2] == 0x01),
            )

    for offset in (2, 3, 4):
        if len(data) < offset + 3:
            continue
        code = data[offset]
        if code not in _EVENT_CODES:
            continue
        p1, p2 = data[offset + 1], data[offset + 2]

        if code in (EVENT_BATTERY, EVENT_BATTERY_ALT):
            if not (1 <= p1 <= 3 and 0 <= p2 <= 100):
                continue
            return DeviceEvent(
                kind="battery",
                raw=bytes(data),
                battery_status=p1,
                battery_level=p2,
            )
        if code == EVENT_ACK:
            if p1 not in (0, 1) or p2 not in _COMMAND_IDS:
                continue
            return DeviceEvent(
                kind="ack",
                raw=bytes(data),
                ack_command=p2,
                ack_ok=(p1 == 0),
            )
        if code == EVENT_DPI_CYCLE:
            if not (1 <= p1 <= 8):
                continue
            return DeviceEvent(kind="dpi_cycle", raw=bytes(data), stage=p1)
        return DeviceEvent(kind="other", raw=bytes(data))
    return None
