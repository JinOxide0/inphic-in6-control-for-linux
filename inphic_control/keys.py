"""键盘按键 -> USB HID usage id 映射 (用于按键重映射 / 宏)."""
from __future__ import annotations

_KEYVAL_TABLE: dict[int, int] | None = None


def _build_table() -> dict[int, int]:
    from gi.repository import Gdk  # 延迟导入, 方便无界面测试

    table: dict[int, int] = {}

    def add(name: str, usage: int, *aliases: str) -> None:
        for n in (name, *aliases):
            keyval = Gdk.keyval_from_name(n)
            if keyval:
                table[keyval] = usage

    for i, ch in enumerate("abcdefghijklmnopqrstuvwxyz"):
        add(ch, 4 + i)
    for i, ch in enumerate("123456789"):
        add(ch, 30 + i)
    add("0", 39)

    add("Return", 40, "KP_Enter")
    add("Escape", 41)
    add("BackSpace", 42)
    add("Tab", 43)
    add("space", 44)
    add("minus", 45)
    add("equal", 46)
    add("bracketleft", 47)
    add("bracketright", 48)
    add("backslash", 49)
    add("semicolon", 51)
    add("apostrophe", 52)
    add("grave", 53)
    add("comma", 54)
    add("period", 55)
    add("slash", 56)
    add("Caps_Lock", 57)

    for i in range(1, 13):
        add(f"F{i}", 57 + i)
    add("Print", 70)
    add("Scroll_Lock", 71)
    add("Pause", 72)
    add("Insert", 73)
    add("Home", 74)
    add("Page_Up", 75, "Prior")
    add("Delete", 76)
    add("End", 77)
    add("Page_Down", 78, "Next")
    add("Right", 79)
    add("Left", 80)
    add("Down", 81)
    add("Up", 82)
    add("Num_Lock", 83)
    add("KP_Divide", 84)
    add("KP_Multiply", 85)
    add("KP_Subtract", 86)
    add("KP_Add", 87)
    for i in range(1, 10):
        add(f"KP_{i}", 88 + i)
    add("KP_0", 98)
    add("KP_Decimal", 99, "KP_Delete")
    add("Menu", 101)
    add("KP_Equal", 103)
    for i in range(13, 25):
        add(f"F{i}", 91 + i)  # F13=104 ... F24=115

    add("Control_L", 224)
    add("Shift_L", 225)
    add("Alt_L", 226)
    add("Super_L", 227, "Meta_L")
    add("Control_R", 228)
    add("Shift_R", 229)
    add("Alt_R", 230)
    add("Super_R", 231, "Meta_R")
    return table


def keyval_to_usage(keyval: int) -> int | None:
    global _KEYVAL_TABLE
    if _KEYVAL_TABLE is None:
        _KEYVAL_TABLE = _build_table()
    return _KEYVAL_TABLE.get(keyval)


def modifier_mask(state) -> int:
    """Gdk.ModifierType -> 官方掩码 (Ctrl=1 Shift=2 Alt=4 Win=8)."""
    from gi.repository import Gdk

    mask = 0
    if state & Gdk.ModifierType.CONTROL_MASK:
        mask |= 1
    if state & Gdk.ModifierType.SHIFT_MASK:
        mask |= 2
    if state & Gdk.ModifierType.ALT_MASK:
        mask |= 4
    if state & (Gdk.ModifierType.SUPER_MASK | Gdk.ModifierType.META_MASK):
        mask |= 8
    return mask


def describe_key(usage: int) -> str:
    """给 UI 显示的按键名称."""
    from gi.repository import Gdk

    global _KEYVAL_TABLE
    if _KEYVAL_TABLE is None:
        _KEYVAL_TABLE = _build_table()
    for keyval, value in _KEYVAL_TABLE.items():
        if value == usage:
            name = Gdk.keyval_name(keyval) or "?"
            return name
    return f"0x{usage:02X}"


def describe_shortcut(mods: int, usage: int) -> str:
    parts = []
    if mods & 1:
        parts.append("Ctrl")
    if mods & 2:
        parts.append("Shift")
    if mods & 4:
        parts.append("Alt")
    if mods & 8:
        parts.append("Super")
    parts.append(describe_key(usage))
    return "+".join(parts)
