# Installing on the 2008 polycarbonate MacBook

Target: black polycarbonate MacBook (MacBook4,1 / 3,1 / 2,1 era, Core 2 Duo).

## Before you start: what to expect

The dongle's Wi-Fi 6 radio **cannot deliver Wi-Fi 6 speeds on this machine.** These
MacBooks have USB 2.0 only — 480 Mb/s of signalling, which in practice means roughly
**150–250 Mb/s of real TCP throughput** through the USB stack, regardless of what the
radio negotiates. The link may report a 1200 Mb/s PHY rate; the bus is the ceiling.

It is still very likely worth doing:

- The built-in BCM4321 needs either `b43` (no usable 802.11n) or the out-of-tree `wl`
  blob (breaks on kernel updates, no WPA3).
- The AIC8800D80 gives you WPA3, reliable association with modern APs, clean 5 GHz,
  and 2–3× the practical throughput of a flaky 11n link.
- Bluetooth comes along for free via `btusb`.

So: expect "reliable ~200 Mb/s," not "Wi-Fi 6."

## Step 0 — bootstrap networking

The MacBook has no working Wi-Fi until this driver is built, and you need the network
to install the build tools. **Use the built-in Gigabit Ethernet port** for the install.
(Alternatively, tether a phone over USB.)

## Step 1 — check what you're running

```bash
uname -r                    # kernel version
uname -m                    # x86_64 or i686
cat /etc/os-release         # distro
```

`uname -m` matters. All Core 2 Duo MacBooks are 64-bit capable, but these machines have
**32-bit EFI**, so many people end up on a 32-bit install. If you see `i686`:

- The driver source is architecture-neutral and the Makefile already maps `i.86` → `i386`,
  so it should build — but this combination is far less tested than x86_64. Budget time
  for compile errors on 32-bit.
- Debian 13 no longer ships an i386 kernel/installer. If you're on 32-bit you're on
  Debian 12, MX/antiX, or similar.

If you're on `x86_64`, this is the same path that already works on the desktop.

## Step 2 — install build dependencies

```bash
# Debian / Ubuntu / MX / antiX
sudo apt update
sudo apt install -y dkms build-essential linux-headers-$(uname -r) \
                    usb-modeswitch usbutils rfkill wireless-tools

# Fedora
sudo dnf install -y dkms kernel-devel-$(uname -r) gcc make usb_modeswitch usbutils

# Arch
sudo pacman -S --needed dkms base-devel linux-headers usb_modeswitch usbutils
```

The critical one is `linux-headers-$(uname -r)` — it must match the **running** kernel
exactly, not just "the latest headers."

## Step 3 — run the installer

From this directory, on the MacBook:

```bash
sudo ./install.sh
```

It detects the package manager, removes conflicting `aic8800*` firmware directories,
installs firmware to `/lib/firmware`, the udev rules to `/lib/udev/rules.d/`, the
mode-switch config to `/etc/usb_modeswitch.d/1111:1111`, registers the tree with DKMS,
and builds.

## Step 4 — verify

```bash
lsusb                       # before: 1111:1111  -> after modeswitch: a69c:8d80/8d81/8d83
lsmod | grep aic            # aic8800_fdrv + aic_load_fw loaded
ip link                     # a new wlanN interface
dmesg | grep -iE 'aic|rwnx' # firmware load messages
hciconfig -a                # Bluetooth hci0
```

## Step 5 — measure, so the USB 2.0 ceiling is a known quantity, not a surprise

```bash
iperf3 -c <a machine on your LAN>       # expect ~150-250 Mb/s
```

Also watch CPU during a transfer — a Core 2 Duo pushing 200 Mb/s through a
software-heavy USB Wi-Fi driver will show real load. If one core pegs, that's the
bottleneck, not the radio.

## MacBook-specific gotchas

- **Port choice.** Use the port *not* shared with the built-in iSight/keyboard hub if
  you see enumeration flakiness. Try both ports before concluding anything.
- **Power.** The dongle must stay within the 500 mA USB 2.0 budget. If you see random
  re-enumeration under load, a powered hub rules the power supply in or out.
- **Disable the built-in radio** once this works, so NetworkManager doesn't fight over
  the default route:
  ```bash
  sudo modprobe -r wl b43 b43legacy ssb 2>/dev/null
  echo -e "blacklist wl\nblacklist b43\nblacklist b43legacy" | sudo tee /etc/modprobe.d/blacklist-macbook-wifi.conf
  ```
- **Thermals.** These machines run hot and the GPU/CPU throttle. Sustained transfers on
  a 2008 chassis will heat-soak; that's the machine, not the driver.
- **Kernel updates** rebuild the module automatically via DKMS. Verify after each update
  with `sudo dkms status`.

## If the build fails on 32-bit

Capture the log and bring it back:

```bash
sudo dkms build aic8800/1.0.0 -k $(uname -r)
cat /var/lib/dkms/aic8800/1.0.0/build/make.log
```

The likely failure classes are 64-bit division on 32-bit (`__udivdi3` link errors) and
pointer/`int` cast warnings promoted to errors. Both are fixable in the source.
