# Provenance and licensing

## Summary

This repository is a **downstream copy of
[shenmintao/aic8800d80](https://github.com/shenmintao/aic8800d80)**, not an
independent driver. The driver, its firmware, the installer, the udev rules and the
`1111:1111` mode-switch configuration all come from upstream or from AICSemi.

What this repository adds is listed in [What this repository adds](#what-this-repository-adds):
safety fixes to upstream's scripts, an uninstaller, a test suite, a hardware smoke
test, and documentation, including hardware findings for one clone dongle. Everything
else is someone else's work, credited below.

## Chain of origin

1. **AICSemi** wrote the `aic8800` driver for its chipset family and released it as
   Linux kernel source. Both main modules declare `MODULE_LICENSE("GPL")`.
2. The **Tenda U11** vendor driver drop is the code upstream started from (upstream
   commit `1d404e3`, "init: add source codes from tenda", 2024-12-18).
3. **[shenmintao/aic8800d80](https://github.com/shenmintao/aic8800d80)** carried it
   forward to current kernels, with contributions from many people (see
   [Credits](#credits)). Its README says plainly that its author did not develop the
   driver either.
4. **This repository** was first published (commit `d309ff7`, 2026-08-02) as a copy of
   upstream's `bluetooth` branch at commit `8006daf` (now tag `archive/bluetooth-final`
   upstream). Apart from `README.md`, `NOTICE.md`, `LICENSE`, `MACBOOK.md` and
   `.gitignore`, every file was byte-for-byte identical to that commit. It was imported
   without upstream's history.
5. On 2026-11-01 it was re-synced onto upstream `main` at commit `fab5be8` with a merge
   that brings in upstream's full history, so `git log` shows upstream's authors for
   upstream's files.
6. On 2026-11-02 upstream `main` at `2e75f88` was merged. Upstream had by then adopted
   parts of this repository's installer and udev fixes in its own PR
   [#131](https://github.com/shenmintao/aic8800d80/pull/131).

## Where each part comes from

| Part | Origin | Evidence |
|---|---|---|
| `drivers/` | AICSemi, by way of the Tenda U11 drop, maintained upstream | upstream history; identical to upstream at the sync point except where noted in [CHANGELOG.md](CHANGELOG.md) (no driver source changes so far) |
| `fw/` | AICSemi binary firmware, distributed by upstream | identical to upstream |
| `install.sh`, `diagnostic_build.sh`, `dkms.conf`, `INSTALL_SCRIPT.md` | written by upstream contributor Spacery (December 2025), extended by Shen Mintao | upstream commits `d685d20`, `6cefc43`; the Portuguese header ("VERSÃO CORRIGIDA", "Version 2.0.4") is from `6cefc43` |
| `aic.rules` | the Tenda drop, extended by Shen Mintao (the `1111:1111` rule, 2026-02-27) and Jonatas Fischer (the `a69c:572c` rule); the restriction to 88M80 adapters and whole-disk events was proposed here and adopted upstream | upstream commits `1d404e3`, `8b90bd8`, `9f05f51`, `e2c5835` |
| `usb_modeswitch/1111_1111` | Shen Mintao, upstream (2026-02-27, two-stage F3 then F2 since 2026-08-17) | upstream commits `8b90bd8`, `b0787d9`, `3050506`; see [docs/mode-switch.md](docs/mode-switch.md) for where the commands come from |
| `diagnose_bt.sh` | Shen Mintao, upstream | upstream commit `cf63c8e` |
| `bazzite/` | Nurmukhamed Artykaly, with Shen Mintao, ccyuen1 and heydemoura, upstream | upstream history |
| `aicrf_test/`, `release_note.txt` | the Tenda drop | upstream commit `1d404e3` |
| `AGENTS.md`, `INSTALL_ARCH.md`, `OPENWRT.md`, `tests/firmware/`, `tests/installer/test_install.py`, `tests/installer/test_udev.py`, `tests/issue63-zlp-quirk/`, `tests/openwrt-backports/`, `tests/unified-wifi-bt/` | upstream | upstream history |
| `LICENSE` | the GPL-2.0 text; added here in `d309ff7` and later added upstream as well (`b7a476c`); the two copies are identical | `git diff` |

### The `1111:1111` mode switch is not original to this repository

Earlier versions of this README and NOTICE described the `1111:1111` mode switch and its
udev rule as this repository's contribution. That was wrong: the configuration file in
the first commit here was a copy of upstream's. How the original owner of this
repository came across it is not recorded. Nothing found suggests it was worked out
independently, and the file matches upstream's byte for byte. The public history of the
commands is in [docs/mode-switch.md](docs/mode-switch.md).

## Credits

Upstream maintainer: **Shen Mintao**. Authors of non-merge commits in upstream's history
up to `2e75f88`, by area:

- Driver: Shen Mintao, vorasilp, nomdetom, Lucas Kawatoko (the Linux 6.12.101
  `set_monitor_channel` fix), MastaG (Linux 7.3 cfg80211 changes), YaQia,
  xuxinchun1003, Vladislav Tatyanin, toor11
- Bluetooth through the standard `btusb` driver: bnister
  ([upstream PR #35](https://github.com/shenmintao/aic8800d80/pull/35))
- Installer and DKMS configuration: Spacery, Shen Mintao, rtk94 (the log location, `33d33af`)
- udev rules: Shen Mintao, Jonatas Fischer
- Bazzite packaging: Nurmukhamed Artykaly, Shen Mintao, ccyuen1, heydemoura
- Arch Linux notes: Wennington123

The `1111:1111` mode-switch commands were first published by a5a5aa555oo in
[radxa-pkg/aic8800#68](https://github.com/radxa-pkg/aic8800/issues/68#issuecomment-3731512432);
olamellberg's reverse engineering of the Windows driver
([olamellberg/AIC8800D80](https://github.com/olamellberg/AIC8800D80)) identifies the
`F2` command as the one the Windows driver uses to switch modes.

## What this repository adds

All changes are on top of upstream `main` at `2e75f88`. Details and commits are in
[CHANGELOG.md](CHANGELOG.md).

- **Fixes to upstream's scripts and rules**: the installer test-builds the driver
  before changing the system, backs up firmware instead of deleting it and leaves
  package-owned firmware alone, installs kernel headers that follow kernel upgrades,
  writes its log to `/var/log` instead of a world-writable `/tmp` file, installs udev
  rules under `/etc`, and handles Secure Boot prompts without a terminal correctly. The
  `1111:1111` udev rule only acts on 88M80 adapters. The diagnostic scripts mask
  personal identifiers. Upstream adopted the test build, the log location and the udev
  rule changes in its PR #131 (2026-11-02); the rest is offered in upstream PRs #128
  and #130.
- **New files**: `uninstall.sh`, `scripts/hw-smoke.sh`, `scripts/privacy-scan.sh`,
  `Makefile`, `tests/static/`, `tests/installer/test_install_safety.py`,
  `tests/distros/`, `tests/build/`, `.github/`, and the documentation files
  (`README.md`, `NOTICE.md`, `MACBOOK.md`, `CONTRIBUTING.md`, `KNOWN_ISSUES.md`,
  `ROADMAP.md`, `CHANGELOG.md`, `docs/`).
- **Hardware findings** for one dongle, recorded in [README.md](README.md) and
  [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

## License

The driver source is **GPL-2.0**. This is not a choice this project made: the code
descends from GPL vendor source and its modules declare `MODULE_LICENSE("GPL")`, so the
license carries forward. The full text is in [LICENSE](LICENSE).

There is also a written record of the vendor's position: Radxa's commit
[`969601f`](https://github.com/radxa-pkg/aic8800/commit/969601fd69b5c33f965558c9e90633067733e8c1)
(2025-09-17), which adds the GPLv2 license to its copy of the AIC driver source, states
that "AIC has agreed to include GPLv2 notice in future code releases". Upstream's README
cites the same commit.

Upstream states the driver source is `GPL-2.0-only`. Files written for this repository,
and this repository's changes to upstream's files, are distributed under the same terms,
`GPL-2.0-only`, so that they can be contributed upstream without a license change.

## Firmware blobs

The files under `fw/` are **proprietary binary firmware** produced by AICSemi. They are:

- not covered by the GPL-2.0 license above,
- shipped without any explicit redistribution grant,
- redistributed here because there is no other way to make the hardware function, and
  because other packagings of this driver do the same (upstream, and
  [radxa-pkg/aic8800](https://github.com/radxa-pkg/aic8800), which ships the same
  firmware directories).

This is the same posture as most out-of-tree wireless drivers, but it is a posture, not
a permission. Anyone redistributing this tree, including in a distro package, is
adopting it knowingly. If AICSemi objects, the firmware should be removed and users
directed to extract it from the vendor Windows driver themselves.

## Commit references

Commit IDs without a link are in this repository's history (`git show <id>`). Four
upstream commits cited above are on upstream's archived `bluetooth` branch (tag
`archive/bluetooth-final`) rather than in `main`'s history, so they are not in this
repository: [`8006daf`](https://github.com/shenmintao/aic8800d80/commit/8006daf), [`8b90bd8`](https://github.com/shenmintao/aic8800d80/commit/8b90bd8), [`b0787d9`](https://github.com/shenmintao/aic8800d80/commit/b0787d9)
and [`cf63c8e`](https://github.com/shenmintao/aic8800d80/commit/cf63c8e).
