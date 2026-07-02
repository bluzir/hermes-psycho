# Деплой профиля relationship — ранбук

> **Это продвинутый self-host под мультипрофильный сервер автора.** Новичку — начни с
> [`docs/INSTALL.md`](../../docs/INSTALL.md) (Тир 1/Тир 2 с нуля).

Профиль `relationship` в консолидированном контейнере `hermes` (`/opt/data/profiles/relationship/`),
по образцу `deploy/health`. Изоляция = отдельный `HERMES_HOME`, отдельный бот, allowlist=пользователь,
свой gbrain-индекс.

> **⚠️ Топология сервера (с 15.06.2026):** все профили живут в ОДНОМ контейнере `hermes`
> (стек `/home/hermes/hermes/`, volume `/home/hermes/hermes/hermes-home → /opt/data`).
> Профиль relationship: `/opt/data/profiles/relationship/`. Операции —
> `docker exec -u 1101 -e HERMES_HOME=/opt/data/profiles/relationship hermes hermes …`

---

## Структура на сервере

```
/opt/data/profiles/relationship/
├── config.yaml          # скопирован из deploy/relationship/config.yaml.example
├── .env                 # скопирован из deploy/relationship/.env.example (заполнен)
├── auth.json            # hermes setup / provider env var (openai-codex + xai)
├── gb                   # обёртка gbrain (создаётся install-gbrain.sh)
├── .bun/bin/gbrain      # бинарь gbrain 0.42.53.0 (создаётся install-gbrain.sh)
├── scripts/             # ← СЮДА копировать *.sh из workspace перед регистрацией кронов
│   ├── brain-maintain.sh
│   ├── install-gbrain.sh
│   └── gbrain-config.sh
├── workspace/
│   └── relationship-ai/ # git clone этого репо
│       ├── knowledge/   # теория → gbrain (embedder); слои: attachment ifs schema-therapy
│       │                #   communication systemic family (+ _meta, templates, RESOLVER, schema)
│       ├── protocols/   # «шляпы» агента (brain-first, weekly-review, ...)
│       ├── hermes/      # SOUL.md — персона агента
│       ├── skills/      # Hermes-скилы (Фаза 3; сейчас пустая директория — безвредно)
│       ├── people/      # ← GITIGNORED; личные страницы людей; только локально, НЕ в embedder
│       ├── self/        # ← GITIGNORED; личный профиль пользователя; только локально, НЕ в embedder
│       ├── contexts/    # ← GITIGNORED; контексты разговоров; только локально, НЕ в embedder
│       └── scripts/     # источник — cp *.sh → ../scripts/ (выше)
└── MEMORY.md  USER.md   # curated-память (создаётся Hermes автоматически)
```

**Приватность:** `people/`, `self/`, `contexts/`, аудио и транскрипты — gitignored,
хранятся только локально в volume, НЕ идут в embedder; поиск по ним grep/file.
В gbrain-embedder идёт ТОЛЬКО `knowledge/` (общая теория, без PII).

---

## Bootstrap — порядок шагов (строго по порядку)

### 1. Подготовить HERMES_HOME профиля

```bash
ssh hermes@<server>
mkdir -p /opt/data/profiles/relationship/scripts
```

### 2. Клонировать репо в workspace

```bash
mkdir -p /opt/data/profiles/relationship/workspace
git clone <relationship-ai-repo-url> /opt/data/profiles/relationship/workspace/relationship-ai
```

> **Публичного remote нет.** Репо локальный или закрытый. При деплое с локальной машины —
> положи архив или используй `rsync`. Пуш в публичный remote не делать — данные интимные.

### 3. Создать `.env` и `config.yaml`

```bash
# .env — заполнить TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS (только id пользователя),
#         TELEGRAM_HOME_CHANNEL, LITELLM_API_KEY, XAI_API_KEY
cp /opt/data/profiles/relationship/workspace/relationship-ai/deploy/relationship/.env.example \
   /opt/data/profiles/relationship/.env

# config.yaml — при необходимости скорректировать модель
cp /opt/data/profiles/relationship/workspace/relationship-ai/deploy/relationship/config.yaml.example \
   /opt/data/profiles/relationship/config.yaml
```

Ключевые переменные `.env`:

| Переменная | Значение |
|---|---|
| `TELEGRAM_BOT_TOKEN` | токен **нового** бота relationship (BotFather → `/newbot`) |
| `TELEGRAM_ALLOWED_USERS` | только telegram_id пользователя |
| `TELEGRAM_HOME_CHANNEL` | личный канал или чат пользователя |
| `LITELLM_API_KEY` | OpenRouter sk-or-... (для gbrain-embedder) |
| `XAI_API_KEY` | xAI-ключ (для STT голосовых сообщений) |

