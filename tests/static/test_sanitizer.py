#!/usr/bin/env python3
"""Check the output filter shared by the diagnostic and smoke-test scripts.

Usage: python3 tests/static/test_sanitizer.py

diagnose_bt.sh, diagnostic_build.sh and scripts/hw-smoke.sh each carry a
copy of sanitize_output() so that each can be run on its own. This test
keeps the copies identical and checks what each copy masks.
"""

from pathlib import Path
import re
import subprocess
import unittest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = [REPO / "diagnose_bt.sh", REPO / "diagnostic_build.sh", REPO / "scripts" / "hw-smoke.sh"]


def extract(script):
    match = re.search(r"(?ms)^sanitize_output\(\) \{.*?^\}", script.read_text(encoding="utf-8"))
    if not match:
        raise AssertionError(f"sanitize_output not found in {script}")
    return match.group()


def sanitize(text, user="alice", host="workstation", raw=False, source=SCRIPTS[0]):
    env = {"PATH": "/usr/bin:/bin", "SUDO_USER": user, "AIC_DIAG_RAW": "1" if raw else "0"}
    # Make hostname return a known value.
    script = f'hostname() {{ echo {host}; }}\n{extract(source)}\nsanitize_output'
    return subprocess.run(["bash", "-c", script], input=text, text=True, capture_output=True, env=env, check=True).stdout


class SanitizerTests(unittest.TestCase):
    def test_copies_are_identical(self):
        # Compare with whitespace removed: shfmt formats scripts/hw-smoke.sh
        # (for example "2> /dev/null"), while the other two keep upstream's
        # style. Any change to the commands themselves still fails here.
        def normalized(script):
            return re.sub(r"\s+", "", extract(script))

        first = normalized(SCRIPTS[0])
        for script in SCRIPTS[1:]:
            with self.subTest(script=script.name):
                self.assertEqual(normalized(script), first)

    def assert_sanitized(self, cases):
        # Run every case through every copy, so a copy that diverges in
        # behaviour fails here even if the text comparison above misses it.
        for script in SCRIPTS:
            for raw, expected in cases.items():
                with self.subTest(script=script.name, raw=raw):
                    self.assertEqual(sanitize(raw + "\n", source=script).strip(), expected)

    def test_masks_identifiers(self):
        cases = {
            "BD Address: 02:00:00:00:00:01 ACL MTU": "BD Address: <MAC> ACL MTU",
            "link/ether 02-00-00-aa-bb-cc": "link/ether <MAC>",
            "iface wlx0123456789ab up": "iface wlx<MAC> up",
            "usb 3-1: SerialNumber: ABCDEF012345": "usb 3-1: SerialNumber: <SERIAL>",
            "inet 192.0.2.10/24": "inet <IP>/24",
            "/home/alice/src/aic8800": "/home/<user>/src/aic8800",
            "owner alice on workstation": "owner <user> on <host>",
        }
        self.assert_sanitized(cases)

    def test_masks_space_separated_driver_addresses(self):
        # aic8800_fdrv prints these with "%x %x %x %x %x %x" (rwnx_main.c),
        # so bytes below 0x10 have a single digit. The P2P line is logged at
        # the default level on every load; the P2P address differs from the
        # adapter MAC at most in the first byte.
        cases = {
            "AICWFDBG(LOGERROR)\tp2p dev addr=2 11 22 33 44 55": "AICWFDBG(LOGERROR)\tp2p dev addr=<MAC>",
            "AICWFDBG(LOGERROR)\tp2p dev addr=2 0 4c a 3 ff": "AICWFDBG(LOGERROR)\tp2p dev addr=<MAC>",
            "AICWFDBG(LOGERROR)\tp2p dev addr=02 11 22 33 44 55": "AICWFDBG(LOGERROR)\tp2p dev addr=<MAC>",
            "interface add:2 11 22 33 44 55": "interface add:<MAC>",
            "rwnx_cfg80211_add_iface mac_addr:2 11 22 33 44 55 addr:2 11 22 33 44 56 ":
                "rwnx_cfg80211_add_iface mac_addr:<MAC> addr:<MAC>",
        }
        self.assert_sanitized(cases)

    def test_keeps_versions_and_ids(self):
        for line in (
            "Linux 6.12.113+deb13-amd64",
            "gcc (Debian 14.2.0-19) 14.2.0",
            "firmware 1.2.3.4.5",
            "ID a69c:8d81 bcdDevice=0100",
            "usb 3-1.1: New USB device found",
            "sr 2:0:0:0: [sr0] tag#7 CDB: Read(10) 28 00 00 00 00 00 00 00 01 00",
            "aicbt_patch_table_load bt uart_baud[4]:1000000",
            "AICWFDBG(LOGERROR)\tRead FW mem: 120000",
        ):
            for script in SCRIPTS:
                with self.subTest(script=script.name, line=line):
                    self.assertEqual(sanitize(line + "\n", source=script).strip(), line)

    def test_raw_mode_disables_masking(self):
        line = "BD Address: 02:00:00:00:00:01"
        self.assertEqual(sanitize(line + "\n", raw=True).strip(), line)


if __name__ == "__main__":
    unittest.main(verbosity=2)
