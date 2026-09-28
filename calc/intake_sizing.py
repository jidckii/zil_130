"""Расход воздуха, точки компрессора, метановые и бензиновые форсунки, раннеры для ЗИЛ-130/375.

Запуск: uv run python calc/intake_sizing.py > calc/results.md
Коды источников ([D73 дж.N] и т.п.) расшифрованы в research/engine-data.md, раздел 9.
"""
import math

from CoolProp.CoolProp import PropsSI

R_AIR, K_AIR, M_AIR = 287.05, 1.4, 28.965
P_ATM = 101325.0
HP = 735.5

BORES = {"6,0 л": 100e-3, "7,0 л": 108e-3}  # [D73 дж.53]
STROKE, CYL = 95e-3, 8  # [D73 дж.53]
ALTITUDES = {"0 м": 0, "1000 м (Ереван)": 1000, "2000 м (перевал)": 2000}
BOOSTS = {"атмосферный": None, "+0,3 бар": 0.3e5, "+0,5 бар": 0.5e5}  # над 1 атм, docs/project.md
RPMS = (1500, 2000, 2500, 3200, 3600)

# Допущения, а не заводские данные.
VE = (0.70, 0.85)  # 0,70 — заводской расчёт К-88 [D73 дж.150]; 0,85 — docs/project.md
T_AMB = 303.15  # лето +30 °C, на всех высотах
DP_FILTER = 2e3  # фильтр и патрубки до компрессора
DP_CHARGE = 5e3  # интеркулер и дроссель
ETA_C, EPS_IC = 0.70, 0.70  # КПД компрессора, эффективность интеркулера
LAMBDA_RICH = 0.90  # самая богатая смесь под наддувом, по ней считаем форсунки
DUTY_MAX = 0.80
DP_RAIL = (1.2e5, 2.0e5)  # рампа над MAP, диапазон редукторов 4-го поколения
T_GAS = 313.15  # газ после подогреваемого редуктора
CD_NOZZLE = 0.80
IDLE_RPM, IDLE_MAP = 600, 0.35e5
IDLE_FUEL = 2.09 / 3600 * 43.5 / 50.0  # бензин на ХХ 2,09 кг/ч [D73 дж.225] → метан по теплу, кг/с
T_RUNNER = 313.15  # воздух в раннере для скорости звука
K_ENGELMAN = 2.0  # f_Helmholtz / f_поршня на пике момента, эмпирика Энгельмана
RUNNER_TOTALS = (0.3, 0.5, 0.7, 0.9)  # раннер + канал ГБЦ, м; 0,3 — нынешний ресивер (cad/receiver.py)
AFR_PETROL = 14.7  # АИ-92/95 без спиртов
RHO_PETROL = 0.745  # кг/л; ГОСТ Р 51866 допускает 0,720–0,775
LAMBDA_PETROL = (0.88, 0.80)  # полная нагрузка без наддува / под наддувом: охлаждение заряда и выпуска
IDLE_PETROL = 2.09 / 3600  # кг/с на ХХ [D73 дж.225]

LHV_CH4 = 50.0e6
M_CH4 = PropsSI("M", "Methane") * 1e3
AIR_PER_CH4 = 2 / 0.2095  # моль воздуха на моль CH4
AFR_CH4 = AIR_PER_CH4 * M_AIR / M_CH4
R_CH4 = 8314.46 / M_CH4
K_CH4 = PropsSI("Cpmass", "T", T_GAS, "P", 3e5, "Methane") / PropsSI("Cvmass", "T", T_GAS, "P", 3e5, "Methane")

# ЗИЛ-5086 (138А) на метане: 92 кВт при расходе 41,26 м³/ч [GBA89 дж.39].
# Условия м³ в книге не указаны; берём 20 °C — при 0 °C КПД вышел бы 0,224.
ETA_E = 92e3 / (41.26 / 3600 * PropsSI("D", "T", 293.15, "P", P_ATM, "Methane") * LHV_CH4)


def displacement(bore):
    return math.pi / 4 * bore**2 * STROKE * CYL


def isa_pressure(h):
    return P_ATM * (1 - 2.25577e-5 * h) ** 5.25588


