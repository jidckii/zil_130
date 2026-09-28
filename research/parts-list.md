# Комплект: состав, закупка и смета

Дата: 2026-09-28. Состав и зачем каждый узел — `docs/project.md`, порядок работ — `docs/plan.md`. Цены — продавцы РФ, сентябрь 2026, ссылки в указанных файлах; позиции без ссылки там — ниже со ссылкой. Запчасти везём из РФ.

**Статус:** «выбрано» — номер решён; «класс» — понятно, что нужно, модель не выбрана; «оценка» — цены у продавцов нет, порядок величины.

## Общее для обоих вариантов

### ЭБУ, проводка, датчики

| Что | Номер | Кол. | Цена, ₽ | Статус | Где подробно |
|---|---|---|---|---|---|
| ЭБУ | rusEFI **uaEFI121**, два контроллера ШДК встроены | 1 | ≈32 000 ($375 через Петербург) | выбрано | [../ecu/README.md](../ecu/README.md) |
| ШДК | Bosch LSU 4.9 (0 258 017 025) | 2 | ≈22 000 (51 760 AMD за шт., оценка курса) | выбрано | [fuel-system.md](fuel-system.md) |
| Жгут: провод, разъёмы Superseal/EV1, реле, предохранители, гофра | — | 1 | 8 000–15 000 | оценка | — |
| ДПКВ | 2112-3847010 | 1 | 320–845 ([avtoall](https://www.avtoall.ru/datchik_polojeniya_kolenvala_vaz_2110_2112_emi-476438/)) | выбрано | [valvetrain.md](valvetrain.md) |
| Датчик фазы | Холл 2108-3706800 в б/у корпусе трамблёра, однолопастная шторка | 1 | 445 ([avtoall](https://www.avtoall.ru/datchik_holla_vaz_2108_s_raz_emom_aenk_k-037219/)) + корпус ≈1 000–3 000 | выбрано | [valvetrain.md](valvetrain.md) |
| Датчик детонации | 2112-3855020, М8 | 1 | 399–650 ([timeturbo](https://timeturbo.ru/catalog/standartnye-zapchasti-vaz/datchiki-vaz/datchiki-vaz-2110-2112/datchiki-detonatsii-vaz-2110-2112/datchik-detonatsii-dlya-vaz-2110-2112/)) | выбрано; место без сверления блока | [../docs/plan.md](../docs/plan.md) |
| ДАД с температурой воздуха (TMAP), 3 бар абс. | Bosch 0 281 002 437 | 1 | 1 919–4 707 ([tov54](https://tov54.ru/catalog/zapchasti/podgotovka_toplivnoy_smesi/prigotovlenie_smesi/datchik_zond_ts/bosch_dsldf6t_0281002437.html), [АлмаТЭК](https://almatekrf.com/catalog/zapasnye-chasti-dlya-gazoballonnyh-avtomobiley/datchik-davleniya-i-temperatury-nadduvochnogo-vozduha-0281002437-65446f42.html)) | выбрано; один на оба варианта | [../ecu/README.md](../ecu/README.md) |
| Датчик температуры ОЖ | Bosch 0 280 130 093 + разъём | 1 | 460–970 + 266 ([uazist](https://uazist.ru/catalog/elektrooborudovanie/datchik_temperatury_tm_bosch_0_280_130_093_zmz_40904_40524_40525_evro_3_/)) | выбрано | [cooling-accessories.md](cooling-accessories.md) |
| Датчик скорости | 4202.3843 на привод спидометра, М22×1,5 | 1 | 1 190–1 500 ([tns64](https://tns64.ru/datchik-skorosti-4202-3843/)) | выбрано; посадку на КПП проверить | [../ecu/README.md](../ecu/README.md) |
| Датчик давления и температуры газа | STAG PS-02 | 1 | от 2 200 ([togbo](https://togbo.ru/product/map-sensor-ps-02-alaska/)) | выбрано | [fuel-system.md](fuel-system.md) |
| Датчики давления (0–5 В) и температуры масла | класс «150 psi, 1/8 NPT» + NTC | 1 + 1 | ≈1 500–3 000 | оценка | [lubrication.md](lubrication.md) |

### Зажигание и шкив

| Что | Номер | Кол. | Цена, ₽ | Статус | Где подробно |
|---|---|---|---|---|---|
| Модули зажигания, парная искра | ВАЗ 2112-3705010 (042.3705) | 2 + 1 | 9 300–13 500 | выбрано; вход от rusEFI проверить на столе | [ignition.md](ignition.md) |
| Провода высокого напряжения | 130-3707080 силикон или набор под длины от модулей | 1 компл. | 687–1 530 ([sparox](https://sparox.ru/catalog/gaz/provod/1650888?instock=0&viewtype=list&sort=1)) | класс; длины по месту | [ignition.md](ignition.md) |
| Свечи | А11 / Brisk N19C, зазор 0,6–0,7 | 8 | 400–1 200 | класс; холоднее под газ — не найдены | [ignition.md](ignition.md) |
| Шкив коленвала: 2 клиновых ручья, 6PK, кольцо 60-2 | своё изготовление, горячая посадка, балансировка | 1 | 5 000–13 000 | оценка; готовых колец 60-2 в РФ нет — лазерная резка | [cooling-accessories.md](cooling-accessories.md) |
| Кронштейн ДПКВ | своё | 1 | 1 000–2 000 | оценка | — |

### Впуск и газ

| Что | Номер | Кол. | Цена, ₽ | Статус | Где подробно |
|---|---|---|---|---|---|
| Плита развала и ресивер | `cad/valley_plate.py`, `cad/receiver.py`, алюминий 13–15 кг | 1 компл. | 45 000–135 000 | модель готова, способ не выбран | [intake-manufacturing.md](intake-manufacturing.md) |
| Дроссель с ДПДЗ | ЗМЗ-406 **4062.1148100-02** | 1 | 4 845 | выбрано | [electronic-throttle.md](electronic-throttle.md) |
| РХХ | РХХ-60 406.1147051-02 = Bosch 0 280 140 545 | 1 | 1 890–4 270 | выбрано | [electronic-throttle.md](electronic-throttle.md) |
| Трос и качалка | трос 3110-1108050 + качалка на тяге ЗИЛ | 1 | 115–310 ([b2motor](https://b2motor.ru/catalog/gaz/zmz406/6109)) + ≈1 000 | класс; качалка по месту | [../docs/plan.md](../docs/plan.md) |
| Редуктор метана 12 В | Tomasetto AT12 Super **RMAT3882V** | 1 | 8 650 (нет в наличии) – 14 200 | выбрано | [fuel-system.md](fuel-system.md) |
| Газовые форсунки | Rail IG7 Dakota LHF 2 Ом, рампа на 4 | 2 | 21 900 | выбрано | [fuel-system.md](fuel-system.md) |
| Peak-and-hold драйвер | плата на LM1949, 4 канала | 2 | ≈8 000–16 000 (€40–80) | класс; готового в рознице РФ нет | [fuel-system.md](fuel-system.md) |
| Сопла, штуцеры М8×1, шланг Ø6, хомуты | — | набор | 3 000–6 000 | оценка | [fuel-system.md](fuel-system.md) |

### Головки

Обрабатывается запасной комплект, пока машина работает; свои головки после снятия становятся следующим запасным.

| Что | Номер | Кол. | Цена, ₽ | Статус | Где подробно |
|---|---|---|---|---|---|
| Запасные головки б/у | 130-1003012-20 | 2 | 10 000–30 000 | оценка; новая ≈26 000 за шт. | — |
| Фрезеровка под ε 8,5 | услуга | 2 | 4 000–8 200 ([lsumadi](https://lsumadi.ru/tseni/otechestvennie-avtomobili-i-spetstehnika/zil/zil-130/), [mehanka](https://www.mehanka.ru/remont-golovok-cilindra/)) | выбрано | [../docs/project.md](../docs/project.md) |
| Сёдла под газ | услуга с материалом, 3 100 за седло | 16 | 49 600 (только выпускные — 24 800) | класс; объём — по состоянию | [lsumadi](https://lsumadi.ru/tseni/otechestvennie-avtomobili-i-spetstehnika/zil/zil-130/) |
| Клапаны | 130-1007010 впуск, 130-1007015 выпуск | 8 + 8 | 6 000–8 000 | класс | [sparox](https://sparox.ru/catalog/zil/klapan/387708?instock=0&viewtype=list&sort=1) |
| Прокладки ГБЦ и комплект прокладок двигателя | 130-1003020, 130-1000001 РК | 1 + 1 | 2 200 | выбрано | [sparox](https://sparox.ru/catalog/zil/remkomplekt/407420?instock=0&viewtype=list&sort=1) |
| Пружины клапанов | штатные 130-1007020, проверенные по усилию | 16 | 2 000–4 000 | оценка | [valvetrain.md](valvetrain.md) |

### Смазка, охлаждение, навесное

| Что | Номер | Кол. | Цена, ₽ | Статус | Где подробно |
|---|---|---|---|---|---|
| Переходник фильтра вместо центрифуги | своё изготовление | 1 | 5 000–15 000 | оценка | [lubrication.md](lubrication.md) |
| Масляный фильтр | DIFA 5101/1 = MANN W 940/25 | 1 | 605–933 | выбрано | [lubrication.md](lubrication.md) |
| Шланги AN-10 2 м и 4 фитинга | — | 1 компл. | ≈5 000 | класс | [forwardauto](https://forwardauto.ru/catalog/product_autobahn88_hs025a10_shlang_an10_vysokogo_davleniya_armirovannyy_vnutrenniy_d_14_3_mm_gb202b10m_18577/) |
| Термоклапан маслорадиатора | 70–85 °C, AN-10 | 1 | 3 000–6 000 | оценка | [lubrication.md](lubrication.md) |
| Водяная труба с Y-сборником, отбор на отопитель, компрессор и редуктор | своё изготовление | 1 | 5 000–15 000 | оценка | [cooling-accessories.md](cooling-accessories.md) |
| Корпуса термостата | штатные 130-1303051 и 130-1303014-Б2 | 1 | 3 000–5 000 | выбрано | [cooling-accessories.md](cooling-accessories.md) |
| Термостат | ТС108-01, 80 °C | 1 | 411 | выбрано | [cooling-accessories.md](cooling-accessories.md) |
| Вискомуфта с крыльчаткой | Валдай 020005216 + переходной фланец | 1 | 5 950–6 430 + 2 000–4 000 | выбрано | [cooling-accessories.md](cooling-accessories.md) |
| Генератор 150 А | Prestolite AViH1150A + кронштейн + ремень 6PK | 1 | 19 140 + 3 500–7 000 | выбрано | [cooling-accessories.md](cooling-accessories.md) |
| Тормозной компрессор | АМ.3509009-130 (АЙК) | 1 | 14 100–14 935 | выбрано | [cooling-accessories.md](cooling-accessories.md) |
| Осушитель 12 В | модуль подготовки воздуха | 1 | 7 165–7 961 | выбрано | [cooling-accessories.md](cooling-accessories.md) |

## Добавляется в варианте с наддувом

| Что | Номер | Кол. | Цена, ₽ | Статус | Где подробно |
|---|---|---|---|---|---|
| Турбины | MHI TD04L-13T (реплики) или Garrett GBC17-250 | 2 | 35 600–49 600 (TD04L); ≈130 000 (GBC17, €647 × 2, ЕС) | выбор между двумя | [turbo.md](turbo.md) |
| Переходники-колена 3×М12 → T25, приёмные трубы, раздельный выпуск, термоэкраны | своё изготовление | 1 компл. | 20 000–40 000 | оценка | [drivetrain-cooling-exhaust.md](drivetrain-cooling-exhaust.md) |
| Подвод и слив масла и воды к турбинам | — | 2 | 5 000–10 000 | оценка | [turbo.md](turbo.md) |
| Интеркулер с патрубками, BOV | 280-1172010 | 1 | ≈11 000 + 8 000–18 000 | выбрано / оценка | [cooling-accessories.md](cooling-accessories.md) |
| Клапан наддува | MAC 35A-AAA-DDBA-1BA | 1 | 2 230–2 300 ([racesnab](https://racesnab.ru/catalog/ecu_i_elektronika/solenoidy_upravleniya/solenoid_upravleniya_nadduvom_mac_solenoid_3_kh_portovyy/)) | выбрано | [../ecu/README.md](../ecu/README.md) |
| Термопары K перед турбинами и модуль на CAN | Ecumaster EGT to CAN | 2 + 1 | ≈22 000–24 000 (£128, продавца в РФ нет) | класс; альтернатива — MAX31855 на плате | [turbo.md](turbo.md) |
| Радиатор | 133ВЯ-1301010 ЛРЗ | 1 | 33 029 (нет в наличии) | выбрано, посадку проверить | [cooling-accessories.md](cooling-accessories.md) |
| Маслорадиаторы воздушные | 5323-1013010-01 ШААЗ | 2 | 30 320–35 700 | выбрано; место не найдено | [cooling-accessories.md](cooling-accessories.md) |
| Электровентиляторы | Luzar LFc 0310 (ГАЗ, 365 мм) или SPAL VA18 | 2 | 6 540 (Luzar); SPAL ≈40 000–60 000 (оценка) | класс | [cooling-accessories.md](cooling-accessories.md) |
| Сцепление: диск и нажимные пружины | 130-1601130, 130-1601190 | 1 + 16 | 3 490 + 2 000–4 000 | класс | [drivetrain-cooling-exhaust.md](drivetrain-cooling-exhaust.md) |
| Выпускные пружины | ЗМЗ-402 24-1007020 + 24-1007021 | 2 компл. | ≈2 800 | класс; совместить с механизмом поворота | [valvetrain.md](valvetrain.md) |

## Смета

Суммы по таблицам выше, округлено до тысяч. Работа по установке не входит: считаем, что владелец ставит сам или договаривается с мастерской.

| Группа | Атмосферный, тыс. ₽ |
|---|---|
| ЭБУ, проводка, датчики | 72–90 |
| Зажигание и шкив | 16–31 |
| Впуск и газ (с коллектором) | 94–204 |
| из них коллектор | 45–135 |
| Головки | 49–102 |
| Смазка, охлаждение, навесное | 74–107 |
| **Итого атмосферный** | **≈300–530** |
| Добавка на наддув (TD04L-13T, Luzar) | ≈180–240 |
| **Итого с наддувом** | **≈490–770** |

Больше всего в разбросе: способ изготовления коллектора (45–135 тыс.), объём работ по сёдлам (25–50 тыс.) и б/у головки. С GBC17-250 и SPAL вариант с наддувом дороже ещё на ≈130 тыс.

## Что выбрать до закупки

- Турбины: GBC17-250 или TD04L-13T.
- Peak-and-hold драйвер, который продаётся в РФ.
- Холодные свечи М14 под газ, датчик давления масла 0–5 В.
- Способ изготовления коллектора — по КП на литьё (`intake-manufacturing.md`).
