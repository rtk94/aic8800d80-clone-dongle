#!/usr/bin/env python3
"""Safety tests for install.sh and uninstall.sh.

Usage: python3 tests/installer/test_install_safety.py
Runs as a normal user. Every path the scripts write is redirected into a
temporary directory with DESTDIR, and every command that could change the
system (dkms, package managers, modprobe, udevadm, initramfs tools, make)
is replaced by a stub on PATH that only records its arguments.
"""

from pathlib import Path
import os
import shlex
import shutil
import subprocess
import tempfile
import textwrap
import unittest

REPO = Path(__file__).resolve().parents[2]
INSTALLER = REPO / "install.sh"
UNINSTALLER = REPO / "uninstall.sh"

# Commands that must never reach the real system during a test.
STUBBED = [
    "apt-get", "apt-cache", "dnf", "yum", "pacman", "zypper",
    "dkms", "modprobe", "depmod", "udevadm",
    "update-initramfs", "dracut", "mkinitcpio",
    "make", "mokutil", "dpkg", "rpm",
]


SCRIPT_DIR_LINE = 'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'


def installer_library(script_dir="/nonexistent"):
    """install.sh without its final call to main, so its functions can be sourced.

    SCRIPT_DIR is readonly in install.sh, so its definition is replaced with
    the sandbox checkout instead of being overridden afterwards.
    """
    text = INSTALLER.read_text(encoding="utf-8")
    if text.count(SCRIPT_DIR_LINE) != 1:
        raise AssertionError("install.sh no longer defines SCRIPT_DIR as expected")
    text = text.replace(SCRIPT_DIR_LINE, f"SCRIPT_DIR={shlex.quote(script_dir)}\n")
    tail = '\n# Execute main function\nmain "$@"\n\nexit 0\n'
    if not text.endswith(tail):
        raise AssertionError("install.sh no longer ends with the expected main call")
    return text[: -len(tail)] + "\n"


class Sandbox:
    """A temporary root, a stub directory and helpers to run scripts inside them."""

    def __init__(self, test):
        self.temp = tempfile.TemporaryDirectory(prefix="aic-safety-test-")
        test.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.root = base / "root"  # DESTDIR
        self.src = base / "src"  # stands in for the repository checkout
        self.stubs = base / "stubs"
        self.calls = base / "calls.log"
        for d in (self.root, self.src, self.stubs):
            d.mkdir()
        self.calls.touch()
        # install.sh's main() creates the log directory; tests that call
        # single functions need it too, or every ">> $LOG_FILE" fails.
        (self.root / "var/log").mkdir(parents=True)
        for name in STUBBED:
            self.stub(name, "exit 0")

    def stub(self, name, body):
        """Create a stub command that logs its arguments, then runs body."""
        path = self.stubs / name
        path.write_text(
            "#!/bin/bash\n"
            f'printf "%s\\n" "{name} $*" >> {shlex.quote(str(self.calls))}\n'
            + textwrap.dedent(body)
            + "\n",
            encoding="utf-8",
        )
        path.chmod(0o755)

    def calls_to(self, name):
        return [l for l in self.calls.read_text().splitlines() if l.split(" ", 1)[0] == name]

    def env(self, **extra):
        env = {
            "PATH": f"{self.stubs}:{os.environ['PATH']}",
            "HOME": str(self.root),
            "DESTDIR": str(self.root),
            "LANG": "C",
        }
        env.update(extra)
        return env

    def write(self, relative, content="x", base=None):
        path = (base or self.root) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def run_function(self, body, **env):
        """Source install.sh's functions in the sandbox and run body."""
        script = (
            installer_library(str(self.src))
            + "trap cleanup_on_error ERR\n"
            + body
        )
        return subprocess.run(
            ["bash", "-c", script], input="", text=True, capture_output=True,
            timeout=60, env=self.env(**env),
        )

    def run_uninstaller(self, *args):
        return subprocess.run(
            ["bash", str(UNINSTALLER), *args], text=True, capture_output=True,
            timeout=60, env=self.env(),
        )


