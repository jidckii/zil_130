"""Запас по детонации метана: интеграл Ливенгуда — Ву для несгоревшего заряда.

Запуск: uv run python calc/knock.py > calc/knock_results.md
Задержка самовоспламенения — Cantera, GRI-Mech 3.0, адиабатический реактор постоянного объёма.
Давление — однозонная модель: закон сгорания Вибе, без теплоотдачи в стенки.
Несгоревший заряд сжимается изоэнтропно по давлению в цилиндре. Детонация, если интеграл
∫dt/τ(p, T) доходит до 1 раньше, чем сгорит 90% смеси.
Чистая модель детонацию метана сильно занижает, поэтому к температуре несгоревшего заряда
добавлена «горячая точка» HOT, подобранная по критической степени сжатия метана 14,4 на CFR.
"""
import math
from dataclasses import dataclass
from functools import cache

import cantera as ct
import numpy as np

K = 1.32  # показатель адиабаты смеси
AFR_CH4, LHV_CH4, R_MIX = 17.24, 50.0e6, 290.0
WIEBE_A, WIEBE_M = 6.9, 2.0
KNOCK_AT = 0.9  # до этой доли сгоревшей смеси несгоревший заряд ещё есть
DT_IVC = 30.0  # допущение: подогрев заряда от стенок и остаточных газов к закрытию впуска, К


@dataclass(frozen=True)
class Engine:
    bore: float
    stroke: float
    rod: float
    ivc: float  # закрытие впуска, град до ВМТ сжатия со знаком «−»
    burn: float  # длительность сгорания 0–99,9% по Вибе, град (допущение)
    ca50: float  # середина сгорания, град после ВМТ


ZIL = {  # ход и шатун [D73 дж.53], [R68 дж.67]; закрытие впуска 83° после НМТ [D73 дж.54]
    "6,0 л": Engine(100e-3, 95e-3, 185e-3, -97.0, 70.0, 8.0),
    "7,0 л": Engine(108e-3, 95e-3, 185e-3, -97.0, 70.0, 8.0),
}
# Установка CFR F-2 при определении метанового числа: 82,55×114,3 мм, 900 об/мин, зажигание 15° до ВМТ,
# у метана критическая ε 14,4 (Malenshek, Olsen, Fuel 2009, по Ryan et al.).
# Шатун 254 мм, закрытие впуска 34° после НМТ, сгорание 50° и середина 12° после ВМТ — допущения.
CFR = Engine(82.55e-3, 114.3e-3, 254e-3, -146.0, 50.0, 12.0)
CFR_RPM, CFR_EPS, CFR_T_INTAKE = 900, 14.4, 303.15
IVC_ABDC = (83, 60, 50, 40, 30)  # варианты нового распредвала

P_GRID = np.array([10, 20, 30, 45, 60, 80, 110, 150, 200]) * 1e5
T_GRID = np.arange(700.0, 1401.0, 50.0)
TAU_MAX = 1.0


def ignition_delay(p, t, phi):
    gas = ct.Solution("gri30.yaml")
    gas.TP = t, p
    gas.set_equivalence_ratio(phi, "CH4", "O2:1, N2:3.76")
    reactor = ct.IdealGasReactor(gas, clone=False)
    net = ct.ReactorNet([reactor])
    time = 0.0
    while time < TAU_MAX and reactor.T < t + 400:
        time = net.step()
    return time if reactor.T >= t + 400 else math.inf


@cache
def ln_tau_table(phi):
    table = np.array([[ignition_delay(p, t, phi) for t in T_GRID] for p in P_GRID])
    return np.log(np.minimum(table, 1e3))


def tau(p, t, phi):
    """Лог-интерполяция по сетке; вне сетки — по ближайшей границе."""
    ln = ln_tau_table(phi)
    it = np.clip(t, T_GRID[0], T_GRID[-1])
    row = [np.interp(it, T_GRID, ln[i]) for i in range(len(P_GRID))]
    return math.exp(np.interp(math.log(np.clip(p, P_GRID[0], P_GRID[-1])), np.log(P_GRID), row))