def charge(p_amb, boost):
    """MAP, T во впуске, степень повышения давления, T за компрессором."""
    p1 = p_amb - DP_FILTER
    if boost is None:
        return p1, T_AMB, 1.0, T_AMB
    map_ = P_ATM + boost
    pr = (map_ + DP_CHARGE) / p1
    t2 = T_AMB * (1 + (pr ** ((K_AIR - 1) / K_AIR) - 1) / ETA_C)
    return map_, t2 - EPS_IC * (t2 - T_AMB), pr, t2


def air_flow(bore, rpm, ve, map_, t_man, methane=True):
    """Масса воздуха, кг/с. Метан во впуске при λ=1 занимает ~9,5% объёма заряда."""
    air_share = AIR_PER_CH4 / (1 + AIR_PER_CH4) if methane else 1.0
    return ve * map_ / (R_AIR * t_man) * displacement(bore) * rpm / 120 * air_share


def power_hp(m_air):
    return ETA_E * m_air / AFR_CH4 * LHV_CH4 / HP


def nozzle_flux(p0, p_back, t0=T_GAS, k=K_CH4, r=R_CH4):
    """Изоэнтропное истечение газа через сопло, кг/(с·м²); ниже критического перепада — запирание."""
    ratio = max(p_back / p0, (2 / (k + 1)) ** (k / (k - 1)))
    return p0 * math.sqrt(2 * k / ((k - 1) * r * t0) * (ratio ** (2 / k) - ratio ** ((k + 1) / k)))


def garrett_lbmin(m, p_amb):
    """Приведённый расход по стандарту карт Garrett: 545 °R, 13,95 psia."""
    return m * 132.277 * math.sqrt(T_AMB / 302.78) / ((p_amb - DP_FILTER) / 96180)


def helmholtz_length(bore, dia, rpm, eps):
    """Длина раннера с каналом ГБЦ, при которой резонанс Гельмгольца попадает на rpm."""
    v_eff = displacement(bore) / CYL / 2 * (eps + 1) / (eps - 1)
    c = math.sqrt(K_AIR * R_AIR * T_RUNNER)
    f = K_ENGELMAN * rpm / 60
    return math.pi / 4 * dia**2 / v_eff * (c / (2 * math.pi * f)) ** 2


def self_check():
    q = 0.7 * displacement(100e-3) * 3200 / 120 * 3600  # заводской расчёт: 403 м³/ч [D73 дж.150]
    assert abs(q - 403) < 2, q
    choked = nozzle_flux(3e5, 1e5)
    assert abs(nozzle_flux(3e5, 0.5e5) - choked) < 1e-9
    assert nozzle_flux(3e5, 2.9e5) < 0.5 * choked


def row(*cells):
    print("| " + " | ".join(str(c) for c in cells) + " |")


