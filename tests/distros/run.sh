#!/bin/bash
#
# Run install.sh and uninstall.sh for real in unprivileged distribution
# containers (Docker or Podman). Needs network access; takes several
# minutes per distribution. Nothing on the host is changed: the containers
# are not privileged, so they cannot load or unload kernel modules.
#
# Usage: tests/distros/run.sh [distro ...]
#        (default: debian ubuntu fedora arch opensuse)
# Results: tests/distros/out/<distro>/ (ignored by git)

set -euo pipefail

repo="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
outdir="$repo/tests/distros/out"

declare -A images=(
    [debian]=debian:trixie
    [ubuntu]=ubuntu:24.04
    [fedora]=fedora:latest
    [arch]=archlinux:latest
    [opensuse]=opensuse/tumbleweed:latest
)

engine=""
for candidate in docker podman; do
    if command -v "$candidate" > /dev/null; then
        engine="$candidate"
        break
    fi
done
[ -n "$engine" ] || {
    echo "docker or podman is required" >&2
    exit 1
}

if [ "$#" -gt 0 ]; then
    distros=("$@")
else
    distros=(debian ubuntu fedora arch opensuse)
fi

# Copy the tracked files (with any uncommitted edits) to a staging tree,
# so the containers never see untracked files or the .git directory.
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
(cd "$repo" && git ls-files -z | xargs -0 cp --parents -t "$stage")

mkdir -p "$outdir"
pids=()
for distro in "${distros[@]}"; do
    image="${images[$distro]:-}"
    [ -n "$image" ] || {
        echo "unknown distro: $distro" >&2
        exit 2
    }
    rm -rf "${outdir:?}/$distro"
    mkdir -p "$outdir/$distro"
    echo "starting $distro ($image)"
    "$engine" run --rm \
        -v "$stage:/src:ro" \
        -v "$repo/tests/distros/in-container.sh:/in-container.sh:ro" \
        -v "$outdir/$distro:/out" \
        "$image" bash /in-container.sh "$distro" > "$outdir/$distro/console.log" 2>&1 &
    pids+=($!)
done

status=0
for i in "${!pids[@]}"; do
    if ! wait "${pids[$i]}"; then
        status=1
    fi
done

echo
for distro in "${distros[@]}"; do
    cat "$outdir/$distro/summary.txt" 2> /dev/null || echo "[$distro] no summary; see $outdir/$distro/console.log"
done
exit "$status"
