# Notes for an older polycarbonate MacBook

The maintainer has run this adapter on a late-2007 black polycarbonate MacBook
(2.4 GHz Core 2 Duo, 2 GB of RAM, shipped with Mac OS X 10.5 Leopard) running Debian 13
(x86_64), with the older code this repository carried before the 2026-11-01 sync
(kernels 6.12.101 and 6.12.107). Its model identifier has not been checked. The current
code has not been run on it yet.

## What to expect

This MacBook only has USB 2.0, whose signalling rate is 480 Mb/s. Real throughput
through a USB 2.0 Wi-Fi adapter is lower than that, whatever rate the radio reports.
**How much lower has not been measured on this machine;** see
[Measure throughput](#measure-throughput). Do not expect Wi-Fi 6 speeds.

## Before you start

1. **Use a wired connection for the install.** The installer downloads packages, and
   the adapter has no driver until it finishes. The built-in Ethernet port works, as
   does USB tethering from a phone.
2. **Check the architecture:**
   ```bash
   uname -m        # x86_64 or i686
   ```
   Everything here was done on `x86_64`. Some early Intel Macs have 32-bit EFI firmware,
   which makes installing a 64-bit system harder; check your model. Debian 13 has no
   i386 kernel or installer, so a 32-bit system means an older release or another
   distribution. The driver's Makefile maps `i?86` to `i386`, but **a 32-bit build has
   not been tried.**

## Install

Follow the [README](README.md#install): `sudo ./install.sh`. It installs the headers
metapackage (`linux-headers-amd64` on Debian). That matters on this machine in
particular: on the MacBook the metapackage was missing, so after a kernel update from
6.12.101 to 6.12.107 DKMS had no headers to build against, skipped the rebuild without
any error, and the adapter stopped working until the headers were installed.

## Things seen on the MacBook

- **NetworkManager switched the default route to the dongle** as soon as it connected,
  so the laptop's address changed and an SSH session to it dropped. If you work on the
  machine over SSH, expect that, or lower the dongle connection's priority.
- **`dkms` is in `/usr/sbin`**, which is not on the `PATH` of non-interactive SSH
  sessions, so `ssh <host> dkms status` reports "command not found". Use
  `ssh <host> sudo dkms status`.
- **The built-in Wi-Fi card** (a Broadcom card on this machine, according to the
  maintainer's earlier notes) stays present. To keep NetworkManager from using it, you
  can unload and blacklist its driver; which driver that is depends on the card and on
  what is installed (`lspci -k` shows it).

## Measure throughput

Not done yet; tracked in [ROADMAP.md](ROADMAP.md). Install `iperf3` on the MacBook and
on another machine on the same network, start `iperf3 -s` on the other machine, then on
the MacBook:

```bash
iperf3 -c <SERVER_ADDRESS> -t 30          # MacBook sends
iperf3 -c <SERVER_ADDRESS> -t 30 -R       # MacBook receives
```

Run each a few times, close to the access point, and note the access point's band and
channel width. Watch CPU use during the transfer (`top`): on a Core 2 Duo the CPU may
be the limit rather than the USB bus, and this shows which. Please post results in an issue (see [CONTRIBUTING.md](CONTRIBUTING.md)).
