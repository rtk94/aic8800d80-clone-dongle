#!/bin/bash
#
# Runs inside a distribution container (started by tests/distros/run.sh).
# Installs the distribution's kernel headers, makes "uname -r" report that
# kernel, then runs install.sh twice and uninstall.sh once for real and
# checks the result. The container is unprivileged, so module loading fails
# and the host kernel is never touched; everything else runs as on a real
# system.
#
# Usage: in-container.sh <distro-id>   (source tree at /src, results to /out)

set -u
distro="$1"
out=/out
mkdir -p "$out"

log() { echo "[$distro] $*" | tee -a "$out/summary.txt"; }
fail() {
    log "FAIL: $*"
    cp /var/log/aic8800-install.log "$out/aic8800-install.log" 2> /dev/null || true
    exit 1
}

grep PRETTY_NAME /etc/os-release | tee "$out/os-release.txt" > /dev/null

# 1. Kernel headers for some kernel the distribution ships.
case "$distro" in
    debian | ubuntu)
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq > "$out/prep.log" 2>&1
        meta=linux-headers-amd64
        [ "$distro" = ubuntu ] && meta=linux-headers-generic
        apt-get install -y -qq "$meta" kmod >> "$out/prep.log" 2>&1 || fail "could not install $meta"
        ;;
    fedora)
        dnf install -y -q kernel-devel kmod > "$out/prep.log" 2>&1 || fail "could not install kernel-devel"
        ;;
    arch)
        pacman -Syu --noconfirm --needed linux-headers > "$out/prep.log" 2>&1 || fail "could not install linux-headers"
        ;;
    opensuse)
        zypper --non-interactive install kernel-default-devel kmod > "$out/prep.log" 2>&1 || fail "could not install kernel-default-devel"
        ;;
    *) fail "unknown distro $distro" ;;
esac

kver=""
for build in /lib/modules/*/build /usr/src/kernels/*; do
    [ -e "$build/Makefile" ] || continue
    case "$build" in
        /usr/src/kernels/*) kver=$(basename "$build") ;;
        *) kver=$(basename "$(dirname "$build")") ;;
    esac
    break
done
[ -n "$kver" ] || fail "no kernel build tree found after installing headers"
# Fedora's kernel-devel does not create the /lib/modules/<kver>/build link
# (the kernel package does); create it as the kernel package would.
if [ ! -e "/lib/modules/$kver/build" ] && [ -d "/usr/src/kernels/$kver" ]; then
    mkdir -p "/lib/modules/$kver"
    ln -s "/usr/src/kernels/$kver" "/lib/modules/$kver/build"
fi
log "headers: $kver"

# 2. Make "uname -r" report that kernel (the container shares the host's).
cat > /usr/local/bin/uname << EOF
#!/bin/sh
if [ "\$1" = "-r" ]; then echo "$kver"; else exec /usr/bin/uname "\$@"; fi
EOF
chmod +x /usr/local/bin/uname
# depmod takes the kernel version from uname(2), which in a container is the
# host's kernel, not the stub above; pass the kernel under test explicitly.
real_depmod="$(command -v depmod)" || fail "depmod not found (kmod not installed)"
cat > /usr/local/bin/depmod << EOF
#!/bin/sh
for arg; do case "\$arg" in [0-9]*) exec "$real_depmod" "\$@" ;; esac; done
exec "$real_depmod" "\$@" "$kver"
EOF
chmod +x /usr/local/bin/depmod
export PATH="/usr/local/bin:$PATH"

# 3. Install, install again, uninstall.
cp -r /src /work
cd /work || fail "no /work"

./install.sh < /dev/null > "$out/install1.log" 2>&1
rc=$?
[ "$rc" = 0 ] || fail "install.sh exited $rc (see install1.log)"
dkms status 2> /dev/null | grep -q "aic8800/1.0.0, $kver.*installed" || fail "dkms status does not show aic8800 installed for $kver"
for path in /etc/udev/rules.d/aic.rules /etc/usb_modeswitch.d/1111:1111 /lib/firmware/aic8800D80 /usr/src/aic8800-1.0.0/SOURCE_REVISION /var/log/aic8800-install.log; do
    [ -e "$path" ] || fail "missing after install: $path"
done
[ "$(stat -c %a /var/log/aic8800-install.log)" = 644 ] || fail "log file mode is not 644"
find "/lib/modules/$kver" -name 'aic8800_fdrv.ko*' | grep -q . || fail "aic8800_fdrv not installed for $kver"
log "install: ok"

./install.sh < /dev/null > "$out/install2.log" 2>&1
rc=$?
[ "$rc" = 0 ] || fail "second install.sh exited $rc (see install2.log)"
ls -d /var/backups/aic8800-firmware-* > /dev/null 2>&1 || fail "second install did not back up the firmware"
log "reinstall: ok"

./uninstall.sh > "$out/uninstall.log" 2>&1
rc=$?
[ "$rc" = 0 ] || fail "uninstall.sh exited $rc (see uninstall.log)"
dkms status 2> /dev/null | grep -q '^aic8800/' && fail "dkms still lists aic8800 after uninstall"
for path in /etc/udev/rules.d/aic.rules /etc/usb_modeswitch.d/1111:1111 /lib/firmware/aic8800D80 /usr/src/aic8800-1.0.0 /var/log/aic8800-install.log; do
    [ -e "$path" ] && fail "still present after uninstall: $path"
done
find "/lib/modules/$kver" -name 'aic8800_fdrv.ko*' | grep -q . && fail "aic8800_fdrv still installed for $kver"
log "uninstall: ok"
log "PASS"
