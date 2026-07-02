#!/usr/bin/env bash
# Fails if personal data leaks into git-tracked content.
set -euo pipefail
cd "$(dirname "$0")/.."
fail=0

# 1. Personal dirs must hold no tracked real data. Only the public scaffolds are
# allowed: _TEMPLATE/ dirs, people/_index.md, and the data/ drop-folder explainer
# data/README.md. Any other tracked path under people/ self/ contexts/ data/
# (e.g. a real person dir, or real sourced material under data/raw/) fails the build.
TRACKED_PERSONAL=$(git ls-files people self contexts data 2>/dev/null \
  | grep -vE '^(people|self|contexts)/_TEMPLATE/' \
  | grep -vE '^people/_index\.md$' \
  | grep -vE '^data/README\.md$' || true)
if [[ -n "$TRACKED_PERSONAL" ]]; then
  echo "PRIVACY FAIL: real personal files are tracked by git:" >&2
  echo "$TRACKED_PERSONAL" >&2
  fail=1
fi

# 1b. The principal's name must not appear in knowledge LAYER theory pages — those
# are general theory, not personal records. The principal name is read from
# hermes-profile.yaml; RESOLVER/schema/00-index/_meta legitimately reference the
# operator, so they are excluded. Catches personalized examples leaking into the
# embedder. Skipped while the name is still the template placeholder.
PRINCIPAL=$(sed -n 's/^  principal:[[:space:]]*//p' hermes-profile.yaml | head -1 | tr -d '"'"'"'')
if [[ -n "$PRINCIPAL" && "$PRINCIPAL" != *"ВАШЕ_ИМЯ"* ]]; then
  LAYER_HIT=$(git grep -l -nE "$PRINCIPAL" -- \
    'knowledge/attachment' 'knowledge/ifs' 'knowledge/schema-therapy' \
    'knowledge/communication' 'knowledge/systemic' 'knowledge/family' \
    'knowledge/cofounder' 'knowledge/playbooks' 2>/dev/null | grep -v '/00-index.md' || true)
  if [[ -n "$LAYER_HIT" ]]; then
    echo "PRIVACY FAIL: principal name «$PRINCIPAL» appears in knowledge theory pages (should be generic):" >&2
    echo "$LAYER_HIT" >&2
    fail=1
  fi
fi

# 2. Real-name denylist (one name/slug per line) must not appear in tracked theory.
DENYLIST="${PRIVACY_DENYLIST:-.privacy-denylist}"
if [[ -f "$DENYLIST" ]]; then
  while IFS= read -r name; do
    [[ -z "$name" || "$name" == \#* ]] && continue
    if git grep -l -i -e "$name" -- knowledge protocols hermes 2>/dev/null | grep -q .; then
      echo "PRIVACY FAIL: '$name' found in git-tracked knowledge/protocols/hermes" >&2
      fail=1
    fi
  done < "$DENYLIST"
fi

[[ $fail -eq 0 ]] && echo "privacy OK"
exit $fail