class SafetyTestCase(unittest.TestCase):
    def setUp(self):
        if os.geteuid() == 0:
            self.fail("run the test suite as a normal user, not root")
        self.box = Sandbox(self)

    def assertOk(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assertFailed(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)


class InstallOrderTests(SafetyTestCase):
    def test_checks_run_before_any_system_change(self):
        main = installer_library().split("\nmain() {", 1)[1]
        order = [main.index(step) for step in (
            "check_kernel_build_tree", "require_dkms_conf", "preflight_build",
            "install_firmware", "install_via_dkms",
        )]
        self.assertEqual(order, sorted(order))


class PreflightTests(SafetyTestCase):
    def setUp(self):
        super().setUp()
        self.box.write("drivers/aic8800/Makefile", "all:\n", base=self.box.src)
        self.old_fw = self.box.write("lib/firmware/aic8800D80/old.bin", "installed")

    def test_failed_build_changes_nothing(self):
        self.box.stub("make", "exit 2")
        result = self.box.run_function("preflight_build\necho UNEXPECTED_CONTINUE")
        self.assertFailed(result)
        self.assertIn("Existing firmware and DKMS installation were not changed", result.stdout)
        self.assertNotIn("UNEXPECTED_CONTINUE", result.stdout)
        self.assertEqual(self.old_fw.read_text(), "installed")
        self.assertEqual(self.box.calls_to("dkms"), [])

    def test_successful_build_targets_running_kernel(self):
        result = self.box.run_function("preflight_build")
        self.assertOk(result)
        clean, build = self.box.calls_to("make")
        self.assertTrue(clean.endswith(" clean"), clean)
        kver = subprocess.run(["uname", "-r"], capture_output=True, text=True).stdout.strip()
        for call in (clean, build):
            self.assertIn(f"KVER={kver}", call)
            self.assertIn(f"KDIR=/lib/modules/{kver}/build", call)

    def test_missing_dkms_conf_stops(self):
        result = self.box.run_function("require_dkms_conf\necho UNEXPECTED_CONTINUE")
        self.assertFailed(result)
        self.assertNotIn("UNEXPECTED_CONTINUE", result.stdout)

    def test_present_dkms_conf_passes(self):
        self.box.write("dkms.conf", 'PACKAGE_NAME="aic8800"\n', base=self.box.src)
        self.assertOk(self.box.run_function("require_dkms_conf"))


class FirmwareTests(SafetyTestCase):
    def setUp(self):
        super().setUp()
        self.box.write("fw/aic8800D80/new.bin", "new", base=self.box.src)
        self.old_fw = self.box.write("lib/firmware/aic8800D80/old.bin", "old")

    def test_package_owned_firmware_is_left_alone(self):
        self.box.stub("dpkg", '[ "$1" = -S ] && echo "firmware-aic8800: $2" && exit 0\nexit 1')
        result = self.box.run_function("install_firmware\necho UNEXPECTED_CONTINUE")
        self.assertFailed(result)
        self.assertIn("firmware-aic8800", result.stdout)
        self.assertNotIn("UNEXPECTED_CONTINUE", result.stdout)
        self.assertEqual(self.old_fw.read_text(), "old")
        self.assertFalse((self.box.root / "var/backups").exists())

    def test_ownership_is_checked_on_the_real_path(self):
        self.box.stub("dpkg", "exit 1")
        self.box.run_function("install_firmware")
        queried = [c.split()[-1] for c in self.box.calls_to("dpkg")]
        self.assertIn("/lib/firmware/aic8800D80", queried)
        self.assertFalse(any(str(self.box.root) in q for q in queried))

    def test_old_firmware_is_backed_up_under_destdir(self):
        self.box.stub("dpkg", "exit 1")
        result = self.box.run_function("install_firmware")
        self.assertOk(result)
        self.assertEqual((self.box.root / "lib/firmware/aic8800D80/new.bin").read_text(), "new")
        self.assertFalse(self.old_fw.exists())
        backups = list((self.box.root / "var/backups").glob("aic8800-firmware-*/aic8800D80/old.bin"))
        self.assertEqual(len(backups), 1)

    def _install_matching_firmware(self):
        shutil.rmtree(self.old_fw.parent)
        return self.box.write("lib/firmware/aic8800D80/new.bin", "new")

    def test_firmware_identical_to_the_shipped_copy_is_not_backed_up(self):
        installed = self._install_matching_firmware()
        self.box.stub("dpkg", "exit 1")
        self.assertOk(self.box.run_function("install_firmware"))
        self.assertFalse((self.box.root / "var/backups").exists())
        self.assertEqual(installed.read_text(), "new")
        # Replaced in place, not copied into a nested directory.
        self.assertFalse((installed.parent / "aic8800D80").exists())

    def test_changed_firmware_is_still_backed_up(self):
        installed = self._install_matching_firmware()
        installed.write_text("edited by hand")
        self.box.stub("dpkg", "exit 1")
        self.assertOk(self.box.run_function("install_firmware"))
        backups = list((self.box.root / "var/backups").glob("aic8800-firmware-*/aic8800D80/new.bin"))
        self.assertEqual([b.read_text() for b in backups], ["edited by hand"])

    def test_extra_file_in_installed_firmware_is_still_backed_up(self):
        installed = self._install_matching_firmware()
        (installed.parent / "extra.bin").write_text("extra")
        self.box.stub("dpkg", "exit 1")
        self.assertOk(self.box.run_function("install_firmware"))
        backups = list((self.box.root / "var/backups").glob("aic8800-firmware-*/aic8800D80/extra.bin"))
        self.assertEqual(len(backups), 1)
        self.assertFalse((installed.parent / "extra.bin").exists())

    def test_reinstalling_does_not_add_backups(self):
        self.box.stub("dpkg", "exit 1")
        self.assertOk(self.box.run_function("install_firmware"))  # backs up old.bin once
        self.assertOk(self.box.run_function("install_firmware"))
        self.assertOk(self.box.run_function("install_firmware"))
        backups = list((self.box.root / "var/backups").glob("aic8800-firmware-*"))
        self.assertEqual(len(backups), 1)


class UdevInstallTests(SafetyTestCase):
    def setUp(self):
        super().setUp()
        self.box.write("fw/aic8800D80/new.bin", "new", base=self.box.src)
        self.box.write("aic.rules", "# AIC8800 rules\n", base=self.box.src)
        self.box.write("usb_modeswitch/1111_1111", "# AIC8800D80\n", base=self.box.src)

    def test_rules_go_to_etc_and_old_copies_are_left_alone(self):
        """/etc shadows same-named rules in /usr/lib and /lib, and a copy there
        may belong to a package, so the installer does not delete it."""
        old = self.box.write("usr/lib/udev/rules.d/aic.rules", "# AIC8800 old\n")
        foreign = self.box.write("lib/udev/rules.d/aic.rules", "# someone else's rules\n")
        result = self.box.run_function("install_firmware")
        self.assertOk(result)
        self.assertTrue((self.box.root / "etc/udev/rules.d/aic.rules").exists())
        self.assertTrue((self.box.root / "etc/usb_modeswitch.d/1111:1111").exists())
        self.assertEqual(old.read_text(), "# AIC8800 old\n")
        self.assertTrue(foreign.exists())

    def test_trigger_is_limited_to_1111_devices(self):
        self.assertOk(self.box.run_function("install_firmware"))
        triggers = [c for c in self.box.calls_to("udevadm") if " trigger" in c]
        self.assertEqual(len(triggers), 1)
        self.assertIn("--attr-match=idVendor=1111", triggers[0])
        self.assertIn("--attr-match=idProduct=1111", triggers[0])


class KernelHeadersTests(SafetyTestCase):
    def flavour(self, release):
        self.box.stub("uname", f'echo "{release}"')
        result = self.box.run_function("kernel_flavour")
        self.assertOk(result)
        return result.stdout.strip()

    def test_flavours(self):
        cases = {
            "6.12.113+deb13-amd64": "amd64",
            "6.12.74+deb13+1-amd64": "amd64",
            "6.12.90+deb13.1-amd64": "amd64",
            "6.12.113+deb13-cloud-amd64": "cloud-amd64",
            "6.1.0-27-amd64": "amd64",
            "6.8.0-47-generic": "generic",
            "6.6.51+rpt-rpi-v8": "rpi-v8",
        }
        for release, expected in cases.items():
            with self.subTest(release=release):
                self.assertEqual(self.flavour(release), expected)

    def headers(self, manager, release, build_tree=True, apt_has_meta=True):
        self.box.stub("uname", f'echo "{release}"')
        self.box.stub("apt-cache", "exit 0" if apt_has_meta else "exit 100")
        body = (
            f"kernel_build_tree_available() {{ return {0 if build_tree else 1}; }}\n"
            f"install_kernel_headers {manager}"
        )
        result = self.box.run_function(body)
        return result, self.box.calls_to({"apt": "apt-get"}.get(manager, manager))

    def test_apt_installs_metapackage(self):
        result, calls = self.headers("apt", "6.12.113+deb13-amd64")
        self.assertOk(result)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].endswith("install -y linux-headers-amd64"), calls)

    def test_apt_adds_running_kernel_headers_when_build_tree_missing(self):
        result, calls = self.headers("apt", "6.8.0-47-generic", build_tree=False)
        self.assertOk(result)
        self.assertTrue(calls[0].endswith("install -y linux-headers-6.8.0-47-generic linux-headers-generic"), calls)

    def test_apt_warns_without_metapackage(self):
        result, calls = self.headers("apt", "6.12.113+deb13-amd64", apt_has_meta=False)
        self.assertOk(result)
        self.assertIn("No kernel headers metapackage", result.stdout)
        self.assertEqual(calls, [])

    def test_dnf_installs_versioned_and_tracking_package(self):
        result, calls = self.headers("dnf", "6.11.4-301.fc41.x86_64")
        self.assertOk(result)
        self.assertEqual(calls, ["dnf install -y kernel-devel-6.11.4-301.fc41.x86_64 kernel-devel"])

    def test_pacman_falls_back_to_linux_headers(self):
        # No /usr/lib/modules/<release>/pkgbase exists for this made-up release.
        result, calls = self.headers("pacman", "0.0.0-test-not-installed")
        self.assertOk(result)
        self.assertEqual(calls, ["pacman -S --needed --noconfirm linux-headers"])

    def test_zypper_uses_flavour_devel_package(self):
        result, calls = self.headers("zypper", "6.4.0-150600.23.25-default")
        self.assertOk(result)
        self.assertEqual(calls, ["zypper --non-interactive install kernel-default-devel"])


