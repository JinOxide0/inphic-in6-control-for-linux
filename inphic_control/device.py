"""hidraw 设备发现与读写 (IN6 8K 接收器 / 有线模式)."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from .protocol import REPORT_ID, frame_packet

VENDOR_ID = 0x1D57          # Inphic / Xenta
KNOWN_PRODUCTS = {
    0xFA65: "IN6 8K 接收器",
    0xFA55: "IN6 (有线)",
    0xFA60: "IN6 接收器",
}

SYSFS_HIDRAW = Path("/sys/class/hidraw")
VENDOR_USAGE_PAGE = b"\x06\x00\xff"      # Usage Page (Vendor-Defined 0xFF00)


@dataclass
class DeviceInfo:
    hidraw: str                     # /dev/hidrawN
    vid: int
    pid: int
    name: str                       # HID_NAME
    product: str                    # USB 产品字符串
    interface: str                  # 例如 1-2:1.2
    accessible: bool

    @property
    def label(self) -> str:
        return KNOWN_PRODUCTS.get(self.pid, self.product or self.name or "Inphic 设备")

    @property
    def is_wireless(self) -> bool:
        return "receiver" in (self.product or "").lower() or self.pid in (0xFA65, 0xFA60)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(errors="replace").strip()
    except OSError:
        return ""


def _parse_uevent(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        for line in path.read_text(errors="replace").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                out[k] = v
    except OSError:
        pass
    return out


def _has_vendor_collection(descriptor_path: Path) -> bool:
    try:
        data = descriptor_path.read_bytes()
    except OSError:
        return False
    return VENDOR_USAGE_PAGE in data and b"\x85\x04" in data


def discover() -> list[DeviceInfo]:
    """扫描所有 hidraw, 返回可作为命令通道的 Inphic 设备."""
    found: list[DeviceInfo] = []
    if not SYSFS_HIDRAW.is_dir():
        return found
    for entry in sorted(SYSFS_HIDRAW.iterdir()):
        uevent = _parse_uevent(entry / "device" / "uevent")
        hid_id = uevent.get("HID_ID", "")
        parts = hid_id.split(":")
        if len(parts) != 3:
            continue
        try:
            vid, pid = int(parts[1], 16), int(parts[2], 16)
        except ValueError:
            continue
        if vid != VENDOR_ID:
            continue
        if not _has_vendor_collection(entry / "device" / "report_descriptor"):
            continue

        real = os.path.realpath(entry / "device")
        interface = os.path.basename(os.path.dirname(real))
        product = _read_text(Path(real).parent / "product")
        dev = f"/dev/{entry.name}"
        found.append(
            DeviceInfo(
                hidraw=dev,
                vid=vid,
                pid=pid,
                name=uevent.get("HID_NAME", ""),
                product=product,
                interface=interface,
                accessible=os.access(dev, os.R_OK | os.W_OK),
            )
        )
    return found


class InphicDevice:
    """命令通道 (Report ID 4) 的打开/写入/读取."""

    def __init__(self, info: DeviceInfo):
        self.info = info
        self._fd: int | None = None

    @property
    def is_open(self) -> bool:
        return self._fd is not None

    def open(self) -> None:
        if self._fd is not None:
            return
        self._fd = os.open(self.info.hidraw, os.O_RDWR | os.O_NONBLOCK)

    def close(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            finally:
                self._fd = None

    def send(self, payload: bytes) -> None:
        """发送一条配置命令. payload 为协议载荷 (官方帧格式)."""
        self.write_raw(frame_packet(payload))

    def write_raw(self, data: bytes) -> None:
        """按原样写入 (用于宏页等自带报告 ID 的数据)."""
        if self._fd is None:
            raise RuntimeError("设备未打开")
        deadline = time.monotonic() + 1.0
        while True:
            try:
                os.write(self._fd, data)
                return
            except BlockingIOError:
                if time.monotonic() > deadline:
                    raise TimeoutError("写入 hidraw 超时")
                time.sleep(0.005)

    def read(self, size: int = 64) -> bytes | None:
        """非阻塞读取一条输入报告; 无数据返回 None."""
        if self._fd is None:
            raise RuntimeError("设备未打开")
        try:
            data = os.read(self._fd, size)
        except BlockingIOError:
            return None
        except OSError:
            return None
        if not data:
            return None
        # hidraw 读取带 Report ID
        if data[0] == REPORT_ID:
            return data[1:]
        return data

    def fileno(self) -> int:
        if self._fd is None:
            raise RuntimeError("设备未打开")
        return self._fd
