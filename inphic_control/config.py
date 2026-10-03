"""本地配置持久化 (~/.config/inphic-control/config.json)."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import protocol as P

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "inphic-control"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class ButtonBinding:
    """一个按键槽位的绑定."""

    kind: str = "preset"          # preset | shortcut | macro
    preset: str = "off"           # kind=preset
    mods: int = 0                 # kind=shortcut
    usage: int = 0                # kind=shortcut
    macro_id: int = 0             # kind=macro

    def to_action(self) -> tuple[int, int, int]:
        if self.kind == "shortcut":
            return P.shortcut_action(self.mods, self.usage)
        if self.kind == "macro":
            return P.macro_action(self.macro_id)
        return P.BUTTON_ACTIONS.get(self.preset, P.BUTTON_ACTIONS["off"])


@dataclass
class MacroDef:
    """一个宏定义 (按槽位存储, 宏编号 = 槽位 1-5)."""

    trigger: int = 0              # 0=循环N次 1=任意键停止 2=按住播放 3=宏键停止
    loops: int = 1
    color: list[int] = field(default_factory=lambda: [0, 0, 0])
    actions: list[dict] = field(default_factory=list)


@dataclass
class Config:
    # DPI
    dpi_values: list[int] = field(
        default_factory=lambda: [800, 1600, 3200, 6500, 13000, 26000, 0, 0]
    )
    dpi_enabled: list[bool] = field(
        default_factory=lambda: [True, True, True, True, True, True, False, False]
    )
    active_stage: int = 1
    dpi_colors: list[list[int]] = field(
        default_factory=lambda: [list(c) for c in P.DEFAULT_DPI_COLORS]
    )

    # 性能
    polling_rate: int = 1000
    ripple: bool = True
    angle_snap: bool = False
    motion_sync: bool = True
    lift_off: int = 0                     # 0 = 1mm, 1 = 2mm
    sleep_minutes: float = 0.5            # 0.5 - 30
    deep_sleep_minutes: int = 10          # 1 - 60
    debounce_ms: int = 8                  # 4 - 50, 偶数

    # 灯光
    light_mode: str = "static_dpi"
    brightness: int = 2                   # 1-8
    speed: int = 3                        # 1-8 (呼吸类模式)
    color: list[int] = field(default_factory=lambda: [0, 0, 255])

    # 按键 (18 个槽位, 顺序同 protocol.BUTTON_SLOTS)
    buttons: list[ButtonBinding] = field(
        default_factory=lambda: [
            ButtonBinding(preset=preset) for _, preset in P.BUTTON_SLOTS
        ]
    )

    # 宏 (键 = 槽位字符串 "1".."5")
    macros: dict[str, MacroDef] = field(default_factory=dict)

    # 界面语言: auto(跟随系统) / zh / en
    language: str = "auto"

    # ------------------------------------------------------------ 编码
    def active_mask(self) -> int:
        mask = 0
        for i, on in enumerate(self.dpi_enabled[:8]):
            if on:
                mask |= 1 << i
        return mask

    def to_dict(self) -> dict:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        cfg = cls()
        for key, value in (data or {}).items():
            if key == "buttons" and isinstance(value, list):
                binds = []
                for i, item in enumerate(value[: len(P.BUTTON_SLOTS)]):
                    if isinstance(item, dict):
                        binds.append(ButtonBinding(**{
                            k: v for k, v in item.items()
                            if k in ButtonBinding.__dataclass_fields__
                        }))
                    else:
                        binds.append(ButtonBinding(preset=P.BUTTON_SLOTS[i][1]))
                binds += [ButtonBinding(preset=p) for _, p in P.BUTTON_SLOTS[len(binds):]]
                cfg.buttons = binds
            elif key == "macros" and isinstance(value, dict):
                for slot, item in value.items():
                    if isinstance(item, dict):
                        cfg.macros[str(slot)] = MacroDef(**{
                            k: v for k, v in item.items()
                            if k in MacroDef.__dataclass_fields__
                        })
            elif hasattr(cfg, key):
                setattr(cfg, key, value)
        return cfg

    # ------------------------------------------------------------ 磁盘
    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(CONFIG_DIR), prefix=".config-", suffix=".json")
        try:
            with os.fdopen(fd, "w") as fh:
                json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)
            os.replace(tmp, CONFIG_FILE)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    @classmethod
    def load(cls) -> "Config":
        try:
            with open(CONFIG_FILE) as fh:
                return cls.from_dict(json.load(fh))
        except (OSError, ValueError):
            return cls()
