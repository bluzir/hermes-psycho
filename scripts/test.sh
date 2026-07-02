#!/usr/bin/env bash
# Run the Python unit tests from the repo root.
#
# Footgun this fixes: a bare `python3 -m unittest discover` invoked from the
# repo root finds 0 tests and still exits 0 — a green "pass" that ran nothing.
# Pinning `-s tests` makes discovery deterministic regardless of cwd, and the
# exit code is passed straight through so CI/verify.sh see real failures.
set -euo pipefail
cd "$(dirname "$0")/.."

exec python3 -m unittest discover -s tests -v