> **Новый бот — обязательно.** Это должен быть отдельный бот (`relationship-bot`),
> отдельный от любых других ботов. Allowlist — только владелец.

### 4. Установить gbrain (install-gbrain.sh)

```bash
docker exec -u 1101 -e HERMES_HOME=/opt/data/profiles/relationship hermes bash -lc \
  'bash /opt/data/profiles/relationship/workspace/relationship-ai/scripts/install-gbrain.sh'
```

Скрипт:
- **fast-path (мультипрофильный сервер):** копирует весь `.bun/` (bun + gbrain) из
  соседнего профиля (content или health);
- **fallback (первый/единственный профиль, соседа нет):** канонная установка gbrain —
  `git clone https://github.com/garrytan/gbrain.git && bun install && bun link`
  (Bun ≥1.3.10) либо бинарь из [релизов](https://github.com/garrytan/gbrain/releases).
  Если ни то ни другое не удалось — скрипт падает с внятной инструкцией (см. gbrain
  `INSTALL_FOR_AGENTS.md` и `docs/INSTALL.md`, Тир 2), а не с криптичной ошибкой;
- создаёт обёртку `/opt/data/profiles/relationship/gb` (GBRAIN_HOME + LITELLM_API_KEY + PATH).

### 5. Инициализировать gbrain (PGlite)

**ВАЖНО:** запускаем `init --pglite` (не апгрейд с 0.35 — мажорные миграции сломают схему).

```bash
docker exec -u 1101 hermes bash -lc \
  'export GBRAIN_HOME=/opt/data/profiles/relationship; \
   /opt/data/profiles/relationship/.bun/bin/gbrain init --pglite'
```

### 6. Синхронизировать скрипты через bootstrap.sh

⚠️ Крон резолвит `--script name.sh` относительно `HERMES_HOME/scripts/`
(= `/opt/data/profiles/relationship/scripts/`), а НЕ из workspace репо. Раньше
это был ручной `cp` (легко забыть после правки скрипта). Теперь — **идемпотентный
`scripts/bootstrap.sh`**, который в т.ч. re-синхронизирует скрипты в profile
scripts-dir (шаги 4/6 install-gbrain + init + config + cp scripts + import).
Повторный запуск безопасен и печатает `already installed` / `updated`.

```bash
docker exec -u 1101 -e HERMES_HOME=/opt/data/profiles/relationship hermes bash -lc \
  'bash /opt/data/profiles/relationship/workspace/relationship-ai/scripts/bootstrap.sh'
```

> `bootstrap.sh` — тонкая обёртка над внешними `hermes`/`gbrain`; НЕ запускает
> интерактивный `hermes setup` и host-level `docker compose up` (их печатает как
> ручные шаги). Если гоняешь шаги вручную — синхронизацию скриптов всё равно делает
> bootstrap (не отдельный `cp`).

### 7. Настроить эмбеддер (gbrain-config.sh)

```bash
docker exec -u 1101 -e HERMES_HOME=/opt/data/profiles/relationship hermes bash -lc \
  'bash /opt/data/profiles/relationship/workspace/relationship-ai/scripts/gbrain-config.sh'
```

Пишет `$GBRAIN_HOME/.gbrain/config.json`: `embedding_model: litellm:text-embedding-3-small`,
`embedding_dimensions: 1536`, `provider_base_urls.litellm: https://openrouter.ai/api/v1`.
Нужен LITELLM_API_KEY (sk-or-...) в `.env`.

### 8. Авторизовать модель (провайдер)

`hermes login` **удалён**. Авторизация модели теперь — через `hermes setup` (интерактивный
мастамер) либо через env-переменную провайдера в `.env` (без интерактива).

```bash
# Вариант А — интерактивный мастер (создаёт/обновляет auth.json):
docker exec -it -u 1101 -e HERMES_HOME=/opt/data/profiles/relationship hermes hermes setup
# Вариант Б — ключ провайдера в .env (без интерактива), напр. для OpenRouter:
#   OPENROUTER_API_KEY=sk-or-...    # либо ANTHROPIC_API_KEY / XAI_API_KEY — по выбранному провайдеру
# Вариант В — скопировать auth.json существующего профиля (если провайдер там уже авторизован):
#   cp /opt/data/profiles/<другой>/auth.json /opt/data/profiles/relationship/auth.json
```

> **Провайдер модели — сменный.** `openrouter` / `anthropic` / `xai` / … — выбор за тобой;
> `openai-codex` / `gpt-5.5` — это просто выбор автора, не требование. Нужен только ключ
> выбранного провайдера (`OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY` / `XAI_API_KEY`).

> **Спайк авторизации:** `openai-codex` (модель) + `xai` (STT) из одного `auth.json` —
> доказано профилем content (xai primary + openai-codex fallback в одном auth.json).

### 9. Запустить профиль

> **Preflight (обязательно ДО `docker compose up`):** запусти read-only доктора
> внутри контейнера с выставленным `HERMES_HOME` — он проверит .env (5 ключей,
> без вывода значений), наличие `hermes`/`gb` на PATH, дрейф скриптов, права на
> logs и включён ли gbrain, ничего не меняя:
>
> ```bash
> docker exec -u 1101 -e HERMES_HOME=/opt/data/profiles/relationship hermes bash -lc \
>   'bash /opt/data/profiles/relationship/workspace/relationship-ai/scripts/doctor.sh'
> ```
>
> Локально на чистом checkout (без сервера) достаточно `bash scripts/verify.sh`
> (render --check + тесты + privacy + structure).

```bash
cd /home/hermes/hermes
HERMES_UID=$(id -u) HERMES_GID=$(id -g) \
  docker compose --env-file /opt/data/profiles/relationship/.env -f compose.yaml -p hermes up -d
```

> **`.env` — сверка переменных:** compose-команда читает `.env` через `--env-file`
> и берёт из него только TELEGRAM_*/LITELLM_*/XAI_* (+ OPENAI_API_KEY legacy).
> Проект (`-p hermes`), image и имя контейнера заданы стеком/командной строкой, а
> `HERMES_UID/GID` — inline `$(id -u)`/`$(id -g)`. Старые `HERMES_IMAGE` /
> `HERMES_HOST_HOME` / `HERMES_COMPOSE_PROJECT=hermes-relationship` /
> `HERMES_CONTAINER_NAME=…-gateway` / `HERMES_UID=1000` из `.env.example` удалены как
> устаревшие (описывали отдельный контейнер; сейчас все профили в одном `hermes`).

Проверить:

```bash
docker exec -u 1101 -e HERMES_HOME=/opt/data/profiles/relationship hermes hermes profile list
docker logs hermes --tail 50
```

### 10. Импортировать knowledge в gbrain

После `gbrain init --pglite` — проиндексировать только общие знания (knowledge/).
Личные разделы `people/`, `self/`, `contexts/` не импортируем и не эмбедим:
агент читает их через file/grep (brain-first.md).
Один каталог на вызов (multi-arg `gb import a/ b/` молча берёт только первый — грабля):

```bash
docker exec -u 1101 hermes bash -lc '
  P=/opt/data/profiles/relationship
  W=$P/workspace/relationship-ai
  for d in attachment ifs schema-therapy communication systemic family; do
    "$P/gb" import "$W/knowledge/$d/"
  done
  "$P/gb" embed --stale
'
```

### 11. Зарегистрировать крон-ритуалы

После того как контейнер запущен и скрипты скопированы в `scripts/` — см. `cron-rituals.md`.
Порядок: сначала no-agent-крон (brain-maintain), затем агентные (обзор, стиль).

---

## Эксплуатация без редеплоя

Большинство изменений — живые (правки файлов, reindex через `gb import`):

- `/reload-skills` в чат боту — пересканировать каталог скилов (после правки SKILL.md).
- `/reload-mcp` — после изменения `mcp_servers` в config.yaml.
- `/reset` или `/new` — обновить авто-список навыков в системном промпте.
- `/restart` — перезапустить профиль (предпочтительно; роняет только relationship).

Изменения config.yaml:

```bash
# Редактировать профильный config на сервере:
nano /opt/data/profiles/relationship/config.yaml
# Затем через чат: /restart
```

Изменения скриптов — повторить шаг 6 (`bash scripts/bootstrap.sh`, идемпотентно
re-синхронизирует скрипты в profile scripts-dir).

Reindex knowledge после правок:

```bash
docker exec -u 1101 hermes bash -lc \
  '/opt/data/profiles/relationship/gb import \
   /opt/data/profiles/relationship/workspace/relationship-ai/knowledge/attachment/ && \
   /opt/data/profiles/relationship/gb embed --stale'
```

---

## Чек-лист изоляции (acceptance gate)

После полного деплоя пройти все пункты:

- [ ] **Бот отвечает только пользователю:** написать боту с чужого аккаунта → получить отказ или молчание.
  ```bash
  # Проверить TELEGRAM_ALLOWED_USERS в .env — должен содержать только id пользователя
  grep TELEGRAM_ALLOWED_USERS /opt/data/profiles/relationship/.env
  ```

- [ ] **gbrain находит известный концепт:**
  ```bash
  docker exec -u 1101 -e HERMES_HOME=/opt/data/profiles/relationship hermes \
    /opt/data/profiles/relationship/gb search "four horsemen"
  # Ожидать: результат из knowledge/communication/ (Gottman)
  ```

- [ ] **Нет PII в git:**
  ```bash
  cd /opt/data/profiles/relationship/workspace/relationship-ai
  git ls-files | grep -E "^(people|self|contexts)/" \
    && echo "LEAK!" || echo "OK: no personal data tracked"
  git ls-files | grep -E "\.env$|auth\.json" \
    && echo "LEAK!" || echo "OK: no secrets"
  ```

- [ ] **knowledge/ идёт в gbrain, people/ — нет:**
  ```bash
  # gbrain search находит контент knowledge/:
  /opt/data/profiles/relationship/gb search "IFS parts"
  # Ожидать: результат из knowledge/ifs/
  ```

- [ ] **Изоляция профилей:** данные relationship не видны другим профилям.
  ```bash
  ls /opt/data/profiles/relationship/   # ≠ /opt/data/profiles/health/
  ```

- [ ] **Крон доставляет в home-channel:** дождаться ближайшего срабатывания стиль-бэкстопа (23:30)
  и убедиться, что сообщение (или тишина при отсутствии правок) пришло корректно.

---

## Rollback

При проблемах с профилем:

```bash
# 1. Вернуть config к рабочей версии:
git -C /opt/data/profiles/relationship/workspace/relationship-ai checkout deploy/relationship/config.yaml.example
cp /opt/data/profiles/relationship/workspace/relationship-ai/deploy/relationship/config.yaml.example \
   /opt/data/profiles/relationship/config.yaml

# 2. Перезапустить профиль через чат: /restart
# Или принудительно:
docker exec -u 1101 -e HERMES_HOME=/opt/data/profiles/relationship hermes hermes restart
```

При полном пересоздании контейнера (роняет ВСЕ профили — согласовать):

```bash
cd /home/hermes/hermes
HERMES_UID=$(id -u) HERMES_GID=$(id -g) \
  docker compose --env-file /opt/data/profiles/relationship/.env -f compose.yaml -p hermes up -d
```

---

## Открытые вопросы (деплой) — статус после разведки

1. **Авторизация (codex + xai в одном `auth.json`) — ✅ РЕШЕНО.** Профиль `content`
   (`deploy/content-trendwatch/`) доказывает сосуществование: xai primary + `openai-codex` fallback
   в одном `auth.json`. Для relationship: модель `openai-codex` через `hermes setup` (или
   ключ провайдера в `.env`); STT `xai` — проще всего `XAI_API_KEY` в `.env` (либо xai-creds
   в auth.json). В config добавлен `fallback_providers: xai/grok-4.3`. Провайдер сменный —
   `openai-codex`/`gpt-5.5` лишь выбор автора; подойдёт `openrouter`/`anthropic`/`xai`/….
2. **Точный id модели — проверить `hermes models list`.** Цель `gpt-5.5`; известно-рабочий
   аналог `gpt-5.3-codex` (профиль content). Если 5.5 ещё не в образе — временно `gpt-5.3-codex`.
3. **Эмбеддер — ✅ РЕШЕНО через OpenRouter (проверено эмпирически).** OpenRouter отдаёт
   `text-embedding-3-small` по OpenAI-wire (HTTP 200, 1536 dims). Настройка через `scripts/gbrain-config.sh`.
4. **gbrain установка — ✅ РЕШЕНО.** `install-gbrain.sh` fast-path'ом копирует рабочий
   `.bun/` из соседнего профиля (content или health); если соседа нет (первый/единственный
   профиль) — fallback на канонную установку (`git clone garrytan/gbrain && bun install &&
   bun link`, либо релизный бинарь). Затем `gbrain init --pglite`.
5. **Активация семантики:** `gbrain init --pglite` → **`scripts/gbrain-config.sh`** (эмбеддер→OpenRouter)
   → `gb import` knowledge-слоёв → `gb embed --stale` → `mcp_servers.gbrain.enabled: true` в `config.yaml`.
   До этого knowledge работает грепом (brain-first.md).
6. **Скилы (Фаза 3).** `skills/external_dirs` уже прописан в config.yaml; директория `skills/`
   сейчас пустая — это безвредно. Скилы появятся в Фазе 3 (process-conversation, add-context, и др.).
7. **Большие аудио (>20 МБ).** Голосовые в Telegram ≤20 МБ проходят без overlay.
   Если понадобится слать большие записи разговоров — поднять `compose.tg-bot-api.yaml` (локальный Bot API).
8. **(Опционально) нативный gbrain `dream`:** потребует `ANTHROPIC_API_KEY`; по умолчанию синтез и поиск
   противоречий делает агент (GPT-5.5) в weekly-review — ключ не нужен.
