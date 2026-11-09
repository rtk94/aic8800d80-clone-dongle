# Known issues

Problems and gaps that are known but not fixed. Each entry says how sure we are and
what evidence there is. Planned improvements are in [ROADMAP.md](ROADMAP.md).
Each entry links its GitHub issue where there is one.

## Coverage gaps

### Hardware testing covers one adapter on two kernels
The current code has been run on real hardware only on Debian 13 with Linux 6.12.113
and 6.12.115, on two machines, with one dongle (`a69c:8d80` / `a69c:8d81` behind an
internal `214b:7250` hub). Every other kernel in the README's table is a compile or
container result only. Issue: [#2](https://github.com/rtk94/aic8800d80-clone-dongle/issues/2)

### The installer has been run on real hardware only on Debian 13
On the maintainer's main computer (Linux 6.12.115), `install.sh`, a reboot, a replug,
`uninstall.sh` and a reinstall all worked on 2026-11-02. On the late-2007 MacBook
(Linux 6.12.113 and 6.12.115), install, reboot, replug, a DKMS rebuild on a kernel update,
`uninstall.sh` and a reinstall worked. Other distributions have only been tested in unprivileged
containers, where kernel modules cannot be loaded.
Issue: [#2](https://github.com/rtk94/aic8800d80-clone-dongle/issues/2)

### The 88M80 `1111:1111` mode switch is untested here
No 88M80 adapter has been available. Upstream reports disagree on what works for units
with the same `bcdDevice` 10.01: one switched with `F3` then `F2` (the sequence used
here); another only switched with `F2` alone followed by a USB reset. The `F3` command
is also sent without a data phase, although the reverse-engineered Windows driver treats
it as a query that returns data. Details in [docs/mode-switch.md](docs/mode-switch.md).
Issue: [#3](https://github.com/rtk94/aic8800d80-clone-dongle/issues/3)

### The 88M80 rule only matches the product string `88M80`
To stop the rule from sending vendor commands to unrelated `1111:1111` devices, it now
requires the product string `88M80`. An 88M80 adapter that reports a different string
will not be switched automatically. Issue: [#4](https://github.com/rtk94/aic8800d80-clone-dongle/issues/4)

### The `a69c:57xx` eject rules are untested here
They come from upstream, and their syntax and intent are checked by tests, but no
adapter that starts as `a69c:5721` to `a69c:572f` or `a69c:5732` has been available.
Issue: [#5](https://github.com/rtk94/aic8800d80-clone-dongle/issues/5)

### Secure Boot is untested
The maintainer's machine has Secure Boot disabled. Signing the modules and enrolling a
key has not been tried with this repository. Issue: [#6](https://github.com/rtk94/aic8800d80-clone-dongle/issues/6)

### Throughput has not been measured
No throughput figures have been measured on any machine, including the USB 2.0 MacBook
described in [MACBOOK.md](MACBOOK.md). Issue: [#8](https://github.com/rtk94/aic8800d80-clone-dongle/issues/8)

### `chip_mcu_id=1` adapters need upstream's `legacy-mcu1` branch
Upstream says adapters whose driver log reports `chip_mcu_id=1` need its
[`legacy-mcu1`](https://github.com/shenmintao/aic8800d80/tree/legacy-mcu1) branch. This
repository only carries upstream `main`. The tested dongle reports
`chip_id=7, chip_mcu_id = 0` (kernel log, 2026-11-02), for which upstream says to use
`main`; it works with `main`.

## Installer

### A failure after the preflight build can still leave the system half changed
The installer now test-builds the driver before touching anything, so the common
failure (the source does not compile) leaves the system as it was. If something fails
later, for example `dkms install` itself, the old firmware has already been moved to
`/var/backups` and the old DKMS registration removed. The backup makes this recoverable
by hand but not automatic. Issue: [#9](https://github.com/rtk94/aic8800d80-clone-dongle/issues/9)

### The DKMS version is always `1.0.0`
`dkms status` cannot show which code is installed. The installer records the revision in
`/usr/src/aic8800-1.0.0/SOURCE_REVISION`, but that shows `unknown` when the source was
not a git checkout (for example a downloaded archive). Issue: [#10](https://github.com/rtk94/aic8800d80-clone-dongle/issues/10)

### No headers metapackage is found for some kernel flavours
On apt systems the installer derives the metapackage name from `uname -r` (for example
`linux-headers-amd64`, `linux-headers-generic`). If no such package exists, it only
warns, and DKMS will not rebuild after the next kernel update unless headers for that
kernel are installed by hand.

## Driver (upstream code)

### Compiler warnings on newer kernels
The driver code compiles without warnings against Debian 13 (6.12), Debian 12 (6.1) and
Ubuntu 24.04 (6.8) headers. Against Fedora 44 (7.2.13) and Arch Linux (7.2.14) headers
it produces `-Wimplicit-fallthrough` warnings in `rwnx_main.c` (4), `rwnx_msg_tx.c`
(2), `rwnx_tx.c` (1), `rwnx_txq.c` (1) and one reported inside the kernel's
`compiler.h`. The build succeeds in all cases. (The build matrix also counts notices
from the build environment, such as "the compiler differs from the one used to build
the kernel"; those are not about the driver code.) These are in the vendor code, which
this repository does not change except for kernel compatibility; they are best reported
upstream. Issue: [#11](https://github.com/rtk94/aic8800d80-clone-dongle/issues/11)

### Two `MODULE_IMPORT_NS` uses are still selected by kernel version
`rwnx_main.c` and `aic_bluetooth_main.c` choose between the quoted (Linux 6.13 and
later) and unquoted form of `MODULE_IMPORT_NS` with a `>= 6.13.0` version check. That is
correct for every kernel built so far, but would break on a distribution kernel older
than 6.13 that backports the change, the same way the `set_monitor_channel` check broke
on 6.12.101. Issue: [#12](https://github.com/rtk94/aic8800d80-clone-dongle/issues/12)

### Error-level log lines during normal operation
On every successful firmware load, `aic_load_fw` logs
`probe with driver aic_load_fw failed with error -1` for `a69c:8d81`, and the driver
logs `AICWFDBG(LOGERROR) Read FW mem: ...` lines. The first is deliberate: the loader
declines the device once the firmware is loaded so `aic8800_fdrv` can take it
(`aicwf_usb.c`, it returns `-1` instead of `-ENODEV`). The adapter works in both cases.
They are noise, not failures.

Two more error-level lines were seen on the MacBook (2026-11-02). Their causes were not
investigated, so treat them as unverified observations: the kernel's Bluetooth core
logged `hci0: Opcode 0x2037 failed: -38` (`-38` is `ENOSYS`, function not implemented)
once at boot and again after a replug, and Bluetooth worked anyway; and after Wi-Fi
scans the driver logged `rwnx_rx_scanu_start_cfm rwnx_hw->scan_request is NULL!!`.

## Licensing

### The firmware has no explicit redistribution grant
The binaries in `fw/` are AICSemi's and are redistributed without an explicit license.
See [NOTICE.md](NOTICE.md#firmware-blobs). Issue: [#13](https://github.com/rtk94/aic8800d80-clone-dongle/issues/13)
