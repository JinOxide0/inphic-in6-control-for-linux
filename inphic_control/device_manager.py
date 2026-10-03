"""设备连接管理与事件分发 (GObject 信号)."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, GObject

from . import protocol as P
from .device import InphicDevice, discover


class DeviceManager(GObject.Object):
    __gsignals__ = {
        # (connected, DeviceInfo | None)
        "changed": (GObject.SignalFlags.RUN_FIRST, None, (bool, object)),
        # (status, level)
        "battery": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        # (command_id, success)
        "ack": (GObject.SignalFlags.RUN_FIRST, None, (int, bool)),
        # (stage)
        "dpi-cycle": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        # (payload_len)
        "sent": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __init__(self):
        super().__init__()
        self.device: InphicDevice | None = None
        self.info = None
        self.battery_status: int | None = None
        self.battery_level: int | None = None
        self._watch_id: int | None = None
        self._poll_id: int | None = None
        self._last_error = ""
        self._last_payload: bytes | None = None
        self._retry_count = 0
        self._send_gen = 0

    # ------------------------------------------------------------ 生命周期
    def start(self) -> None:
        if self._poll_id is None:
            self._poll_id = GLib.timeout_add_seconds(2, self._poll)
            self._poll()

    def stop(self) -> None:
        if self._poll_id is not None:
            GLib.source_remove(self._poll_id)
            self._poll_id = None
        self._close()

    def _poll(self) -> bool:
        if self.device is None:
            candidates = discover()
            if candidates:
                self._open(candidates[0])
        return True

    def _open(self, info) -> None:
        dev = InphicDevice(info)
        try:
            dev.open()
        except OSError as exc:
            self._last_error = str(exc)
            return
        self.device = dev
        self.info = info
        self._watch_id = GLib.io_add_watch(
            dev.fileno(),
            GLib.IO_IN | GLib.IO_ERR | GLib.IO_HUP,
            self._on_io,
        )
        self.emit("changed", True, info)

    def _close(self) -> None:
        if self._watch_id is not None:
            GLib.source_remove(self._watch_id)
            self._watch_id = None
        if self.device is not None:
            self.device.close()
        self.device = None
        was = self.info is not None
        self.info = None
        self.battery_status = None
        self.battery_level = None
        if was:
            self.emit("changed", False, None)

    def _on_io(self, _fd, condition) -> bool:
        if condition & (GLib.IO_ERR | GLib.IO_HUP):
            self._watch_id = None  # 让 GLib 自行移除源, 避免双重移除警告
            self._close()
            return False
        assert self.device is not None
        for _ in range(16):
            data = self.device.read()
            if data is None:
                break
            event = P.parse_event(data)
            if event is None:
                continue
            if event.kind == "battery":
                self.battery_status = event.battery_status
                self.battery_level = event.battery_level
                self.emit("battery", event.battery_status, event.battery_level)
            elif event.kind == "ack":
                stage = event.raw[1] & 0x0F if len(event.raw) > 1 else 0
                if stage == 0:
                    # 接收器已收到 (校验和通过), 鼠标还没确认
                    self.emit("sent", 0)
                elif event.ack_ok:
                    self._retry_count = 0
                    self.emit("ack", 0, True)
                else:
                    # 鼠标侧拒绝/超时 (常见于休眠), 递进式自动重试:
                    # 1s / 6s / 21s, 用户回来动一下鼠标后即可自动生效
                    if self._retry_count < 3 and self._last_payload:
                        delays = (1000, 6000, 21000)
                        delay = delays[self._retry_count]
                        self._retry_count += 1
                        self._schedule_retry(delay)
                    else:
                        self._retry_count = 0
                        self.emit("ack", 0, False)
            elif event.kind == "dpi_cycle" and event.stage:
                self.emit("dpi-cycle", event.stage)
        return True

    def _schedule_retry(self, delay_ms: int) -> None:
        gen = self._send_gen
        payload = self._last_payload
        if payload is None:
            return

        def _retry() -> bool:
            if self.device is None or self._send_gen != gen:
                return False
            try:
                self.device.write_raw(payload)
            except (OSError, TimeoutError):
                self._close()
            return False

        GLib.timeout_add(delay_ms, _retry)

    # ------------------------------------------------------------ 发送
    @property
    def connected(self) -> bool:
        return self.device is not None

    def send(self, payload: bytes) -> bool:
        """发送配置命令 (官方帧格式)."""
        return self.send_raw(P.frame_packet(payload))

    def send_raw(self, data: bytes) -> bool:
        """按原样发送 (宏页等). 同样带递进式重试."""
        if self.device is None:
            return False
        try:
            self.device.write_raw(data)
        except (OSError, TimeoutError):
            self._close()
            return False
        self._last_payload = data
        self._send_gen += 1
        self._retry_count = 0
        self.emit("sent", len(data))
        return True

    def send_pages(self, pages: list[bytes], gap_ms: int = 1200) -> None:
        """按顺序原始发送多页 (宏分包), 每页间隔 1.2 秒."""
        pages = [p for p in pages if p]
        if not pages:
            return

        def step(items: list[bytes]) -> bool:
            if not items:
                return False
            if not self.send_raw(items[0]):
                return False
            if len(items) > 1:
                GLib.timeout_add(gap_ms, step, items[1:])
            return False

        step(pages)

    def send_many(self, payloads: list[bytes], gap_ms: int = 1500) -> None:
        """按顺序发送多条命令. 鼠标处理每条命令约需 0.7-1 秒,
        且休眠状态下更慢, 间隔太短会被丢弃, 所以默认间隔 1.5 秒."""
        payloads = [p for p in payloads if p]
        if not payloads:
            return

        def step(items: list[bytes]) -> bool:
            if not items:
                return False
            if not self.send(items[0]):
                return False
            if len(items) > 1:
                GLib.timeout_add(gap_ms, step, items[1:])
            return False

        step(payloads)
