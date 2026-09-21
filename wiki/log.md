# Хронология

## [2026-09-17] feat | скилл создан

- Разведка: 354 реестра из `ui.shadcn.com/r/registries.json`, из них 103 с визуальными
  ключевыми словами; awesome-списки; GitHub org Codrops (345 демо-репозиториев).
- Каждый кандидат проверен HTTP-пробой, не по памяти. Записано 42 источника.
- Написаны `search.py`, `fetch.py`, `probe.py`, `add_source.py` (Python 3 stdlib).
- Ключевое открытие: протокол shadcn-реестра (`<base>/registry.json` + `<base>/<item>.json`
  с инлайн-исходниками) работает во всех 354 реестрах → см. [[shadcn-registry-protocol]].
- Записаны bot-walls: uiverse.io, lottiefiles.com, shadertoy.com — 403 и для curl, и для headless.
- `hover-dev` добавлен через `add_source.py` — проверка записи в реестр на живом примере.

## [2026-09-17] docs | правила вынесены в глобальный конфиг

- `~/.claude/rules/ui-sources.md` — человекочитаемый справочник источников,
  способов доступа, стен и лицензий.
- `~/.claude/CLAUDE.md` — секция «🧰 UI Arsenal» со ссылкой на правила и на
  [[../references/maintaining.md|maintaining.md]]. Правило «сначала спроси»
  продублировано там же — см. [[pages/concepts/ask-before-install|ask-before-install]].
- Сквозной тест пройден: search → fetch index → fetch item (233 строки настоящего
  исходника Aurora-TS-TW без установки) → поиск CSS-альтернативы по тегу `zero-deps`.

## [2026-09-17] feat | +33 источника, закрыт пласт прикладного UI

- Реестр 42 → **75**. Добавлены категории, которых в курируемом слое не было
  вообще: графики, дашборды, kanban/gantt/календарь, AI-чат, rich-text редакторы,
  data grid, просмотрщики документов, карты, флаги, видеоплееры, загрузка файлов,
  auth, e-commerce, тосты, error boundary, цветовые системы, ретро/неубрутализм.
- Все 33 добавлены через [[pages/entities/add-source-py|add_source.py]] с живой пробой.
  У всех 33 найдены `shadcn-registry` + `registry-json`, у 15 ещё и `llms-full`.
- `SKILL.md`: таблица маршрутизации разбита на «Effects and visuals» и
  «Application UI» — стала длинной для одного списка.

## [2026-09-17] fix | ложные срабатывания детектора bot-wall

- **Баг.** `BOT_WALL` в [[pages/entities/probe-py|probe.py]] матчил голые слова
  `cloudflare` и `captcha` в первых 6 КБ. Обычные страницы, упоминающие Cloudflare
  в футере или captcha в списке фич, помечались `browse-headed`. Поймано на
  `lytenyte` и `cognicatch` — оба рендерятся в headless нормально.
  Ложный флаг хуже пропущенной стены: он запрещает будущему агенту трогать
  рабочий сайт.
- **Фикс.** Регулярка сужена до формулировок самих интерстишелов
  (`just a moment...`, `attention required! | cloudflare`,
  `enable javascript and cookies to continue`, `cf_chl_opt`,
  `/cdn-cgi/challenge-platform`) плюс порог размера тела 120 КБ.
- **Следствие.** Сузив регулярку, перестали ловить uiverse.io: urllib с браузерным
  UA получает 200, а curl и headless — 403. Добавлена кросс-проверка
  `browse_status()` — запуск самого gstack-браузера. Стена теперь определяется по
  тому клиенту, которым агент и будет ходить. Флаг `--no-browse` отключает.
- Заодно: рядом со стеной больше не предлагается обычный `browse`, и текст caveat
  называет настоящую причину (403 / интерстишел / client-specific).
- Записи `lytenyte` и `cognicatch` перепробованы, caveat снят.

## [2026-09-19] feat | +17 источников, закрыты WebGPU, диаграммы и не-веб

- Реестр 75 → **92**. Живой каталог вырос 354 → 372 за два дня.
- Закрыты пробелы из [[../references/maintaining.md|maintaining.md]] §7:
  WebGPU (`webgpu-samples`), диаграммы и холст (`reactflow`, `tldraw`, `excalidraw`),
  не-веб стеки (`react-native-reusables`, `reanimated`, `moti`, `pow-swiftui`,
  `compose-samples`, `flutter-animate`), подсветка кода (`shiki`).
- Новые категории из каталога: email (`@emailcn`), product tour (`@tour`),
  аудио-waveform (`@waves-cn`), доступность (`@intentui`), SaaS-биллинг
  (`@billingsdk`), агентные интерфейсы (`@inferencesh`).
- `@openpolicy` (cookie-баннеры) **не добавлен**: статус unavailable, доступность 11%.
  Пробел оставлен записанным честно.
- `SKILL.md`: третья таблица маршрутизации «Not the web». Файл вырос до 189 строк —
  вместо нарушения собственного лимита вырезано дублирование
  (таблица способов доступа дублировала `references/access-methods.md`,
  раздел конвенций дублировал глобальный CLAUDE.md).

## [2026-09-19] fix | проба выдавала чужие методы доступа за свои

Два бага одного корня: [[pages/entities/probe-py|probe.py]] сводил URL к origin и
дальше считал общий хост принадлежащим источнику.

- **`github.com` как сайт.** URL вида `https://github.com/owner/repo` давал origin
  `https://github.com`. Проба записывала **собственный `/llms.txt` гитхаба**
  (он реально отдаёт 200) как «дамп исходников библиотеки», а матч по каталогу
  shadcn шёл подстрокой по хосту — и совпадал с `@delego`, одним из шести реестров,
  у которых homepage лежит на github.com. Три записи получили чужой реестр.
- **Фикс.** Введены `CODE_HOSTS` и `PKG_HOSTS`: такие URL резолвятся напрямую в
  git-clone / gh-api / npm и как сайт не пробуются вообще. Матч по каталогу —
  строгое равенство хостов. `pow-swiftui`, `compose-samples`, `flutter-animate`,
  `webgpu-samples` перепробованы.
- **Аудит.** В `maintaining.md` §8 добавлен запускаемый сниппет, который ловит этот
  класс: любая `llms`/`registry` команда, указывающая не на собственный хост записи.
  Прогнан по всем 92 — чисто.

## [2026-09-19] feat | npm-детект и релевантность поиска

- `probe.py` умеет находить npm-пакет: кандидаты из команд установки на странице и
  из `package.json` репозитория, плюс флаг `--npm` как подсказка. Каждый кандидат
  **проверяется по registry.npmjs.org** — инвариант «access только из пробы» цел.
  Для монорепо (xyflow) автодетект не срабатывает, отсюда и флаг.
- `search.py`: добавлены IDF-веса и префиксное совпадение. До фикса запрос
  «react aria» возвращал все React-источники подряд — токен `react` есть в `stack`
  почти каждой записи. «accessibility» не находил тег `accessible`.
  После: «react aria» → `intentui`, «accessibility» → `originui`, `intentui`.
