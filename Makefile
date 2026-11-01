# Test entry points for this repository. The driver itself is built by
# drivers/aic8800/Makefile (via DKMS or install.sh), not by this file.
#
#   make test           lint + unit tests + privacy scan (no root, no network)
#   make lint           shellcheck, shfmt (repository-owned scripts), udevadm verify
#   make unit           Python unit tests (standard library only)
#   make privacy        scan tracked files and commit messages for personal identifiers
#   make test-build     compile the modules against installed kernel headers
#   make test-distros   run install.sh and uninstall.sh in distribution containers
#   make test-build-matrix  compile against several distributions' headers in containers
#
# Tools can be overridden, for example: make lint SHELLCHECK=/path/to/shellcheck

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

PYTHON     ?= python3
SHELLCHECK ?= shellcheck
SHFMT      ?= shfmt
UDEVADM    ?= udevadm
KVER       ?= $(shell uname -r)
KDIR       ?= /lib/modules/$(KVER)/build

SH_FILES     := $(shell git ls-files '*.sh')
# Only scripts written for this repository are formatted with shfmt;
# upstream's scripts keep their own style.
SHFMT_FILES  := uninstall.sh $(wildcard scripts/*.sh) $(wildcard tests/distros/*.sh) $(wildcard tests/build/*.sh)
SHFMT_FLAGS  := -i 4 -ci -sr
UNIT_TESTS   := $(shell git ls-files 'tests/*/test_*.py')

.PHONY: help test lint shellcheck shfmt udev-verify unit privacy test-build test-distros test-build-matrix

help:
	@sed -n '4,11p' Makefile | sed 's/^# \{0,1\}//'

test: lint unit privacy
	@echo "make test: all checks passed"

lint: shellcheck shfmt udev-verify

shellcheck:
	@command -v $(SHELLCHECK) > /dev/null || { echo "shellcheck not found; install it (apt/dnf/pacman/zypper: shellcheck) or set SHELLCHECK=" >&2; exit 1; }
	$(SHELLCHECK) $(SH_FILES)

shfmt:
	@if command -v $(SHFMT) > /dev/null; then \
		$(SHFMT) $(SHFMT_FLAGS) -d $(SHFMT_FILES); \
	else \
		echo "SKIP shfmt: not installed (CI runs it)"; \
	fi

# "udevadm verify" exists since systemd 254.
udev-verify:
	@if $(UDEVADM) verify --help > /dev/null 2>&1; then \
		$(UDEVADM) verify --resolve-names=never aic.rules; \
	else \
		echo "SKIP udevadm verify: needs systemd 254 or later (CI runs it)"; \
	fi

unit:
	@for t in $(UNIT_TESTS); do \
		echo "== $$t"; \
		$(PYTHON) -B -I $$t 2>&1 | tail -n 3; \
		test "$${PIPESTATUS[0]}" -eq 0; \
	done

privacy:
	./scripts/privacy-scan.sh

# Compile-only check against the headers of one kernel, in a temporary copy.
test-build:
	@test -r "$(KDIR)/Makefile" || { echo "No kernel build tree at $(KDIR); install headers for $(KVER)" >&2; exit 1; }
	@tmp=$$(mktemp -d); trap 'rm -rf "$$tmp"' EXIT; \
	cp -r drivers "$$tmp/"; \
	$(MAKE) -C "$$tmp/drivers/aic8800" -j"$$(nproc)" KVER=$(KVER) KDIR=$(KDIR) > "$$tmp/build.log" 2>&1 \
		|| { tail -n 40 "$$tmp/build.log"; exit 1; }; \
	echo "Built for $(KVER):"; find "$$tmp/drivers" -name '*.ko' -printf '  %f\n' | sort; \
	echo "warnings: $$(grep -c 'warning:' "$$tmp/build.log" || true)"

test-distros:
	./tests/distros/run.sh

test-build-matrix:
	./tests/build/run.sh
