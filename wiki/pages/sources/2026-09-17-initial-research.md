---
title: Первичный ресёрч источников
type: source
tags: [research, 2026-09]
created: 2026-09-17
updated: 2026-09-17
sources: [https://ui.shadcn.com/r/registries.json, https://voiceorbs.vercel.app/llms.txt]
---

# Первичный ресёрч, 2026-09-17

Отправная точка — https://voiceorbs.vercel.app, который пользователь привёл как
образец желаемого паттерна: галерея + live-конфигуратор (state/speed/size/color)
+ «Copy AI prompt» + «View code» + StackBlitz.

## Что нашлось на самом voiceorbs

`llms.txt` и `llms-full.txt`. Второй — полный дамп исходников всех 14 орбов плюс
общая библиотека и гайд по интеграции. То есть весь сайт читается одним curl.
Это задало иерархию [[access-methods]].

## Как расширяли

1. `ui.shadcn.com/r/registries.json` — **354 реестра** с health-скорами.
   Фильтр описаний по `3d|webgl|shader|animat|particle|scroll|parallax|gsap|
   effect|canvas|glass|cursor` дал 103 из 354. Отсюда же вырос
   [[shadcn-registry-protocol]] и живой слой [[two-layer-registry]].
2. `birobirobiro/awesome-shadcn-ui` ⭐20.5k, `terkelg/awesome-creative-coding` ⭐15.3k,
   `AxiomeCG/awesome-threejs`, `sjfricke/awesome-webgl`.
3. GitHub org enumeration: `api.github.com/orgs/codrops/repos` — 345 демо-репозиториев.
4. Web search на форму вещи, затем **проба каждого кандидата**. Поиск легко выдаёт
   SEO-мусор; проба отделяет реальные источники от листиклов.

## Найденные стены

`uiverse.io`, `lottiefiles.com`, `shadertoy.com` — 403 и для curl, и для headless
Chromium. Для uiverse рабочий путь — зеркало `uiverse-io/galaxy` ⭐12.9k MIT,
но последний push 2024-09, то есть зеркало отстаёт от живого сайта.

`motion-primitives.com` и `cult-ui.com` — 429 при частых запросах, не постоянная блокировка.

## Проверенные цифры

react-bits 688 элементов · ui-layouts 327 · aceternity 278 · magicui 250 ·
aicanvas 178 · kokonutui 51 · shadcn.io 57 шейдеров · Codrops 345 репозиториев.

## См. также

- [[../../data/sources.json|sources.json]] · [[two-layer-registry]]
