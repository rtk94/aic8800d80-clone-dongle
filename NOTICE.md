# Provenance and licensing

## Summary

This repository is a **derivative work**, not original code. It exists to document and
package a specific hardware variant that was not previously supported. Read this before
redistributing.

## Chain of origin

1. **AICSemi** authored the original `aic8800` driver for their chipset family and
   released it as Linux kernel source. Both modules in this tree declare
   `MODULE_LICENSE("GPL")` and link against GPL-only kernel symbols.
2. The **Tenda U11** vendor driver drop is the immediate ancestor of this code.
3. **[shenmintao/aic8800d80](https://github.com/shenmintao/aic8800d80)** (`bluetooth`
   branch) carried it forward to modern kernels and established that Bluetooth works
   through the stock `btusb` driver once `aic_load_fw` uploads the firmware patch — see
   [PR #35](https://github.com/shenmintao/aic8800d80/pull/35). That upstream author
   states plainly that they did not develop the driver either.
4. **This repository** adds support for the `1111:1111` "Pandora" clone dongle and a
   hardened multi-distro installer (see "What is new here" below).

## License

The driver source is **GPL-2.0**. This is not a choice this project made — the code
descends from GPL vendor source and its modules declare `MODULE_LICENSE("GPL")`, so
the license carries forward. The full text is in [LICENSE](LICENSE).

Upstream shipped no `LICENSE` file. One is included here so the terms the code was
already under are actually stated.

## Firmware blobs

The files under `fw/` are **proprietary binary firmware** produced by AICSemi. They are:

- not covered by the GPL-2.0 license above,
- shipped without any explicit redistribution grant,
- redistributed here because there is no other way to make the hardware function, and
  because every other packaging of this driver does the same.

This is the same posture as most out-of-tree wireless drivers, but it is a posture, not
a permission. Anyone redistributing this tree — including in a distro package — is
adopting it knowingly. If AICSemi objects, the firmware should be removed and users
directed to extract it from the vendor Windows driver themselves.

## What is new here

The genuinely original contribution of this repository, versus its upstream:

- **`1111:1111` mode-switch support.** These clone dongles enumerate as USB Mass Storage
  with a placeholder VID:PID and require a vendor-specific 16-byte SCSI CDB
  (`FD 00 … F2`) to flip into Wi-Fi + Bluetooth mode, after which they re-enumerate as
  `a69c:8d80`/`8d81`/`8d83`. See `usb_modeswitch/1111_1111`.
- **udev rules** (`aic.rules`) automating that switch and the subsequent driver bind.
- **A multi-distro `install.sh`** handling apt/dnf/yum/pacman/zypper, conflicting
  firmware removal, and DKMS registration.
- **Bluetooth verification tooling** (`diagnose_bt.sh`).

Everything else is upstream's work and AICSemi's.
