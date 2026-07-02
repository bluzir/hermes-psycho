#!/usr/bin/env bash
# generated from hermes-profile.yaml by scripts/render-hermes-profile.py
# Configure gbrain embeddings through OpenRouter/litellm. Privacy: private dirs
# (people, self, contexts, data) are not embedded.
set -euo pipefail
P="${HERMES_HOME:-/opt/data/profiles/relationship}"
CFG="$P/.gbrain/config.json"
mkdir -p "$(dirname "$CFG")"
python3 - "$CFG" <<'PY'
import json, os, sys
p = sys.argv[1]
cfg = {}
if os.path.exists(p):
    try:
        cfg = json.load(open(p))
    except Exception:
        cfg = {}
cfg["embedding_model"] = "litellm:text-embedding-3-small"
cfg["embedding_dimensions"] = 1536
cfg.setdefault("provider_base_urls", {})["litellm"] = "https://openrouter.ai/api/v1"
json.dump(cfg, open(p, "w"), indent=2)
os.chmod(p, 0o600)
print("wrote", p, "->", cfg.get("embedding_model"))
PY

# Synthesis is off by design in this profile (privacy-first, corpus=public_only).
# Make gbrain's own nightly dream Patterns phase structurally inert too, so a
# stray `/patterns` can never surface generic filler. Best-effort: key name is
# gbrain-version-specific, so failures are swallowed.
if [ "false" != "true" ] && [ -x "$P/.bun/bin/gbrain" ]; then
  "$P/.bun/bin/gbrain" config set dream.patterns.enabled false >/dev/null 2>&1 || true
fi
