"""协议编码单元测试: python3 -m unittest discover tests"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from inphic_control import protocol as P
from inphic_control.config import ButtonBinding, Config


class DpiTests(unittest.TestCase):
    def test_encode_official_values(self):
        self.assertEqual(P.encode_dpi(800), (15, 0))
        self.assertEqual(P.encode_dpi(26000), (7, 2))
        self.assertEqual(P.encode_dpi(0), (0, 0))

    def test_packet_header_and_checksum(self):
        packet = P.build_dpi_packet([800, 1600, 3200, 6500, 13000, 26000], 1)
        self.assertEqual(len(packet), 56)
        self.assertEqual(packet[0], 0x04)
        self.assertEqual(packet[1], 56)
        self.assertEqual(packet[2], 1)
        self.assertEqual(packet[3], 0)   # LOD 1mm
        self.assertEqual(packet[4], 1)   # ripple
        self.assertEqual(packet[5], 0x3F)
        checksum = sum(packet[3:50]) & 0xFFFF
        self.assertEqual(packet[50] << 8 | packet[51], checksum)

    def test_active_mask(self):
        cfg = Config()
        cfg.dpi_enabled = [True, True, False, False, False, False, False, False]
        self.assertEqual(cfg.active_mask(), 0b11)


class PollingTests(unittest.TestCase):
    def test_rates(self):
        expected = {125: 32, 250: 16, 500: 8, 1000: 4, 2000: 2, 4000: 1, 8000: 64}
        for rate, raw in expected.items():
            packet = P.build_polling_packet(rate)
            self.assertEqual(len(packet), 9)
            self.assertEqual(packet[:5], bytes([6, 9, 1, raw, (~raw) & 0xFF]))

    def test_invalid_rate(self):
        with self.assertRaises(ValueError):
            P.build_polling_packet(123)


class LightingTests(unittest.TestCase):
    def test_checksums(self):
        packet = P.build_lighting_packet(
            light_mode="static_dpi",
            brightness=2,
            speed=3,
            red=0, green=0, blue=255,
            sleep_minutes=0.5,
            deep_sleep_minutes=10,
            debounce_ms=8,
        )
        self.assertEqual(len(packet), 15)
        self.assertEqual(packet[0], 5)
        self.assertEqual(packet[1], 15)
        self.assertEqual(packet[3], 0x50)               # static DPI
        self.assertEqual(packet[9], 1)                  # 0.5 * 2
        self.assertEqual(packet[10], 8)                 # debounce
        self.assertEqual(packet[11] << 8 | packet[12], sum(packet[3:11]) & 0xFFFF)
        self.assertEqual(packet[4] & 0x0F, (9 - 3) & 0x0F)   # 呼吸速度取反
        self.assertEqual(packet[5] & 0x0F, 2)                # 亮度
        self.assertEqual(packet[4] >> 4, (10 >> 4) & 0x0F)
        self.assertEqual(packet[5] >> 4, 10 & 0x0F)


class ButtonsTests(unittest.TestCase):
    def test_defaults(self):
        cfg = Config()
        packet = P.build_buttons_packet([b.to_action() for b in cfg.buttons])
        self.assertEqual(len(packet), 59)
        self.assertEqual(packet[0], 8)
        self.assertEqual(packet[1], 59)
        self.assertEqual(packet[2], 1)
        self.assertEqual(packet[3:6], bytes([2, 0, 0]))     # 左键
        self.assertEqual(packet[21:24], bytes([5, 0, 0]))   # 后退 (slot 6)
        self.assertEqual(packet[24:27], bytes([6, 0, 0]))   # 前进 (slot 7)
        self.assertEqual(packet[57] << 8 | packet[58], sum(packet[3:57]) & 0xFFFF)

    def test_shortcut(self):
        cfg = Config()
        cfg.buttons[0] = ButtonBinding(kind="shortcut", mods=1, usage=6)  # Ctrl+C
        packet = P.build_buttons_packet([b.to_action() for b in cfg.buttons])
        self.assertEqual(packet[3:6], bytes([17, 1, 6]))


class EventTests(unittest.TestCase):
    def test_battery(self):
        raw = bytes([0x03, 0x41, 0x40, 0x03, 0x45]) + bytes(58)
        event = P.parse_event(raw)
        self.assertIsNotNone(event)
        self.assertEqual(event.kind, "battery")
        self.assertEqual(event.battery_status, 3)
        self.assertEqual(event.battery_level, 69)

    def test_ack_official(self):
        # 官方写入确认: 06 c0 01 00 cb (报告 ID 4 已剥离)
        raw = bytes([0x06, 0xC0, 0x01, 0x00, 0xCB])
        event = P.parse_event(raw)
        self.assertEqual(event.kind, "ack")
        self.assertTrue(event.ack_ok)

    def test_ack_fail(self):
        raw = bytes([0x06, 0xC0, 0x00, 0x00, 0xCA])
        event = P.parse_event(raw)
        self.assertEqual(event.kind, "ack")
        self.assertFalse(event.ack_ok)

    def test_ack_bad_checksum_ignored(self):
        raw = bytes([0x06, 0xC0, 0x01, 0x00, 0x00])
        self.assertIsNone(P.parse_event(raw))

    def test_ack_legacy(self):
        raw = bytes([0x03, 0x41, 0x50, 0x00, 0x04]) + bytes(58)
        event = P.parse_event(raw)
        self.assertEqual(event.kind, "ack")
        self.assertTrue(event.ack_ok)
        self.assertEqual(event.ack_command, 4)

    def test_garbage(self):
        self.assertIsNone(P.parse_event(bytes(63)))

    def test_pad(self):
        self.assertEqual(len(P.pad_payload(b"\x01\x02")), 63)

    def test_frame_packet(self):
        payload = bytes([5, 15, 1, 0x50, 1, 0xA8, 0, 255, 0, 1, 8, 0, 2, 0, 0])
        frame = P.frame_packet(payload)
        self.assertEqual(frame[0], 4)
        self.assertEqual(frame[1], len(payload) + 5)
        self.assertEqual(frame[2], 0)
        self.assertEqual(frame[3:3 + len(payload)], payload)
        cs = sum(frame[0:len(payload) + 3]) & 0xFFFF
        self.assertEqual(frame[len(payload) + 3] << 8 | frame[len(payload) + 4], cs)


class MacroTests(unittest.TestCase):
    def test_payload(self):
        actions = [
            P.MacroAction(kind="key", key=4, down=True, delay=20),
            P.MacroAction(kind="key", key=4, down=False, delay=20),
        ]
        payload = P.build_macro_payload(4, trigger=0, loops=3, actions=actions)
        self.assertEqual(len(payload), 111)
        self.assertEqual(payload[:3], bytes([9, 111, 4]))
        self.assertEqual(payload[3], 0)          # trigger
        self.assertEqual(payload[7], 3)          # loops
        self.assertEqual(payload[8], 2)          # count
        self.assertEqual(payload[9], 0x15)       # down, 20ms
        self.assertEqual(payload[10], 4)         # key A
        self.assertEqual(payload[11], 0x94)      # up, 20ms
        self.assertEqual(payload[12], 4)
        self.assertEqual(payload[109] << 8 | payload[110], sum(payload[3:109]) & 0xFFFF)

    def test_pages(self):
        actions = [P.MacroAction(kind="key", key=4, down=True, delay=20)]
        payload = P.build_macro_payload(1, 0, 2, actions)
        pages = P.build_macro_pages(payload)
        self.assertEqual(len(pages), 2)
        self.assertEqual(len(pages[0]), 64)
        self.assertEqual(len(pages[1]), 64)
        self.assertEqual(pages[0][:3], bytes([4, 0x40, 0]))
        self.assertEqual(pages[1][:3], bytes([4, 0x39, 1]))
        self.assertEqual(pages[0][62] << 8 | pages[0][63], sum(pages[0][0:62]) & 0xFFFF)
        self.assertEqual(pages[1][55] << 8 | pages[1][56], sum(pages[1][0:55]) & 0xFFFF)
        # 页1 数据 = 载荷[59:111]
        self.assertEqual(pages[1][3:55], payload[59:111])

    def test_move_encoding(self):
        actions = [P.MacroAction(kind="move", x=-100, y=250, delay=30)]
        payload = P.build_macro_payload(2, 1, 1, actions)
        self.assertEqual(payload[9], 30)
        self.assertEqual(payload[10], 0xF6)
        self.assertEqual(payload[11], 0xFF)      # x 高字节 (-100)
        self.assertEqual(payload[12], 0x9C)
        self.assertEqual(payload[13], 0x00)      # y 高字节 (250)
        self.assertEqual(payload[14], 0xFA)
        self.assertEqual(payload[8], 3)          # move 计数 = 3



if __name__ == "__main__":
    unittest.main()
