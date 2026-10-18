"""Режим «эко» на 4 цилиндрах: хватает ли момента и сколько газа экономит.

Запуск: uv run python calc/cylinder_cut.py
Разбор — research/cylinder-deactivation.md.
"""
import math

WHEEL_R, FINAL, ETA = 0.476, 6.32, 0.88  # research/transmission/alternatives.md
F_ROLL = 0.015                           # там же
VD = 5.969e-3
P_AMB = 90e3                             # Ереван, calc/results.md
RHO = 1.06                               # оценка, ~1000 м, +20 °C
CD_A = 0.8 * 5.0                         # оценка: Cd 0,8, лобовая ~5 м²
FMEP = 150e3                             # оценка для 2000 об/мин
P_EXH = 100e3                            # оценка, атмосферный выпуск
P_TRAPPED = 5e3                          # оценка потерь «газовой пружины» при закрытых клапанах
MAP_MAX = 0.95 * P_AMB                   # дроссель открыт полностью

# Атмосферный 6,0 л, Ереван, кгс·м — calc/results.md раздел 2
WOT8 = {1500: 29.9 * 9.81, 2000: 30.5 * 9.81, 2500: 29.2 * 9.81}


def wot8(rpm):
    pts = sorted(WOT8.items())
    if rpm <= pts[0][0]:
        return pts[0][1]
    for (n0, m0), (n1, m1) in zip(pts, pts[1:]):
        if rpm <= n1:
            return m0 + (m1 - m0) * (rpm - n0) / (n1 - n0)
    return pts[-1][1]


def gross_imep(bmep, k, active, dead_pmep):
    """Средняя по 8 цилиндрам брутто-работа при нужном BMEP; None — не хватает дросселя."""
    lo, hi, p = 10e3, MAP_MAX, MAP_MAX
    for _ in range(60):
        p = (lo + hi) / 2
        made = k * p * active / 8
        need = bmep + FMEP + ((P_EXH - p) * active + dead_pmep(p) * (8 - active)) / 8
        lo, hi = (p, hi) if made < need else (lo, p)
    return (p, k * p * active / 8) if hi < MAP_MAX * 0.999 else None


def point(mass, kmh):
    v = kmh / 3.6
    force = mass * 9.81 * F_ROLL + 0.5 * RHO * CD_A * v * v
    rpm = v / (2 * math.pi * WHEEL_R) * FINAL * 60
    torque = force * WHEEL_R / FINAL / ETA
    bmep = torque * 4 * math.pi / VD
    # брутто-IMEP пропорционален MAP, точка привязки — полный дроссель на 8 цилиндрах
    k = (wot8(rpm) * 4 * math.pi / VD + FMEP + P_EXH - MAP_MAX) / MAP_MAX
    base = gross_imep(bmep, k, 8, lambda p: 0)
    cut = gross_imep(bmep, k, 4, lambda p: P_EXH - p)
    mds = gross_imep(bmep, k, 4, lambda p: P_TRAPPED)
    saving = lambda r: None if r is None else 1 - r[1] / base[1]
    return dict(mass=mass, kmh=kmh, rpm=rpm, torque=torque, load4=torque / (wot8(rpm) / 2),
                map8=base[0], map4=cut and cut[0], cut=saving(cut), mds=saving(mds))


def fmt(x, scale=100, unit="%"):
    return "не тянет" if x is None else f"{x * scale:.0f}{unit}"


if __name__ == "__main__":
    rows = [point(m, v) for m in (4300, 9525) for v in (50, 60, 70, 80)]
    print("| Масса, кг | км/ч | об/мин (V) | Момент, Н·м | От полного на 4 цил. | MAP 8 цил., кПа | MAP 4 цил., кПа | Экономия: отсечка газа | Экономия: MDS |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['mass']} | {r['kmh']} | {r['rpm']:.0f} | {r['torque']:.0f} | {r['load4'] * 100:.0f}% "
              f"| {r['map8'] / 1e3:.0f} | {fmt(r['map4'], 1e-3, '')} | {fmt(r['cut'])} | {fmt(r['mds'])} |")

    empty60 = point(4300, 60)
    assert 0 < empty60["cut"] < empty60["mds"] < 0.2, empty60
    assert point(9525, 60)["cut"] is None