def volume(theta, eng, eps):
    vd = math.pi / 4 * eng.bore**2 * eng.stroke
    r = eng.rod / (eng.stroke / 2)
    a = math.radians(theta)
    return vd / (eps - 1) + vd / 2 * (r + 1 - math.cos(a) - math.sqrt(r**2 - math.sin(a) ** 2))


def knock_integral(eng, eps, map_, t_intake, rpm, hot, lam=1.0, dt_ivc=DT_IVC, tau_fn=None, afr=AFR_CH4, lhv=LHV_CH4,
                   **override):
    eng = Engine(**{**eng.__dict__, **override})
    p, t_ivc = map_, t_intake + dt_ivc
    v = volume(eng.ivc, eng, eps)
    q_total = p * v / (R_MIX * t_ivc) / (1 + afr * lam) * lhv * 0.95
    tau_fn = tau_fn or tau
    start = eng.ca50 - eng.burn * (math.log(2) / WIEBE_A) ** (1 / (WIEBE_M + 1))
    step, theta, xb, integral = 0.2, eng.ivc, 0.0, 0.0
    while xb < KNOCK_AT:
        theta2 = theta + step
        z = max(theta2 - start, 0.0) / eng.burn
        xb2 = 1 - math.exp(-WIEBE_A * z ** (WIEBE_M + 1))
        v2 = volume(theta2, eng, eps)
        p += ((K - 1) * q_total * (xb2 - xb) - K * p * (v2 - v)) / v
        t_unburned = t_ivc * (p / map_) ** ((K - 1) / K) + hot
        integral += step / (6 * rpm) / tau_fn(p, t_unburned, 1 / lam)
        theta, xb, v = theta2, xb2, v2
    return integral


def bisect(f, lo, hi, n=14):
    """Корень возрастающей f(x) − 1 на [lo, hi]; inf, если на hi ещё меньше 1."""
    if f(hi) < 1:
        return math.inf
    for _ in range(n):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < 1 else (lo, mid)
    return lo


def calibrate_hot(**cfr_override):
    t = cfr_override.pop("t_intake", CFR_T_INTAKE)
    return bisect(lambda hot: knock_integral(CFR, CFR_EPS, 1.0e5, t, CFR_RPM, hot, **cfr_override), 0.0, 400.0)


def knock_limited_map(eng, eps, t_intake, rpm, hot, **kw):
    return bisect(lambda m: knock_integral(eng, eps, m, t_intake, rpm, hot, **kw), 0.8e5, 4.0e5)


def self_check(hot):
    assert tau(60e5, 1000, 1.0) < tau(60e5, 900, 1.0) < tau(30e5, 900, 1.0)
    assert abs(knock_integral(CFR, CFR_EPS, 1e5, CFR_T_INTAKE, CFR_RPM, hot) - 1) < 0.05
    assert knock_integral(CFR, 12.0, 1e5, CFR_T_INTAKE, CFR_RPM, hot) < 1


def eff_eps(eng, eps, ivc_abdc):
    return volume(ivc_abdc - 180.0, eng, eps) / volume(0.0, eng, eps)


def row(*cells):
    print("| " + " | ".join(str(c) for c in cells) + " |")