class TerminalOutputTests(SafetyTestCase):
    """The installer's terminal output must not carry identifiers (issue #35).

    People paste installer output into issues. The tools it calls print the
    connected network name, interface names that embed the adapter's MAC
    address, Bluetooth addresses and the host name, none of which reach the
    install log. All values below are fake and use the documentation prefix 02:00:00.
    """

    FAKE_SSID = "FakeNetworkNameForTest"
    FAKE_IFACE = "wlx020000000055"
    FAKE_MAC = "02:00:00:00:00:56"
    FAKE_HOST = "fake-host-for-test"

    def stub_wireless_and_bluetooth(self):
        b = self.box
        b.stub("iwconfig", f"""
            echo 'lo        no wireless extensions.'
            echo ''
            echo '{self.FAKE_IFACE}  IEEE 802.11  ESSID:"{self.FAKE_SSID}"'
            echo '          Mode:Managed  Access Point: 02:00:00:00:00:EE'
        """)
        b.stub("bluetoothctl", f"""
            [ "$1" = list ] && echo 'Controller {self.FAKE_MAC} {self.FAKE_HOST} [default]'
            exit 0
        """)

    def assertNoIdentifiers(self, text):
        for value in (self.FAKE_SSID, self.FAKE_IFACE, self.FAKE_MAC, self.FAKE_HOST,
                      "020000000055", "02:00:00:00:00:EE"):
            self.assertNotIn(value, text)

    def test_verification_prints_counts_not_identifiers(self):
        self.stub_wireless_and_bluetooth()
        result = self.box.run_function("verify_installation")
        self.assertOk(result)
        output = result.stdout + result.stderr
        self.assertNoIdentifiers(output)
        self.assertIn("1 wireless interface(s) present", output)
        self.assertIn("1 Bluetooth controller(s) present", output)

    def test_verification_reports_when_nothing_is_present(self):
        self.box.stub("iwconfig", "echo 'lo        no wireless extensions.'")
        self.box.stub("bluetoothctl", "exit 0")
        result = self.box.run_function("verify_installation")
        self.assertOk(result)
        output = result.stdout + result.stderr
        self.assertIn("No wireless interfaces detected", output)
        self.assertIn("No Bluetooth interfaces detected", output)

    def test_next_steps_do_not_suggest_the_password_argument(self):
        result = self.box.run_function("show_final_instructions")
        self.assertOk(result)
        self.assertIn("nmcli --ask device wifi connect", result.stdout)
        self.assertNotIn('password "PASSWORD"', result.stdout)


