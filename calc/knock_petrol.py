"""Запас по детонации на бензине: та же модель, что в knock.py, но задержка — по Дуо — Эйза.

Запуск: uv run python calc/knock_petrol.py > calc/knock_petrol_results.md
τ = 17,68·(ОЧ/100)^3,402·p^−1,7·exp(3800/T) мс, p в атм (Douaud, Eyzat, SAE 780080, 1978).
Формула эмпирическая, и температура несгоревшего заряда у нас без теплоотдачи, поэтому задержку
масштабируем одним коэффициентом так, чтобы штатный мотор был ровно на пороге на своём бензине:
ε 6,5 — потребное октановое число 76 по моторному методу [D73 дж.46 табл.8].
"""
import math

from intake_sizing import P_ATM, charge
from knock import ZIL, bisect, knock_integral, row

AFR_PETROL, LHV_PETROL = 14.7, 43.5e6
RPM = 1500  # худший режим, как в knock.py
T_NA = 303.15  # лето +30 °C, как в intake_sizing.py
STOCK = (6.5, 76.0)  # ε и потребное ОЧ по моторному методу [D73 дж.46 табл.8]
FUELS = {"АИ-92 (ОЧМ 83)": 83.0, "АИ-95 (ОЧМ 85)": 85.0}  # минимум ОЧМ по ГОСТ 32513
EPSS = (6.5, 7.1, 8.0, 8.5)
CA50 = {"середина сгорания 8° после ВМТ": 8.0, "зажигание позже на 6°": 14.0}


def tau_de(octane, scale):
    return lambda p, t, phi: scale * 17.68e-3 * (octane / 100) ** 3.402 * (p / P_ATM) ** -1.7 * math.exp(3800 / t)


def integral(eps, octane, scale, map_, t, rpm=RPM, **kw):
    return knock_integral(ZIL["6,0 л"], eps, map_, t, rpm, 0.0, tau_fn=tau_de(octane, scale),
                          afr=AFR_PETROL, lhv=LHV_PETROL, **kw)


def na_map():
    return charge(P_ATM, None)[0]


def boosted(boost):
    """MAP и T за интеркулером для наддува над 1 атм; без наддува — атмосфера за фильтром."""
    map_, t, _, _ = charge(P_ATM, boost) if boost > 0 else (na_map(), T_NA, 1, T_NA)
    return map_, t


def limit_boost(eps, octane, scale, **kw):
    """Наибольший наддув над 1 атм с интеркулером, бар; отрицательный — детонация уже без наддува."""
    f = lambda b: integral(eps, octane, scale, *boosted(b), **kw)
    if f(0.0) >= 1:
        return -1.0
    return bisect(f, 0.0, 1.5e5) / 1e5


def main():
    scale = integral(*STOCK, 1.0, na_map(), T_NA)
    assert abs(integral(*STOCK, scale, na_map(), T_NA) - 1) < 1e-6
    f = lambda x, n=2: f"{x:.{n}f}".replace(".", ",")

    print("# Запас по детонации на бензине\n")
    print("Сгенерировано `calc/knock_petrol.py`. Модель давления и интеграл Ливенгуда — Ву — из `calc/knock.py` "
          "(6,0 л, Вибе 70°, штатный распредвал: впуск закрывается на 83° после НМТ). Задержка самовоспламенения — "
          "эмпирическая формула Дуо — Эйза по октановому числу, по моторному методу.\n")
    print(f"**Калибровка.** Задержка умножена на {f(scale, 3)}: при этом штатный мотор (ε {f(STOCK[0], 1)}, "
          f"без наддува, {T_NA - 273.15:.0f} °C, {RPM} об/мин) ровно на пороге на бензине с ОЧМ {STOCK[1]:.0f} — "
          "потребное октановое число по заводу [D73 дж.46 табл.8].\n")

    print("## 1. Проверка по заводскому опыту с наддувом\n")
    print("ЗИЛ-130, ε 6,5, бензин ОЧМ 85–86, интеркулера нет [D73 дж.256–260]. Мотор работал, значит интеграл "
          "должен быть меньше 1. Температура — за компрессором (КПД 0,70), без охлаждения.\n")
    row("Опыт", "MAP абс, бар", "Воздух во впуске, °C", "Интеграл")
    row("---", "---", "---", "---")
    for name, boost, rpm in (("ТКР-8,5, 0,3 кгс/см², 2000 об/мин", 0.294e5, 2000),
                             ("импульсная турбина, 0,58 кгс/см², 3200 об/мин", 0.569e5, 3200)):
        map_, _, _, t2 = charge(P_ATM, boost)
        row(name, f(map_ / 1e5), f"{t2 - 273.15:.0f}", f(integral(6.5, 85.5, scale, map_, t2, rpm=rpm)))

    print(f"\n## 2. Предельный наддув на бензине, бар над 1 атм, {RPM} об/мин, интеркулер 0,7\n")
    print("«нет» — детонация уже без наддува при таком зажигании. Под наддувом смесь богаче, а ЭБУ по датчику "
          "детонации может сдвинуть зажигание позже, поэтому вторая таблица — запас на откате.\n")
    for name, ca50 in CA50.items():
        print(f"**{name[0].upper() + name[1:]}**\n")
        row("Бензин", *[f"ε {f(e, 1)}" for e in EPSS])
        row(*["---"] * (1 + len(EPSS)))
        for fuel, octane in FUELS.items():
            cells = []
            for e in EPSS:
                b = limit_boost(e, octane, scale, ca50=ca50)
                cells.append("нет" if b < 0 else (">1,5" if math.isinf(b) else f(b)))
            row(fuel, *cells)
        print()


if __name__ == "__main__":
    main()
