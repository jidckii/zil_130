---
sidebar_position: 1
title: Окружение
---

# Окружение

Всё работает на Linux, Windows и macOS. Для замеров и фото ничего ставить не нужно, эта страница — для тех, кто будет запускать расчёты и модели.

## Что понадобится

| Что | Зачем | Где взять |
|---|---|---|
| git | Получить репозиторий, прислать правки | [git-scm.com](https://git-scm.com/) |
| [uv](https://docs.astral.sh/uv/) | Python 3.13 и зависимости (build123d, Cantera, CoolProp, numpy, scipy, matplotlib) одной командой | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| FreeCAD 1.1 | Смотреть и мерить модели, рендеры | [freecad.org](https://www.freecad.org/downloads.php) |
| Lua 5.4 | Тест скрипта ЭБУ | пакет `lua` вашего дистрибутива |
| Node.js 20+ и yarn | Только для правки этого сайта | [nodejs.org](https://nodejs.org/) |

Для работы со сканами заводских книг пригодятся `djvulibre` (`djvutxt`, `ddjvu`), `poppler` (`pdftotext`, `pdftoppm`) и `ocrmypdf` с русским языком.

## Первый запуск

```bash
git clone https://github.com/jidckii/zil_130.git
cd zil_130
uv sync                                   # Python и все зависимости в .venv
uv run python calc/intake_sizing.py       # пересчитать calc/results.md
uv run python cad/valley_plate.py         # плита развала → cad/out/
uv run python cad/receiver.py             # ресивер и сборка → cad/out/
lua ecu/zil130_test.lua                   # тест Lua-скрипта rusEFI
```

Модели собираются 20–30 секунд, скрипты печатают зазоры и результаты проверок. Файлы `cad/out/*.step` открываются в FreeCAD: **Файл → Открыть** или **Файл → Импорт**.

## Что лежит не в git

- `cad/out/` — STEP, STL и картинки. Они всегда собираются из скриптов.
- Сканы заводских книг (DjVu, PDF) — тяжёлые. В git лежит их текст (`research/sources/ocr/*.txt`) и вырезанные страницы с чертежами (`research/sources/figures/`). Откуда скачать сами книги, сказано в [заводских данных](/repo/research/engine-data), раздел 9.

## Сайт

```bash
cd docs-site
yarn install
yarn start        # http://localhost:3000/zil_130/, обновляется при правке
yarn build        # проверка перед pull request: битые ссылки ломают сборку
```

Страницы раздела «Документация» лежат в `docs-site/docs/`. Раздел «Исследования и расчёты» собирается прямо из `docs/plan.md`, `research/`, `calc/` и `ecu/`, поэтому правьте исходный файл. После слияния в `main` сайт публикуется на GitHub Pages автоматически.

## Как прислать правку

1. Сделайте fork репозитория на GitHub и ветку под задачу.
2. Проверьте, что затронутые скрипты запускаются, а сайт собирается.
3. Откройте pull request. В описании укажите, что меняется и откуда взяты новые цифры.
