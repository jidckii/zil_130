"""Верхний этаж коллектора ЗИЛ-130/375 — ресивер с раннерами на площадках плиты развала.

Запуск: uv run python cad/receiver.py  → cad/out/receiver.{step,stl}, cad/out/intake_assembly.step
Стоит на площадках SPLIT_Z плиты (valley_plate.py) на тех же болтах М8; раннеры входят в боковые стенки,
поэтому болты и гайки шпилек под ним остаются доступны ключом сверху.
"""
from pathlib import Path

from build123d import Box, Circle, Cylinder, Keep, Plane, Pos, Spline, Vector, Wire, export_step, export_stl, sweep

from manifold_skeleton import BASE, PLENUM_VOL, RUNNER_D, STUDS, WALL, flange_point
from valley_plate import (EXIT_Y, NECK, SPLIT_Z, build as build_plate, exits, keepout, pad, pad_bolts, seat_rise)

UP_T = 12.0
BOLT_CLEAR = 9.0  # М8
PLENUM_W = 120.0  # внутри; стенки на ±63 — внутри линии болтов ±77
PLENUM_Z0 = 440.0  # дно над площадками, под ним свободно для шлангов воды и сапуна
ENTRY_Z = 475.0  # ось входа раннера в стенку: поворот R≈55 от вертикали у площадки
# Дроссель ЗМЗ-406 4062.1148100 на тросе, один на оба мотора: Ø60, 4 отверстия Ø9 по квадрату 70×70
# (research/engine-data.md, 12.3) — площадка под метчик М8.
THROTTLE_OPENING, THROTTLE_BOLTS = 60.0, 70.0
THROTTLE_PAD_T, THROTTLE_TAP = 12.0, 6.8
THROTTLE_BODY = (130.0, 100.0, 75.0)  # габарит с сектором троса и ДПДЗ по бокам: Y, Z, длина — оценка
# Сверху, X от передней стенки: М12×1,5 под датчик или переходник на штуцер, М22×1,5 — штуцер шланга РХХ-60
# (диаметр шланга снять с детали). Редуктор держит давление над MAP. Картерные газы — в середину:
# подальше от заслонки и ровнее по цилиндрам [D73 дж.110].
PORTS = {"ДАД": (40.0, -25.0, 10.2), "ДТВ": (80.0, -25.0, 10.2), "газовый редуктор": (40.0, 25.0, 10.2),
         "РХХ": (130.0, 0.0, 20.4), "картерные газы": (204.0, 0.0, 10.2)}
HEAD_PORT = 120.0  # канал ГБЦ, оценка по [HD87 л.1 И1–И1] (engine-data.md, раздел 13)
SOCKET_BOLT, SOCKET_NUT = 9.5, 12.0  # радиус торцевой головки: М8 (13 мм), гайка М10×1 (17 мм)


def runner(side, x, grow):
    a = Vector(x, side * EXIT_Y, SPLIT_Z - 1)
    b = Vector(x, side * (PLENUM_W / 2 - 5), ENTRY_Z)
    path = Wire([Spline(a, b, tangents=((0, 0, 1), (0, -side, 0)))])
    return sweep(Plane(a, z_dir=(0, 0, 1)) * Circle(RUNNER_D / 2 + grow), path=path), path.length


def plenum_x():
    xs = [x for side in (1, -1) for _, x in exits(side)]
    margin = RUNNER_D / 2 + WALL + 5
    return min(xs) - margin, max(xs) + margin


def plenum():
    x0, x1 = plenum_x()
    length = x1 - x0 - 2 * WALL
    h = PLENUM_VOL / (length * PLENUM_W)
    top = PLENUM_Z0 + h + 2 * WALL
    outer = Pos((x0 + x1) / 2, 0, PLENUM_Z0) * Box(x1 - x0, PLENUM_W + 2 * WALL, h + 2 * WALL, align=BASE)
    inner = Pos((x0 + x1) / 2, 0, PLENUM_Z0 + WALL) * Box(length, PLENUM_W, h, align=BASE)
    front = Plane((x0, 0, PLENUM_Z0 + WALL + h / 2), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))
    sq, half = THROTTLE_BOLTS + 24, THROTTLE_BOLTS / 2
    bodies = [outer, front * Box(sq, sq, THROTTLE_PAD_T, align=BASE)]
    bodies += [Pos(x0 + x, y, top - 1) * Cylinder(tap / 2 + 6, 11, align=BASE) for x, y, tap in PORTS.values()]
    cuts = [inner, front * Pos(0, 0, -WALL - 1) * Cylinder(THROTTLE_OPENING / 2, THROTTLE_PAD_T + WALL + 2, align=BASE)]
    cuts += [front * Pos(dx, dy, THROTTLE_PAD_T - 20) * Cylinder(THROTTLE_TAP / 2, 21, align=BASE)
             for dx in (-half, half) for dy in (-half, half)]
    cuts += [Pos(x0 + x, y, top - WALL - 1) * Cylinder(tap / 2, 15, align=BASE) for x, y, tap in PORTS.values()]
    throttle = front * Pos(0, 0, THROTTLE_PAD_T) * Box(*THROTTLE_BODY, align=BASE)
    return bodies, cuts, throttle, (x0, x1, h, top)


