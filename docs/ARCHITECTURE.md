# Архитектура

Коротко о том, как устроен движок: три слоя, принцип brain-first, разделение публичного и
приватного, где живёт сам фреймворк Hermes и что из фаз ещё не собрано.

---

## Три слоя

| Слой | Ответственность | Куда идёт |
|---|---|---|
| [`knowledge/`](../knowledge/) | методология — общие психологические фреймворки без личных историй (attachment, ifs, schema-therapy, communication, systemic, family, self-regulation) + `RESOLVER.md` (маршрутизатор), `schema.md` (формат страницы) | эмбедится в gbrain (семантический индекс) |
| [`protocols/`](../protocols/) | операционные «шляпы» агента — как обработать разговор, прогнать через оптики, собрать weekly-review, провести онбординг. Реестр — [`00-index.md`](../protocols/00-index.md) | читаются агентом как инструкции |
| [`hermes/SOUL.md`](../hermes/SOUL.md) | персона агента: роль, тон, язык, обращение. Не пишется руками — рендерится из [`hermes-profile.yaml`](../hermes-profile.yaml) | системный промпт агента |

`hermes-profile.yaml` — единственный источник правды: из него `scripts/render-hermes-profile.py`
генерирует `SOUL.md`, `config.yaml.example` и bash-скрипты. Ручная правка сгенерированного = drift,
ловится `scripts/check-hermes-profile.sh`.

---

## Brain-first

Агент работает от базы, а не от догадок. Перед любым разбором он идёт через
[`knowledge/RESOLVER.md`](../knowledge/RESOLVER.md): ситуация → слой → протокол. Сначала читает
релевантные страницы методологии, потом отвечает — и ссылается на конкретные записи, а не на
generic-советы. Пока `self/` и `people/` пусты, опоры нет, и разборы получаются общими; наполняет
их онбординг ([life-interview](../protocols/life-interview.md)).

---

## Приватность: публичное отделено от приватного

Разделение заложено в архитектуру, а не прикручено сбоку:

- **Публичная теория** (`knowledge/`) — git-tracked, эмбедится в gbrain. Ни одного личного факта:
  реальные примеры в `knowledge/` запрещены (`.privacy-denylist` + `check-privacy.sh` роняют сборку
  при утечке PII).
- **Личные данные** (`people/`, `self/`, `contexts/`, `data/`) — в `.gitignore`, живут только на
  локальной машине, **не эмбедятся**. Агент читает их напрямую через grep/файлы. В `config` это
  зафиксировано: `import_policy: public_only`, `synthesis.corpus: public_only`.

Так система может знать о владельце много и при этом не утекать наружу ничем.

---

## Где находится внешний Hermes

`hermes-psycho` — это **контент/конфиг-пак**, а не сам движок. Внешний фреймворк **Hermes**:

- **hermes-agent** — гейтвей/CLI: Telegram-бот, сессии, крон-ритуалы, рантайм-команды
  (`/restart`, `/reload-skills`, …). Живёт в контейнере на сервере, не в этом репо.
- **gbrain** — семантический корпус (embedder + поиск). Индексирует только `knowledge/`.

Этот репо подключается к ним при деплое: клон в workspace контейнера, `gb import knowledge/*`,
`config.yaml` из `deploy/relationship/`. Локально — только авторинг и валидация (см. README,
раздел «Локально vs на сервере»). Ранбук — [`../deploy/relationship/README.md`](../deploy/relationship/README.md).

---

## Честный статус: что уже есть, чего нет

- **Фаза 2 — ещё не собрано:** нет `knowledge/cofounder/` (equity/вестинг/конфликты кофаундеров).
  Пока такие ситуации ведёт `decision-support`, RESOLVER это помечает.
- **Фаза 3 — ещё не собрано:** нет `knowledge/playbooks/` (типовые сложные разговоры с набором
  ходов) и каталог `skills/` пустой (`external_dir` в config прописан — это безвредно).
- **Синтез (dream/think) выключен by design.** `synthesis.dream_enabled` и `think_enabled: false`,
  `corpus: public_only` — ночной gbrain-цикл над reflections намеренно инертен ради приватности
  (не молотить по личным данным). Поэтому **паттерны — по запросу** через
  [pattern-review](../protocols/pattern-review.md) (прогон через
  [multi-lens-read](../protocols/multi-lens-read.md)), а не ночным `/patterns`-циклом.

Подробнее о командах и о `/patterns` — [`COMMANDS.md`](COMMANDS.md).
Сквозные сценарии — [`SCENARIOS.md`](SCENARIOS.md).