def main():
    self_check()
    f = lambda x, n=2: f"{x:.{n}f}".replace(".", ",")

    print("# Расчёт впуска ЗИЛ-130/375: воздух, турбины, форсунки, раннеры\n")
    print("Сгенерировано `calc/intake_sizing.py`. Допущения — в начале скрипта.\n")
    print(f"Метан: стехиометрия {f(AFR_CH4)} кг воздуха/кг, k = {f(K_CH4, 3)} при {T_GAS - 273.15:.0f} °C (CoolProp). "
          f"Эффективный КПД по ЗИЛ-138А [GBA89 дж.39]: {f(ETA_E, 3)}.\n")

    print("## 1. Воздух и мощность на 3200 об/мин\n")
    print(f"Воздух — вилка по коэффициенту наполнения {f(VE[0])}–{f(VE[1])}. Мощность — оценка на метане при ε 6,5 "
          "и КПД ЗИЛ-138А: трение при наддуве не падает, поэтому оценка занижена.\n")
    row("Двигатель", "Высота", "p атм, бар", "Режим", "MAP абс, бар", "πк", "T за компр., °C", "T впуска, °C",
        "Воздух, кг/с", "Мощность, л.с.")
    row(*["---"] * 10)
    for eng, bore in BORES.items():
        for alt, h in ALTITUDES.items():
            p_amb = isa_pressure(h)
            for mode, boost in BOOSTS.items():
                map_, t_man, pr, t2 = charge(p_amb, boost)
                lo, hi = (air_flow(bore, 3200, ve, map_, t_man) for ve in VE)
                row(eng, alt, f(p_amb / 1e5), mode, f(map_ / 1e5), f(pr), f"{t2 - 273.15:.0f}",
                    f"{t_man - 273.15:.0f}", f"{f(lo, 3)}–{f(hi, 3)}", f"{power_hp(lo):.0f}–{power_hp(hi):.0f}")

    print("\n## 2. Точки на карте компрессора (одна турбина на ряд)\n")
    print(f"Приведённый расход, lb/min по стандарту Garrett, при коэффициенте наполнения {f(VE[1])} (верх вилки). "
          f"Для {f(VE[0])} умножить на {f(VE[0] / VE[1])}. πк от оборотов не зависит: целевой MAP постоянный.\n")
    row("Двигатель", "Высота", "Наддув", "πк", *[f"{n} об/мин" for n in RPMS])
    row(*["---"] * (4 + len(RPMS)))
    for eng, bore in BORES.items():
        for alt, h in ALTITUDES.items():
            p_amb = isa_pressure(h)
            for mode, boost in list(BOOSTS.items())[1:]:
                map_, t_man, pr, _ = charge(p_amb, boost)
                flows = [garrett_lbmin(air_flow(bore, n, VE[1], map_, t_man) / 2, p_amb) for n in RPMS]
                row(eng, alt, mode, f(pr), *[f(m, 1) for m in flows])

    print("\n## 3. Метановые форсунки\n")
    worst_rpm = max(RPMS)
    print(f"Расчётная точка: {worst_rpm} об/мин, +0,5 бар, уровень моря (самый плотный заряд), "
          f"коэффициент наполнения {f(VE[1])}, λ {f(LAMBDA_RICH)}, скважность ≤{DUTY_MAX:.0%}, газ {T_GAS - 273.15:.0f} °C. "
          f"Ø сопла — эквивалентное круглое отверстие, при Cd = 1 и Cd = {f(CD_NOZZLE)}. "
          f"ХХ: {IDLE_RPM} об/мин, MAP {f(IDLE_MAP / 1e5)} бар, метан по теплу бензинового ХХ; "
          "длительность импульса без времени открытия форсунки.\n")
    row("Двигатель", "Рампа над MAP, бар", "Мощность, л.с./цил", "Метан на форсунку, г/с", "p рампы абс, бар",
        "Запирание", "Cd·A, мм²", "Ø Cd=1, мм", f"Ø Cd={f(CD_NOZZLE)}, мм", "Импульс ХХ, мс")
    row(*["---"] * 10)
    map_, t_man, _, _ = charge(P_ATM, BOOSTS["+0,5 бар"])
    for eng, bore in BORES.items():
        m_air = air_flow(bore, worst_rpm, VE[1], map_, t_man)
        per_inj = m_air / (AFR_CH4 * LAMBDA_RICH) / CYL / DUTY_MAX
        for dp in DP_RAIL:
            p0 = map_ + dp
            cda = per_inj / nozzle_flux(p0, map_)
            d1 = math.sqrt(4 * cda / math.pi)
            idle_cda_flow = cda * nozzle_flux(IDLE_MAP + dp, IDLE_MAP)
            idle_pulse = IDLE_FUEL / CYL / (IDLE_RPM / 120) / idle_cda_flow
            crit = map_ / p0 <= (2 / (K_CH4 + 1)) ** (K_CH4 / (K_CH4 - 1))
            row(eng, f(dp / 1e5, 1), f"{power_hp(m_air) / CYL:.0f}", f(per_inj * 1e3), f(p0 / 1e5),
                "да" if crit else "нет", f(cda * 1e6), f(d1 * 1e3), f(d1 / math.sqrt(CD_NOZZLE) * 1e3),
                f(idle_pulse * 1e3, 1))

    print("\n## 4. Раннеры и ресивер\n")
    print(f"Длина — раннер плюс канал ГБЦ до клапана (длина канала в головке неизвестна). Резонатор Гельмгольца "
          f"«цилиндр + раннер», K = {f(K_ENGELMAN, 1)} по Энгельману, воздух {T_RUNNER - 273.15:.0f} °C, ε 8. "
          "При ε 6,5 длины на 6% короче. Скорость — средняя за такт впуска на 3200 об/мин при наполнении 1.\n")
    row("Двигатель", "Ø раннера, мм", *[f"L на {n} об/мин, м" for n in (2000, 2500, 3000)],
        *[f"Пик при L {f(x, 1)} м, об/мин" for x in RUNNER_TOTALS], "Скорость, м/с")
    row(*["---"] * (6 + len(RUNNER_TOTALS)))
    piston_speed = 2 * STROKE * 3200 / 60
    for eng, bore in BORES.items():
        for dia in (40e-3, 45e-3, 50e-3):
            lengths = [f(helmholtz_length(bore, dia, n, 8.0)) for n in (2000, 2500, 3000)]
            peaks = [f"{2000 * math.sqrt(helmholtz_length(bore, dia, 2000, 8.0) / x):.0f}" for x in RUNNER_TOTALS]
            row(eng, f"{dia * 1e3:.0f}", *lengths, *peaks, f"{(bore / dia) ** 2 * piston_speed:.0f}")
    print()
    for eng, bore in BORES.items():
        vd = displacement(bore) * 1e3
        print(f"- Ресивер {eng}: 0,7–1,0 рабочего объёма = {f(0.7 * vd, 1)}–{f(vd, 1)} л.")

    print("\n## 5. Дроссель\n")
    for rpm in (3200, 3600):
        q = VE[1] * displacement(BORES["7,0 л"]) * rpm / 120 * AIR_PER_CH4 / (1 + AIR_PER_CH4)
        speeds = ", ".join(f"Ø{d} мм — {v:.0f} м/с, напор {f(v ** 2 / (2 * R_AIR * T_RUNNER) * 100, 1)}% MAP"
                           for d in (60, 71) for v in [q / (math.pi / 4 * (d / 1e3) ** 2)])
        print(f"- 7,0 л, {rpm} об/мин, наполнение {f(VE[1])}: {f(q, 3)} м³/с при давлении во впуске, "
              f"от наддува и высоты почти не зависит; {speeds}.")
    print("- Для сравнения: штатный К-88АМ — 2×Ø36 = 20,4 см², расчётная скорость 52–55 м/с [D73 дж.150–151]; "
          "Ø60 — 28,3 см².")
    print("- Потеря на открытом дросселе не больше скоростного напора. В долях MAP наддув её не меняет, но цель "
          f"наддува — MAP после дросселя, и турбина добирает разницу: в подборе турбин на интеркулер и дроссель "
          f"заложено {f(DP_CHARGE / 1e3, 0)} кПа.")

    print("\n## 6. Бензиновые форсунки\n")
    print(f"Та же точка: {worst_rpm} об/мин, уровень моря, наполнение {f(VE[1])}, скважность ≤{DUTY_MAX:.0%}; "
          f"без наддува λ {f(LAMBDA_PETROL[0])}, под наддувом {f(LAMBDA_PETROL[1])}. "
          f"Бензин {f(AFR_PETROL, 1)} кг воздуха/кг, {f(RHO_PETROL, 3)} кг/л. Производительность — паспортная при том "
          "перепаде, который держит регулятор: с отсылкой к MAP он постоянный. Форсунка, паспортная при 3,0 бар, "
          f"на 3,8 бар даёт в {f((3.8 / 3.0) ** 0.5, 3)} раза больше. ХХ — {IDLE_RPM} об/мин, "
          f"{f(IDLE_PETROL * 3600)} кг/ч [D73 дж.225], импульс без времени открытия.\n")
    row("Двигатель", "Режим", "Бензин на форсунку, г/с", "Нужно, см³/мин", "Импульс ХХ такой форсунки, мс")
    row(*["---"] * 5)
    for eng, bore in BORES.items():
        for mode, boost in BOOSTS.items():
            map_, t_man, _, _ = charge(P_ATM, boost)
            lam = LAMBDA_PETROL[0] if boost is None else LAMBDA_PETROL[1]
            per_inj = air_flow(bore, worst_rpm, VE[1], map_, t_man, methane=False) / (AFR_PETROL * lam) / CYL
            static = per_inj / DUTY_MAX
            idle_pulse = IDLE_PETROL / CYL / (IDLE_RPM / 120) / static
            row(eng, mode, f(per_inj * 1e3), f"{static / RHO_PETROL * 6e4:.0f}", f(idle_pulse * 1e3, 1))


if __name__ == "__main__":
    main()