def build():
    outer, cuts, air, lengths = [], [], [], []
    for side in (1, -1):
        outer.append(pad(side, z_top=SPLIT_Z + UP_T, t=UP_T))
        cuts += [Pos(x, y, SPLIT_Z - 1) * Cylinder(BOLT_CLEAR / 2, UP_T + 2, align=BASE) for x, y in pad_bolts(side)]
        for _, x in exits(side):
            o, _ = runner(side, x, WALL)
            f, length = runner(side, x, 0)
            outer.append(o)
            air.append(f)
            lengths.append(length)
    bodies, holes, throttle, dims = plenum()
    part = sum(outer + bodies[1:], bodies[0]) - sum(air + cuts + holes[1:], holes[0])
    part = part.split(Plane((0, 0, SPLIT_Z), z_dir=(0, 0, 1)), keep=Keep.TOP)
    return part, sum(air[1:], air[0]), throttle, lengths, dims


def access():
    """Что должно сниматься сверху: торцевые головки на болты площадок и гайки шпилек, крышка горловины."""
    tools = [Pos(x, y, SPLIT_Z + UP_T + 1) * Cylinder(SOCKET_BOLT, 200, align=BASE)
             for side in (1, -1) for x, y in pad_bolts(side)]
    for side in (1, -1):
        for a, c in STUDS:
            p = flange_point(side, a, c)
            tools.append(Pos(p.X, p.Y, p.Z + seat_rise() + 1) * Cylinder(SOCKET_NUT, 200, align=BASE))
    x, y, d, top = NECK
    return tools + [Pos(x, y, top) * Cylinder(d / 2 + 10, 80, align=BASE)]


def overlap(a, b):
    x = a & b
    return x.volume if x else 0.0


if __name__ == "__main__":
    part, air, throttle, lengths, (x0, x1, h, top) = build()
    assert part.is_valid and len(part.solids()) == 1, "ресивер невалиден или развалился на части"
    assert len(air.solids()) == 8, "раннеры пересекаются"
    plate, plate_lengths = build_plate()
    assert overlap(part, plate) < 1, "ресивер залез в плиту"
    ko = keepout()
    for name, k in (("трамблёр с приводом", ko[:4]), ("клапанные крышки", ko[4:])):
        gap = min(part.distance_to(s) for s in k)
        assert gap > 0, f"ресивер задевает: {name}"
        print(f"Зазор до {name}: {gap:.1f} мм")
    blocked = [t for t in access() if overlap(part + throttle, t) > 1]
    assert not blocked, f"сверху не подлезть в {len(blocked)} местах"
    out = Path(__file__).parent / "out"
    out.mkdir(exist_ok=True)
    export_step(part, out / "receiver.step")
    export_stl(part, out / "receiver.stl", tolerance=0.05, angular_tolerance=0.2)
    export_step(plate + part, out / "intake_assembly.step")
    bb = part.bounding_box()
    print(f"Габарит X {bb.min.X:.0f}…{bb.max.X:.0f}, Y {bb.min.Y:.0f}…{bb.max.Y:.0f}, Z {bb.min.Z:.0f}…{bb.max.Z:.0f}")
    print(f"Ресивер X {x0:.0f}…{x1:.0f}, внутри {PLENUM_W:.0f} × {h:.0f} мм, {PLENUM_VOL / 1e6:.1f} л, верх +{top:.0f}")
    print(f"Раннер ресивера {min(lengths):.0f}–{max(lengths):.0f} мм; "
          f"с плитой и каналом ГБЦ ≈{min(lengths) + min(plate_lengths) + HEAD_PORT:.0f} мм")
    print(f"Масса PLA ~{part.volume * 1.24e-6:.1f} кг")
