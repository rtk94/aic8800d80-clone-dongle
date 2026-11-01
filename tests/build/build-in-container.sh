#!/bin/bash
#
# Compile-only build of the driver against one distribution's kernel
# headers. Runs inside a container started by tests/build/run.sh or CI.
# This proves that the source compiles for that kernel; it says nothing
# about whether the hardware works with it.
#
# Usage: build-in-container.sh <target>   (source tree at /src)
# Targets:
#   debian13            current Debian 13 kernel (linux-headers-amd64)
#   debian13-6.12.100   Debian 6.12.100-1 from snapshot.debian.org (before the
#                       set_monitor_channel backport)
#   debian13-6.12.101   Debian 6.12.101-1 from snapshot.debian.org (first
#                       Debian 13 kernel with the backport)
#   debian12            current Debian 12 kernel
#   ubuntu2404          current Ubuntu 24.04 generic kernel
#   fedora              current Fedora kernel-devel
#   arch                current Arch Linux linux-headers

set -euo pipefail
target="$1"

# Download one binary package from snapshot.debian.org by name and version.
snapshot_deb() {
    local name="$1" version="$2" hash
    hash=$(curl -fsS "https://snapshot.debian.org/mr/binary/${name}/${version}/binfiles" |
        python3 -c 'import sys,json; r=[x for x in json.load(sys.stdin)["result"] if x["architecture"] in ("amd64","all")]; print(r[0]["hash"])')
    curl -fsS -o "/tmp/${name}.deb" "https://snapshot.debian.org/file/${hash}"
    echo "/tmp/${name}.deb"
}

debian_snapshot_headers() {
    local v="$1"
    apt-get install -y -qq curl python3 ca-certificates > /dev/null
    local debs=()
    debs+=("$(snapshot_deb "linux-headers-${v}+deb13-amd64" "${v}-1")")
    debs+=("$(snapshot_deb "linux-headers-${v}+deb13-common" "${v}-1")")
    debs+=("$(snapshot_deb "linux-kbuild-${v}+deb13" "${v}-1")")
    apt-get install -y -qq "${debs[@]}" > /dev/null
}

case "$target" in
    debian13 | debian12 | debian13-6.12.*)
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y -qq build-essential > /dev/null
        case "$target" in
            debian13-6.12.*) debian_snapshot_headers "${target#debian13-}" ;;
            *) apt-get install -y -qq linux-headers-amd64 > /dev/null ;;
        esac
        ;;
    ubuntu2404)
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y -qq build-essential linux-headers-generic > /dev/null
        ;;
    fedora)
        dnf install -y -q gcc make kernel-devel > /dev/null
        ;;
    arch)
        pacman -Syu --noconfirm --needed base-devel linux-headers > /dev/null
        ;;
    *)
        echo "unknown target: $target" >&2
        exit 2
        ;;
esac

kver=""
for build in /lib/modules/*/build /usr/src/kernels/*; do
    [ -e "$build/Makefile" ] || continue
    case "$build" in
        /usr/src/kernels/*) kver=$(basename "$build") ;;
        *) kver=$(basename "$(dirname "$build")") ;;
    esac
    kdir="$build"
    break
done
[ -n "$kver" ] || {
    echo "no kernel build tree found" >&2
    exit 1
}

cp -r /src/drivers /tmp/build
log=/tmp/build.log
if make -C /tmp/build/aic8800 -j"$(nproc)" KVER="$kver" KDIR="$kdir" > "$log" 2>&1; then
    result=PASS
else
    result=FAIL
fi
modules=$(find /tmp/build -name '*.ko' -printf '%f ' | tr -s ' ')
warnings=$(grep -c 'warning:' "$log" || true)
echo "RESULT target=$target kernel=$kver result=$result warnings=$warnings modules=${modules:-none}"
# One line per distinct warning: source file and compiler flag.
grep -E 'warning:' "$log" |
    sed -E 's#^/tmp/build/aic8800/##; s#^([^:]+):[0-9]+:[0-9]+: warning: .*\[(-W[^]]+)\]$#WARNING \1 \2#; /^WARNING/!s#^.*warning: *#WARNING (other) #' |
    sort | uniq -c | sed 's/^ */  /' || true
if [ "$result" = FAIL ]; then
    grep -E 'error:' "$log" | head -20
    exit 1
fi
