# Changelog

All notable changes to this repository. Upstream's own changes are in its history
(merged here, so `git log` shows them) and are not repeated.

## Unreleased

### Synced with upstream

- Merged upstream `shenmintao/aic8800d80` `main` at `fab5be8`, with its full history
  (`a82a47e`). Until then every code file here was a copy of upstream's older
  `bluetooth` branch at [`8006daf`](https://github.com/shenmintao/aic8800d80/commit/8006daf). Taking upstream `main` brings:
  - builds on Linux 6.12.101 and later 6.12.y. Those kernels carry the backport of
    mainline commit [`9c4f8309`](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=9c4f830927750a2bf9fd9426a5257f0fdce3b662) ("wifi: cfg80211: pass net_device to
    .set_monitor_channel", Linux 6.13; backported to 6.12.101 as
    [`4dae80dd`](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/commit/?id=4dae80dd259b5c24f6c657f434afd5de1f791d12)), and the
    old `>= 6.13.0` check picked the wrong prototype, so the build failed in
    `rwnx_main.c`. Upstream now picks the callback by its type in the kernel headers;
  - the two-stage `F3` then `F2` mode switch for `1111:1111` 88M80 adapters;
  - upstream's tests, OpenWrt and Arch notes, and the `aic_zlp_quirk` module.

### Fixed

- `install.sh` test-builds the driver for the running kernel before changing anything;
  a failed build leaves the system as it was. Before, it removed the existing driver
  for every kernel and only then found that the new source did not compile (`50c66a4`).
- `install.sh` moves existing `/lib/firmware/aic8800*` directories to
  `/var/backups/aic8800-firmware-<date>/` instead of deleting them, and refuses to touch
  them if a package owns them (`4866800`).
- `install.sh` installs the kernel headers package that follows kernel upgrades
  (`linux-headers-amd64`, `linux-headers-generic`, `kernel-devel`,
  `<pkgbase>-headers`, `kernel-<flavour>-devel`). Without it DKMS silently skipped the
  rebuild after a kernel update (`82939b3`).
- `install.sh` writes its log to `/var/log/aic8800-install.log` (mode 0644) instead of a
  world-writable file at a fixed path in `/tmp` (`e71dfef`).
- `install.sh` fails if `dkms.conf` is missing instead of generating one that would
  build for the wrong kernel, and records the installed revision in
  `/usr/src/aic8800-1.0.0/SOURCE_REVISION` (`50c66a4`).
- `aic.rules`: the `1111:1111` rule only acts on adapters whose product string is
  `88M80`, and points usb_modeswitch at the device that raised the event. It used to run
  on any `1111:1111` device, including a dongle's separate flash disk, which it left
  with no driver. The eject rules only run when a whole disk is added (`e0c7882`).
- `install.sh` installs the udev rules to `/etc/udev/rules.d` and re-triggers only
  `1111:1111` devices instead of every device on the system (`e0c7882`).
- `install.sh` explains MOK enrollment for Secure Boot, and exits with an error instead
  of reporting success when the Secure Boot prompt cannot be answered (`945e429`).
- `install.sh` warns when an older build of the driver is still loaded after install
  (`1d05e1c`), creates `/lib/firmware` if it is missing (`1212708`), and prints its
  final instructions without raw colour codes (`944591e`).
- `diagnose_bt.sh` and `diagnostic_build.sh` mask MAC addresses, serial numbers, IP
  addresses, user and host names and home paths in their output (`bb2dc6c`);
  `diagnose_bt.sh` is executable (`944591e`).

### Added

- `uninstall.sh`, with `--dry-run` (`fc5165c`).
- `scripts/hw-smoke.sh`: a read-only hardware report that is safe to paste (`d71626c`).
- `scripts/privacy-scan.sh`: checks tracked files and commit messages for personal
  identifiers (`4d28f15`).
- Tests: static checks of the mode-switch configuration and udev rules (`7dcbdec`),
  installer and uninstaller safety tests (`4bc0322`), a check of the shared output
  filter (`145d0d6`), install/uninstall runs in five distribution containers
  (`4d510f2`), a compile-only build matrix (`042e10d`), a `Makefile` (`2063cc7`) and a
  GitHub Actions workflow (`27e036d`). Upstream's installer tests were updated for the
  changed behaviour (`2b40691`). `DESTDIR` lets the tests redirect the scripts' writes
  (`ed0cf7f`).
- Documentation: rewritten `README.md`, corrected `NOTICE.md`, `MACBOOK.md` limited to
  what has been observed, `docs/mode-switch.md`, `CONTRIBUTING.md`, `KNOWN_ISSUES.md`,
  `ROADMAP.md` and this file.
- GitHub issue forms (bug report, new hardware report, feature request) and a pull
  request template.

## 2026-08-02

- First commit (`d309ff7`): a copy of upstream's `bluetooth` branch at `8006daf`
  (according to its commit message, recovered from an installed DKMS tree), plus `README.md`, `NOTICE.md`, `LICENSE`,
  `MACBOOK.md` and `.gitignore`. The README and NOTICE in that commit wrongly presented
  the `1111:1111` mode switch, the udev rules and the installer as original work; see
  [NOTICE.md](NOTICE.md).
