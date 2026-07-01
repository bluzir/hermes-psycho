#!/usr/bin/env bash
# Full contract check for the generated Hermes profile seed.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/render-hermes-profile.py --check
bash scripts/check-structure.sh
bash scripts/check-privacy.sh
