# Схема вики ui-arsenal

Obsidian-friendly. Связи — через `[[wikilinks]]`, они и строят Graph View.

## Структура

```
wiki/
├── CLAUDE.md   этот файл
├── index.md    каталог страниц по типам
├── log.md      хронология операций
├── raw/assets/ картинки, если появятся
└── pages/{entities,concepts,sources,analyses}/
```

## Frontmatter

```yaml
---
title: Название
type: entity | concept | source | analysis
tags: [тег]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [пути или URL]
---
```

## Правила для этой вики

- Язык контента — русский, технические термины не переводим.
- Имена файлов — kebab-case, английский.
- Не дублируй `SKILL.md` и `references/*` — давай wikilink и пиши только то,
  чего там нет: решения, причины, отвергнутые альтернативы.
- Не храни здесь список источников — он в `data/sources.json`, машиночитаемый.
  Вики объясняет *почему* реестр устроен так, а не *что* в нём лежит.
- Триггер на обновление: меняется схема `sources.json`, добавляется скрипт,
  меняется иерархия способов доступа, или найден новый bot-wall.
