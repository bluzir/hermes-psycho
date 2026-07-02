#!/usr/bin/env bash
# generated from hermes-profile.yaml by scripts/render-hermes-profile.py
# Install or copy gbrain into profile home and create the profile-local gb wrapper.
# Two paths, tried in order (idempotent, safe to re-run):
#   1. Fast-path (multi-profile server): copy a working .bun from a sibling profile.
#   2. Fallback (first/only profile, no sibling): canonical gbrain install via
#      `git clone + bun install + bun link`, or a downloaded GitHub release binary.
set -euo pipefail
P="${HERMES_HOME:-/opt/data/profiles/relationship}"
BUN_DIR="$P/.bun"
BIN="$BUN_DIR/bin"
echo "==> Installing gbrain into $BIN/"
mkdir -p "$BIN"

# --- Path 1: sibling-copy fast-path (multi-profile server optimization) ---
SIBLING=""
for d in /opt/data/owners/*/profiles/*/.bun /opt/data/profiles/content/.bun /opt/data/profiles/health/.bun /opt/data/profiles/*/.bun /opt/data/.bun; do
  [ -x "$d/bin/gbrain" ] && [ -x "$d/bin/bun" ] && [ "$d" != "$BUN_DIR" ] && { SIBLING="$d"; break; }
done
if [ -n "$SIBLING" ]; then
  echo "==> Found sibling .bun with bun + gbrain: $SIBLING (copying)"
  rm -rf "$BUN_DIR" && cp -a "$SIBLING" "$BUN_DIR"
fi

# --- Path 2: canonical install fallback (first/only profile, no sibling) ---
# Only runs if the fast-path did not already produce a working .bun/bin/gbrain.
if [ ! -x "$BIN/gbrain" ]; then
  echo "==> No sibling .bun found; attempting canonical gbrain install"
  export PATH="$BIN:$P/.bun/bin:$PATH"
  # 2a. If bun is missing, install it into the profile .bun (BUN_INSTALL=$BUN_DIR).
  if [ ! -x "$BIN/bun" ] && ! command -v bun >/dev/null 2>&1; then
    if command -v curl >/dev/null 2>&1; then
      echo "==> Installing bun into $BUN_DIR"
      BUN_INSTALL="$BUN_DIR" bash -c 'curl -fsSL https://bun.sh/install | bash' || true
    fi
  fi
  BUN_BIN="$BIN/bun"
  [ -x "$BUN_BIN" ] || BUN_BIN="$(command -v bun 2>/dev/null || true)"
  # 2b. Canonical source install: git clone gbrain + bun install + bun link.
  if [ -n "$BUN_BIN" ] && [ -x "$BUN_BIN" ] && command -v git >/dev/null 2>&1; then
    SRC="$P/.gbrain-src"
    if [ ! -d "$SRC/.git" ]; then
      rm -rf "$SRC"
      git clone --depth 1 https://github.com/garrytan/gbrain.git "$SRC"
    else
      git -C "$SRC" pull --ff-only || true
    fi
    ( cd "$SRC" && "$BUN_BIN" install && "$BUN_BIN" link )
    # bun link exposes the `gbrain` bin on $BIN; symlink into the profile bin if needed.
    if [ ! -x "$BIN/gbrain" ] && [ -f "$SRC/package.json" ]; then
      GBRAIN_ENTRY="$SRC/bin/gbrain.ts"
      [ -f "$GBRAIN_ENTRY" ] || GBRAIN_ENTRY="$SRC/src/cli.ts"
      if [ -f "$GBRAIN_ENTRY" ]; then
        { echo '#!/usr/bin/env bash'; echo "exec \"$BUN_BIN\" \"$GBRAIN_ENTRY\" \"\$@\""; } > "$BIN/gbrain"
      fi
    fi
  fi
fi

# --- Actionable failure if neither path produced a usable gbrain ---
if [ ! -x "$BIN/gbrain" ] || [ ! -x "$BIN/bun" ]; then
  cat >&2 <<'ERR'
ERROR: could not install gbrain (no sibling .bun, and canonical install failed).

To fix, install gbrain manually, then re-run this script:
  1. Install Bun >=1.3.10:            https://bun.sh
  2. git clone https://github.com/garrytan/gbrain.git
     cd gbrain && bun install && bun link
     (see gbrain's INSTALL_FOR_AGENTS.md)
  3. Or download a release binary:    https://github.com/garrytan/gbrain/releases
  4. Ensure `bun` and `gbrain` land on $HERMES_HOME/.bun/bin/, then re-run.

Full self-host walkthrough: docs/INSTALL.md (Тир 2 — с нуля без соседнего профиля).
ERR
  exit 1
fi
chmod +x "$BIN/gbrain"
cat > "$P/gb" <<'WRAPPER'
#!/usr/bin/env bash
P="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export GBRAIN_HOME="$P"
export PATH="$P/.bun/bin:$PATH"
if [ -f "$P/.env" ]; then
  if [ -z "${LITELLM_API_KEY:-}" ]; then
    _KEY=$(grep -E '^LITELLM_API_KEY=' "$P/.env" | cut -d= -f2- | tr -d '"' | tr -d "'" | xargs)
    [ -n "$_KEY" ] && export LITELLM_API_KEY="$_KEY"
  fi
fi
export LITELLM_BASE_URL="${LITELLM_BASE_URL:-https://openrouter.ai/api/v1}"
exec "$P/.bun/bin/gbrain" "$@"
WRAPPER
chmod +x "$P/gb"
echo "==> gb wrapper created: $P/gb"
