# AIC8800D80 Linux driver — with support for `1111:1111` clone dongles

Linux Wi-Fi + Bluetooth support for AIC8800D80 USB adapters, **including the cheap
unbranded "Pandora" clone dongles that enumerate as `1111:1111` and are ignored by every
other driver package.**

If you bought an AX900/AX300-class Wi-Fi 6 dongle from Temu/AliExpress/eBay, plugged it
into Linux, and got a fake USB CD-ROM instead of a network interface — this is the repo
for you.

## Is this your device?

Run `lsusb` with the dongle plugged in:

| What you see | Status |
|---|---|
| `1111:1111` | **The clone dongle. This repo is the reason it works.** |
| `a69c:8d80`, `a69c:8d81`, `a69c:8d83` | AIC8800D80 already in Wi-Fi mode — supported |
| `a69c:5721`–`a69c:572f` | Mass-storage mode (Tenda U11, Cudy, UGREEN, etc.) — supported |

### Why the clone needs special handling

The `1111:1111` dongles ship in USB Mass Storage mode with a placeholder vendor ID that
matches no known device. They require a **vendor-specific 16-byte SCSI CDB**
(`FD 00 00 00 00 00 00 00 00 00 00 00 00 00 00 F2`, wrapped in a standard 31-byte CBW)
to switch into Wi-Fi + Bluetooth mode, after which they re-enumerate as `a69c:8d80`.

Standard `usb_modeswitch` has no entry for this, and the ejection tricks that work for
the Tenda units do nothing. `usb_modeswitch/1111_1111` in this repo is that missing
entry, and `aic.rules` fires it automatically on hotplug.

## Requirements

- Kernel headers for the **running** kernel
- `dkms`, `build-essential`/`base-devel`, `usb_modeswitch`, `usbutils`
- Secure Boot users: modules must be signed with your own enrolled MOK

## Install

```bash
git clone <this repo>
cd dongle-driver
sudo ./install.sh
```

The installer detects your package manager (apt/dnf/yum/pacman/zypper), installs build
dependencies, **removes conflicting `aic8800*` firmware directories** (see warning
below), installs firmware, udev rules and the mode-switch config, then registers the
tree with DKMS so it rebuilds automatically on kernel updates.

> **Warning:** delete all pre-existing `aic8800*` folders under `/lib/firmware` first.
> Mismatched firmware versions can hard-freeze the system. The installer does this, but
> if you install manually, do it yourself.

<details>
<summary>Manual installation</summary>

```bash
sudo cp aic.rules /lib/udev/rules.d/
sudo cp -r ./fw/aic8800D80 /lib/firmware/
sudo cp usb_modeswitch/1111_1111 /etc/usb_modeswitch.d/1111:1111
cd drivers/aic8800 && make && sudo make install
sudo modprobe aic8800_fdrv
```

The mode-switch config **must** be installed under a filename containing a colon
(`1111:1111`). It is stored as `1111_1111` in git because Windows cannot check out
filenames containing colons.

</details>

## Verify

```bash
lsusb                        # should now show a69c:8d8x, not 1111:1111
lsmod | grep aic             # aic8800_fdrv + aic_load_fw
ip link                      # new wlanN interface
hciconfig -a                 # hci0 for Bluetooth
dmesg | grep -iE 'aic|rwnx'  # firmware load progress
```

## Bluetooth

Bluetooth needs **no custom module.** `aic_load_fw` uploads the firmware patch at init,
after which the stock Linux `btusb` driver handles the HCI interface. If you have a
legacy `aic_btusb` installed from another package, remove it — it conflicts.

```bash
sudo ./diagnose_bt.sh        # if Bluetooth does not come up
```

Common causes: missing `fw_patch_8800d80_u02.bin` / `fw_patch_table_8800d80_u02.bin` /
`fw_adid_8800d80_u02.bin` in `/lib/firmware/aic8800D80/`, or an rfkill soft block
(`sudo rfkill unblock bluetooth`).

## Kernel updates

DKMS rebuilds automatically. Confirm with:

```bash
sudo dkms status
```

If a new kernel breaks the build, that is an upstream kernel-API change — open an issue
with the contents of `/var/lib/dkms/aic8800/1.0.0/build/make.log`.

## Tested on

| Distro | Kernel | Arch | Result |
|---|---|---|---|
| Debian 13 (trixie) | 6.12.95 / 6.12.96 / 6.12.100 | x86_64 | Wi-Fi + BT working |
| Ubuntu 25.04 | 6.16 | x86_64 | upstream-reported |
| Debian 12 | 6.1.0-27 | x86_64 | upstream-reported |

## Platform notes

- [Installing on a 2008 polycarbonate MacBook](MACBOOK.md) — including why USB 2.0 caps
  you at ~150–250 Mb/s regardless of the radio
- `bazzite/` — RPM spec for immutable Fedora-derived systems

## Provenance and licensing

This is a **derivative work**. The driver is AICSemi's, by way of the Tenda U11 vendor
drop and [shenmintao/aic8800d80](https://github.com/shenmintao/aic8800d80). The
contribution here is clone-dongle support, the udev/mode-switch plumbing, and the
installer.

Driver source is GPL-2.0 ([LICENSE](LICENSE)). The firmware under `fw/` is proprietary
AICSemi binary with no explicit redistribution grant — read [NOTICE.md](NOTICE.md)
before redistributing this tree.

## Scope

There is **no mainline kernel support** for AIC8800 as of 2026, so out-of-tree is the
only option. Bug reports about kernel-API breakage are welcome. Requests to re-architect
the underlying vendor driver are out of scope.
