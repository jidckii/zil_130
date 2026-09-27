"""Нижний этаж коллектора ЗИЛ-130/375 — плита развала, пластиковый макет для примерки.

Запуск: uv run python cad/valley_plate.py  → cad/out/valley_plate.{step,stl}, cad/out/keepout.step
Оси, фланцы головок и штуцеры форсунок — из manifold_skeleton.py; опоры развала — research/engine-data.md, раздел 14.
Верхний этаж (ресивер с раннерами) встаёт на две горизонтальные площадки SPLIT_Z на болтах М8.
"""
import math
from pathlib import Path

from build123d import (Box, Circle, Cylinder, Keep, Plane, Polyline, Pos, RectangleRounded, Spline, Vector, Wire,
                       export_step, export_stl, extrude, loft, make_face, sweep)

from manifold_skeleton import (BASE, FLANGE_T, PITCH, PORT_H, PORT_PITCH, PORT_R, PORT_W, RUNNER_D, STUD_HOLE,
                               STUDS, WALL, WATER, flange_normal, flange_point, injector_boss)

VALLEY_Z = 306.0  # верх передней площадки и заднего ребра [BD л.2 вид спереди, л.3 И₁–И₁]
BLOCK_FRONT = -116.0  # передний торец блока [BD л.1]
DOWEL = (BLOCK_FRONT + 43.0, 0.0)  # Ø8 на оси блока [BD л.2 С–С]
# Ось заднего ребра в плане (Y, X), промер [BD л.1 вид сверху] ±3; правый конец дальше назад.
RIB = ((-113, 434), (-35, 437), (0, 446), (79, 461), (113, 466))
RIB_LAND = 10.0  # ребро 9 мм, запас на промер
FLOOR_T = 10.0  # перекрывается с нижней кромкой фланца на 2 мм
FLANGE_ACROSS = (-43.0, 50.0)  # к блоку — почти до угла головки у разъёма (+52, расчёт)
FLANGE_ALONG = 278.5 + 13.0  # крайняя шпилька [HD87 л.2 вид И] + прилив
HEAD_X = {1: (-87.0, 493.5), -1: (-116.0, 464.5)}  # плоскости разъёма рядов [BD л.1 вид сверху]

SPLIT_Z = 420.0  # разъём с ресивером: на уровне штатного фланца карбюратора (+410…416)
EXIT_Y = 110.0
EXIT_SPREAD = 25.0  # у окна пара через 32,9 — круги Ø42 разводим, иначе каналы сольются
TRANSITION = 40.0  # окно 27,8×56,8 → круг
INJECTOR_AT = 25.0  # ближе к окну, чтобы шланг форсунки прошёл снаружи площадки
PAD_T, PAD_IN, PAD_OUT = 16.0, 42.0, 25.0  # площадка от оси выходов внутрь / наружу
PAD_BOLT = 6.8  # под метчик М8
SEAT_D = 22.0  # горизонтальная опора гайки М10×1 на вертикальной шпильке

WATER_FRONT = (23.0, 30.0)  # канал головки Ø23 [D73 дж.64] → шланг к термостату
WATER_REAR = (8.0, 12.0)  # как дозирующая вставка Ø8 [D73 дж.65–66]; правый — к компрессору
NECK = (425.0, 40.0, 36.0, 445.0)  # горловина: X, Y, Ø, верх — за ресивером у ребра; спереди над ней встал бы дроссель
BREATHER = (-10.0, 30.0, 13.0, 19.0, 360.0)  # сапун: X, Y, Ø канала, Ø штуцера, верх
TRAP = (70.0, 60.0, 22.0)  # маслоуловитель под плитой, щель 50×10 в задней стенке

# Оценка по [D73 рис.22] и [RE85 рис.11]; ось — по чертежу блока: Ø43 под 35°30′ влево,
# на Z = +306 в 60 мм от оси [BD л.3 вид Б] и X ≈ 497 [BD л.1 вид сверху].
DIST_AXIS = (Vector(497, -60, VALLEY_Z), math.radians(35.5))
DIST_PARTS = ((45, -20, 80), (75, 80, 110), (85, 110, 195), (120, 195, 265))  # Ø, от, до по оси
COVER_UV = ((-140.0, 122.0), (406.0, 455.0))  # клапанная крышка в осях ряда, верх +408 [D73 рис.22]


