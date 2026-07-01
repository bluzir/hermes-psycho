#!/usr/bin/env bash
# generated from hermes-profile.yaml by scripts/render-hermes-profile.py
# Install or copy gbrain into profile home and create the profile-local gb wrapper.
set -euo pipefail
P="${HERMES_HOME:-/opt/data/profiles/relationship}"
BUN_DIR="$P/.bun"
BIN="$BUN_DIR/bin"
echo "==> Installing gbrain into $BIN/"
SIBLING=""
for d in /opt/data/owners/*/profiles/*/.bun /opt/data/profiles/content/.bun /opt/data/profiles/health/.bun /opt/data/profiles/*/.bun /opt/data/.bun; do
  [ -x "$d/bin/gbrain" ] && [ -x "$d/bin/bun" ] && [ "$d" != "$BUN_DIR" ] && { SIBLING="$d"; break; }
done
if [ -n "$SIBLING" ]; then
  rm -rf "$BUN_DIR" && cp -a "$SIBLING" "$BUN_DIR"
fi
if [ ! -x "$BIN/gbrain" ] || [ ! -x "$BIN/bun" ]; then
  echo "ERROR: working .bun with bun + gbrain not found" >&2
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
