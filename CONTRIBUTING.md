# Contributing

Thanks for helping. This repository is a downstream copy of
[shenmintao/aic8800d80](https://github.com/shenmintao/aic8800d80). Problems in the
driver itself (crashes, firmware errors, connection problems that also happen with
upstream's code) are best reported upstream, where the driver is maintained. Problems
with this repository's installer, uninstaller, udev rules, tests or documentation, and
reports of new hardware, belong here.

## Before you post anything: clean your logs

Logs from Wi-Fi and USB tools contain identifiers you should not post publicly: MAC
addresses (also inside `wlx...` interface names), USB serial numbers, IP addresses,
network names (SSIDs), your user name, host name and home directory.

- `scripts/hw-smoke.sh`, `diagnose_bt.sh` and `diagnostic_build.sh` mask these for you.
  Still read their output before posting; the masking catches the common formats, not
  every possible one.
- Do **not** post raw output of `ip a`, `iw dev`, `nmcli`, `hciconfig -a`,
  `bluetoothctl show`, `lsusb -v` or a full `dmesg` without editing it. Replace
  identifiers with placeholders such as `<MAC>`, `<SERIAL>` or `<SSID>`.
- Never post a Wi-Fi password.

## Reporting a bug

Open an issue with the bug report template and include:

1. Distribution and version (`grep PRETTY_NAME /etc/os-release`) and kernel (`uname -r`).
2. How you installed (`sudo ./install.sh`, or something else) and the revision
   (`git rev-parse --short HEAD`, or `cat /usr/src/aic8800-1.0.0/SOURCE_REVISION`).
3. The output of `sudo ./scripts/hw-smoke.sh` with the adapter plugged in.
4. For install or build failures: the output of `sudo ./diagnostic_build.sh`, and the
   end of `/var/log/aic8800-install.log`.
5. For Bluetooth problems: the output of `sudo ./diagnose_bt.sh`.
6. What you expected and what happened instead.

## Reporting new hardware

If your adapter is not in the README's table, or behaves differently from what it says,
open an issue with the new hardware template and include:

- the output of `sudo ./scripts/hw-smoke.sh` (USB IDs, product strings, hub chain,
  which drivers bound), before and, if anything changes, a minute after plugging in;
- the product name and where it was sold, if you know;
- whether Wi-Fi and Bluetooth work.

For an adapter that stays at `1111:1111`, also say which mode-switch commands you tried
(see [docs/mode-switch.md](docs/mode-switch.md)) and what `usb_modeswitch` printed.

## Running the tests

```bash
make test              # lint, unit tests and privacy scan; no root, no network
make test-build        # compile against the installed headers for the running kernel
make test-build-matrix # compile against several distributions' headers (Docker or Podman, network)
make test-distros      # run install.sh and uninstall.sh in five distribution containers (Docker or Podman, network, slow)
```

`make test` needs `python3`, `bash`, `git` and `shellcheck`; `shfmt` and a `udevadm`
from systemd 254 or later are used when present. The tests never need root and never
change the system: `install.sh` and `uninstall.sh` are run against a temporary
`DESTDIR` with every system-changing command replaced by a stub, or inside unprivileged
containers that cannot load kernel modules. `make test` must pass before a change is
merged.

The privacy scan also reads a local denylist, `~/.config/aic8800-privacy-denylist` (one
string per line, for example your user name, host name and device MACs), if you create
one. Keep that file out of the repository.

## Manual hardware smoke test

CI cannot test hardware. Before claiming that a change works on an adapter, or adding a
row to the README's table, run these steps and attach the cleaned output:

1. Install: `sudo ./install.sh`, then reboot or replug the adapter.
2. Plug the adapter **directly** into the computer (not through a hub), wait about 15
   seconds, and run `sudo ./scripts/hw-smoke.sh`. Expected: `a69c:8d81` with
   `aic8800_fdrv` on the vendor-class interface and `btusb` on the Bluetooth
   interfaces, a `wlx<MAC>` interface and `hci0` present.
3. Unplug, wait 5 seconds, plug back in, and run it again: the result must be the same.
4. Connect to a throwaway network (a phone hotspot is fine) with
   `nmcli device wifi connect "<SSID>" password "<PASSWORD>" ifname <WLX_INTERFACE>`,
   then check traffic through the adapter only:
   `ping -c 4 -I <WLX_INTERFACE> 9.9.9.9`. Report only whether it connected and the
   ping summary line, then delete the connection with
   `nmcli connection delete "<SSID>"`.
5. Bluetooth: `bluetoothctl show` should list the controller as powered (do not post
   its address). Optionally pair a device and say whether it worked.
6. Record the kernel (`uname -r`), the distribution and the revision you tested.

## Changing the code

- Work on a branch and keep commits small, with plain imperative commit messages that
  explain why.
- `drivers/` and `fw/` are upstream's. Change driver source only when needed for kernel
  compatibility, explain each change in the commit message, and do not reformat it.
  Driver fixes are better sent upstream.
- `install.sh`, `aic.rules`, `diagnose_bt.sh` and `diagnostic_build.sh` are upstream
  files with local fixes. Keep changes small so later syncs with upstream merge
  cleanly, and record them in [CHANGELOG.md](CHANGELOG.md).
- Every factual claim in the documentation must be checkable. If something has not
  been tested, say "untested".
- Add or update tests for behaviour you change.

## Syncing with upstream

```bash
git remote add upstream https://github.com/shenmintao/aic8800d80.git   # once
git fetch upstream
git switch -c sync/upstream-<DATE> main
git merge upstream/main
make test && make test-build
```

Resolve conflicts in favour of upstream for driver and firmware files, keep this
repository's fixes in the scripts and rules (see [CHANGELOG.md](CHANGELOG.md)), and open
a pull request.
