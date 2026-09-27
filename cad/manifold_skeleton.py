"""Скелет впускного коллектора ЗИЛ-130/375: продольный ресивер, 8 раннеров, фланцы по оценке с фото.

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

BANK_OFFSET = 29.0  # левый ряд назад на ширину головки шатуна [TU66 печ.188], [D73 дж.21]

# Чертёж ГБЦ 130-1003012-20СБ [HD87] (research/engine-data.md, раздел 13).
DECK = 295.0 + 1.5  # ось КВ → разъём блока [раздел 12.2] + прокладка ГБЦ в сжатом виде (допущение)
PORT_ABOVE_DECK = 51.5  # центр окна над разъёмом: плоскость П5 [HD87 л.1, И1–И1]
PORT_FROM_AXIS = 136.5  # от оси цилиндра до фланца на этой высоте [HD87 л.1 И1–И1, л.2 Б–Б]
FLANGE_TO_DECK = 80.0  # угол фланца П3 к разъёму [HD87 л.2 Б–Б, В–В]
BANK = math.radians(45.0)
FLANGE_Y = DECK * math.sin(BANK) + PORT_ABOVE_DECK * math.sin(BANK) - PORT_FROM_AXIS * math.cos(BANK)
FLANGE_Z = DECK * math.cos(BANK) + PORT_ABOVE_DECK * math.cos(BANK) + PORT_FROM_AXIS * math.sin(BANK)
FLANGE_TILT = 90.0 - (45.0 - (90.0 - FLANGE_TO_DECK))  # нормаль над горизонтом
# Вид И (М1:2), промер скана по размеру 125 между шпильками, ±0,3 мм.
PORT_W, PORT_H, PORT_R = 27.8, 56.8, 5.0  # окно на фланце: вдоль вала × поперёк, R5 [HD87 л.2]
PORT_PITCH = 32.9  # между центрами спаренных окон
# Отверстия М10×1,5 под шпильки вертикальные: ось под 45° к разъёму [HD87 л.2 В–В].
# (вдоль от центра головки [HD87 л.2 вид И: 81–125–72,5–72,5–125–81], поперёк от линии окон, «+» к блоку)
STUDS = ((-278.5, 28.7), (278.5, 28.7), (-197.5, 0), (197.5, 0), (-72.5, 0), (0, 0), (72.5, 0))
WATER = ((-247.8, 20.0), (247.8, 20.0))  # водяные окна 35,6×31,8, здесь круг
WATER_D, STUD_HOLE = 35.0, 11.0
FLANGE_ALONG, FLANGE_ACROSS = 300.0, (-43.0, 46.0)  # полудлина и границы плиты поперёк

PLENUM_W, PLENUM_Z = 140.0, 480.0  # низкий: центрифугу меняем на фильтр (docs/project.md)

FLANGE_T, FLANGE_MARGIN = 12.0, 40.0
HEAD_CENTER = 1.5 * PITCH  # середина между цилиндрами 2–3
BASE = (Align.CENTER, Align.CENTER, Align.MIN)
STRAIGHT = 60.0  # прямой участок у фланца: переход окно → круг, штуцер форсунки
BOSS_AT, BOSS_ANGLE, BOSS_D, BOSS_HOLE = 35.0, 30.0, 14.0, 5.0  # штуцер М6 Valtek: отверстие под метчик


def port_xs(side):
    """Окна по ходу головки: вып–вп–вп–вып–вып–вп–вп–вып [D73 дж.61] → впуск спарен у середины пары цилиндров."""
    return [flange_point(side, pair + d * PORT_PITCH / 2, 0).X for pair in (-PITCH, PITCH) for d in (-1, 1)]


def flange_normal(side):
    t = math.radians(FLANGE_TILT)
    return Vector(0, -side * math.cos(t), math.sin(t))


def flange_point(side, along, across):
    """Точка на плоскости фланца; across > 0 — к нижней кромке (к блоку)."""
    t = math.radians(FLANGE_TILT)
    to_block = Vector(0, -side * math.sin(t), -math.cos(t))
    shift = 0.0 if side > 0 else BANK_OFFSET
    return Vector(HEAD_CENTER + shift + along, side * FLANGE_Y, FLANGE_Z) + to_block * across


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


def flange(side):
    """Плита фланца, вертикальные отверстия шпилек, водяные окна со штуцерами под шланг."""
    n = flange_normal(side)
    mid = (FLANGE_ACROSS[0] + FLANGE_ACROSS[1]) / 2
    origin = flange_point(side, 0, mid) + n * (FLANGE_T / 2)
    plane = Plane(origin, (1, 0, 0), n)
    height = FLANGE_ACROSS[1] - FLANGE_ACROSS[0]
    plate = plane * Box(2 * FLANGE_ALONG, height, FLANGE_T)
    holes = [Pos(*flange_point(side, a, c)) * Cylinder(STUD_HOLE / 2, 200) for a, c in STUDS]
    spigots, water = [], []
    for a, c in WATER:
        w = Plane(flange_point(side, a, c), (1, 0, 0), n)
        spigots.append(w * Cylinder(WATER_D / 2 + WALL, FLANGE_T + 30, align=BASE))
        water.append(w * Pos(0, 0, -1) * Cylinder(WATER_D / 2, FLANGE_T + 32, align=BASE))
    return [plate] + spigots, holes + water


def build():
    x0, x1, h = plenum_box()
    cx = (x0 + x1) / 2
    fluid, outer, cuts, lengths = [], [], [], []
    for side in (1, -1):
        body, holes = flange(side)
        outer += body
        cuts += holes
        for x in port_xs(side):
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
    return body - air - sum(cuts[1:], cuts[0]), air, lengths, h


if __name__ == "__main__":
    part, air, lengths, h = build()
    assert part.is_valid and air.is_valid
    out = Path(__file__).parent / "out"
    out.mkdir(exist_ok=True)
    export_step(part, out / "manifold_skeleton.step")
    export_step(air, out / "manifold_air.step")
    print(f"Раннер от фланца до ресивера: {min(lengths):.0f}–{max(lengths):.0f} мм, высота ресивера {h:.0f} мм")
    print(f"Объём проточной части {air.volume / 1e6:.2f} л, масса ABS ~{part.volume * 1.05e-6:.1f} кг")
