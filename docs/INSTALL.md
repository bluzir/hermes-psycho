# Установка — с нуля до работающего AI-психолога

Этот репозиторий — **контент/методология-пак**, а не сам движок. Рантайм — два внешних
**публичных** фреймворка:

- **[hermes-agent](https://github.com/NousResearch/hermes-agent)** — гейтвей/CLI: Telegram-бот,
  сессии, крон-ритуалы, свободно переключаемый провайдер модели.
- **[gbrain](https://github.com/garrytan/gbrain)** — семантический корпус (embedder + поиск) над
  теорией из `knowledge/`; работает встроенно (PGLite, без сервера) и умеет отдавать себя как
  MCP-сервер.

Ниже — два тира. Выбери один по тому, что тебе нужно:

- **Тир 1 — быстрый локальный** (Claude Code / любой кодинг-агент): без сервера, без Telegram.
  Самый быстрый способ пощупать опыт.
- **Тир 2 — полный self-host** (как у автора): Telegram-бот + gbrain + cron.

Сравнение — в таблице [в конце](#сравнение-тиров).

---

## Тир 1 — Быстрый локальный (агент + gbrain MCP, без сервера и Telegram)

Ты общаешься с методологией прямо в своём кодинг-агенте (Claude Code, Cursor и т. п.).
Ни контейнера, ни бота, ни крона — только репо на диске и агент, которому ты объясняешь правила игры.

### 1. Клонируй репо

```bash
git clone <hermes-psycho-repo-url> hermes-psycho
cd hermes-psycho
```

### 2. (Рекомендуется) Подними gbrain для семантического поиска по теории

Без gbrain агент ищет по `knowledge/` через grep — это работает. gbrain **добавляет** семантический
поиск (по смыслу, не по словам). Ставь **канонично** — не через `npm i -g` / `bun add -g`
(там пакет-сквоттер и сломанный postinstall):

```bash
git clone https://github.com/garrytan/gbrain.git ~/gbrain && cd ~/gbrain \
  && curl -fsSL https://bun.sh/install | bash \
  && export PATH="$HOME/.bun/bin:$PATH" \
  && bun install && bun link
```

Дальше — ключ для эмбеддингов (OpenAI как пример; всего 14 провайдеров, список —
`gbrain providers list`), инициализация встроенной базы, импорт теории и индексация:

```bash
export OPENAI_API_KEY=sk-...
cd /path/to/hermes-psycho
gbrain init                    # встроенный PGLite, без сервера
gbrain import knowledge/       # загрузить методологию
gbrain embed --stale           # проиндексировать новое/изменённое
gbrain doctor                  # самопроверка
```

Подключи gbrain как MCP-сервер в свой агент. В конфиге `mcpServers`:

```json
{
  "gbrain": {
    "command": "gbrain",
    "args": ["serve"]
  }
}
```

`gbrain serve` поднимает MCP по stdio — так его видит Claude Code / Cursor и может искать по корпусу
теории семантически.

### 3. Наведи агента на методологию

Скажи агенту (одним сообщением, дословно можно так):

> Действуй по `hermes/SOUL.md` + `protocols/` (маршрутизатор — `knowledge/RESOLVER.md`);
> мои данные в `self/` и `people/`.

Так агент понимает: персона — в `hermes/SOUL.md`, «как работать» — в `protocols/`, каждую ситуацию
он сначала прогоняет через `knowledge/RESOLVER.md` (ситуация → слой → протокол), а личный контекст
читает из `self/` и `people/`.

### 4. Пройди онбординг

Попроси агента: **«хочу рассказать о себе»** — это запускает
[life-interview](../protocols/life-interview.md): агент по блокам задаёт по 2–3 вопроса и наполняет
`self/` (карту) и `people/` (карточки людей). Пока карта пуста, разборы будут generic.

### 5. Скармливай разговоры текстом

Вставляй диалоги/пересказы как обычный текст в чат агента и проси разобрать
(«разбери разговор с X», «прогони через оптики»). Артефакты — в `self/`, `people/`, `contexts/`.

### Честные оговорки Тира 1

- **Нет Telegram**, **нет голосового ввода (STT)**, **нет крон-ритуалов** — это методология
  в чате агента, а не живущий сам по себе бот.
- **grep-режим работает и без gbrain.** gbrain нужен только для семантического поиска по теории;
  без него агент всё равно читает `knowledge/` напрямую.

---

## Тир 2 — Полный self-host (Telegram-бот + gbrain + cron)

Как у автора: агент живёт в контейнере, отвечает в Telegram, ночью гоняет ритуалы. Ставим с нуля.

### 1. Установи hermes-agent и настрой его

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

Затем мастер настройки:

```bash
hermes setup     # выбор провайдера/модели + мессенджер
```

`hermes setup` спрашивает провайдера — это **openrouter / anthropic / …** на твой выбор,
**не обязательно** codex. Провайдер свободно меняется потом через `hermes model`.
Аутентификация — через `hermes setup` или переменные окружения
(`OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY` / и т. д.). Отдельной команды `hermes login` **нет**.

Telegram-гейтвей:

```bash
hermes gateway setup   # bot token от @BotFather, allowed user IDs от @userinfobot, home-канал
hermes gateway         # запустить гейтвей
```

Docker-вариант (если поднимаешь в контейнере):

```bash
HERMES_UID=$(id -u) HERMES_GID=$(id -g) docker compose up -d
```

### 2. Установи gbrain (канонично)

```bash
git clone https://github.com/garrytan/gbrain.git ~/gbrain && cd ~/gbrain \
  && curl -fsSL https://bun.sh/install | bash \
  && export PATH="$HOME/.bun/bin:$PATH" \
  && bun install && bun link
export OPENAI_API_KEY=sk-...   # эмбеддинги (14 провайдеров: gbrain providers list)
gbrain init                    # встроенный PGLite, без сервера
```

### 3. Положи hermes-psycho как workspace профиля

Клонируй этот репо в workspace профиля и наведи профиль на его `knowledge/` / `protocols/` /
`hermes/SOUL.md`. Ориентир по проводке профиля — [`hermes-profile.yaml`](../hermes-profile.yaml)
и ранбук [`deploy/relationship/README.md`](../deploy/relationship/README.md).

> ⚠️ **Ранбук написан под мульти-профильный сервер автора** (несколько профилей в одном контейнере,
> кастомные `HERMES_HOME` вида `/opt/data/profiles/...`). Одиночному новичку это не нужно: бери
> **дефолты фреймворка** — один `~/.hermes`, один гейтвей. Из ранбука тебе полезны логика проводки
> workspace → `knowledge/`/`protocols/`/`SOUL.md` и порядок шагов, а не серверная топология.

### 4. Импортируй теорию в gbrain

```bash
cd /path/to/workspace/hermes-psycho
gbrain import knowledge/
gbrain embed --stale
gbrain doctor
```

В индекс идёт **только** `knowledge/` (общая теория без PII); `self/` / `people/` / `contexts/`
не эмбедятся — агент читает их через grep/файлы.

### 5. Запусти и напиши боту

```bash
hermes gateway
```

Открой своего бота в Telegram, напиши **«хочу рассказать о себе»** — запустится
[life-interview](../protocols/life-interview.md) и наполнит `self/` + `people/`.

### 6. (Опционально) Крон-ритуалы

Ночные/недельные ритуалы (weekly-review, обслуживание gbrain) — по
[`deploy/relationship/cron-rituals.md`](../deploy/relationship/cron-rituals.md).

### Префлайт

Перед запуском прогони проверки пака:

```bash
bash scripts/verify.sh   # render --check + тесты + гейт приватности + гейт структуры
bash scripts/doctor.sh   # диагностика окружения
```

---

## Сравнение тиров

| | **Тир 1 — локальный** | **Тир 2 — self-host** |
|---|---|---|
| **Что получаешь** | Методология в чате кодинг-агента: RESOLVER → протоколы → разборы, семантический поиск по теории (если поднял gbrain MCP) | Полный опыт: Telegram-бот, голосовой ввод (STT), крон-ритуалы, живущий сам по себе агент |
| **Что нужно** | Клон репо + кодинг-агент; опционально gbrain (`init`/`import`/`serve` как MCP) | hermes-agent + `hermes setup` + Telegram (@BotFather / @userinfobot); gbrain (`init`/`import`/`embed`); опционально cron |
| **Порог входа** | Минимальный — минуты, без сервера и контейнера | Выше — установка гейтвея, бот, ключи, (опц.) Docker и cron |
| **Нет** | Telegram, STT, крон | — |

---

## Дальше

- Обзор проекта и структура — [`../README.md`](../README.md)
- Как этим пользоваться (сквозные сценарии) — [`SCENARIOS.md`](SCENARIOS.md)
- Шпаргалка команд/фраз — [`COMMANDS.md`](COMMANDS.md)
- Устройство движка — [`ARCHITECTURE.md`](ARCHITECTURE.md)
