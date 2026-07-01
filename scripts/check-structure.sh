#!/usr/bin/env bash
# Fails if a knowledge leaf dir lacks 00-index.md or an index links a missing file.
set -euo pipefail
cd "$(dirname "$0")/.."
fail=0

# Every dir under knowledge/ that has .md files must have 00-index.md.
while IFS= read -r dir; do
  if ls "$dir"/*.md >/dev/null 2>&1 && [[ ! -f "$dir/00-index.md" ]]; then
    echo "STRUCTURE FAIL: $dir missing 00-index.md" >&2
    fail=1
  fi
done < <(find knowledge -type d)

# Relative links in any index must resolve.
while IFS= read -r idx; do
  { grep -oE '\]\(([^)]+\.md)\)' "$idx" || true; } | sed -E 's/\]\(([^)]+)\)/\1/' | while IFS= read -r link; do
    [[ "$link" == http* ]] && continue
    target="$(dirname "$idx")/$link"
    if [[ ! -f "$target" ]]; then
      echo "STRUCTURE FAIL: $idx -> missing $link" >&2
      exit 1
    fi
  done || fail=1
done < <(find knowledge protocols -name '00-index.md')

# Wikilinks [[layer/slug]] in knowledge pages must resolve to knowledge/layer/slug.md.
# The literal placeholder [[layer/slug]] (used in schema/template docs) is exempt.
while IFS= read -r page; do
  { grep -oE '\[\[[a-z0-9/_-]+\]\]' "$page" || true; } | sed -E 's/\[\[|\]\]//g' | while IFS= read -r wl; do
    [[ "$wl" == "layer/slug" ]] && continue
    if [[ ! -f "knowledge/$wl.md" ]]; then
      echo "STRUCTURE FAIL: $page -> broken wikilink [[$wl]] (no knowledge/$wl.md)" >&2
      exit 1
    fi
  done || fail=1
done < <(find knowledge -name '*.md')

[[ $fail -eq 0 ]] && echo "structure OK"
exit $fail
