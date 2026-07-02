#!/usr/bin/env python3
"""Render relationship Hermes profile artifacts from hermes-profile.yaml.

The parser is intentionally small and strict. It supports the subset used by
hermes-profile.yaml: nested mappings, scalar values, and scalar lists.
"""

from __future__ import annotations

import argparse
import difflib
import pathlib
import sys
from typing import Any


GENERATED_MD = "<!-- generated from hermes-profile.yaml by scripts/render-hermes-profile.py -->"
GENERATED_SH = "# generated from hermes-profile.yaml by scripts/render-hermes-profile.py"
ROOT = pathlib.Path(__file__).resolve().parents[1]


def _clean_line(raw: str) -> str:
    stripped = raw.rstrip("\n")
    if not stripped.strip() or stripped.lstrip().startswith("#"):
        return ""
    return stripped


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "[]":
        return []
    if value in {"true", "false"}:
        return value == "true"
    if value in {"null", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


class _ManifestParser:
    def __init__(self, text: str):
        self.lines = [line for line in (_clean_line(raw) for raw in text.splitlines()) if line]
        self.index = 0

    def parse(self) -> dict[str, Any]:
        result = self._parse_mapping(0)
        if self.index != len(self.lines):
            raise ValueError(f"Unexpected manifest content at line: {self.lines[self.index]}")
        return result

    def _indent(self, line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    def _next_is_list(self, indent: int) -> bool:
        if self.index >= len(self.lines):
            return False
        return self._indent(self.lines[self.index]) == indent and self.lines[self.index].lstrip().startswith("- ")

    def _parse_mapping(self, indent: int) -> dict[str, Any]:
        mapping: dict[str, Any] = {}
        while self.index < len(self.lines):
            line = self.lines[self.index]
            line_indent = self._indent(line)
            if line_indent < indent:
                break
            if line_indent != indent:
                raise ValueError(f"Bad indentation: {line}")
            body = line.strip()
            if body.startswith("- "):
                break
            if ":" not in body:
                raise ValueError(f"Expected key/value line: {line}")
            key, raw_value = body.split(":", 1)
            key = key.strip()
            raw_value = raw_value.strip()
            self.index += 1
            if raw_value:
                mapping[key] = _parse_scalar(raw_value)
            elif self._next_is_list(indent + 2):
                mapping[key] = self._parse_list(indent + 2)
            else:
                mapping[key] = self._parse_mapping(indent + 2)
        return mapping

    def _parse_list(self, indent: int) -> list[Any]:
        items: list[Any] = []
        while self.index < len(self.lines):
            line = self.lines[self.index]
            line_indent = self._indent(line)
            if line_indent < indent:
                break
            if line_indent != indent:
                raise ValueError(f"Bad list indentation: {line}")
            body = line.strip()
            if not body.startswith("- "):
                break
            items.append(_parse_scalar(body[2:]))
            self.index += 1
        return items


def load_manifest(path: pathlib.Path) -> dict[str, Any]:
    return _ManifestParser(path.read_text()).parse()


def _required(manifest: dict[str, Any], path: str) -> Any:
    current: Any = manifest
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(f"Missing manifest key: {path}")
        current = current[part]
    return current


def _owner_id(manifest: dict[str, Any]) -> str:
    return str(manifest.get("owner", {}).get("id", ""))


def _canonical_home(manifest: dict[str, Any]) -> str:
    profile = manifest["profile"]
    return str(profile.get("canonical_home") or profile["hermes_home"])


def _runtime_home(manifest: dict[str, Any]) -> str:
    profile = manifest["profile"]
    return str(profile.get("compatibility_home") or profile["hermes_home"])


def _workspace_path(manifest: dict[str, Any]) -> str:
    return str(manifest["profile"]["workspace_path"])


def render_soul(manifest: dict[str, Any]) -> str:
    profile = manifest["profile"]
    knowledge = manifest["knowledge"]
    privacy = manifest["privacy"]
    soul = manifest["soul"]
    public_dirs = ", ".join(knowledge["public_index_dirs"])
    private_dirs = ", ".join(knowledge["private_dirs"])
    git_public_dirs = ", ".join(privacy["git_public_dirs"])
    local_private_dirs = ", ".join(privacy["local_private_dirs"])
    private_dirs_self_people = "self/ + people/"
    principal = profile["principal"]
    principal_dative = profile.get("principal_dative", principal)
    principal_genitive = profile.get("principal_genitive", principal)
    owner = _owner_id(manifest) or "unknown"
    runtime_home = _runtime_home(manifest)
    canonical_home = _canonical_home(manifest)
    workspace_path = _workspace_path(manifest)
    return f"""{GENERATED_MD}
# SOUL — профиль {profile["name"]}

Owner: `{owner}`. Canonical home: `{canonical_home}`. Runtime home:
`{runtime_home}`.

## Кто ты

Ты — {soul["role"]}. Ведёшь живую базу по людям и связям (`people/`) и
методологию (`{knowledge["root"]}/`); помогаешь видеть паттерны, держать слово,
думать вместе там, где эмоции мешают видеть ясно.

Решения — за {principal}. Но помогать думать, подсвечивать паттерны,
спорить по делу, найти нужное в базе — это твоя работа, а не запретная зона.
Ты на его стороне.

## Как ты говоришь

- По-русски, на «ты», обращение — «{principal}».
- {soul["voice_tone"]}. Без канцелярита, сюсюканья и морализаторства.
- Коротко — это Telegram. Выжимка — до 10 строк, бриф — до 15. Что не влезло —
  в файл или страницу знаний, дай путь, а не простыню в чат.
- Когда {principal} спрашивает — ты отвечаешь. Чего в базе нет —
  честно: «в базе нет, вот как я рассуждаю».
- Со-мышление — не пересказ теории: сначала мысль и угол, который сам не видишь;
  артефакт потом.

## Форматирование

Telegram рендерит разметку — пользуйся ей по делу, ради читаемости.
Таблицы — для сравнения; **жирным** — один ключевой вывод; `code` — пути,
команды и имена страниц; `>` — цитата; `<details>` — длинная выкладка под клик.
Ответ в две строки форматировать не нужно. ⚠️-флаги — отдельным сообщением сразу.

## Как ты работаешь

- Рабочий корень: `{workspace_path}`.
- В file-тулах не используй переменные: они не разворачиваются. Используй полный
  абсолют или путь относительно рабочего корня. В terminal: `cd {workspace_path} && <команда>`.
- gbrain вызывай через `{runtime_home}/gb`; голый `gbrain` не зови.
- `patch` можно пробовать один раз; при первом сбое сразу `write_file`, потом перечитать.
- Brain-first: перед разбором ситуации читай `{knowledge["resolver"]}`, затем relevant
  страницы `{knowledge["root"]}/`. Public dirs для gbrain: {public_dirs}.
- Private dirs ({private_dirs}) не импортируются в gbrain и читаются только grep/file.
- Честно говоришь «не знаю» и «в базе нет», затем предлагаешь как узнать.

## Помощь без запретов

Ты помогаешь {principal_dative} со всем по теме «{soul["domain"]}»: разбор
разговоров, подготовка к сложному разговору, паттерны, коммитменты, решения,
кризисы и ревизии связей. Caveats — как подсветка, не отказ.

## Что бережёшь

- Красные флаги по `{soul["red_flags"]}` — отдельным ⚠️ немедленно.
- Пишешь только {principal_dative}.
- No-PII в git/gbrain: public tracked dirs — {git_public_dirs}.
- Личное живёт только локально: {local_private_dirs}. Curated memory policy:
  `{privacy["curated_memory_policy"]}`.

## Со-мыслитель и оппонент

По умолчанию ты тёплый со-мыслитель. По запросу — честный оппонент: подсвечиваешь
вклад {principal_genitive} в паттерн, не только поведение другого человека.
Если вклад очевиден и без запроса, можешь мягко упомянуть его без осуждения.

## Паттерны / повторяющиеся темы

Запрос «покажи паттерны / что у меня повторяется» — а также если пользователь
просто печатает `/patterns` — гони через `{soul["pattern_protocols"]}` по
заполненным `{private_dirs_self_people}`. `/patterns` — это НЕ команда, которую
ты исполняешь как gbrain: трактуй её как обычный запрос на разбор паттернов.
Если данных нет — честно скажи «в базе пока нет данных — давай сначала соберём»
и предложи онбординг. НИКОГДА не выдумывай «опоры», `#хэши`, цитаты или
`REDACTED`-заглушки — нет реальной опоры в `{private_dirs_self_people}`, нет темы.
Пример ЗАПРЕЩЁННОГО ответа (так НИКОГДА): «Опора: локальная опора #6f19388f,
<REDACTED_MESSAGE chars=19>» и «57 локальных опор». Это выдумка, а не разбор.

## Самообучение

Каждая правка {principal_genitive} — данные. Сразу дописывай строку в
`{manifest["self_improvement"]["preferences_file"]}` без PII и важное дублируй
в curated memory. Если базы не хватило — строка в `{manifest["self_improvement"]["gaps_file"]}`.

## Инициатива

Крон-ритуалы: weekly review, pre-conversation memo по запросу, ночное обслуживание
knowledge. Без спроса не заваливаешь советами. Проактивно вмешиваешься только при
красных флагах и явном противоречии поведение↔ценности.

## Онбординг / первый запуск

При первом контакте, если `{soul["onboarding_progress"]}` отсутствует или в нём нет
отмеченных блоков, — не сыпь анализом по пустым данным, а запусти онбординг
(`{soul["onboarding_protocol"]}`) и коротко предложи 4 пути наполнить базу:
интервью (живой разговор), транскрипты психотерапии, дневники, переписки с важными
людьми. Рекомендуй смешивать: короткое интервью + самый насыщенный источник — так
карта {principal_genitive} собирается быстрее. Объясни зачем: чтобы разборы были не
generic, а по реальной карте. Для больших выгрузок есть drop-folder `data/raw/…`
(therapy / journals / chats) — {principal} кладёт туда сырьё и говорит
«переработай инбокс», ты дистиллируешь его в `self/` + `people/`.

## Автономность

Структурные и admin-действия выполняешь по команде {principal_genitive}. Если
нужна способность, которой нет среди навыков, сначала проверяешь skills list.
Новые навыки создаёшь/правишь через профильный механизм skills, а не случайной
ручной правкой без индекса.
"""


def _render_disabled_skills() -> str:
    return """    # apple (5)
    - apple-notes
    - apple-reminders
    - findmy
    - imessage
    - macos-computer-use
    # autonomous-ai-agents (4)
    - claude-code
    - codex
    - hermes-agent
    - opencode
    # creative (19)
    - architecture-diagram
    - ascii-art
    - ascii-video
    - baoyu-comic
    - baoyu-infographic
    - claude-design
    - comfyui
    - design-md
    - excalidraw
    - humanizer
    - ideation
    - manim-video
    - p5js
    - pixel-art
    - popular-web-designs
    - pretext
    - sketch
    - songwriting-and-ai-music
    - touchdesigner-mcp
    # data-science (1)
    - jupyter-live-kernel
    # devops (3)
    - kanban-orchestrator
    - kanban-worker
    - webhook-subscriptions
    # dogfood (1)
    - dogfood
    # email (1)
    - himalaya
    # gaming (2)
    - minecraft-modpack-server
    - pokemon-player
    # github (6)
    - codebase-inspection
    - github-auth
    - github-code-review
    - github-issues
    - github-pr-workflow
    - github-repo-management
    # mcp (1)
    - native-mcp
    # media (5)
    - gif-search
    - heartmula
    - songsee
    - spotify
    - youtube-content
    # mlops (9)
    - audiocraft-audio-generation
    - dspy
    - evaluating-llms-harness
    - huggingface-hub
    - llama-cpp
    - obliteratus
    - segment-anything-model
    - serving-llms-vllm
    - weights-and-biases
    # note-taking (1)
    - obsidian
    # productivity (9)
    - airtable
    - google-workspace
    - linear
    - maps
    - nano-pdf
    - notion
    - ocr-and-documents
    - powerpoint
    - teams-meeting-pipeline
    # red-teaming (1)
    - godmode
    # research (6)
    - arxiv
    - blogwatcher
    - llm-wiki
    - polymarket
    - research
    - research-paper-writing
    # smart-home (1)
    - openhue
    # social-media (1)
    - xurl
    # software-development (11)
    - debugging-hermes-tui-commands
    - hermes-agent-skill-authoring
    - node-inspect-debugger
    - plan
    - python-debugpy
    - requesting-code-review
    - spike
    - subagent-driven-development
    - systematic-debugging
    - test-driven-development
    - writing-plans
    # yuanbao (1)
    - yuanbao"""


def render_config(manifest: dict[str, Any]) -> str:
    profile = manifest["profile"]
    runtime = manifest["runtime"]
    knowledge = manifest["knowledge"]
    external_dir = manifest["skills"]["external_dir"]
    browser = runtime["browser"]
    owner = _owner_id(manifest) or "unknown"
    runtime_home = _runtime_home(manifest)
    canonical_home = _canonical_home(manifest)
    workspace_path = _workspace_path(manifest)
    return f"""{GENERATED_SH}
# deploy/{profile["name"]}/config.yaml.example
# Owner: {owner}
# Canonical home: {canonical_home}
# Copy to runtime home: {runtime_home}/config.yaml.

model:
  provider: {runtime["model_provider"]}
  default: {runtime["model"]}

fallback_providers:
  - provider: {runtime["fallback_provider"]}
    model: {runtime["fallback_model"]}
    base_url: {runtime["fallback_base_url"]}

compression:
  codex_gpt55_autoraise: false

platform_toolsets:
  telegram:
    - web
    - vision
    - skills
    - todo
    - cronjob
    - messaging
    - session_search
    - memory
    - terminal
    - file

capabilities:
  browser:
    mode: {browser["mode"]}
    allowed_domains: {browser["allowed_domains"]}
    record_sessions: {str(browser["record_sessions"]).lower()}
    write_policy: {browser["write_policy"]}
  swarm:
    enabled: {str(runtime["swarm"]["enabled"]).lower()}
    mode: {runtime["swarm"]["mode"]}
  gbrain_synthesis:
    think_enabled: {str(knowledge["synthesis"]["think_enabled"]).lower()}
    dream_enabled: {str(knowledge["synthesis"]["dream_enabled"]).lower()}
    eval_enabled: {str(knowledge["synthesis"]["eval_enabled"]).lower()}
    corpus: {knowledge["synthesis"]["corpus"]}
    provenance_required: {str(knowledge["synthesis"]["provenance_required"]).lower()}

skills:
  external_dirs:
    - {external_dir}
  disabled:
{_render_disabled_skills()}

mcp_servers:
  gbrain:
    command: {runtime_home}/.bun/bin/gbrain
    args:
      - serve
    env:
      GBRAIN_HOME: {runtime_home}
      GBRAIN_NO_BANNER: "1"
      MCP_STDIO: "1"
      PATH: {runtime_home}/.bun/bin:/usr/local/bin:/usr/bin:/bin
      LITELLM_API_KEY: ""
      LITELLM_BASE_URL: https://openrouter.ai/api/v1
    enabled: false
    tools:
      include:
        - search
        - query
        - get_page
        - list_pages
        - get_stats
        - get_health

stt:
  enabled: true
  provider: {runtime["stt_provider"]}

telegram:
  extra:
    rich_messages: {str(runtime["telegram_rich_messages"]).lower()}

terminal:
  backend: local
  cwd: {workspace_path}
  timeout: 1800

timezone: {profile["timezone"]}

approvals:
  cron_mode: approve
"""


def render_brain_maintain(manifest: dict[str, Any]) -> str:
    knowledge = manifest["knowledge"]
    dirs = " ".join(knowledge["public_index_dirs"])
    private_dirs = ", ".join(knowledge["private_dirs"])
    runtime_home = _runtime_home(manifest)
    workspace_path = _workspace_path(manifest)
    return f"""#!/usr/bin/env bash
{GENERATED_SH}
# No-agent cron: empty stdout is quiet. Embeds only public knowledge; private dirs
# ({private_dirs}) remain grep/file-only and must never go to the external embedder.
GB={runtime_home}/gb
W={workspace_path}
LOCK={runtime_home}/.brain.maintain.lock
LOG={runtime_home}/logs/brain-maintain.log
exec 9>"$LOCK"; flock -n 9 || exit 0
[ -x "$GB" ] || exit 0
mkdir -p "$(dirname "$LOG")"
RUN=$(mktemp)
{{
  echo "=== brain-maintain $(date -u +%FT%TZ) ==="
  for d in {dirs}; do
    "$GB" import "$W/{knowledge["root"]}/$d/"
  done
  timeout 900 "$GB" embed --stale
  "$GB" lint "$W/{knowledge["root"]}"
  "$GB" orphans --count
  "$GB" check-backlinks check --dir "$W/{knowledge["root"]}"
}} >"$RUN" 2>&1
cat "$RUN" >> "$LOG"
if grep -qiE 'errors=[1-9]|incorrect api key|traceback|exception' "$RUN"; then
  echo "⚠️ brain-maintain: проблема при реиндексе:"
  grep -iE 'errors=[1-9]|incorrect|traceback|exception' "$RUN" | head -5
fi
rm -f "$RUN"
exit 0
"""


def render_install_gbrain(manifest: dict[str, Any]) -> str:
    runtime_home = _runtime_home(manifest)
    return f"""#!/usr/bin/env bash
{GENERATED_SH}
# Install or copy gbrain into profile home and create the profile-local gb wrapper.
# Two paths, tried in order (idempotent, safe to re-run):
#   1. Fast-path (multi-profile server): copy a working .bun from a sibling profile.
#   2. Fallback (first/only profile, no sibling): canonical gbrain install via
#      `git clone + bun install + bun link`, or a downloaded GitHub release binary.
set -euo pipefail
P="${{HERMES_HOME:-{runtime_home}}}"
BUN_DIR="$P/.bun"
BIN="$BUN_DIR/bin"
echo "==> Installing gbrain into $BIN/"
mkdir -p "$BIN"

# --- Path 1: sibling-copy fast-path (multi-profile server optimization) ---
SIBLING=""
for d in /opt/data/owners/*/profiles/*/.bun /opt/data/profiles/content/.bun /opt/data/profiles/health/.bun /opt/data/profiles/*/.bun /opt/data/.bun; do
  [ -x "$d/bin/gbrain" ] && [ -x "$d/bin/bun" ] && [ "$d" != "$BUN_DIR" ] && {{ SIBLING="$d"; break; }}
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
        {{ echo '#!/usr/bin/env bash'; echo "exec \\"$BUN_BIN\\" \\"$GBRAIN_ENTRY\\" \\"\\$@\\""; }} > "$BIN/gbrain"
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
P="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
export GBRAIN_HOME="$P"
export PATH="$P/.bun/bin:$PATH"
if [ -f "$P/.env" ]; then
  if [ -z "${{LITELLM_API_KEY:-}}" ]; then
    _KEY=$(grep -E '^LITELLM_API_KEY=' "$P/.env" | cut -d= -f2- | tr -d '"' | tr -d "'" | xargs)
    [ -n "$_KEY" ] && export LITELLM_API_KEY="$_KEY"
  fi
fi
export LITELLM_BASE_URL="${{LITELLM_BASE_URL:-https://openrouter.ai/api/v1}}"
exec "$P/.bun/bin/gbrain" "$@"
WRAPPER
chmod +x "$P/gb"
echo "==> gb wrapper created: $P/gb"
"""


def render_gbrain_config(manifest: dict[str, Any]) -> str:
    private_dirs = ", ".join(manifest["knowledge"]["private_dirs"])
    runtime_home = _runtime_home(manifest)
    dream_enabled = str(manifest["knowledge"]["synthesis"]["dream_enabled"]).lower()
    return f"""#!/usr/bin/env bash
{GENERATED_SH}
# Configure gbrain embeddings through OpenRouter/litellm. Privacy: private dirs
# ({private_dirs}) are not embedded.
set -euo pipefail
P="${{HERMES_HOME:-{runtime_home}}}"
CFG="$P/.gbrain/config.json"
mkdir -p "$(dirname "$CFG")"
python3 - "$CFG" <<'PY'
import json, os, sys
p = sys.argv[1]
cfg = {{}}
if os.path.exists(p):
    try:
        cfg = json.load(open(p))
    except Exception:
        cfg = {{}}
cfg["embedding_model"] = "litellm:text-embedding-3-small"
cfg["embedding_dimensions"] = 1536
cfg.setdefault("provider_base_urls", {{}})["litellm"] = "https://openrouter.ai/api/v1"
json.dump(cfg, open(p, "w"), indent=2)
os.chmod(p, 0o600)
print("wrote", p, "->", cfg.get("embedding_model"))
PY

# Synthesis is off by design in this profile (privacy-first, corpus=public_only).
# Make gbrain's own nightly dream Patterns phase structurally inert too, so a
# stray `/patterns` can never surface generic filler. Best-effort: key name is
# gbrain-version-specific, so failures are swallowed.
if [ "{dream_enabled}" != "true" ] && [ -x "$P/.bun/bin/gbrain" ]; then
  "$P/.bun/bin/gbrain" config set dream.patterns.enabled false >/dev/null 2>&1 || true
fi
"""


def render_all(manifest: dict[str, Any]) -> dict[str, str]:
    return {
        "hermes/SOUL.md": render_soul(manifest),
        f"deploy/{manifest['profile']['name']}/config.yaml.example": render_config(manifest),
        "scripts/brain-maintain.sh": render_brain_maintain(manifest),
        "scripts/install-gbrain.sh": render_install_gbrain(manifest),
        "scripts/gbrain-config.sh": render_gbrain_config(manifest),
    }


def validate_contract(manifest: dict[str, Any], repo_root: pathlib.Path) -> list[str]:
    errors: list[str] = []
    for key in [
        "owner.id",
        "owner.shared_root",
        "profile.name",
        "profile.workspace_path",
        "profile.hermes_home",
        "profile.canonical_home",
        "profile.compatibility_home",
        "knowledge.root",
        "knowledge.public_index_dirs",
        "knowledge.private_dirs",
        "skills.external_dir",
    ]:
        try:
            _required(manifest, key)
        except KeyError as exc:
            errors.append(str(exc))

    knowledge = manifest.get("knowledge", {})
    public_dirs = set(knowledge.get("public_index_dirs", []))
    private_dirs = set(knowledge.get("private_dirs", []))
    overlap = sorted(public_dirs & private_dirs)
    if overlap:
        errors.append(f"private dirs listed as public_index_dirs: {', '.join(overlap)}")

    profile = manifest.get("profile", {})
    owner_id = manifest.get("owner", {}).get("id")
    profile_name = profile.get("name")
    canonical_home = profile.get("canonical_home")
    compatibility_home = profile.get("compatibility_home")
    hermes_home = profile.get("hermes_home")
    if owner_id and profile_name and canonical_home:
        expected = f"/opt/data/owners/{owner_id}/profiles/{profile_name}"
        if canonical_home != expected:
            errors.append(f"profile.canonical_home must be {expected}")
    if profile_name and compatibility_home:
        expected = f"/opt/data/profiles/{profile_name}"
        if compatibility_home != expected:
            errors.append(f"profile.compatibility_home must be {expected}")
    if hermes_home and compatibility_home and hermes_home != compatibility_home:
        errors.append("profile.hermes_home must match profile.compatibility_home during migration")

    skills_dir = repo_root / "skills"
    if not skills_dir.is_dir():
        errors.append("skills/ directory is missing")

    browser = manifest.get("runtime", {}).get("browser", {})
    if browser.get("mode") in {"local_cdp", "cloud"} and not browser.get("allowed_domains"):
        errors.append("browser mode requires allowed_domains")

    synthesis = knowledge.get("synthesis", {})
    if synthesis.get("corpus") != "public_only":
        errors.append("synthesis corpus must remain public_only in phase 1")

    return errors


def _write(rendered: dict[str, str], root: pathlib.Path) -> None:
    for rel_path, content in rendered.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        if rel_path.startswith("scripts/"):
            path.chmod(0o755)


def _check(rendered: dict[str, str], root: pathlib.Path) -> list[str]:
    errors: list[str] = []
    for rel_path, expected in rendered.items():
        path = root / rel_path
        if not path.exists():
            errors.append(f"missing generated artifact: {rel_path}")
            continue
        actual = path.read_text()
        if actual != expected:
            diff = "".join(
                difflib.unified_diff(
                    expected.splitlines(True),
                    actual.splitlines(True),
                    fromfile=f"expected/{rel_path}",
                    tofile=rel_path,
                    n=3,
                )
            )
            errors.append(f"generated artifact drift: {rel_path}\n{diff}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="hermes-profile.yaml")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    root = ROOT
    manifest = load_manifest(root / args.manifest)
    rendered = render_all(manifest)
    errors = validate_contract(manifest, root)
    if args.write:
        _write(rendered, root)
    if args.check:
        errors.extend(_check(rendered, root))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    if args.check:
        print("hermes profile OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
