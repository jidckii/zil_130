"""Квазистационарное согласование турбины с рядом ЗИЛ (4 цилиндра на турбину): с каких оборотов держится наддув.

Запуск: uv run python calc/turbo_match.py. Кривые турбин сняты с графиков Garrett (research/turbo.md).
Оценка, не расчёт: пульсации не учтены, КПД турбины×мех 0,60 для всех.
ТКР-8,5 калибруем по заводскому факту [D73]: 0,3 кгс/см² держится с 2000 об/мин.
Поток турбины Garrett — приведённый к 288 К и 1,013 бар (допущение).
"""
import math

import numpy as np

R, CP_A, CP_E, G_E = 287.05, 1005.0, 1150.0, 1.33
LB = 0.45359237 / 60
STROKE = 0.095
ETA_TM = 0.60
P4_DP = 0.10e5  # противодавление за турбиной

# Кривые с графиков Garrett: (PR турбины, приведённый расход lb/min)
TURB = {
    "GBC17-250 0.50": [(1.0, 0), (1.21, 6.9), (1.3, 7.9), (1.4, 8.6), (1.5, 9.2), (1.6, 9.6), (1.75, 10.1), (2.0, 10.6), (2.25, 10.95), (2.5, 11.1), (3.0, 11.2)],
    "GBC20-300 0.55": [(1.0, 0), (1.19, 7.7), (1.25, 8.7), (1.4, 10.1), (1.5, 10.8), (1.6, 11.4), (1.75, 11.95), (2.0, 12.45), (2.25, 12.8), (2.5, 12.95), (3.0, 12.9)],
    "GT2554R 0.64":   [(1.0, 0), (1.15, 7.8), (1.2, 8.9), (1.3, 10.1), (1.4, 11.2), (1.5, 12.1), (1.6, 12.7), (1.7, 13.1), (1.8, 13.4), (1.9, 13.8), (2.0, 13.9), (3.0, 13.9)],
}


def phi(curve, pr, k=1.0):
    xs, ys = zip(*curve)
    return k * np.interp(pr, xs, ys)


def engine(bore, rpm, p_amb, t_amb, map_, pr_c, eta_c, ic, methane, ve):
    t2 = t_amb * (1 + (pr_c ** (0.4 / 1.4) - 1) / eta_c)
    t_int = t2 - ic * (t2 - t_amb)
    share = (2 / 0.2095) / (1 + 2 / 0.2095) if methane else 1.0
    vd_bank = math.pi / 4 * bore**2 * STROKE * 4
    m_air = ve * map_ / (R * t_int) * vd_bank * rpm / 120 * share
    w_c = m_air * CP_A * (t2 - t_amb)
    return m_air, w_c


def turbine_power(curve, k, m_exh, t3, p4):
    """Вестгейт закрыт: весь газ через турбину."""
    lo, hi = 1.0001, 4.0
    f = lambda pr: m_exh * math.sqrt(t3 / 288) / (pr * p4 / 1.013e5) / LB - phi(curve, pr, k)
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) > 0 else (lo, mid)
    pr_t = lo
    return m_exh * CP_E * t3 * (1 - pr_t ** (-(G_E - 1) / G_E)) * ETA_TM, pr_t


def threshold(curve, k, case, t3):
    for rpm in range(1000, 4050, 50):
        m_air, w_c = engine(rpm=rpm, **case["eng"])
        w_t, _ = turbine_power(curve, k, m_air * case["exh"], t3, case["p4"])
        if w_t >= w_c:
            return rpm
    return None


def wastegate(curve, k, case, t3, rpm=3600):
    """Доля газа мимо турбины и p3/p2 на заданных оборотах."""
    m_air, w_c = engine(rpm=rpm, **case["eng"])
    m_exh = m_air * case["exh"]
    for pr_t in np.arange(1.02, 4.0, 0.005):
        m_t = phi(curve, pr_t, k) * LB * (pr_t * case["p4"] / 1.013e5) / math.sqrt(t3 / 288)
        if m_t * CP_E * t3 * (1 - pr_t ** (-(G_E - 1) / G_E)) * ETA_TM >= w_c:
            return 1 - m_t / m_exh, pr_t * case["p4"] / case["eng"]["map_"]
    return None, None


def isa(h):
    return 101325 * (1 - 2.25577e-5 * h) ** 5.25588


def project_case(bore, h, boost, ve=0.85):
    p_amb = isa(h)
    map_ = 101325 + boost
    pr_c = (map_ + 5e3) / (p_amb - 2e3)
    return {"eng": dict(bore=bore, p_amb=p_amb, t_amb=303.15, map_=map_, pr_c=pr_c, eta_c=0.70,
                        ic=0.70, methane=True, ve=ve),
            "exh": 1.06, "p4": p_amb + P4_DP}


D73 = {"eng": dict(bore=0.100, p_amb=101325, t_amb=293.15, map_=101325 + 0.30 * 98066.5,
                   pr_c=(101325 + 0.30 * 98066.5) / (101325 - 2e3), eta_c=0.65, ic=0.0,
                   methane=False, ve=0.85),
       "exh": 1.07, "p4": 101325 + P4_DP}


def calibrate_tkr85(t3):
    base = TURB["GT2554R 0.64"]
    for k in np.arange(0.8, 4.0, 0.01):
        if threshold(base, k, D73, t3) == 2000:
            return k
    return None


if __name__ == "__main__":
    for t3 in (1073.15, 1173.15):
        k = calibrate_tkr85(t3)
        curves = dict(TURB)
        curves["ТКР-8,5 (калибр. D73)"] = [(p, f * k) for p, f in TURB["GT2554R 0.64"]]
        print(f"\nT3 = {t3 - 273.15:.0f} °C; ТКР-8,5 ≈ {k:.2f}×GT2554R 0.64 → запирание ≈ {13.9 * k:.1f} lb/min")
        print(f"{'турбина':24s} | " + " | ".join(f"{b} {h}м {d}" for b in ('6,0', '7,0') for h in (0, 1000, 2000, 3000, 4000) for d in ('+0,3', '+0,5')))
        for name, c in curves.items():
            row = []
            for bore in (0.100, 0.108):
                for h in (0, 1000, 2000, 3000, 4000):
                    for boost in (0.3e5, 0.5e5):
                        row.append(threshold(c, 1.0, project_case(bore, h, boost), t3))
            print(f"{name:24s} | " + " | ".join(f"{r or '>4000':>12}" for r in row))
        for name, c in curves.items():
            wg, p32 = wastegate(c, 1.0, project_case(0.108, 4000, 0.5e5), t3)
            wg0, p320 = wastegate(c, 1.0, project_case(0.100, 0, 0.3e5), t3)
            print(f"  {name:24s} 3600: 7,0 л 4000 м +0,5 — мимо турбины {wg:.0%}, p3/p2 {p32:.2f}; 6,0 л 0 м +0,3 — {wg0:.0%}, p3/p2 {p320:.2f}")
    assert threshold(TURB["GBC17-250 0.50"], 1.0, project_case(0.100, 0, 0.3e5), 1073.15) < \
           threshold(TURB["GT2554R 0.64"], 1.0, project_case(0.100, 0, 0.3e5), 1073.15)
