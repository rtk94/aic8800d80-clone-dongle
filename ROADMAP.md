# Roadmap

Planned work, roughly in order of priority. Nothing here has a date. `<ISSUE_TBD>`
marks items whose GitHub issue has not been created yet. Known problems are in
[KNOWN_ISSUES.md](KNOWN_ISSUES.md).

## Next

- **Offer the installer and rule fixes upstream.** The fixes listed in
  [CHANGELOG.md](CHANGELOG.md) are meant for
  [shenmintao/aic8800d80](https://github.com/shenmintao/aic8800d80) as well, so that this
  repository does not drift from it. `<ISSUE_TBD>`
- **Run the current installer on real hardware**, on the maintainer's main computer and
  MacBook, and update the README's table. `<ISSUE_TBD>`
- **Measure throughput** on the main computer and on the USB 2.0 MacBook
  ([procedure](MACBOOK.md#measure-throughput)). `<ISSUE_TBD>`

## Installer

- **Make the DKMS step recoverable**: keep the previous DKMS installation until the new
  one is installed, or restore the firmware backup automatically if a later step fails.
  `<ISSUE_TBD>`
- **Give the DKMS package a real version** derived from the source revision, so
  `dkms status` shows what is installed. `<ISSUE_TBD>`
- **Secure Boot signing helper**: detect whether DKMS will sign the modules and which
  key it uses, and print the exact enrollment command for the distribution.
  `<ISSUE_TBD>`

## Driver compatibility

- **Feature detection for the remaining version checks**: select `MODULE_IMPORT_NS`
  by what the kernel headers provide rather than by version number, as upstream already
  does for `set_monitor_channel`. This is driver code, so it belongs upstream.
  `<ISSUE_TBD>`

## Test coverage

- **More kernels in the build matrix**: Ubuntu's HWE kernel, Debian backports, the
  previous Fedora release, Arch's `linux-lts` (which also exercises the installer's
  `pkgbase` lookup), and a 32-bit build. `<ISSUE_TBD>`
- **CI on GitHub**: confirm the workflow runs green on GitHub itself; it has so far
  only been run locally. `<ISSUE_TBD>`

## Hardware support

- **Collect reports of other clone IDs**: `1111:1111` variants (with their product
  strings and whether a mode switch is needed) and `a69c:57xx` mass-storage IDs, so the
  udev rules can be checked against real devices. `<ISSUE_TBD>`
- **Settle the 88M80 switch sequence** (`F3` then `F2`, or `F2` with a USB reset). This
  needs someone with an 88M80 adapter. `<ISSUE_TBD>`

## Packaging

- **Packages for other distributions** (a `.deb`, an RPM spec for this repository's
  code, an AUR `PKGBUILD`). `<ISSUE_TBD>`
