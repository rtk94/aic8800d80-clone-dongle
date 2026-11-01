## What and why

<!-- What does this change, and what problem does it solve? Link the issue if there is one. -->

## Testing

- [ ] `make test` passes
- [ ] Tested on hardware: <!-- kernel (`uname -r`), distribution and adapter, or write "not tested on hardware" -->
- [ ] Other tests run, if relevant (`make test-build`, `make test-build-matrix`, `make test-distros`)

## Checklist

- [ ] Documentation and CHANGELOG.md updated where behaviour changed
- [ ] No MAC addresses, serial numbers, SSIDs, IP addresses, user or host names, or home paths in code, logs or commit messages (`make privacy`)
- [ ] Driver source (`drivers/`) changed only for kernel compatibility, with each change explained
