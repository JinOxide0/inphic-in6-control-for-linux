"""命令行诊断工具: python -m inphic_control --probe."""
from __future__ import annotations

import argparse
import select
import sys
import time

from . import protocol as P
from .config import Config
from .device import InphicDevice, discover


def _print_devices() -> list:
    infos = discover()
    if not infos:
        print("未发现可配置的 Inphic 设备 (1d57:* 且带厂商接口)")
    for info in infos:
        ok = "可访问" if info.accessible else "无权限 (需要 udev 规则)"
        print(
            f"* {info.hidraw}  {info.vid:04x}:{info.pid:04x}  {info.label}\n"
            f"    接口 {info.interface} · HID 名 {info.name} · {ok}"
        )
    return infos


def run_probe(seconds: float, apply_config: bool) -> int:
    infos = _print_devices()
    if not infos:
        return 2
    info = infos[0]
    if not info.accessible:
        print(
            "\n没有访问权限。临时授权:\n"
            f"  sudo setfacl -m u:$USER:rw {info.hidraw}\n"
            "或安装 RPM 后重新插拔接收器 (包含 udev 规则)。"
        )
        return 3

    device = InphicDevice(info)
    device.open()
    try:
        if apply_config:
            cfg = Config.load()
            packets = [
                P.build_dpi_packet(
                    cfg.dpi_values,
                    cfg.active_stage,
                    active_mask=cfg.active_mask(),
                    lift_off_distance=cfg.lift_off,
                    ripple=cfg.ripple,
                    angle_snap=cfg.angle_snap,
                    motion_sync=cfg.motion_sync,
                    colors=[tuple(c) for c in cfg.dpi_colors],
                ),
                P.build_polling_packet(cfg.polling_rate),
                P.build_lighting_packet(
                    light_mode=cfg.light_mode,
                    brightness=cfg.brightness,
                    speed=cfg.speed,
                    red=cfg.color[0],
                    green=cfg.color[1],
                    blue=cfg.color[2],
                    sleep_minutes=cfg.sleep_minutes,
                    deep_sleep_minutes=cfg.deep_sleep_minutes,
                    debounce_ms=cfg.debounce_ms,
                ),
                P.build_buttons_packet([b.to_action() for b in cfg.buttons]),
            ]
            for packet in packets:
                device.send(packet)
                print(f"已发送 {len(packet):>2} 字节: {packet[:12].hex(' ')} ...")
                time.sleep(1.5)

        print(f"\n监听设备事件 {seconds:.0f} 秒 (Ctrl+C 退出)...")
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            ready, _, _ = select.select([device.fileno()], [], [], 0.5)
            if not ready:
                continue
            data = device.read()
            if data is None:
                continue
            event = P.parse_event(data)
            stamp = time.strftime("%H:%M:%S")
            if event is None:
                print(f"[{stamp}] 原始: {data[:16].hex(' ')}")
            elif event.kind == "battery":
                print(
                    f"[{stamp}] 电量: {event.battery_level}% "
                    f"(状态 {event.battery_status})"
                )
            elif event.kind == "ack":
                print(f"[{stamp}] ACK: {'成功' if event.ack_ok else '失败'}")
            elif event.kind == "dpi_cycle":
                print(f"[{stamp}] DPI 切换到档位 {event.stage}")
            else:
                print(f"[{stamp}] 其他事件: {event.raw[:16].hex(' ')}")
    finally:
        device.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inphic-control --probe")
    parser.add_argument("--seconds", type=float, default=8.0, help="监听时长")
    parser.add_argument(
        "--apply", action="store_true", help="先写入一次本地配置再监听"
    )
    args = parser.parse_args(argv)
    return run_probe(args.seconds, args.apply)


if __name__ == "__main__":
    sys.exit(main())
