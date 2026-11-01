#!/usr/bin/env python3
"""Static checks for aic.rules.

Usage: python3 tests/static/test_udev_rules.py
Needs only the Python standard library. Syntax is checked separately with
"udevadm verify" (see the Makefile); this file checks intent.
"""

from pathlib import Path
import re
import unittest

RULES = Path(__file__).resolve().parents[2] / "aic.rules"


def rule_lines():
    lines = []
    for number, line in enumerate(RULES.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            lines.append((number, stripped))
    return lines


def keys(line):
    """Map each match/assignment key (e.g. ACTION, ATTR{idVendor}) to its operator and value."""
    found = {}
    for key, op, value in re.findall(r'([A-Z]+(?:\{[^}]+\})?)\s*(==|!=|\+=|=|:=)\s*"([^"]*)"', line):
        found.setdefault(key, []).append((op, value))
    return found


class UdevRuleTests(unittest.TestCase):
    def test_every_run_rule_is_limited_to_add_events(self):
        # Without ACTION=="add" a RUN fires again on change/remove events.
        for number, line in rule_lines():
            if "RUN+=" not in line:
                continue
            with self.subTest(line=number):
                self.assertIn(("==", "add"), keys(line).get("ACTION", []))

    def test_eject_rules_target_whole_disks_only(self):
        eject = [(n, l) for n, l in rule_lines() if "eject" in l]
        self.assertGreater(len(eject), 0)
        for number, line in eject:
            with self.subTest(line=number):
                k = keys(line)
                self.assertIn(("==", "block"), k.get("SUBSYSTEM", []))
                self.assertIn(("==", "disk"), k.get("ENV{DEVTYPE}", []))
                self.assertIn(("==", "a69c"), k.get("ATTRS{idVendor}", []))

    def test_1111_rule_is_narrow(self):
        rules = [(n, l) for n, l in rule_lines() if 'idVendor}=="1111"' in l]
        self.assertEqual(len(rules), 1)
        number, line = rules[0]
        k = keys(line)
        # Match the USB device itself, not its children (ATTR, not ATTRS).
        self.assertIn(("==", "usb_device"), k.get("ENV{DEVTYPE}", []))
        self.assertNotIn("ATTRS{idVendor}", k)
        # 1111:1111 is a placeholder ID; only the 88M80 product is switched.
        self.assertIn(("==", "88M80*"), k.get("ATTR{product}", []))
        # usb_modeswitch must act on the device that raised the event.
        self.assertIn("-b $attr{busnum} -g $attr{devnum}", line)

    def test_no_new_id_writes(self):
        # aic8800_fdrv matches its IDs natively; writing new_id raced the probe.
        for number, line in rule_lines():
            with self.subTest(line=number):
                self.assertNotIn("new_id", line)


if __name__ == "__main__":
    unittest.main(verbosity=2)
