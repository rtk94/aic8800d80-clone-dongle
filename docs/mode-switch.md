# How the `1111:1111` mode switch works

Some AIC8800D80 clone adapters, sold as "AX900" and reported with the product string
`88M80`, first appear on USB as `1111:1111`: a USB mass-storage device carrying the
Windows driver installer, with a placeholder vendor ID that no Linux driver claims. A
vendor-specific SCSI command switches them to the Wi-Fi/Bluetooth function. This
document describes that command, where it comes from, how this repository sends it, and
what is and is not known.

Not every adapter that shows `1111:1111` needs this. See
[An adapter that shows 1111:1111 but needs no switch](#an-adapter-that-shows-11111111-but-needs-no-switch).

## What the Windows driver does

[olamellberg/AIC8800D80](https://github.com/olamellberg/AIC8800D80) reverse-engineered
the Windows installer. Per its
[docs/windows-driver-analysis.md](https://github.com/olamellberg/AIC8800D80/blob/main/docs/windows-driver-analysis.md),
a service (`AicWifiService`) loads `Usb_Driver.dll`, finds the adapter's storage
interface, and calls `Set_CS1_0()`. That sends a SCSI command with opcode `0xFD` and
sub-command `0xF2` through the Windows SCSI pass-through interface. The service then
ejects the storage device and rescans USB. The same DLL has a function `GetHippo()` that
sends opcode `0xFD` with sub-command `0xF3`, described there as a device status query.

## The command on Linux

On Linux, [usb_modeswitch](https://www.draisberghof.de/usb_modeswitch/) sends the
command as a raw USB Mass Storage Bulk-Only Transport **Command Block Wrapper (CBW)**:
31 bytes written to the device's bulk OUT endpoint. `usb_modeswitch/1111_1111` contains
two of them, sent in order:

```text
MessageContent ="555342438765432100000000000010fd0000000000000000000000000000f3"
MessageContent2="555342438765432100000000000010fd0000000000000000000000000000f2"
```

| Bytes | Field | Value | Meaning |
|---|---|---|---|
| 0 to 3 | `dCBWSignature` | `55 53 42 43` | ASCII `USBC`, marks a CBW |
| 4 to 7 | `dCBWTag` | `87 65 43 21` | arbitrary tag, echoed back in the status reply |
| 8 to 11 | `dCBWDataTransferLength` | `00 00 00 00` | no data phase |
| 12 | `bmCBWFlags` | `00` | direction OUT (irrelevant with no data) |
| 13 | `bCBWLUN` | `00` | logical unit 0 |
| 14 | `bCBWCBLength` | `10` | the command block is 16 bytes |
| 15 to 30 | `CBWCB` | `FD 00 00 00 00 00 00 00 00 00 00 00 00 00 00 F3` (first), `... F2` (second) | the vendor command: opcode `FD`, sub-command in the last byte |

`tests/static/test_modeswitch.py` checks every one of these fields on each commit.
`NeedResponse=1` makes usb_modeswitch read the 13-byte status reply (CSW) after each
message. After a successful switch the adapter re-enumerates as `a69c:8d80` (the
`TargetProduct` in the file): a loader mode with no firmware. `aic_load_fw` then
uploads the firmware, and the adapter re-enumerates again as `a69c:8d81`, which
`aic8800_fdrv` and `btusb` bind to.

## Where the commands come from

- **2026-01-10:** a5a5aa555oo posted the two-message command (`F3`, then `F2`) as a
  working fix in
  [radxa-pkg/aic8800#68](https://github.com/radxa-pkg/aic8800/issues/68#issuecomment-3731512432).
  This is the earliest public source found. How they arrived at it is not stated there.
- **2026-02-27 and 2026-03-04:** Shen Mintao added a `1111:1111` usb_modeswitch
  configuration to upstream, at first sending only the `F2` command, with a corrected
  CBW a week later (upstream commits [`8b90bd8`](https://github.com/shenmintao/aic8800d80/commit/8b90bd8), [`b0787d9`](https://github.com/shenmintao/aic8800d80/commit/b0787d9)).
- **2026-08-17:** after
  [upstream issue #81](https://github.com/shenmintao/aic8800d80/issues/81), upstream
  switched to sending `F3` then `F2` (commit `3050506`). This repository uses that
  configuration.

The configuration in this repository's first commit was a copy of upstream's. Whether
its owner learned of it from upstream or elsewhere is not recorded.

## What is not known

- **Which sequence is right for which unit.** In upstream issue #81, one reporter's
  adapter (`bcdDevice` 10.01) switched with `F3` then `F2`. Another reporter, with the
  same `bcdDevice` and SCSI vendor string `LGX WIFI6 2.30`, found that `F3` then `F2`
  never switched it, while `F2` alone followed by a USB reset (`ResetUSB=1`) worked on
  every cold plug. The two reports have not been reconciled.
- **Whether `F3` is sent correctly.** The reverse-engineering notes describe `F3` as a
  query that returns data, but the CBW above declares no data phase. A device may reject
  that command (one reporter saw a failed status for it). This has not been tested.
- **Nothing in this section has been tested here.** No 88M80 adapter has been available
  to this repository. The `1111:1111` rule and configuration are upstream's and are
  checked only statically (`tests/static/`).

## The udev rule

`aic.rules` runs usb_modeswitch when a matching device is added:

```text
ACTION=="add", SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device",
ATTR{idVendor}=="1111", ATTR{idProduct}=="1111", ATTR{product}=="88M80*",
RUN+="... usb_modeswitch -b $attr{busnum} -g $attr{devnum} -c /etc/usb_modeswitch.d/1111:1111"
```

(shown wrapped; the rule is a single line). It matches the USB device itself rather than
its interfaces, only when the product string is `88M80`, and passes the bus and device
number so usb_modeswitch acts on the device that raised the event. The product match
was added here because `1111:1111` is used by other devices too, as the next section
shows. If your 88M80 adapter reports a different product string, the rule will not
match it; please report it (see [CONTRIBUTING.md](../CONTRIBUTING.md)).

## An adapter that shows `1111:1111` but needs no switch

The one dongle tested for this repository (an unbranded AIC8800D80 Wi-Fi 6 and
Bluetooth adapter) contains a small USB hub. Plugged directly into a computer, it shows
three devices:

```text
214b:7250  "USB2.0 HUB"     internal 4-port hub
  port 1:  a69c:8d80 "AIC Wlan", then a69c:8d81 "AIC 8800D80"   the Wi-Fi/BT function
  port 2:  1111:1111 "FLASH" (bcdDevice 10.01)                  a flash disk with the Windows installer
```

Observed on 2026-11-01 with Linux 6.12.113:

- The Wi-Fi function appears as `a69c:8d80` and `aic_load_fw` uploads the firmware
  **before** the `1111:1111` device has even enumerated. No mode switch is involved.
- The `1111:1111` device is an ordinary flash disk (SCSI vendor and model
  `FLASH UDISK 2.30`). `usb-storage` binds it and it appears as a removable disk.
- With the older upstream rule, which matched every `1111:1111` device, usb_modeswitch
  ran on this flash disk on every plug and left it with no driver bound. With that rule
  disabled, the disk stayed bound to `usb-storage` and Wi-Fi and Bluetooth were
  unaffected. The current rule's `88M80` product match no longer fires on it
  (checked with `udevadm test`).