def main():
    hot = calibrate_hot()
    self_check(hot)
    f = lambda x, n=2: f"{x:.{n}f}".replace(".", ",")
    lim = lambda m: ">4" if math.isinf(m) else f(m / 1e5)
    epss = (6.5, 8.0, 8.5, 9.0, 10.0)
    z7 = ZIL["7,0 л"]

    print("# Запас по детонации метана\n")
    print("Сгенерировано `calc/knock.py`. Интеграл Ливенгуда — Ву, 1 — порог детонации. Задержка "
          "самовоспламенения — Cantera (GRI-Mech 3.0), λ 1. Для ЗИЛ сгорание по Вибе 70°, середина "
          f"сгорания 8° после ВМТ, заряд при закрытии впуска на {DT_IVC:.0f} К горячее, чем во впуске.\n")
    print(f"**Калибровка.** Без поправки модель не даёт детонации даже при ε 10 и 4 бар — это нереально. "
          f"Поэтому к несгоревшему заряду добавлена горячая точка **+{hot:.0f} К**: при ней метан детонирует "
          "на CFR F-2 при ε 14,4, как в опыте (Malenshek, Olsen, Fuel 2009; Ryan et al.).\n")

    print("## 1. Интеграл на расчётных режимах, 7,0 л, 1500 об/мин\n")
    print("Температура во впуске — из `calc/results.md` (интеркулер 0,7). Низкие обороты — худший случай.\n")
    cases = {"атмосферный, 30 °C": (1.0e5, 303.15), "+0,3 бар, 47 °C": (1.31e5, 320.15),
             "+0,5 бар, 53 °C": (1.51e5, 326.15), "+0,5 бар, 59 °C (2000 м)": (1.51e5, 332.15),
             "+0,5 бар, 90 °C (без интеркулера)": (1.51e5, 363.15)}
    row("Режим", *[f"ε {f(e, 1)}" for e in epss])
    row(*["---"] * (1 + len(epss)))
    for name, (map_, t) in cases.items():
        row(name, *[f(knock_integral(z7, e, map_, t, 1500, hot), 2) for e in epss])

    print("\n## 2. Предельный по детонации MAP, бар абс., в зависимости от закрытия впуска\n")
    print("Главный рычаг — фаза закрытия впуска: чем раньше, тем выше эффективная степень сжатия. "
          "Штатный вал закрывает впуск на 83° после НМТ [D73 дж.54]. 7,0 л, 1500 об/мин, во впуске 55 °C. "
          "«>4» — детонации нет до 4 бар.\n")
    row("Закрытие впуска после НМТ", *[f"ε {f(e, 1)}" for e in epss])
    row(*["---"] * (1 + len(epss)))
    for ivc in IVC_ABDC:
        row(f"{ivc}°", *[lim(knock_limited_map(z7, x, 328.15, 1500, hot, ivc=ivc - 180.0)) for x in epss])
    row("ε эфф. при 83° / 40°", *[f"{f(eff_eps(z7, x, 83), 1)} / {f(eff_eps(z7, x, 40), 1)}" for x in epss])
    print("\n## 3. Чувствительность: 7,0 л, ε 8,5, закрытие впуска 40° после НМТ, 1500 об/мин, 55 °C\n")
    print("Для вариантов калибровки горячая точка пересчитывается заново.\n")
    row("Вариант", "Горячая точка, К", "Предельный MAP, бар")
    row("---", "---", "---")
    variants = {
        "база": ({}, {}),
        "сгорание ЗИЛ 50°": ({}, {"burn": 50.0}),
        "сгорание ЗИЛ 90°": ({}, {"burn": 90.0}),
        "раннее зажигание, середина сгорания 2°": ({}, {"ca50": 2.0}),
        "заряд горячее на +30 К": ({}, {"dt_ivc": 60.0}),
        "λ 0,9": ({}, {"lam": 0.9}),
        "CFR: впуск 15 °C": ({"t_intake": 288.15}, {}),
        "CFR: впуск 50 °C": ({"t_intake": 323.15}, {}),
        "CFR: сгорание 40°": ({"burn": 40.0}, {}),
        "CFR: сгорание 60°": ({"burn": 60.0}, {}),
    }
    for name, (cfr_kw, zil_kw) in variants.items():
        h = calibrate_hot(**cfr_kw) if cfr_kw else hot
        row(name, f"{h:.0f}", lim(knock_limited_map(z7, 8.5, 328.15, 1500, h, **{"ivc": -140.0, **zil_kw})))


if __name__ == "__main__":
    main()
