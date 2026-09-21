---
title: data/sources.json
type: entity
tags: [registry, schema]
created: 2026-09-17
updated: 2026-09-17
sources: [data/sources.json]
---

# data/sources.json

Курируемый слой [[two-layer-registry]]. На 2026-09-17 — 42 источника.

## Схема

Корень: `schema_version`, `updated`, `note`, `access_methods` (словарь-документация
всех методов), `sources` (массив).

Запись источника: `id` (kebab-case, уникален), `name`, `url`, `kind`, `why`,
`dimension` (`2d`/`3d`), `tags`, `stack`, `license`, `cost`, `ai_prompt`,
`config_ui`, `access[]`, `verified`. Опционально: `caveat`, `note_for_agent`.

`access[]` упорядочен — первый элемент самый дешёвый. Каждый: `method`, `cmd`, `note`.

## Инварианты

- `access` заполняет только [[probe-py]], никогда не рука. Команда в реестре —
  это обещание, что она работает.
- Исходники компонентов здесь не хранятся. См. [[why-not-vendor-components]].
- `why` — обязательное и содержательное. Это поле будущий агент читает, чтобы
  выбрать источник. [[add-source-py]] режет короткие.
- Добавление необязательного поля безопасно ([[search-py]] игнорирует незнакомые
  ключи). Переименование — нет: нужно grep-нуть все четыре скрипта и поднять
  `schema_version`.

## Что внутри

Заметные записи: `shadcn-registry-index` (мета-вход в живой слой),
`voiceorbs` (эталон паттерна «конфигуратор + AI-промпт»), `codrops`
(345 демо-репозиториев через gh-api), `uiverse` (сайт за Cloudflare, только клон).

## См. также

- [[search-py]] · [[add-source-py]] · [[access-methods]]