class UninstallTests(SafetyTestCase):
    def setUp(self):
        super().setUp()
        b = self.box
        b.stub("dkms", '[ "$1" = status ] && echo "aic8800/1.0.0, 6.12.113+deb13-amd64, x86_64: installed"\nexit 0')
        b.stub("dpkg", "exit 1")
        self.ours = [
            b.write("usr/src/aic8800-1.0.0/dkms.conf", 'PACKAGE_NAME="aic8800"\n'),
            b.write("etc/udev/rules.d/aic.rules", "# AIC8800 rules\n"),
            b.write("etc/usb_modeswitch.d/1111:1111", "# AIC8800D80\n"),
            b.write("var/log/aic8800-install.log", "log\n"),
        ]
        self.fw = b.write("lib/firmware/aic8800D80/fw.bin", "fw")
        self.foreign = [
            b.write("usr/src/aic8800-other/README", "not ours"),
            b.write("lib/udev/rules.d/aic.rules", "# someone else's rules\n"),
        ]

    def test_dry_run_changes_nothing(self):
        result = self.box.run_uninstaller("--dry-run")
        self.assertOk(result)
        self.assertIn("+ dkms remove aic8800/1.0.0 --all", result.stdout)
        for path in self.ours + self.foreign + [self.fw]:
            self.assertTrue(path.exists(), path)
        self.assertNotIn("dkms remove", "\n".join(self.box.calls_to("dkms")))

    def test_removes_only_what_install_sh_installed(self):
        result = self.box.run_uninstaller()
        self.assertOk(result)
        for path in self.ours:
            self.assertFalse(path.exists(), path)
        for path in self.foreign:
            self.assertTrue(path.exists(), path)
        self.assertIn("dkms remove aic8800/1.0.0 --all", self.box.calls_to("dkms"))
        self.assertFalse(self.fw.exists())
        backups = list((self.box.root / "var/backups").glob("aic8800-firmware-*/aic8800D80/fw.bin"))
        self.assertEqual(len(backups), 1)

    def test_dry_run_finds_tools_that_are_only_in_sbin(self):
        """Issue #34: dkms and update-initramfs are not on a normal user's PATH."""
        b = self.box
        sbin = b.root.parent / "sbin"
        sbin.mkdir()
        for name in ("dkms", "update-initramfs"):
            (b.stubs / name).rename(sbin / name)
        for name in ("dracut", "mkinitcpio"):
            (b.stubs / name).unlink()
        # A PATH with only the basic tools and the stubs, so no real dkms or
        # initramfs tool on the machine running the test can be found.
        basic = b.root.parent / "basic"
        basic.mkdir()
        for tool in ("rm", "sed", "grep", "sort", "uname", "readlink", "mv",
                     "mkdir", "find", "date", "dirname", "cat", "tr", "head"):
            found = shutil.which(tool)
            self.assertIsNotNone(found, tool)
            (basic / tool).symlink_to(found)
        result = subprocess.run(
            [shutil.which("bash"), str(UNINSTALLER), "--dry-run"], text=True,
            capture_output=True, timeout=60,
            env=b.env(PATH=f"{b.stubs}:{basic}", SBIN_DIRS=str(sbin)),
        )
        self.assertOk(result)
        self.assertIn("+ dkms remove aic8800/1.0.0 --all", result.stdout)
        self.assertIn("+ update-initramfs", result.stdout)
        self.assertNotIn("is not installed", result.stdout)
        self.assertNotIn("no supported initramfs tool", result.stdout)

    def test_package_owned_firmware_is_kept(self):
        self.box.stub("dpkg", '[ "$1" = -S ] && echo "firmware-aic8800: $2" && exit 0\nexit 1')
        result = self.box.run_uninstaller()
        self.assertOk(result)
        self.assertTrue(self.fw.exists())
        self.assertIn("owned by package 'firmware-aic8800'", result.stdout)

    def test_failed_dkms_remove_keeps_source_and_fails(self):
        """A registration that could not be removed still needs its source tree."""
        b = self.box
        b.stub("dkms", '[ "$1" = status ] && echo "aic8800/1.0.0, 6.12.113+deb13-amd64, x86_64: installed"\n'
                       '[ "$1" = remove ] && exit 1\nexit 0')
        result = b.run_uninstaller()
        self.assertFailed(result)
        self.assertTrue((b.root / "usr/src/aic8800-1.0.0/dkms.conf").exists())
        self.assertIn("keeping", result.stdout)
        # The remaining steps still run.
        self.assertFalse((b.root / "etc/udev/rules.d/aic.rules").exists())
        self.assertFalse(self.fw.exists())

    def test_only_the_failed_version_keeps_its_source(self):
        b = self.box
        b.write("usr/src/aic8800-1.0.1/dkms.conf", 'PACKAGE_NAME="aic8800"\n')
        b.stub("dkms", '[ "$1" = status ] && printf "%s\\n" '
                       '"aic8800/1.0.0, 6.12.113+deb13-amd64, x86_64: installed" '
                       '"aic8800/1.0.1, 6.12.115+deb13-amd64, x86_64: installed"\n'
                       '[ "$1" = remove ] && [ "$2" = aic8800/1.0.1 ] && exit 1\nexit 0')
        result = b.run_uninstaller()
        self.assertFailed(result)
        self.assertFalse((b.root / "usr/src/aic8800-1.0.0").exists())
        self.assertTrue((b.root / "usr/src/aic8800-1.0.1/dkms.conf").exists())

    def test_unreadable_dkms_status_keeps_all_sources(self):
        """If the registrations cannot be listed, no source tree is known to be unused."""
        b = self.box
        b.stub("dkms", '[ "$1" = status ] && exit 3\nexit 0')
        result = b.run_uninstaller()
        self.assertFailed(result)
        self.assertTrue((b.root / "usr/src/aic8800-1.0.0/dkms.conf").exists())
        self.assertNotIn("dkms remove", "\n".join(b.calls_to("dkms")))

    def test_package_owned_rules_and_modeswitch_config_are_kept(self):
        """A marker string alone does not make a file this project's to delete."""
        b = self.box
        packaged = b.write("usr/lib/udev/rules.d/aic.rules", "# AIC8800 rules from a package\n")
        b.stub("dpkg", '[ "$1" = -S ] || exit 1\n'
                       'case "$2" in /usr/lib/udev/rules.d/aic.rules|/etc/usb_modeswitch.d/1111:1111)\n'
                       '  echo "aic8800-dkms: $2"; exit 0 ;;\nesac\nexit 1')
        result = b.run_uninstaller()
        self.assertOk(result)
        self.assertTrue(packaged.exists())
        self.assertTrue((b.root / "etc/usb_modeswitch.d/1111:1111").exists())
        self.assertIn("owned by package 'aic8800-dkms'", result.stdout)
        # The installer's own, unowned copy is still removed.
        self.assertFalse((b.root / "etc/udev/rules.d/aic.rules").exists())

    def test_rejects_unknown_option(self):
        result = self.box.run_uninstaller("--bogus")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
