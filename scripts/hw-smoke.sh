#!/bin/bash
#
# Hardware smoke test for AIC8800 USB adapters.
#
# Prints a report that is safe to paste into a public issue: USB IDs and
# product strings, the hub chain, which driver each interface is bound to,
# whether a Wi-Fi interface and a Bluetooth controller exist, and recent
# kernel log lines. MAC addresses, serial numbers, IP addresses, the user
# name, the host name and home directory paths are masked.
#
# Usage:
#   ./scripts/hw-smoke.sh            # without kernel log lines
#   sudo ./scripts/hw-smoke.sh       # include kernel log lines
#
# Environment:
#   SMOKE_LOG_LINES=N   number of kernel log lines to show (default 40)
#   TEST_KO_DIR=DIR     report whether the loaded modules are the ones built in DIR
#   AIC_DIAG_RAW=1      disable masking (for local debugging only)
#
# This script only reads system state; it changes nothing.

set -u

sanitize_output() {
    if [ "${AIC_DIAG_RAW:-0}" = 1 ]; then
        cat
        return
    fi
    local user="${SUDO_USER:-${USER:-}}" host
    host="$(hostname 2> /dev/null || true)"
    local -a expr=(
        -e 's/([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}/<MAC>/g'
        -e 's/wlx[0-9A-Fa-f]{12}/wlx<MAC>/g'
        -e 's/(Serial(Number)?[=: ]+)[^ ,]+/\1<SERIAL>/g'
        -e 's#/home/[^/[:space:]]+#/home/<user>#g'
        -e 's/(^|[^0-9.])([0-9]{1,3}\.){3}[0-9]{1,3}($|[^0-9.])/\1<IP>\3/g'
    )
    if [ -n "$user" ] && [ "$user" != root ]; then
        expr+=(-e "s/\\b${user}\\b/<user>/g")
    fi
    if [ -n "$host" ]; then
        expr+=(-e "s/\\b${host}\\b/<host>/g")
    fi
    sed -E "${expr[@]}"
}

driver_of() {
    basename "$(readlink "$1/driver" 2> /dev/null)" 2> /dev/null
}

report() {
    echo "kernel: $(uname -r)"
    echo "secure_boot: $( (mokutil --sb-state 2> /dev/null || echo unknown) | head -1)"
    local r rules=""
    for r in /etc/udev/rules.d/aic.rules /usr/lib/udev/rules.d/aic.rules /lib/udev/rules.d/aic.rules; do
        # /lib and /usr/lib are the same directory on merged-/usr systems.
        [ -f "$r" ] && [[ " $rules " != *" $(readlink -f "$r") "* ]] && rules="$rules $(readlink -f "$r")"
    done
    echo "aic.rules installed:${rules:- none}"

    echo "== USB devices (AIC-related)"
    local found=0 d id p chain i
    for d in /sys/bus/usb/devices/*; do
        [ -f "$d/idVendor" ] || continue
        id="$(cat "$d/idVendor"):$(cat "$d/idProduct")"
        case "$id" in
            1111:1111 | a69c:* | 368b:* | 2604:*) ;;
            *) continue ;;
        esac
        found=1
        echo "$id bcdDevice=$(cat "$d/bcdDevice") product=\"$(cat "$d/product" 2> /dev/null)\" speed=$(cat "$d/speed")M port=$(basename "$d")"
        p=$(dirname "$(readlink -f "$d")")
        chain=""
        while [ -f "$p/idVendor" ]; do
            chain="$chain <- $(cat "$p/idVendor"):$(cat "$p/idProduct") \"$(cat "$p/product" 2> /dev/null)\" port=$(basename "$p")"
            p=$(dirname "$p")
        done
        echo "  parents:${chain:- (none)}"
        for i in "$d"/"$(basename "$d")":*; do
            [ -d "$i" ] || continue
            local drv
            drv=$(driver_of "$i")
            echo "  interface ${i##*:} class=$(cat "$i/bInterfaceClass") driver=${drv:-<none>}"
        done
    done
    [ "$found" = 1 ] || echo "(none)"

    echo "== modules"
    local m src origin ko
    for m in aic_load_fw aic8800_fdrv aic_zlp_quirk btusb; do
        if [ -d "/sys/module/$m" ]; then
            src=$(cat "/sys/module/$m/srcversion" 2> /dev/null)
            origin=""
            if [ -n "${TEST_KO_DIR:-}" ]; then
                ko=$(find "$TEST_KO_DIR" -name "$m.ko" 2> /dev/null | head -1)
                if [ -z "$ko" ]; then
                    origin=" (stock/system module)"
                elif [ "$(modinfo -F srcversion "$ko" 2> /dev/null)" = "$src" ]; then
                    origin=" (matches TEST_KO_DIR build)"
                else
                    origin=" (NOT the TEST_KO_DIR build)"
                fi
            fi
            echo "$m: loaded$origin"
        else
            echo "$m: not loaded"
        fi
    done

    echo "== wireless interfaces"
    local n dev drv
    for n in /sys/class/net/*; do
        [ -d "$n/wireless" ] || [ -d "$n/phy80211" ] || continue
        dev="$n/device"
        drv=$(driver_of "$dev")
        # USB drivers that register the netdev on the USB device itself show
        # up as "usb"; report the driver of the vendor-class interface instead.
        if [ "$drv" = usb ]; then
            for i in "$dev"/*:*; do
                [ "$(cat "$i/bInterfaceClass" 2> /dev/null)" = ff ] && drv=$(driver_of "$i")
            done
        fi
        echo "$(basename "$n") driver=${drv:-?} operstate=$(cat "$n/operstate")"
    done

    echo "== bluetooth"
    local h
    for h in /sys/class/bluetooth/hci*; do
        [ -e "$h" ] || {
            echo "(no controller)"
            break
        }
        echo "$(basename "$h") bus_driver=$(driver_of "$h/device")"
    done
    if command -v hciconfig > /dev/null; then
        hciconfig 2> /dev/null | grep -E '^hci|UP|DOWN'
    fi

    if [ "$(id -u)" = 0 ]; then
        local lines="${SMOKE_LOG_LINES:-40}"
        echo "== kernel log (last $lines AIC/USB-related lines)"
        dmesg | grep -iE 'aic|rwnx|1111|a69c|usb_modeswitch|btusb|usb-storage|usbfs|scsi|New USB device|USB disconnect|hub ' |
            grep -viE 'SerialNumber' | tail -n "$lines"
    else
        echo "(run with sudo to include kernel log lines)"
    fi
}

report 2>&1 | sanitize_output
