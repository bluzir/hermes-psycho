#!/usr/bin/env bash
# Local "base smoke" — no network, no container, no server.
# Runs the checks that make sense on a bare checkout and prints a compact
# per-step OK/WARN/FAIL summary. Exits nonzero if any step FAILs.
#
# Steps:
#   1. render --check   — hermes-profile.yaml renders the seed cleanly
#   2. test.sh          — python unit tests (discover -s tests)
#   3. check-privacy.sh — no PII / secrets tracked by git
#   4. check-structure.sh — knowledge/protocols indexes + links resolve
set -uo pipefail            # NOTE: no -e; we handle each step's exit code ourselves
cd "$(dirname "$0")/.."

steps_out=""                # accumulated "STATUS<TAB>label" lines
had_fail=0

run_step() {
  # run_step <label> <cmd...>
  local label="$1"; shift
  local out status
  out="$("$@" 2>&1)"; status=$?
  if [[ $status -eq 0 ]]; then
    steps_out+="OK\t${label}\n"
  else
    steps_out+="FAIL\t${label}\n"
    had_fail=1
    # Echo the failing step's output so the failure is actionable, not opaque.
    echo "--- ${label} FAILED (exit ${status}) ---" >&2
    printf '%s\n' "$out" >&2
  fi
}

run_step "render --check"      python3 scripts/render-hermes-profile.py --check
run_step "test.sh"             bash scripts/test.sh
run_step "check-privacy.sh"    bash scripts/check-privacy.sh
run_step "check-structure.sh"  bash scripts/check-structure.sh

echo
echo "==== verify summary ===="
printf "%b" "$steps_out" | while IFS=$'\t' read -r st label; do
  printf "  %-5s %s\n" "$st" "$label"
done

if [[ $had_fail -ne 0 ]]; then
  echo "verify: FAIL"
  exit 1
fi
echo "verify: OK"
