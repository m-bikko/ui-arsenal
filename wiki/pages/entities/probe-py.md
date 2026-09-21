---
title: scripts/probe.py
type: entity
tags: [script, probe]
created: 2026-09-17
updated: 2026-09-17
sources: [scripts/probe.py]
---

# probe.py

Определяет, какие способы доступа у сайта реально работают. Единственный
легитимный источник поля `access` в [[sources-json]].

Порядок проверок повторяет [[access-methods]]: `llms-full` → `llms.txt` →
официальный каталог shadcn → эвристика `/r`, `/registry`, корень → `.md`-двойник →
GitHub-репозиторий со страницы → простая доступность → детект bot-wall.

Детект bot-wall: код 403/429/503, либо 200 с маркерами
`cloudflare|just a moment|enable cookies|you have been blocked|captcha|cf-ray`
в первых 6 КБ. Тогда в `access` попадает `browse-headed` с явной пометкой
«не повторяй `$B goto`».

Замечание по точности: urllib с браузерным User-Agent иногда проходит там, где
curl и headless получают 403 (наблюдалось на uiverse.io). Поэтому вердикт
«стена» проверяется и вручную, а не только пробой.

## См. также

- [[add-source-py]] · [[access-methods]]
