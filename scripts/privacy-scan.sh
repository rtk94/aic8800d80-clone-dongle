#!/bin/bash
#
# Scan the repository for personal identifiers before pushing.
#
# Checks tracked files (except the vendor driver and firmware trees) and the
# messages of this repository's own commits (the first-parent history, which
# leaves out upstream's merged history) for:
#   - MAC addresses (except the documentation prefix 02:00:00)
#   - private IPv4 addresses (10/8, 172.16/12, 192.168/16)
#   - home directory paths (/home/<name>, /Users/<name>)
#   - committed Python caches or compiled files
#   - every fixed string listed in a local denylist file, if present
#
# The denylist holds identifiers that must never appear (your user name,
# host name, device MACs, network names). It is read from
# $AIC_PRIVACY_DENYLIST, or ~/.config/aic8800-privacy-denylist by default,
# one entry per line, and is never part of the repository.
#
# Exit status: 0 when nothing is found, 1 otherwise.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

denylist="${AIC_PRIVACY_DENYLIST:-$HOME/.config/aic8800-privacy-denylist}"
status=0

report() {
    echo "PRIVACY: $1"
    status=1
}

mapfile -d '' files < <(git ls-files -z -- . ':!drivers' ':!fw' ':!LICENSE')

patterns=(
    '([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}'
    '(^|[^0-9.])(10\.[0-9]{1,3}|192\.168|172\.(1[6-9]|2[0-9]|3[01]))\.[0-9]{1,3}\.[0-9]{1,3}($|[^0-9.])'
    '/(home|Users)/[A-Za-z0-9_.-]+'
)
allowed='02[:-]00[:-]00[:-]|/home/<user>|/home/\$|/Users/<user>'

for pattern in "${patterns[@]}"; do
    while IFS= read -r hit; do
        report "file content: $hit"
    done < <(grep -I -n -H -E "$pattern" "${files[@]}" 2> /dev/null | grep -v -E "$allowed" || true)
done

while IFS= read -r cached; do
    report "compiled or cache file is tracked: $cached"
done < <(printf '%s\n' "${files[@]}" | grep -E '(^|/)__pycache__/|\.py[co]$' || true)

messages="$(git log --first-parent --format='%h %B' HEAD)"
for pattern in "${patterns[@]}"; do
    while IFS= read -r hit; do
        report "commit message: $hit"
    done < <(grep -n -E "$pattern" <<< "$messages" | grep -v -E "$allowed" || true)
done

if [ -r "$denylist" ]; then
    while IFS= read -r entry; do
        [ -z "$entry" ] && continue
        [[ "$entry" == \#* ]] && continue
        if grep -I -n -H -i -w -F -- "$entry" "${files[@]}" > /dev/null 2>&1; then
            report "denylisted string found in files (entry not shown; check $denylist)"
            grep -I -l -i -w -F -- "$entry" "${files[@]}" 2> /dev/null | sed 's/^/    /'
        fi
        if grep -q -i -w -F -- "$entry" <<< "$messages"; then
            report "denylisted string found in a commit message (entry not shown)"
        fi
    done < "$denylist"
else
    echo "note: no denylist at $denylist; only generic patterns were checked"
fi

if [ "$status" = 0 ]; then
    echo "privacy scan: clean"
fi
exit "$status"