def exits(side):
    """(окно, выход) по X для четырёх каналов ряда: пары между 1-м и 2-м, 3-м и 4-м цилиндрами ряда."""
    return [(flange_point(side, pair + d * PORT_PITCH / 2, 0), flange_point(side, pair + d * EXIT_SPREAD, 0).X)
            for pair in (-PITCH, PITCH) for d in (-1, 1)]


def channel(side, port, x, grow):
    n = flange_normal(side)
    a = Vector(x, port.Y, port.Z) + n * TRANSITION
    b = Vector(x, side * EXIT_Y, SPLIT_Z + 2)
    start = port - n * (1 if grow == 0 else 0)
    r = RUNNER_D / 2 + grow
    path = Wire([Spline(a, b, tangents=(n, (0, 0, 1)))])
    body = loft([Plane(start, (1, 0, 0), n) * RectangleRounded(PORT_W + 2 * grow, PORT_H + 2 * grow, PORT_R + grow),
                 Plane(a, (1, 0, 0), n) * Circle(r)])
    return body + sweep(Plane(a, (1, 0, 0), n) * Circle(r), path=path), TRANSITION + path.length


def seat_rise():
    """Верх опоры гайки над точкой шпильки на плоскости фланца: толщина по вертикали + наклон под опорой."""
    nz = flange_normal(1).Z
    return FLANGE_T / nz + SEAT_D / 2 * math.tan(math.radians(90) - math.asin(nz))


def side_flange(side):
    n = flange_normal(side)
    mid = sum(FLANGE_ACROSS) / 2
    plane = Plane(flange_point(side, 0, mid) + n * (FLANGE_T / 2), (1, 0, 0), n)
    plate = plane * Box(2 * FLANGE_ALONG, FLANGE_ACROSS[1] - FLANGE_ACROSS[0], FLANGE_T)
    seats, holes = [], []
    for a, c in STUDS:
        p = flange_point(side, a, c)
        seats.append(Pos(p.X, p.Y, p.Z) * Cylinder(SEAT_D / 2, seat_rise(), align=BASE))
        holes.append(Pos(p.X, p.Y, p.Z - 50) * Cylinder(STUD_HOLE / 2, 150, align=BASE))
    return [plate] + seats, holes


def spigot(side, along, across, direction, bore, od, length):
    p = flange_point(side, along, across)
    pl = Plane(p, z_dir=direction.normalized())
    return pl * Cylinder(od / 2, length, align=BASE), pl * Pos(0, 0, -5) * Cylinder(bore / 2, length + 10, align=BASE)


def water(side):
    n = flange_normal(side)
    (front, c_f), (rear, c_r) = sorted(WATER)
    fb, fh = spigot(side, front, c_f, n + Vector(-1, 0, 0), *WATER_FRONT, 45)
    rb, rh = spigot(side, rear, c_r, n, *WATER_REAR, 35)
    return [fb, rb], [fh, rh]


def pad_bolts(side):
    """Болты только между парами и по краям: над парой проходят раннеры ресивера, ключ туда не пролезет."""
    hc = flange_point(side, 0, 0).X
    return [(hc + dx, side * y) for dx in (-195, 0, 195) for y in (EXIT_Y, EXIT_Y - 33)]


def pad(side, z_top=SPLIT_Z, t=PAD_T):
    hc = flange_point(side, 0, 0).X
    y0, y1 = sorted((side * (EXIT_Y - PAD_IN), side * (EXIT_Y + PAD_OUT)))
    return Pos(hc, (y0 + y1) / 2, z_top - t / 2) * Box(2 * (195 + 12), y1 - y0, t)


def floor():
    rib = [(x + RIB_LAND, y) for y, x in RIB]
    outline = Polyline((BLOCK_FRONT, -130), (rib[0][0], -130), *rib, (rib[-1][0], 130), (BLOCK_FRONT, 130), close=True)
    slab = Pos(0, 0, VALLEY_Z) * extrude(make_face(outline), FLOOR_T)
    return slab, Pos(*DOWEL, VALLEY_Z - 1) * Cylinder(4, FLOOR_T + 2, align=BASE)


