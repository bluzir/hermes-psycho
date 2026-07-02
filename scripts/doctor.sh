#!/usr/bin/env bash
# READ-ONLY preflight for the relationship profile. Never mutates anything:
# no global-config writes, no gbrain init, no cp, no cron create. It only reads
# files and probes the environment, then prints a per-check OK/WARN/FAIL line
# and a final summary.
#
# Two sections:
#   REQUIRED (local)  — always run; validates the checkout itself.
#   OPTIONAL (server) — only when HERMES_HOME is set; validates the deployed
#                       profile home ($HERMES_HOME) without printing secrets.
#
# Exit code: nonzero if any REQUIRED check FAILs (WARN never fails the run).
set -uo pipefail            # no -e; each check reports its own status
cd "$(dirname "$0")/.."

had_fail=0
had_warn=0

ok()   { printf "  OK    %s\n" "$1"; }
warn() { printf "  WARN  %s\n" "$1"; had_warn=1; }
fail() { printf "  FAIL  %s\n" "$1"; had_fail=1; }

# ---------------------------------------------------------------------------
echo "== REQUIRED (local) =="

# python >= 3.10
if command -v python3 >/dev/null 2>&1; then
  if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then
    ok "python3 $(python3 -c 'import sys;print("%d.%d.%d"%sys.version_info[:3])') (>= 3.10)"
  else
    fail "python3 $(python3 -c 'import sys;print("%d.%d.%d"%sys.version_info[:3])') is older than 3.10"
  fi
else
  fail "python3 not found on PATH"
fi

# repo layout — reuse check-structure.sh (it is itself read-only)
if bash scripts/check-structure.sh >/dev/null 2>&1; then
  ok "repo layout (check-structure.sh)"
else
  fail "repo layout: check-structure.sh reported problems (run it directly for detail)"
fi

# render --check — profile seed renders cleanly
if python3 scripts/render-hermes-profile.py --check >/dev/null 2>&1; then
  ok "render --check"
else
  fail "render --check failed (run python3 scripts/render-hermes-profile.py --check)"
fi

# principal placeholder still present?
if grep -q '<ВАШЕ_ИМЯ>' hermes-profile.yaml 2>/dev/null; then
  warn "hermes-profile.yaml principal is still the placeholder <ВАШЕ_ИМЯ> — set your name"
else
  ok "hermes-profile.yaml principal is set (not placeholder)"
fi

# no tracked secrets — reuse check-privacy.sh (read-only)
if bash scripts/check-privacy.sh >/dev/null 2>&1; then
  ok "no tracked secrets/PII (check-privacy.sh)"
else
  fail "check-privacy.sh reported tracked PII/secrets (run it directly for detail)"
fi

# ---------------------------------------------------------------------------
if [ -n "${HERMES_HOME:-}" ]; then
  echo "== OPTIONAL (server: HERMES_HOME=$HERMES_HOME) =="

  ENV_FILE="$HERMES_HOME/.env"
  if [ -f "$ENV_FILE" ]; then
    ok ".env exists at $ENV_FILE"
    # Each required key must be present AND non-empty. We check the pattern
    # only (grep -q '^KEY=.\+') and NEVER print the value.
    for key in TELEGRAM_BOT_TOKEN TELEGRAM_ALLOWED_USERS TELEGRAM_HOME_CHANNEL LITELLM_API_KEY XAI_API_KEY; do
      if grep -q "^${key}=.\+" "$ENV_FILE"; then
        ok ".env $key is set (non-empty)"
      else
        fail ".env $key is missing or empty"
      fi
    done
    # allowlist must not be the placeholder
    if grep -q '^TELEGRAM_ALLOWED_USERS=<owner-telegram-id>' "$ENV_FILE"; then
      fail ".env TELEGRAM_ALLOWED_USERS is still the placeholder <owner-telegram-id>"
    fi
  else
    fail ".env not found at $ENV_FILE"
  fi

  # hermes CLI on PATH
  if command -v hermes >/dev/null 2>&1; then
    ok "hermes on PATH"
  else
    fail "hermes not found on PATH"
  fi

  # gbrain — the profile-local wrapper is 'gb'; upstream binary is 'gbrain'
  if command -v gb >/dev/null 2>&1 || [ -x "$HERMES_HOME/gb" ]; then
    ok "gb wrapper present"
  elif command -v gbrain >/dev/null 2>&1 || [ -x "$HERMES_HOME/.bun/bin/gbrain" ]; then
    ok "gbrain present"
  else
    fail "neither gb wrapper nor gbrain found (run bootstrap.sh / install-gbrain.sh)"
  fi

  # script drift: $HERMES_HOME/scripts/*.sh must match repo scripts/*.sh
  # (the step-6 footgun — crons resolve --script against $HERMES_HOME/scripts).
  SRV_SCRIPTS="$HERMES_HOME/scripts"
  if [ -d "$SRV_SCRIPTS" ]; then
    drift=0
    for f in scripts/*.sh; do
      base="$(basename "$f")"
      if [ ! -f "$SRV_SCRIPTS/$base" ]; then
        warn "script drift: $base missing in $SRV_SCRIPTS (run bootstrap.sh)"
        drift=1
      elif ! cmp -s "$f" "$SRV_SCRIPTS/$base"; then
        warn "script drift: $base differs from repo copy (run bootstrap.sh)"
        drift=1
      fi
    done
    [ "$drift" -eq 0 ] && ok "server scripts match repo scripts/*.sh"
  else
    warn "$SRV_SCRIPTS does not exist yet (run bootstrap.sh to populate it)"
  fi

  # logs dir writable
  LOGS_DIR="$HERMES_HOME/logs"
  if [ -d "$LOGS_DIR" ] && [ -w "$LOGS_DIR" ]; then
    ok "logs dir writable ($LOGS_DIR)"
  elif [ ! -e "$LOGS_DIR" ] && [ -w "$HERMES_HOME" ]; then
    warn "logs dir $LOGS_DIR does not exist yet but $HERMES_HOME is writable (created on first run)"
  else
    fail "logs dir not writable ($LOGS_DIR)"
  fi

  # gbrain enabled vs disabled — read from the profile config (no mutation)
  CFG="$HERMES_HOME/config.yaml"
  if [ -f "$CFG" ]; then
    # look at the gbrain mcp_servers block's `enabled:` line
    gb_enabled="$(awk '/^  gbrain:/{f=1} f&&/^    enabled:/{print $2; exit}' "$CFG" 2>/dev/null)"
    case "$gb_enabled" in
      true)  ok "gbrain semantic search ENABLED in config.yaml" ;;
      false) warn "gbrain semantic search DISABLED in config.yaml (knowledge served by grep until enabled)" ;;
      *)     warn "gbrain enabled-state not found in $CFG" ;;
    esac
  else
    warn "config.yaml not found at $CFG"
  fi
else
  echo "== OPTIONAL (server) skipped: HERMES_HOME not set =="
fi

# ---------------------------------------------------------------------------
echo
echo "==== doctor summary ===="
if [ "$had_fail" -ne 0 ]; then
  echo "doctor: FAIL"
  exit 1
elif [ "$had_warn" -ne 0 ]; then
  echo "doctor: OK (with warnings)"
else
  echo "doctor: OK"
fi
