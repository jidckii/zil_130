"""Сварной вариант коллектора: каналы и раннеры — башенки из трёх фрезерованных плит на пару каналов.

Запуск: uv run python cad/welded.py  → cad/out/welded/{valley_plate,receiver,welded_assembly}.step
и архив docs-site/static/cad/intake-welded-step.zip для страницы мастерской.
Трубы не проходят: оси каналов в паре через 2 × EXIT_SPREAD = 50 мм, у трубы 48 × 3 (внутри 42) между
соседями остаётся 2 мм — горелкой не подлезть, а шире не дают гайки шпилек (receiver.check).
Башенка — плиты 25 + 50 + 25 мм вдоль коленвала, разъём по осям каналов: в каждой плите полуканал
фрезеруется на 3 осях, швы по наружному контуру. Трасса каналов та же, что у литой модели.
"""
import zipfile
from pathlib import Path

from build123d import Box, Compound, Line, Plane, Spline, Vector, Wire, export_step, extrude, make_face

import receiver
import valley_plate
from head_flange import PORT_H, RUNNER_D, flange_normal
from valley_plate import EXIT_SPREAD, EXIT_Y, SPLIT_Z, TRANSITION, exits

WALL = 4.0  # стенки маслоуловителя и трубных штуцеров
SHEET = 5.0  # лист коробки ресивера
BAND = RUNNER_D / 2 + 4.0  # от оси канала до наружного контура башенки
DENSITY = 2.66e-6  # АМг5, кг/мм³


def tower(points, x, extra=None):
    """Плоская башенка вокруг осевой линии (Y, Z) в плоскости X = x, толщиной ±EXIT_SPREAD."""
    band = make_face(Wire([Line(p, q) for p, q in zip(points, points[1:])]).offset_2d(BAND, closed=True))
    body = Plane.YZ.offset(x - EXIT_SPREAD) * extrude(band, 2 * EXIT_SPREAD)
    return body + extra if extra else body


def yz(p):
    return (p.Y, p.Z)


def plate_body(side, port, x):
    n = flange_normal(side)
    a = Vector(x, port.Y, port.Z) + n * TRANSITION
    b = Vector(x, side * EXIT_Y, SPLIT_Z + 2)
    curve = Spline(a, b, tangents=(n, (0, 0, 1)))
    points = [yz(port - n * 5), yz(a)] + [yz(curve @ (i / 12)) for i in range(1, 13)] + [(side * EXIT_Y, SPLIT_Z + 20)]
    # у фланца окно 56,8 выше трубы 42 — башенка там толще поперёк
    neck = Plane(Vector(x, port.Y, port.Z) + n * (TRANSITION / 2), x_dir=(1, 0, 0), z_dir=n) * Box(
        2 * EXIT_SPREAD, PORT_H + 8, TRANSITION + 10)
    return tower(points, x, neck)


def runner_body(side, x):
    a = Vector(x, side * EXIT_Y, SPLIT_Z - 1)
    b = Vector(x, side * (receiver.PLENUM_W / 2 - 5), receiver.ENTRY_Z)
    curve = Spline(a, b, tangents=((0, 0, 1), (0, -side, 0)))
    points = [(side * EXIT_Y, SPLIT_Z - 20)] + [yz(curve @ (i / 12)) for i in range(13)] + [(side * 20.0, receiver.ENTRY_Z)]
    return tower(points, x)


def main():
    plate, _ = valley_plate.build(WALL, body=plate_body)
    assert plate.is_valid and len(plate.solids()) == 1, "плита невалидна или развалилась на части"
    rec, air, throttle, _, (x0, x1, h, top) = receiver.build(SHEET, body=runner_body)
    receiver.check(rec, air, throttle, plate)
    out = Path(__file__).parent / "out" / "welded"
    out.mkdir(parents=True, exist_ok=True)
    export_step(plate, out / "valley_plate.step")
    export_step(rec, out / "receiver.step")
    export_step(Compound([plate, rec]), out / "welded_assembly.step")
    site = Path(__file__).resolve().parent.parent / "docs-site" / "static" / "cad"
    site.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(site / "intake-welded-step.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out.glob("*.step")):
            z.write(f, f.name)
    for name, part in (("плита", plate), ("ресивер", rec)):
        bb = part.bounding_box()
        print(f"{name}: {bb.size.X:.0f} × {bb.size.Y:.0f} × {bb.size.Z:.0f} мм, {part.volume * DENSITY:.1f} кг")
    print(f"Ресивер: коробка {x1 - x0:.0f} × {receiver.PLENUM_W + 2 * SHEET:.0f} × {h + 2 * SHEET:.0f} мм из листа {SHEET:.0f}")


if __name__ == "__main__":
    main()
