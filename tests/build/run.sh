#!/bin/bash
#
# Compile the driver against several distributions' kernel headers in
# containers (Docker or Podman). Needs network access. CI runs the same
# targets; this is the local equivalent.
#
# Usage: tests/build/run.sh [target ...]
# Default targets: see TARGETS below. Each line of output is one result.

set -euo pipefail

repo="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"

declare -A images=(
    [debian13]=debian:trixie
    ["debian13-6.12.100"]=debian:trixie
    ["debian13-6.12.101"]=debian:trixie
    [debian12]=debian:bookworm
    [ubuntu2404]=ubuntu:24.04
    [fedora]=fedora:latest
    [arch]=archlinux:latest
)
TARGETS=(debian13 debian13-6.12.100 debian13-6.12.101 debian12 ubuntu2404 fedora arch)

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
    targets=("$@")
else
    targets=("${TARGETS[@]}")
fi

status=0
for target in "${targets[@]}"; do
    image="${images[$target]:-}"
    [ -n "$image" ] || {
        echo "unknown target: $target" >&2
        exit 2
    }
    rc=0
    output=$("$engine" run --rm -v "$repo:/src:ro" \
        "$image" bash /src/tests/build/build-in-container.sh "$target" 2>&1) || rc=$?
    grep -E '^RESULT|^  [0-9]+ WARNING|error:' <<< "$output" || echo "RESULT target=$target result=ERROR (no result line; container exit $rc)"
    [ "$rc" = 0 ] || status=1
done
exit "$status"