def crankcase_ports():
    """Горловина, сапун и маслоуловитель под ним."""
    x, y, d, top = NECK
    bx, by, bd, bod, btop = BREATHER
    lx, ly, lz = TRAP
    trap = Pos(bx, by, VALLEY_Z - lz) * Box(lx, ly, lz + 1, align=BASE)
    trap_in = Pos(bx, by, VALLEY_Z - lz + WALL) * Box(lx - 2 * WALL, ly - 2 * WALL, lz, align=BASE)
    slot = Pos(bx + lx / 2, by, VALLEY_Z - lz + WALL) * Box(2 * WALL + 2, 50, 10, align=BASE)
    bodies = [Pos(x, y, VALLEY_Z) * Cylinder(d / 2 + 4, top - VALLEY_Z, align=BASE),
              Pos(bx, by, VALLEY_Z) * Cylinder(bod / 2, btop - VALLEY_Z, align=BASE), trap]
    cuts = [Pos(x, y, VALLEY_Z - 1) * Cylinder(d / 2, top - VALLEY_Z + 2, align=BASE),
            Pos(bx, by, VALLEY_Z - 1) * Cylinder(bd / 2, btop - VALLEY_Z + 2, align=BASE), trap_in, slot]
    return bodies, cuts


def valley_side(shape):
    """Всё, что зашло за плоскость фланца головки, срезаем: плита ложится на головки, а не в них."""
    for side in (1, -1):
        shape = shape.split(Plane(flange_point(side, 0, 0), z_dir=flange_normal(side)), keep=Keep.TOP)
    return shape


def keepout():
    """Трамблёр с приводом и клапанные крышки — только для проверки зазоров."""
    p0, tilt = DIST_AXIS
    d = Vector(0, -math.sin(tilt), math.cos(tilt))
    parts = [Plane(p0 + d * s0, z_dir=d) * Cylinder(dia / 2, s1 - s0, align=BASE) for dia, s0, s1 in DIST_PARTS]
    (u0, u1), (v0, v1) = COVER_UV
    k = math.sqrt(0.5)
    for side in (1, -1):
        pts = [(side * k * (v - u), k * (v + u)) for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]
        x0, x1 = HEAD_X[side]
        parts.append(Pos(x0, 0, 0) * extrude(Plane.YZ * make_face(Polyline(*pts, close=True)), x1 - x0, dir=(1, 0, 0)))
    return parts


def build():
    outer, cuts, lengths = [], [], []
    slab, dowel = floor()
    outer.append(slab)
    cuts.append(dowel)
    for side in (1, -1):
        for bodies, holes in (side_flange(side), water(side)):
            outer += bodies
            cuts += holes
        outer.append(pad(side))
        cuts += [Pos(x, y, SPLIT_Z - PAD_T - 1) * Cylinder(PAD_BOLT / 2, PAD_T + 2, align=BASE) for x, y in pad_bolts(side)]
        for port, x in exits(side):
            o, _ = channel(side, port, x, WALL)
            f, length = channel(side, port, x, 0)
            outer.append(o)
            cuts.append(f)
            lengths.append(length)
            x_boss = port.X + (x - port.X) * INJECTOR_AT / TRANSITION
            outer.append(injector_boss(side, x_boss, hole=False, at=INJECTOR_AT))
            cuts.append(injector_boss(side, x_boss, hole=True, at=INJECTOR_AT))
    part = sum(outer[1:], outer[0]) - sum(cuts[1:], cuts[0])
    part = part.split(Plane((0, 0, SPLIT_Z), z_dir=(0, 0, 1)), keep=Keep.BOTTOM)
    bodies, holes = crankcase_ports()
    part = sum(bodies, part) - sum(holes[1:], holes[0])
    return valley_side(part), lengths


if __name__ == "__main__":
    part, lengths = build()
    assert part.is_valid and len(part.solids()) == 1, "плита невалидна или развалилась на части"
    out = Path(__file__).parent / "out"
    out.mkdir(exist_ok=True)
    export_step(part, out / "valley_plate.step")
    export_stl(part, out / "valley_plate.stl", tolerance=0.05, angular_tolerance=0.2)
    ko = keepout()
    export_step(sum(ko[1:], ko[0]), out / "keepout.step")
    bb = part.bounding_box()
    print(f"Габарит X {bb.min.X:.0f}…{bb.max.X:.0f}, Y {bb.min.Y:.0f}…{bb.max.Y:.0f}, Z {bb.min.Z:.0f}…{bb.max.Z:.0f}")
    print(f"Канал от окна до площадки {min(lengths):.0f}–{max(lengths):.0f} мм, масса PLA ~{part.volume * 1.24e-6:.1f} кг")
    for name, k in zip(("привод трамблёра", "пластины октан-корректора", "трамблёр", "крышка трамблёра",
                        "клапанная крышка справа", "клапанная крышка слева"), ko):
        gap = part.distance_to(k)
        assert gap > 0, f"плита задевает: {name}"
        print(f"Зазор до {name}: {gap:.1f} мм")
