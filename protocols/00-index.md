# Протоколы — реестр

Протокол — пошаговый алгоритм типовой операции: что её запускает, что она читает
и что отдаёт. `red-flags.md` действует ВСЕГДА, поверх любого протокола.

| Протокол | Триггер | Результат |
|---|---|---|
| [process-conversation.md](process-conversation.md) | войс/текст разговора с кем-то → разбор → пишет `conversations/`, обновляет `map.md`, `commitments.md`, `next.md` | артефакты в `people/<slug>/conversations/` + выжимка пользователю |
| [multi-lens-read.md](multi-lens-read.md) | ситуация / паттерн → прогон через 2–3 оптики (attachment / ifs / schema / systemic) + обязательный вклад пользователя | со-мышление в чате, предложение обновить `map.md` |
| [commitment-track.md](commitment-track.md) | фиксация / ревизия обещаний; просроченные / асимметричные → сигнал пользователю | обновление `people/<slug>/commitments.md` |
| [pre-conversation-memo.md](pre-conversation-memo.md) | Пользователь идёт на важный разговор («памятка по X», «скоро встреча») | памятка в Telegram ≤ 15 строк, читает `map.md` / `next.md` / `commitments.md` |
| [weekly-review.md](weekly-review.md) | крон (вс) или «обзор» | одно сообщение: движутся / внимание / просроченные коммитменты / на неделю |
| [decision-support.md](decision-support.md) | крупное решение по связи (сходиться / расходиться / брать ли в кофаундеры) | со-мышление: углы + вопросы, не вердикт |
| [red-flags.md](red-flags.md) | ВСЕГДА; признаки абьюза / токсичности / манипуляции / опасности | ⚠️ отдельным сообщением сразу; граница «это про живого специалиста» |
| [crisis-support.md](crisis-support.md) | острое эмоциональное состояние, разрыв, конфликт только что | поддержка zero-judgment, минимальный следующий шаг |
| [brain-first.md](brain-first.md) | перед разбором любой ситуации или созданием страницы knowledge | чтение `knowledge/RESOLVER.md` + релевантных страниц → дедуп |
| [memory.md](memory.md) | «помнишь, мы...» / новый долговременный факт о работе с пользователем / важное должно всплывать | `session_search` → `memory` (USER.md / MEMORY.md) → файл; маршрутизация по типу |
| [self-improvement.md](self-improvement.md) | пробел базы / фидбэк «не то» / пользователь переспрашивает / brain-first пропущен | строка в `_gaps/queue.md`; правка `knowledge/_meta/preferences.md` |
| [co-thinking.md](co-thinking.md) | «застрял / не знаю / помоги разобраться» | со-мышление: присутствие → база → линзы → свежий угол |
| [new-request-playbook.md](new-request-playbook.md) | ситуация или паттерн без плейбука в `knowledge/playbooks/` | черновик плейбука + строка в индексе после ок пользователя |
| [add-context.md](add-context.md) | голос/текст с новым фактом о человеке из базы | запись в `people/<slug>/notes.md` + при значимости обновление `profile.md` / `map.md` |
| [life-interview.md](life-interview.md) | «хочу рассказать о себе подробно», онбординг, «составь карту меня и моих отношений» | `self/map.md` + `self/spheres/` + `people/<slug>/` карточки + `self/interview-progress.md` |
| [pattern-review.md](pattern-review.md) | по запросу: «покажи паттерны / что у меня повторяется» → читает `self/map.md` + `people/*/map.md` + разговоры | 2–4 повторяющихся темы ACROSS entities как гипотезы + вклад пользователя; пусто → честно «нет данных, давай онбординг». НЕ nightly `/patterns` из gbrain |

## Основные цепочки

**Разговор:** `process-conversation` → `commitment-track` (новые обещания) →
обновление `map.md` / `next.md`. При паттерне → `multi-lens-read`.

**Перед встречей:** `pre-conversation-memo` → читает `map.md` + `next.md` + `commitments.md`.

**Решение:** `decision-support` → `multi-lens-read` (углы) → пользователь решает.

**Неделя:** `weekly-review` → читает все `map.md` + `commitments.md` →
флажит противоречия и просроченное → `commitment-track` при ревизии.

**Кризис:** `crisis-support` → `red-flags` (всегда параллельно) → поддержка.

**Мета:** `brain-first`, `co-thinking`, `red-flags`, `memory`, `self-improvement` — поверх всего.
