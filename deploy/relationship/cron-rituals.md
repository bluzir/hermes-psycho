# Крон-ритуалы профиля relationship

Создаются один раз после запуска контейнера `hermes` (профиль relationship).
Доставка — в home-канал пользователя (`TELEGRAM_HOME_CHANNEL`).

> **Коррекция CLI:** `schedule` и `prompt` в `hermes cron create` — позиционные аргументы,
> не флаги `--schedule`/`--prompt` (подтверждено по `hermes_cli/main.py`).
> Синтаксис: `hermes cron create "РАСПИСАНИЕ" "ПРОМПТ" --deliver TARGET`

Команды выполняются через `docker exec` в работающем контейнере:

```bash
docker exec -u 1101 -e HERMES_HOME=/opt/data/profiles/relationship hermes hermes cron create "РАСПИСАНИЕ" "ПРОМПТ" --deliver telegram
```

Или через инструмент `cronjob` в чате бота (рекомендуется — не нужен доступ к серверу).

---

## ⚠️ ОБЯЗАТЕЛЬНО ДО РЕГИСТРАЦИИ КРОНОВ: скопировать скрипты в profile scripts-dir

Крон резолвит голое имя `--script` относительно `HERMES_HOME/scripts/`, то есть файл
обязан лежать в **`/opt/data/profiles/relationship/scripts/`** — НЕ в workspace репо.
После каждой правки скрипта — прогнать **идемпотентный `scripts/bootstrap.sh`**
(он re-синхронизирует скрипты в profile scripts-dir; заменяет ручной `cp`):

```bash
docker exec -u 1101 -e HERMES_HOME=/opt/data/profiles/relationship hermes bash -lc \
  'bash /opt/data/profiles/relationship/workspace/relationship-ai/scripts/bootstrap.sh'
```

Источник: `hermes-agent/cron/scheduler.py` — `scripts_dir = _get_hermes_home() / "scripts"`.
Типичная грабля: скрипт лежит в `workspace/relationship-ai/scripts/`, а крон ищет в
`/opt/data/profiles/relationship/scripts/` → падает с `Script not found: ...`.

---

## 1. Недельный обзор — воскресенье 19:00 (UTC)

Обзор по активным людям: просроченные коммитменты, провисшие связи, противоречия
поведение↔ценности, открытые паттерны; синтез делает агент (GPT-5.5) — без gbrain dream.

```bash
docker exec -u 1101 -e HERMES_HOME=/opt/data/profiles/relationship hermes hermes cron create \
  "0 19 * * 0" \
  "Сделай недельный обзор по отношениям (протокол weekly-review): пройди по people/ и self/ за неделю, проверь просроченные коммитменты (people/*/commitments.md), найди противоречия между поведением и ценностями (self/values.md), отметь незакрытые паттерны. Отправь пользователю краткую сводку." \
  --deliver telegram
```

---

## 2. Обслуживание knowledge — ежедневно 03:00 (no-agent)

`gb import` по каждому каталогу knowledge/ (по одному за вызов) → `gb embed --stale` →
`gb lint` / `gb orphans --count` / `gb check-backlinks check`.
Реализован как **no-agent крон со скриптом** — не зависит от cwd/окружения терминала
агента, тихий при успехе.

> **Скрипт должен лежать в `/opt/data/profiles/relationship/scripts/`** — см. блок ⚠️ выше.

```bash
docker exec -u 1101 -e HOME=/opt/data/profiles/relationship -e HERMES_HOME=/opt/data/profiles/relationship hermes bash -lc \
  'export PATH=/opt/hermes/.venv/bin:$PATH; hermes cron create "0 3 * * *" \
   --no-agent --script brain-maintain.sh --name brain-maintain --deliver telegram'
```

---

## 3. Стиль-уроки бэкстоп — ежедневно 23:30

Основной путь самообучения — писать в `knowledge/_meta/preferences.md` В ТОТ ЖЕ ход
при правке пользователя (SOUL «Самообучение» + `protocols/self-improvement.md`). Этот крон —
лишь бэкстоп: добирает пропущенные правки за день. Без PII.

```bash
docker exec -u 1101 -e HERMES_HOME=/opt/data/profiles/relationship hermes hermes cron create \
  "30 23 * * *" \
  "Просканируй сессии за сегодня. Где пользователь поправил стиль/формулировку/термин/формат/выбор оптики или техники — допиши датированную строку в knowledge/_meta/preferences.md (ДАТА — что поправил — как применять дальше). Без PII, без реальных имён. Дубли не плоди. Правок не было — ничего не пиши." \
  --deliver telegram
```

---

## Контроль

Проверить создание и статус крон-задач:

```bash
docker exec -u 1101 -e HERMES_HOME=/opt/data/profiles/relationship hermes hermes cron list
docker exec -u 1101 -e HERMES_HOME=/opt/data/profiles/relationship hermes hermes cron status
```

Дождаться первого срабатывания каждого; убедиться, что доставка в `TELEGRAM_HOME_CHANNEL` работает.

---

## Заметки

- `approvals.cron_mode: approve` в config.yaml обязателен для unattended-выполнения (значение `auto` тихо = deny → крон блокируется).
- Недельный обзор читает `people/` и `self/` грепом/файлами (не через gbrain-embedder): личное там gitignored и в embedder не уходит.
- Лимит STT провайдера `xai` — ~500 МБ на файл (голосовые логи проходят). Большой Bot API overlay (`compose.tg-bot-api.yaml`) **НЕ нужен** для коротких голосовых; для записей разговоров (>20 МБ) — поднять локальный Bot API overlay.
- Синтез и детектор противоречий делает АГЕНТ (GPT-5.5) в weekly-review, не gbrain `dream` (тот захардкожен на Anthropic — ANTHROPIC_API_KEY не нужен).
