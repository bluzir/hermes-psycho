#!/usr/bin/env bash
# generated from hermes-profile.yaml by scripts/render-hermes-profile.py
# No-agent cron: empty stdout is quiet. Embeds only public knowledge; private dirs
# (people, self, contexts, data) remain grep/file-only and must never go to the external embedder.
GB=/opt/data/profiles/relationship/gb
W=/opt/data/profiles/relationship/workspace/relationship-ai
LOCK=/opt/data/profiles/relationship/.brain.maintain.lock
LOG=/opt/data/profiles/relationship/logs/brain-maintain.log
exec 9>"$LOCK"; flock -n 9 || exit 0
[ -x "$GB" ] || exit 0
mkdir -p "$(dirname "$LOG")"
RUN=$(mktemp)
{
  echo "=== brain-maintain $(date -u +%FT%TZ) ==="
  for d in attachment ifs schema-therapy communication systemic family; do
    "$GB" import "$W/knowledge/$d/"
  done
  timeout 900 "$GB" embed --stale
  "$GB" lint "$W/knowledge"
  "$GB" orphans --count
  "$GB" check-backlinks check --dir "$W/knowledge"
} >"$RUN" 2>&1
cat "$RUN" >> "$LOG"
if grep -qiE 'errors=[1-9]|incorrect api key|traceback|exception' "$RUN"; then
  echo "⚠️ brain-maintain: проблема при реиндексе:"
  grep -iE 'errors=[1-9]|incorrect|traceback|exception' "$RUN" | head -5
fi
rm -f "$RUN"
exit 0
