#!/usr/bin/env bash
# Server-side convenience wrapper for standing up / re-syncing the relationship
# profile. Idempotent: safe to re-run — each step reports "already installed",
# "updated", or "skipped".
#
# IMPORTANT: the Hermes gateway/CLI ("hermes") and the gbrain corpus tool
# ("gbrain"/"gb") are EXTERNAL frameworks installed on the server. This script
# is THIN GLUE around them — it never reimplements them. It runs only inside a
# profile home (requires HERMES_HOME) and refuses to run otherwise.
#
# It deliberately does NOT run interactive or host-level steps:
#   - `hermes setup`        (interactive auth/provider) -> printed as a manual step
#   - `docker compose up`   (host-level, all profiles) -> printed as a manual step
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$(pwd)"

if [ -z "${HERMES_HOME:-}" ]; then
  echo "ERROR: HERMES_HOME is not set. bootstrap.sh only runs inside a profile home" >&2
  echo "       (e.g. HERMES_HOME=/opt/data/profiles/relationship). Refusing to run." >&2
  exit 1
fi
P="$HERMES_HOME"
echo "==> bootstrap: HERMES_HOME=$P  (repo: $REPO)"

# 1. install-gbrain.sh — copies a working .bun (bun + gbrain) + creates gb wrapper
echo
echo "==> [1/6] install-gbrain.sh"
if [ -x "$P/.bun/bin/gbrain" ] && [ -x "$P/gb" ]; then
  echo "    already installed: $P/.bun/bin/gbrain + $P/gb — re-running to refresh wrapper"
fi
bash "$REPO/scripts/install-gbrain.sh"

# 2. gbrain init --pglite — skip if a DB is already present
echo
echo "==> [2/6] gbrain init --pglite"
if ls "$P"/.gbrain/*.db "$P"/.gbrain/pglite* "$P"/.gbrain/data* >/dev/null 2>&1; then
  echo "    already initialised (found gbrain DB under $P/.gbrain/) — skipping init"
else
  echo "    no DB found — running init --pglite"
  ( export GBRAIN_HOME="$P"; "$P/.bun/bin/gbrain" init --pglite )
fi

# 3. gbrain-config.sh — point embedder at OpenRouter/litellm (idempotent write)
echo
echo "==> [3/6] gbrain-config.sh"
bash "$REPO/scripts/gbrain-config.sh"

# 4. copy repo scripts into $HERMES_HOME/scripts/ — kills the recurring step-6.
#    Crons resolve `--script name.sh` against $HERMES_HOME/scripts/, NOT the repo.
echo
echo "==> [4/6] sync scripts -> $P/scripts/"
mkdir -p "$P/scripts"
changed=0
for f in "$REPO"/scripts/*.sh; do
  base="$(basename "$f")"
  if [ ! -f "$P/scripts/$base" ] || ! cmp -s "$f" "$P/scripts/$base"; then
    cp "$f" "$P/scripts/$base"
    changed=1
  fi
done
chmod 755 "$P"/scripts/*.sh
if [ "$changed" -eq 1 ]; then
  echo "    updated: scripts synced into $P/scripts/"
else
  echo "    already up to date: $P/scripts/ matches repo"
fi

# 5. import each knowledge layer (one dir per call — multi-arg import silently
#    takes only the first, a known gbrain footgun) then embed stale pages.
echo
echo "==> [5/6] gb import knowledge layers + embed --stale"
W="$P/workspace/relationship-ai"
if [ ! -d "$W/knowledge" ]; then
  # fall back to importing from the repo we are running inside
  W="$REPO"
fi
for d in attachment ifs schema-therapy communication systemic family; do
  if [ -d "$W/knowledge/$d" ]; then
    echo "    import knowledge/$d/"
    "$P/gb" import "$W/knowledge/$d/"
  else
    echo "    skip knowledge/$d/ (not present)"
  fi
done
"$P/gb" embed --stale

# 6. crons — check before creating to avoid duplicates. We do NOT auto-create
#    here (schedules/delivery are profile-specific); we report what exists.
echo
echo "==> [6/6] cron check"
if command -v hermes >/dev/null 2>&1; then
  echo "    current crons (hermes cron list):"
  hermes cron list || echo "    (hermes cron list failed — check gateway is up)"
  echo "    -> create missing rituals per deploy/relationship/cron-rituals.md"
  echo "       (skip any name already listed above to avoid duplicates)"
else
  echo "    hermes not on PATH — register crons later per cron-rituals.md"
fi

# ---------------------------------------------------------------------------
echo
echo "==== bootstrap done ===="
echo "Manual next steps (NOT run automatically):"
echo "  - hermes setup            # interactive auth/provider -> auth.json (model + xai STT)"
echo "  - docker compose up -d    # host-level, brings up the shared 'hermes' container"
echo "                            # (see deploy/relationship/README.md for the full command)"
echo "  - enable gbrain: set mcp_servers.gbrain.enabled: true in config.yaml, then /restart"
