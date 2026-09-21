---
title: scripts/fetch.py
type: entity
tags: [script, fetch]
created: 2026-09-17
updated: 2026-09-17
sources: [scripts/fetch.py]
---

# fetch.py

Достаёт машиночитаемый контент без браузера. Четыре подкоманды:
`llms`, `index`, `item`, `md`.

`index` и `item` реализуют [[shadcn-registry-protocol]] и работают против **любого**
из 354 реестров. Резолвинг: `react-bits` → `@react-bits` → живой каталог → реальный
шаблон URL. То есть агенту не нужно помнить, что у Aceternity путь `/registry`.

`fetch.py item` — самая ценная команда скилла: актуальный исходник, инлайн,
без установки и без браузера.

## См. также

- [[shadcn-registry-protocol]] · [[access-methods]]
