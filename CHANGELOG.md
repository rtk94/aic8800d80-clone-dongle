# Changelog

All notable changes to this repository. Upstream's own changes are in its history
(merged here, so `git log` shows them) and are not repeated.

## Unreleased

### Synced with upstream

- Merged upstream `main` at `2e75f88` (2026-11-02). Upstream's PR
  [#131](https://github.com/shenmintao/aic8800d80/pull/131) adopted parts of the
  installer and udev fixes listed under "Fixed" (from upstream PRs #128 and #129): the
  test build before changing the system, the log in `/var/log`, and the narrowed
  `1111:1111` and eject rules. Where the two versions overlapped, this repository now
  uses upstream's: its `preflight_build` (which also runs `make clean` and stops if the
  copy fails) and its stricter log setup, which stops if the log cannot be created.
  The merge also brings upstream's `AGENTS.md` (its maintenance policy, in Chinese) and
  its installer and udev tests. The hardware runs recorded in the README used the
  installer from before this merge (`4b99e2f`).
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

- `install.sh` no longer leaves a new copy of the firmware in `/var/backups` on every
  reinstall. An installed `aic8800*` directory that is identical to the one in this
  repository is replaced without a backup; anything that differs, or has extra files,
  is still moved to `/var/backups/aic8800-firmware-<date>/`. `uninstall.sh` is
  unchanged and still keeps one backup per run. Upstream's `AGENTS.md` asks that
  backups not accumulate without limit.
- `install.sh` no longer prints the connected network name, wireless interface names
  (which embed the adapter's MAC address), Bluetooth addresses or the host name to the
  terminal in its final verification step; it prints counts only. Its "Next Steps" now
  suggest `nmcli --ask device wifi connect` instead of the password-argument form that
  fails when a saved profile exists. The install log was already clean. This is a
  change to upstream's `install.sh`, so it diverges from upstream until sent there
  ([#35](https://github.com/rtk94/aic8800d80-clone-dongle/issues/35)).
- `uninstall.sh --dry-run` run as a normal user no longer reports `dkms` and
  `update-initramfs` as missing and drops their steps from the plan. On Debian they are
  in `/usr/sbin`, which an unprivileged `PATH` lacks; the script now appends the sbin
  directories to `PATH`
  ([#34](https://github.com/rtk94/aic8800d80-clone-dongle/issues/34)).
- `install.sh` test-builds the driver for the running kernel before changing anything;
  a failed build leaves the system as it was. Before, it removed the existing driver
  for every kernel and only then found that the new source did not compile (`50c66a4`).
  Since the 2026-11-02 sync this uses upstream's implementation of the same check
  (`bee4006`).
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
- `scripts/privacy-scan.sh` reads every commit message, not only the first-parent
  history, which after merging pull requests no longer contains this repository's own
  commits (`432e8d4`).
- `diagnose_bt.sh` and `diagnostic_build.sh` mask MAC addresses, serial numbers, IP
  addresses, user and host names and home paths in their output (`bb2dc6c`);
  `diagnose_bt.sh` is executable (`944591e`).
- `scripts/hw-smoke.sh`, `diagnose_bt.sh` and `diagnostic_build.sh` also mask the
  space-separated addresses the Wi-Fi driver logs, such as
  `AICWFDBG(LOGERROR) p2p dev addr=<MAC>`. That line is logged at the default level
  whenever a P2P device is added (it appeared after every load on one of the
  maintainer's machines), and the P2P address differs from the adapter MAC only in the
  first byte, so before this fix the output of these scripts with `sudo` could reveal the
  adapter MAC (`e9847af`).
- The README's Verify section and the manual smoke test in CONTRIBUTING.md suggest
  `nmcli --ask device wifi connect`. The `password "<...>"` form they suggested before
  fails with `802-11-wireless-security.key-mgmt: property is missing` when the network
  already has a saved profile (reproduced with NetworkManager 1.52.1 on Debian 13).

### Added

- `uninstall.sh`, with `--dry-run` (`fc5165c`).
- `scripts/hw-smoke.sh`: a read-only hardware report that is safe to paste (`d71626c`).
- `scripts/privacy-scan.sh`: checks tracked files and commit messages for personal
  identifiers (`4d28f15`).
- Tests: static checks of the mode-switch configuration and udev rules (`7dcbdec`),
  installer and uninstaller safety tests (`4bc0322`), a check of the shared output
  filter (`145d0d6`, run against every copy since `e9847af`), install/uninstall runs in five distribution containers
  (`4d510f2`), a compile-only build matrix (`042e10d`), a `Makefile` (`2063cc7`) and a
  GitHub Actions workflow (`27e036d`). Upstream's installer tests were updated for the
  changed behaviour (`2b40691`). `DESTDIR` lets the tests redirect the scripts' writes
  (`ed0cf7f`).
- Documentation: rewritten `README.md`, corrected `NOTICE.md`, `MACBOOK.md` limited to
  what has been observed, `docs/mode-switch.md`, `CONTRIBUTING.md`, `KNOWN_ISSUES.md`,
  `ROADMAP.md` and this file.
- GitHub issue forms (bug report, new hardware report, feature request) and a pull
  request template.
- Hardware results for the late-2007 MacBook on Linux 6.12.113 and 6.12.115 (installer
  revisions `4b99e2f` and `e5843a4`) in `README.md`, `MACBOOK.md` and `KNOWN_ISSUES.md`.

## 2026-08-02

- First commit (`d309ff7`): a copy of upstream's `bluetooth` branch at `8006daf`
  (according to its commit message, recovered from an installed DKMS tree), plus `README.md`, `NOTICE.md`, `LICENSE`,
  `MACBOOK.md` and `.gitignore`. The README and NOTICE in that commit wrongly presented
  the `1111:1111` mode switch, the udev rules and the installer as original work; see
  [NOTICE.md](NOTICE.md).
