# Roadmap

Planned work, roughly in order of priority. Nothing here has a date. Each item links
its GitHub issue. Known problems are in
[KNOWN_ISSUES.md](KNOWN_ISSUES.md).

## Next

- **Offer the installer and rule fixes upstream.** The fixes listed in
  [CHANGELOG.md](CHANGELOG.md) are meant for
  [shenmintao/aic8800d80](https://github.com/shenmintao/aic8800d80) as well, so that this
  repository does not drift from it. [#14](https://github.com/rtk94/aic8800d80-clone-dongle/issues/14)
- **Run the current installer on real hardware**, on the maintainer's main computer and
  MacBook, and update the README's table. [#1](https://github.com/rtk94/aic8800d80-clone-dongle/issues/1)
- **Measure throughput** on the main computer and on the USB 2.0 MacBook
  ([procedure](MACBOOK.md#measure-throughput)). [#8](https://github.com/rtk94/aic8800d80-clone-dongle/issues/8)

## Installer

- **Make the DKMS step recoverable**: keep the previous DKMS installation until the new
  one is installed, or restore the firmware backup automatically if a later step fails.
  [#9](https://github.com/rtk94/aic8800d80-clone-dongle/issues/9)
- **Give the DKMS package a real version** derived from the source revision, so
  `dkms status` shows what is installed. [#10](https://github.com/rtk94/aic8800d80-clone-dongle/issues/10)
- **Secure Boot signing helper**: detect whether DKMS will sign the modules and which
  key it uses, and print the exact enrollment command for the distribution.
  [#7](https://github.com/rtk94/aic8800d80-clone-dongle/issues/7)

## Driver compatibility

- **Feature detection for the remaining version checks**: select `MODULE_IMPORT_NS`
  by what the kernel headers provide rather than by version number, as upstream already
  does for `set_monitor_channel`. This is driver code, so it belongs upstream.
  [#12](https://github.com/rtk94/aic8800d80-clone-dongle/issues/12)

## Test coverage

- **More kernels in the build matrix**: Ubuntu's HWE kernel, Debian backports, the
  previous Fedora release, Arch's `linux-lts` (which also exercises the installer's
  `pkgbase` lookup), and a 32-bit build. [#15](https://github.com/rtk94/aic8800d80-clone-dongle/issues/15), [#16](https://github.com/rtk94/aic8800d80-clone-dongle/issues/16), [#17](https://github.com/rtk94/aic8800d80-clone-dongle/issues/17), [#18](https://github.com/rtk94/aic8800d80-clone-dongle/issues/18)
- **CI on GitHub**: confirm the workflow runs green on GitHub itself; it has so far
  only been run locally. (checked when the branches are first pushed)

## Hardware support

- **Collect reports of other clone IDs**: `1111:1111` variants (with their product
  strings and whether a mode switch is needed) and `a69c:57xx` mass-storage IDs, so the
  udev rules can be checked against real devices. [#19](https://github.com/rtk94/aic8800d80-clone-dongle/issues/19)
- **Settle the 88M80 switch sequence** (`F3` then `F2`, or `F2` with a USB reset). This
  needs someone with an 88M80 adapter. [#3](https://github.com/rtk94/aic8800d80-clone-dongle/issues/3)

## Packaging

- **Packages for other distributions** (a `.deb`, an RPM spec for this repository's
  code, an AUR `PKGBUILD`). [#20](https://github.com/rtk94/aic8800d80-clone-dongle/issues/20)
