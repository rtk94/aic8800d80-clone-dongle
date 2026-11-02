# AIC8800D80 USB Wi-Fi and Bluetooth driver (downstream of shenmintao/aic8800d80)

Linux driver, firmware and installer for USB Wi-Fi 6 and Bluetooth adapters built on
the AICSemi AIC8800D80 chip, including cheap unbranded "AX900" clone dongles.

This repository is a **downstream copy** of
[shenmintao/aic8800d80](https://github.com/shenmintao/aic8800d80) (`main` branch). The
driver and firmware are AICSemi's; the driver, installer, udev rules and mode-switch
configuration are maintained upstream. This repository adds safety fixes to the
installer and rules, an uninstaller, a test suite and documentation. See
[NOTICE.md](NOTICE.md) for exactly what comes from where.

**Status:** works on the maintainer's one adapter on Debian 13 with Linux 6.12.113 and
6.12.115, on two machines (Wi-Fi association and traffic, Bluetooth controller up).
Builds against the kernels
listed under [Tested on](#tested-on). Everything else is untested.

## Is this your device?

Plug the adapter in and run `lsusb`.

| `lsusb` shows | What it is | Status here |
|---|---|---|
| `a69c:8d80` "AIC Wlan", becoming `a69c:8d81` "AIC 8800D80" about a second later | AIC8800D80 in loader mode, then running | **Tested** with one dongle |
| the above plus `1111:1111` "FLASH" and a `214b:7250` "USB2.0 HUB" | a dongle with an internal hub and a separate flash disk holding the Windows installer (see [docs/mode-switch.md](docs/mode-switch.md)) | **Tested**: this is the maintainer's dongle; the flash disk is normal and needs nothing |
| `1111:1111` with product `88M80`, and no `a69c` device | a "Pandora 88M80" clone in mass-storage mode; needs a vendor command to switch | Switch configuration from upstream; **untested here** |
| `a69c:5721` to `a69c:572f` | mass-storage mode of other AIC adapters (the rule names suggest Tenda, UGREEN and Cudy units) | eject rule from upstream; **untested here** |
| another `a69c:`, `368b:`, `2357:`, `2604:` or `3625:` ID | an AIC8800-family adapter the driver's ID tables list | matched by the driver; **untested here** |

The full list of IDs the modules match is in
[Supported USB IDs](#supported-usb-ids).

## Requirements

- Linux with kernel headers for the running kernel (the installer installs them)
- `dkms`, a C compiler and `make` (installed by the installer)
- `usb_modeswitch` and `eject`, only needed for adapters that start in mass-storage mode
- With Secure Boot enabled: a Machine Owner Key enrolled for DKMS (see
  [Secure Boot](#secure-boot))

## Install

```bash
git clone https://github.com/rtk94/aic8800d80-clone-dongle.git
cd aic8800d80-clone-dongle
sudo ./install.sh
```

`install.sh` detects the package manager (apt, dnf, yum, pacman or zypper), installs the
build dependencies and kernel headers that follow kernel upgrades, and **test-builds the
driver before changing anything**. If that build fails, it stops and the system is left
as it was. Otherwise it:

1. moves any existing `/lib/firmware/aic8800*` directories to
   `/var/backups/aic8800-firmware-<date>/` (mixing firmware versions can hang the
   system, according to upstream), and refuses to touch them if a package owns them;
2. copies the firmware to `/lib/firmware`, the udev rules to
   `/etc/udev/rules.d/aic.rules` and the mode-switch configuration to
   `/etc/usb_modeswitch.d/1111:1111`;
3. registers the source with DKMS as `aic8800/1.0.0`, builds and installs the modules,
   records the installed source revision in `/usr/src/aic8800-1.0.0/SOURCE_REVISION`,
   and refreshes the initramfs;
4. loads the driver.

The log is written to `/var/log/aic8800-install.log`. The installer has been run end to
end, in containers, on Debian 13, Ubuntu 24.04, Fedora 44, Arch Linux and openSUSE
Tumbleweed (see [Tested on](#tested-on)). On real hardware it has been run only on
Debian 13: on the maintainer's main computer (Linux 6.12.115: install, reboot, replug,
uninstall and reinstall) and on a late-2007 MacBook (Linux 6.12.113: install, reboot and
replug).

## Verify

```bash
lsusb | grep -iE 'a69c|1111'   # expect a69c:8d81 once the firmware is loaded
./scripts/hw-smoke.sh          # drivers bound, Wi-Fi interface, Bluetooth state
```

`scripts/hw-smoke.sh` only reads system state, and masks MAC addresses, serial numbers
and other identifiers in the formats known to appear in its output, so that it can be
pasted into an issue; read it before posting. Run it with `sudo` to include kernel log
lines. A working adapter looks like this:

```text
a69c:8d81 bcdDevice=0100 product="AIC 8800D80" speed=480M port=3-1.1
  interface 1.0 class=e0 driver=btusb
  interface 1.1 class=e0 driver=btusb
  interface 1.2 class=ff driver=aic8800_fdrv
== wireless interfaces
wlx<MAC> driver=aic8800_fdrv operstate=up
== bluetooth
hci0 bus_driver=btusb
```

The Wi-Fi interface is named `wlx` followed by the adapter's MAC address. Connect with
your usual network manager, for example
`nmcli --ask device wifi connect "<YOUR_SSID>" ifname wlx<MAC>`, which asks for the
password instead of taking it on the command line. Avoid the `password "<...>"` form if
the network already has a saved profile (for example from another Wi-Fi card): with
NetworkManager 1.52.1 it then fails with
`802-11-wireless-security.key-mgmt: property is missing`, while `--ask` connects.

## Bluetooth

No custom Bluetooth module is needed. `aic_load_fw` uploads the Bluetooth firmware
patch when it initializes the adapter, and the kernel's standard `btusb` driver then
handles the controller. If Bluetooth does not come up:

```bash
./diagnose_bt.sh               # add sudo to include kernel log lines
sudo rfkill unblock bluetooth  # if the controller is soft-blocked
```

## Uninstall

```bash
sudo ./uninstall.sh --dry-run  # list what would be removed
sudo ./uninstall.sh
```

This unloads the modules, removes the DKMS package, its source tree, this project's
udev rules and mode-switch configuration and the installer log, moves the firmware to
`/var/backups/aic8800-firmware-<date>/`, and refreshes the initramfs. It leaves the
packages installed as dependencies, and any firmware a package owns.

## Secure Boot

With Secure Boot enabled, the kernel only loads modules signed by a key it trusts, and
the modules DKMS builds are not signed by your distribution. Recent DKMS versions can
sign them with a Machine Owner Key (MOK) that you enroll once with
`sudo mokutil --import <key file>` and confirm in the MOK manager on the next boot. Where
that key is stored depends on the distribution; see its DKMS documentation. The
installer asks before continuing when Secure Boot is on, and stops if nobody can answer.

**Untested here:** the maintainer's machine has Secure Boot disabled.

## Kernel updates

DKMS rebuilds the driver automatically when headers for the new kernel are installed.
The installer installs the headers package that follows kernel upgrades (for example
`linux-headers-amd64` on Debian). Without it, DKMS skips the rebuild without an error and
the adapter stops working after the next reboot.

After a kernel update, compare the kernel with what DKMS has built:

```bash
uname -r
sudo dkms status aic8800
```

If the build for the new kernel fails, run `sudo ./diagnostic_build.sh` and open an
issue with its output (see [CONTRIBUTING.md](CONTRIBUTING.md)).

## Troubleshooting

- **A removable disk named after the adapter appears.** On dongles with an internal hub,
  the `1111:1111` "FLASH" device is a separate flash disk holding the Windows driver.
  This is normal and does not affect Wi-Fi.
- **`lsusb` stays at `a69c:8d80`.** This usually means the firmware upload failed. Run
  `sudo ./scripts/hw-smoke.sh`. If the kernel log reports `chip_mcu_id=1`, upstream says
  this adapter needs its
  [`legacy-mcu1`](https://github.com/shenmintao/aic8800d80/tree/legacy-mcu1) branch,
  which this repository does not carry.
- **`lsusb` stays at `1111:1111` and there is no `a69c` device.** See
  [docs/mode-switch.md](docs/mode-switch.md); the switch is untested here and reports
  differ on which sequence works.
- **`dkms: command not found` over SSH.** `dkms` lives in `/usr/sbin`, which is often
  not on the `PATH` of non-interactive shells; run `sudo dkms ...` or use the full path.
- **Bluetooth problems.** `./diagnose_bt.sh`.
- **Build failures.** `sudo ./diagnostic_build.sh`.

Known problems are listed in [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

## Tested on

Three different kinds of evidence, kept apart on purpose. CI proves that the code
compiles and that the installer works in a container; it says nothing about whether an
adapter works.

| Kernel | Distribution | Maintainer's hardware | Built (containers, locally and in CI) | Reported by others |
|---|---|---|---|---|
| 6.12.115+deb13.1-amd64 | Debian 13 | **Works** on the main computer, installed with `install.sh` at `4b99e2f`: firmware load, `aic8800_fdrv` and `btusb` bound, `hci0` up, association and traffic, replug re-enumerates, `uninstall.sh` removes the installation (2026-11-02) | yes (DKMS on the maintainer's machine, not in CI) | none yet |
| 6.12.113+deb13-amd64 | Debian 13 | **Works** on the main computer with hand-loaded modules: firmware load, `aic8800_fdrv` and `btusb` bound, `hci0` up, association and traffic (2026-11-01). **Works** on the late-2007 MacBook, installed with the current `install.sh` (revision not recorded): association through the XFCE network applet and traffic, `hci0` up, a keyboard and a mouse paired, replug re-enumerates; `nmcli device wifi connect ... password` failed ([#29](https://github.com/rtk94/aic8800d80-clone-dongle/issues/29)) (2026-11-02) | yes, and installer passed | none yet |
| 6.12.111+deb13-amd64 | Debian 13 | not tested with this code | yes (local build only, not in CI) | none yet |
| 6.12.101+deb13-amd64 | Debian 13 | not tested with this code | yes | none yet |
| 6.12.100+deb13-amd64 | Debian 13 | not tested with this code | yes | none yet |
| 6.1.0-54-amd64 | Debian 12 | not tested | yes | none yet |
| 6.8.0-147-generic | Ubuntu 24.04 | not tested | yes, and installer passed | none yet |
| 7.2.13-200.fc44 | Fedora 44 | not tested | yes, and installer passed | none yet |
| 7.2.14-arch1-1 | Arch Linux | not tested | yes, and installer passed | none yet |
| 7.3.0-1-default | openSUSE Tumbleweed | not tested | installer passed (DKMS build) | none yet |

Before the 2026-11-01 sync with upstream, this repository carried a copy of upstream's
older `bluetooth` branch (`archive/bluetooth-final`); the maintainer's installed copy also
had a local kernel-compatibility patch. With that older code the maintainer ran the
adapter on their main computer under Debian 13 (kernel versions not recorded; the first
commit records successful builds on 6.12.95, 6.12.96 and 6.12.100) and on a late-2007 MacBook
(6.12.101 and 6.12.107). Those runs say nothing about the current code.

The container results were reproduced on GitHub Actions on 2026-11-01
([run 41364326580](https://github.com/rtk94/aic8800d80-clone-dongle/actions/runs/41364326580)):
every build target in the table except 6.12.111, and install, reinstall and uninstall on
all five distributions, with the same kernel versions. CI repeats the builds on every
push and weekly, so newer distribution kernels will replace these versions over time.

For reports about upstream's code on other systems, see upstream's README and issues.

## Supported USB IDs

From the module ID tables of the current source (`modinfo -F alias`). Being listed means
the driver will bind; it does not mean the adapter has been tested.

- `aic_load_fw` (firmware loader): `a69c:8800`, `a69c:8801`, `a69c:8d40`, `a69c:8d41`,
  `a69c:8d80`, `a69c:8d81`, `368b:8d81`, `368b:8d90`, `368b:8d91`, `368b:8d92`,
  `368b:8d99`
- `aic8800_fdrv` (Wi-Fi): `a69c:8801`, `a69c:88dc`, `a69c:88dd`, `a69c:88de`,
  `a69c:8d41`, `a69c:8d81`, `a69c:8d83`, `368b:8870`, `368b:8871`, `368b:88df`,
  `368b:88e0` to `368b:88e3`, `368b:88e5`, `368b:8d45` to `368b:8d4a`, `368b:8d81`,
  `368b:8d83` to `368b:8d86`, `368b:8d88` to `368b:8d8d`, `368b:8d91`, `368b:8d99`,
  `2357:014b`, `2357:014e`, `2604:0013`, `2604:0014`, `2604:001f`, `2604:0020`,
  `3625:0110`
- `aic_zlp_quirk` (Bluetooth workaround): `368b:8d81`
- udev rules (`aic.rules`): `a69c:5721` to `a69c:5727`, `a69c:572a`, `a69c:572c`,
  `a69c:572f` (ejected from mass-storage mode) and `1111:1111` with product `88M80`
  (mode switch)

## Platform notes

- [MACBOOK.md](MACBOOK.md): notes for a late-2007 polycarbonate MacBook (USB 2.0 only).
- `bazzite/`: upstream's RPM spec for Bazzite. It downloads and builds **upstream's**
  code, not this repository's, and is untested here.
- [INSTALL_ARCH.md](INSTALL_ARCH.md) and [OPENWRT.md](OPENWRT.md): upstream's notes for
  Arch-based distributions and OpenWrt, untested here.

## Contributing and testing

```bash
make test        # lint, unit tests, privacy scan; no root, no network, a few seconds
```

[CONTRIBUTING.md](CONTRIBUTING.md) covers reporting bugs and new hardware IDs, cleaning
logs before posting them, and the slower container tests. Planned work is in
[ROADMAP.md](ROADMAP.md), and changes in [CHANGELOG.md](CHANGELOG.md).

## Scope

The mainline Linux kernel has no driver for AIC8800 USB adapters. The only mainline
effort found is an RFC for an **SDIO** driver
([linux-wireless, 23 July 2026](https://lwn.net/Articles/1084468/)), not merged as of
November 2026. Until there is a mainline driver, out-of-tree builds like this one are
the only option.

Bug reports about installation, kernel compatibility and the hardware listed above are
welcome here. Problems in the driver itself are best reported
[upstream](https://github.com/shenmintao/aic8800d80/issues), where it is maintained;
this repository does not change driver source except for kernel compatibility.

## License

The driver source is GPL-2.0 ([LICENSE](LICENSE)). The firmware in `fw/` is proprietary
AICSemi binary with no explicit redistribution grant; read [NOTICE.md](NOTICE.md) before
redistributing this tree.
