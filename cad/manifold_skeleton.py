"""Скелет впускного коллектора ЗИЛ-130/375: продольный ресивер, 8 раннеров, временные фланцы.

Запуск: uv run python cad/manifold_skeleton.py  → cad/out/*.step
Оси: X вдоль коленвала назад от оси 1-го цилиндра, Y вправо, Z вверх от оси коленвала.
Коллектор сухой: вода от головок к термостату идёт отдельной трубой (docs/project.md, раздел 7).
"""
import math
from pathlib import Path

from build123d import (Align, Box, Circle, Cylinder, Plane, Pos, RectangleRounded, Spline, Vector, Wire,
                       export_step, loft, sweep)

PITCH = 135.0  # межцилиндровое [D73 дж.8]
RUNNER_D = 42.0  # calc/results.md: 40–45
PLENUM_VOL = 5.0e6  # мм³; calc/results.md: 4,2–7,0 л
THROTTLE_D = 60.0  # ГАЗ Ø60; для 7 л лучше 71 (calc/results.md)
WALL = 3.0  # пластиковый макет

# Заглушки до замера на двигателе и скана прокладки: грубая прикидка, не данные.
BANK_OFFSET = 25.0  # левый ряд сдвинут назад: шатуны стоят рядом на одной шейке
FLANGE_Y = 170.0  # от оси двигателя до центра окна на фланце
FLANGE_Z = 280.0  # центр окна над осью коленвала
FLANGE_TILT = 45.0  # нормаль фланца над горизонталью, град
PORT_W, PORT_H, PORT_R = 36.0, 44.0, 6.0  # окно: вдоль вала × поперёк, радиус угла
PORT_PITCH = 50.0  # между центрами спаренных окон
PLENUM_W, PLENUM_Z = 140.0, 430.0  # ширина ресивера и высота его оси

FLANGE_T, FLANGE_MARGIN = 12.0, 40.0
BASE = (Align.CENTER, Align.CENTER, Align.MIN)
STRAIGHT = 60.0  # прямой участок у фланца: переход окно → круг, штуцер форсунки
BOSS_AT, BOSS_ANGLE, BOSS_D, BOSS_HOLE = 35.0, 30.0, 14.0, 5.0  # штуцер М6 Valtek: отверстие под метчик


def port_xs(side):
    """Окна по ходу головки: вып–вп–вп–вып–вып–вп–вп–вып [D73 дж.61] → впуск спарен у середины пары цилиндров."""
    shift = 0.0 if side > 0 else BANK_OFFSET
    return [shift + mid + d * PORT_PITCH / 2 for mid in (PITCH / 2, 2.5 * PITCH) for d in (-1, 1)]


def flange_normal(side):
    t = math.radians(FLANGE_TILT)
    return Vector(0, -side * math.cos(t), math.sin(t))


def plenum_box():
    xs = port_xs(1) + port_xs(-1)
    x0, x1 = min(xs) - FLANGE_MARGIN, max(xs) + FLANGE_MARGIN
    h = PLENUM_VOL / ((x1 - x0) * PLENUM_W)
    return x0, x1, h


def runner(side, x, grow):
    """Раннер от окна до дна ресивера; grow = 0 — проточная часть, WALL — наружная поверхность."""
    n = flange_normal(side)
    p = Vector(x, side * FLANGE_Y, FLANGE_Z)
    a = p + n * STRAIGHT
    x0, x1, h = plenum_box()
    b = Vector(x, side * PLENUM_W / 4, PLENUM_Z - h / 2 + 10)
    start = p - n * (1 if grow == 0 else 0)
    port = loft([Plane(start, (1, 0, 0), n) * RectangleRounded(PORT_W + 2 * grow, PORT_H + 2 * grow, PORT_R + grow),
                 Plane(a, (1, 0, 0), n) * Circle(RUNNER_D / 2 + grow)])
    path = Wire([Spline(a, b, tangents=(n, (0, 0, 1)))])
    bend = sweep(Plane(a, (1, 0, 0), n) * Circle(RUNNER_D / 2 + grow), path=path)
    return port + bend, STRAIGHT + path.length


def injector_boss(side, x, hole):
    n = flange_normal(side)
    up = Vector(0, side * n.Z, -side * n.Y)
    b = math.radians(BOSS_ANGLE)
    axis = up * math.cos(b) + n * math.sin(b)
    c = Vector(x, side * FLANGE_Y, FLANGE_Z) + n * BOSS_AT
    if hole:
        return Plane(c, z_dir=axis) * Cylinder(BOSS_HOLE / 2, 60, align=BASE)
    return Plane(c, z_dir=axis) * Pos(0, 0, RUNNER_D / 2 - 2) * Cylinder(BOSS_D / 2, WALL + 17, align=BASE)


def build():
    x0, x1, h = plenum_box()
    cx = (x0 + x1) / 2
    fluid, outer, lengths = [], [], []
    for side in (1, -1):
        n = flange_normal(side)
        xs = port_xs(side)
        fx = (xs[0] + xs[-1]) / 2
        fl = xs[-1] - xs[0] + PORT_W + 2 * FLANGE_MARGIN
        origin = Vector(fx, side * FLANGE_Y, FLANGE_Z) + n * (FLANGE_T / 2)
        outer.append(Plane(origin, (1, 0, 0), n) * Box(fl, PORT_H + 2 * FLANGE_MARGIN, FLANGE_T))
        for x in xs:
            f, length = runner(side, x, 0)
            o, _ = runner(side, x, WALL)
            fluid.append(f)
            outer.append(o)
            lengths.append(length)
            outer.append(injector_boss(side, x, hole=False))
            fluid.append(injector_boss(side, x, hole=True))
    outer.append(Pos(cx, 0, PLENUM_Z) * Box(x1 - x0 + 2 * WALL, PLENUM_W + 2 * WALL, h + 2 * WALL))
    fluid.append(Pos(cx, 0, PLENUM_Z) * Box(x1 - x0, PLENUM_W, h))
    throttle = Plane((x0, 0, PLENUM_Z), z_dir=(-1, 0, 0))
    outer.append(throttle * Pos(0, 0, -WALL) * Cylinder(THROTTLE_D / 2 + WALL, 60 + WALL, align=BASE))
    fluid.append(throttle * Pos(0, 0, -WALL - 1) * Cylinder(THROTTLE_D / 2, 62 + WALL, align=BASE))
    body = sum(outer[1:], outer[0])
    air = sum(fluid[1:], fluid[0])
    return body - air, air, lengths, h


if __name__ == "__main__":
    part, air, lengths, h = build()
    assert part.is_valid and air.is_valid
    out = Path(__file__).parent / "out"
    out.mkdir(exist_ok=True)
    export_step(part, out / "manifold_skeleton.step")
    export_step(air, out / "manifold_air.step")
    print(f"Раннер от фланца до ресивера: {min(lengths):.0f}–{max(lengths):.0f} мм, высота ресивера {h:.0f} мм")
    print(f"Объём проточной части {air.volume / 1e6:.2f} л, масса ABS ~{part.volume * 1.05e-6:.1f} кг")
