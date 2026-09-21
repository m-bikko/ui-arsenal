---
title: Протокол shadcn-реестра
type: entity
tags: [protocol, registry, shadcn]
created: 2026-09-17
updated: 2026-09-17
sources: [https://ui.shadcn.com/docs/registry, scripts/fetch.py]
---

# Протокол shadcn-реестра

Главное открытие ресёрча 2026-09-17 ([[2026-09-17-initial-research]]).

## Механика

Каталог всех реестров: `https://ui.shadcn.com/r/registries.json` — на 2026-09-17
**354 записи**, каждая с `name`, `homepage`, `url` (шаблон вида
`https://site/r/{name}.json`), `description` и `health` (score, availability7d/30d).

У каждого реестра:

- `<base>/registry.json` → список всех элементов;
- `<base>/<item>.json` → один элемент **с полным содержимым каждого файла инлайн**,
  плюс `dependencies`, `devDependencies`, `registryDependencies`.

## Почему это важно

Можно прочитать настоящий, актуальный исходник компонента **не устанавливая
ничего и не открывая браузер**. Один curl.

Проверено на react-bits (688 элементов), magicui (250), aceternity (278),
ui-layouts (327), kokonutui (51), aicanvas (178), originui.

## Ловушки

- Базовый путь различается: у большинства `/r`, у Aceternity `/registry`,
  у Motion Primitives `/c`. [[fetch-py]] берёт реальный шаблон из живого каталога.
- `index.json` есть не везде, `registry.json` — везде.
- React Bits кодирует вариант суффиксом: `-JS-CSS`, `-JS-TW`, `-TS-CSS`, `-TS-TW`.
- AI Canvas без залогина: `npx shadcn add` завершается с кодом **0**, но пишет
  заглушку `(free account required)`. Проверять файл, а не код возврата.

## См. также

- [[fetch-py]] · [[two-layer-registry]] · [[access-methods]]
