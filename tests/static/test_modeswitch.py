#!/usr/bin/env python3
"""Validate usb_modeswitch/1111_1111 byte by byte.

Usage: python3 tests/static/test_modeswitch.py
Needs only the Python standard library; touches no hardware.

Each MessageContent must be a 31-byte USB Mass Storage Command Block
Wrapper (CBW) as defined by the USB Mass Storage Class Bulk-Only Transport
specification, carrying the vendor command FD 00 ... 00 <subcommand>.
"""

from pathlib import Path
import re
import struct
import unittest

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "usb_modeswitch" / "1111_1111"
RULES = REPO / "aic.rules"

CBW_SIGNATURE = b"USBC"
CBW_LENGTH = 31
CDB_LENGTH = 16


def parse_config(text):
    """Return the KEY=value pairs of a usb_modeswitch config, ignoring comments."""
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"')
    return values


def parse_cbw(hex_string):
    """Split a CBW into its fields; raises ValueError on malformed input."""
    data = bytes.fromhex(hex_string)
    if len(data) != CBW_LENGTH:
        raise ValueError(f"CBW is {len(data)} bytes, expected {CBW_LENGTH}")
    signature, tag, transfer_length, flags, lun, cb_length = struct.unpack("<4sIIBBB", data[:15])
    return {
        "signature": signature,
        "tag": tag,
        "transfer_length": transfer_length,
        "flags": flags,
        "lun": lun,
        "cb_length": cb_length,
        "cdb": data[15:],
    }


class ModeSwitchConfigTests(unittest.TestCase):
    def setUp(self):
        self.values = parse_config(CONFIG.read_text(encoding="utf-8"))
        self.messages = [
            (key, value) for key, value in sorted(self.values.items()) if re.fullmatch(r"MessageContent\d*", key)
        ]

    def test_ids_match_file_name_and_target(self):
        # The file is installed as /etc/usb_modeswitch.d/1111:1111, so the
        # default IDs must be the ones in its name.
        vendor, product = CONFIG.name.split("_")
        self.assertEqual(int(self.values["DefaultVendor"], 16), int(vendor, 16))
        self.assertEqual(int(self.values["DefaultProduct"], 16), int(product, 16))
        # After the switch the loader-mode device is a69c:8d80; it becomes
        # a69c:8d81 only after aic_load_fw uploads the firmware.
        self.assertEqual(int(self.values["TargetVendor"], 16), 0xA69C)
        self.assertEqual(int(self.values["TargetProduct"], 16), 0x8D80)

    def test_has_messages(self):
        self.assertGreaterEqual(len(self.messages), 1)

    def test_every_message_is_a_valid_cbw(self):
        for key, hex_string in self.messages:
            with self.subTest(message=key):
                self.assertRegex(hex_string, r"^[0-9a-fA-F]+$")
                cbw = parse_cbw(hex_string)
                self.assertEqual(cbw["signature"], CBW_SIGNATURE)
                self.assertEqual(cbw["cb_length"], CDB_LENGTH)
                self.assertEqual(len(cbw["cdb"]), CDB_LENGTH)
                self.assertEqual(cbw["lun"], 0)
                # No data phase is declared: transfer length 0, direction OUT.
                self.assertEqual(cbw["transfer_length"], 0)
                self.assertEqual(cbw["flags"], 0x00)

    def test_cdbs_are_the_vendor_command(self):
        # Vendor opcode 0xFD, zero padding, sub-command in the last byte.
        subcommands = []
        for key, hex_string in self.messages:
            with self.subTest(message=key):
                cdb = parse_cbw(hex_string)["cdb"]
                self.assertEqual(cdb[0], 0xFD)
                self.assertEqual(cdb[1:15], bytes(14))
                subcommands.append(cdb[15])
        # F3 (query) then F2 (switch), as in upstream commit 3050506.
        self.assertEqual(subcommands, [0xF3, 0xF2])

    def test_parser_rejects_malformed_cbw(self):
        with self.assertRaises(ValueError):
            parse_cbw("5553424387654321")  # truncated
        with self.assertRaises(ValueError):
            parse_cbw("zz" * CBW_LENGTH)  # not hex

    def test_rule_points_at_installed_config(self):
        rules = RULES.read_text(encoding="utf-8")
        self.assertIn("/etc/usb_modeswitch.d/1111:1111", rules)
        self.assertIn('ATTR{idVendor}=="1111"', rules)
        self.assertIn('ATTR{idProduct}=="1111"', rules)


if __name__ == "__main__":
    unittest.main(verbosity=2)
