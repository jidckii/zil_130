"""Сварной вариант коллектора: каналы и раннеры — башенки из трёх фрезерованных плит на пару каналов.

Запуск: uv run python cad/welded.py  → cad/out/welded/{valley_plate,receiver,welded_assembly}.step
позиции сварки: cad/out/welded/parts/{plate,receiver}-NN.{step,dxf,brep} и манифест {plate,receiver}.json.
Трубы не проходят: оси каналов в паре через 2 × EXIT_SPREAD = 50 мм, у трубы 48 × 3 (внутри 42) между
соседями остаётся 2 мм — горелкой не подлезть, а шире не дают гайки шпилек (receiver.check).
Башенка — плиты 25 + 50 + 25 мм вдоль коленвала, разъём по осям каналов: в каждой плите полуканал
фрезеруется на 3 осях, швы по наружному контуру. Трасса каналов та же, что у литой модели.
"""
import json
from pathlib import Path

from build123d import (Box, Compound, Cylinder, ExportDXF, GeomType, Line, Plane, Pos, Rectangle, Spline, Unit,
                       Vector, Wire,
                       export_brep, export_step, extrude, make_face)

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


def slab_x(x0, x1):
    return Pos((x0 + x1) / 2, 0, 400) * Box(x1 - x0, 1000, 1000)


def tower_pieces(bodies_by_pair, tag):
    """Башенки пары каналов → три плиты вдоль коленвала: передняя 25, средняя 50, задняя 25."""
    out = []
    for pair, (xa, xb, body) in enumerate(bodies_by_pair):
        c, s = (xa + xb) / 2, EXIT_SPREAD
        for kind, (a, b) in (("передняя", (c - 2 * s, c - s)), ("средняя", (c - s, c + s)),
                             ("задняя", (c + s, c + 2 * s))):
            out.append((f"Башенка {tag}, {kind} плита", body & slab_x(a, b)))
    return out


def split_by_priority(part, bodies):
    """Деталь сварной сборки = то, что от сборки попало в её заготовку и не занято позициями выше по списку."""
    pieces, taken = [], None
    for name, body in bodies:
        piece = part & body
        if taken is not None:
            piece = piece - taken
        taken = body if taken is None else taken + body
        pieces.append((name, piece))
    return pieces


def plate_bodies():
    bodies = []
    for side, tag in ((1, "правый"), (-1, "левый")):
        parts, _ = valley_plate.side_flange(side)
        bodies.append((f"Фланец {tag}", parts[0]))
    for side in (1, -1):
        bodies.append(("Площадка разъёма", valley_plate.pad(side)))
    for side in (1, -1):
        parts, _ = valley_plate.side_flange(side)
        bodies += [("Опора гайки", seat) for seat in parts[1:]]
    bodies.append(("Пол", valley_plate.floor()[0]))
    for side, tag in ((1, "правая"), (-1, "левая")):
        ex = exits(side)
        pairs = []
        for k in (0, 2):
            (pa, xa), (pb, xb) = ex[k], ex[k + 1]
            pairs.append((xa, xb, plate_body(side, pa, xa) + plate_body(side, pb, xb)))
        bodies += tower_pieces(pairs, tag)
    for side in (1, -1):
        for port, x in exits(side):
            bodies.append(("Бобышка форсунки", valley_plate.gas_fitting(side, port, x, hole=False)))
    for side in (1, -1):
        (front, rear), _ = valley_plate.water(side)
        bodies += [("Штуцер воды передний", front), ("Штуцер воды задний", rear)]
    (neck, breather, trap), _ = valley_plate.crankcase_ports(WALL)
    bodies += [("Горловина", neck), ("Штуцер сапуна", breather), ("Маслоуловитель", trap)]
    return bodies


def receiver_bodies():
    x0, x1 = receiver.plenum_x(SHEET)
    _, _, _, (_, _, h, top) = receiver.plenum(SHEET)
    z0, w = receiver.PLENUM_Z0, receiver.PLENUM_W / 2
    box = lambda xa, xb, ya, yb, za, zb: Pos((xa + xb) / 2, (ya + yb) / 2, (za + zb) / 2) * Box(xb - xa, yb - ya, zb - za)
    bodies = []
    for side in (1, -1):
        bodies.append(("Площадка разъёма", receiver.pad(side, z_top=SPLIT_Z + receiver.UP_T, t=receiver.UP_T)))
    front = Plane((x0, 0, z0 + SHEET + h / 2), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))
    sq = receiver.THROTTLE_BOLTS + 24
    from head_flange import BASE
    bodies.append(("Площадка дросселя", front * Box(sq, sq, receiver.THROTTLE_PAD_T, align=BASE)))
    bodies += [("Крышка ресивера", box(x0, x1, -w - SHEET, w + SHEET, top - SHEET, top)),
               ("Дно ресивера", box(x0, x1, -w - SHEET, w + SHEET, z0, z0 + SHEET)),
               ("Стенка ресивера правая", box(x0, x1, w, w + SHEET, z0 + SHEET, top - SHEET)),
               ("Стенка ресивера левая", box(x0, x1, -w - SHEET, -w, z0 + SHEET, top - SHEET)),
               ("Стенка ресивера передняя", box(x0, x0 + SHEET, -w, w, z0 + SHEET, top - SHEET)),
               ("Стенка ресивера задняя", box(x1 - SHEET, x1, -w, w, z0 + SHEET, top - SHEET))]
    for name, (x, y, tap) in receiver.PORTS.items():
        kind = "М22" if tap > 15 else "М12"
        bodies.append((f"Бобышка {kind}", Pos(x0 + x, y, top - 1) * Cylinder(tap / 2 + 6, 11, align=BASE)))
    for side, tag in ((1, "правая"), (-1, "левая")):
        xs = [x for _, x in exits(side)]
        pairs = [(xs[k], xs[k + 1], runner_body(side, xs[k]) + runner_body(side, xs[k + 1])) for k in (0, 2)]
        bodies += tower_pieces(pairs, tag)
    return bodies


def pieces(part, bodies, label):
    """Разбиение с проверкой: объёмы позиций в сумме дают сборку, пустых позиций нет."""
    out = [(n, p) for n, p in split_by_priority(part, bodies)]
    total = sum(p.volume for _, p in out)
    assert abs(total - part.volume) < 1e-3 * part.volume, f"{label}: позиции не покрывают сборку ({total:.0f} из {part.volume:.0f})"
    empty = [n for n, p in out if p.volume < 1]
    assert not empty, f"{label}: пустые позиции {empty}"
    return out


PLATE_AL, SHEET_AL, ROD_AL = "АМг5 ГОСТ 17232-99", "АМг5 ГОСТ 21631-76", "АМг5 ГОСТ 21488-97"
# Наименование позиции → заготовка и примечание; порядок — порядок позиций в спецификации.
PLATE_SPEC = {
    "Фланец правый": (f"Плита 14 {PLATE_AL}", "фрезеровать до 12 после сварки"),
    "Фланец левый": (f"Плита 14 {PLATE_AL}", "фрезеровать до 12 после сварки"),
    "Площадка разъёма": (f"Плита 18 {PLATE_AL}", "фрезеровать до 16 после сварки"),
    "Пол": (f"Лист 10 {SHEET_AL}", ""),
    "Башенка правая, передняя плита": (f"Плита 25 {PLATE_AL}", "полуканал — по модели"),
    "Башенка правая, средняя плита": (f"Плита 50 {PLATE_AL}", "полуканалы — по модели"),
    "Башенка правая, задняя плита": (f"Плита 25 {PLATE_AL}", "полуканал — по модели"),
    "Башенка левая, передняя плита": (f"Плита 25 {PLATE_AL}", "полуканал — по модели"),
    "Башенка левая, средняя плита": (f"Плита 50 {PLATE_AL}", "полуканалы — по модели"),
    "Башенка левая, задняя плита": (f"Плита 25 {PLATE_AL}", "полуканал — по модели"),
    "Опора гайки": (f"Пруток ⌀22 {ROD_AL}", "торец под 35° к оси"),
    "Бобышка форсунки": (f"Пруток ⌀16 {ROD_AL}", "торец — по месту"),
    "Штуцер воды передний": (f"Пруток ⌀30 {ROD_AL}", "сверлить ⌀23"),
    "Штуцер воды задний": (f"Пруток ⌀12 {ROD_AL}", "сверлить ⌀8"),
    "Горловина": (f"Пруток ⌀45 {ROD_AL}", "расточить ⌀36; допускается труба 44×4"),
    "Штуцер сапуна": (f"Пруток ⌀19 {ROD_AL}", "сверлить ⌀13"),
    "Маслоуловитель": (f"Лист 4 {SHEET_AL}", "гнуть или сварить коробку"),
}
RECEIVER_SPEC = {
    "Площадка разъёма": (f"Плита 14 {PLATE_AL}", "фрезеровать до 12 после сварки"),
    "Площадка дросселя": (f"Плита 14 {PLATE_AL}", "фрезеровать до 12 после сварки"),
    "Крышка ресивера": (f"Лист 5 {SHEET_AL}", ""),
    "Дно ресивера": (f"Лист 5 {SHEET_AL}", ""),
    "Стенка ресивера правая": (f"Лист 5 {SHEET_AL}", ""),
    "Стенка ресивера левая": (f"Лист 5 {SHEET_AL}", ""),
    "Стенка ресивера передняя": (f"Лист 5 {SHEET_AL}", ""),
    "Стенка ресивера задняя": (f"Лист 5 {SHEET_AL}", ""),
    "Башенка правая, передняя плита": (f"Плита 25 {PLATE_AL}", "полуканал — по модели"),
    "Башенка правая, средняя плита": (f"Плита 50 {PLATE_AL}", "полуканалы — по модели"),
    "Башенка правая, задняя плита": (f"Плита 25 {PLATE_AL}", "полуканал — по модели"),
    "Башенка левая, передняя плита": (f"Плита 25 {PLATE_AL}", "полуканал — по модели"),
    "Башенка левая, средняя плита": (f"Плита 50 {PLATE_AL}", "полуканалы — по модели"),
    "Башенка левая, задняя плита": (f"Плита 25 {PLATE_AL}", "полуканал — по модели"),
    "Бобышка М12": (f"Пруток ⌀22 {ROD_AL}", ""),
    "Бобышка М22": (f"Пруток ⌀32 {ROD_AL}", ""),
}
SMALL_HOLE = 15.0  # отверстия меньше — сверлятся после сварки, в DXF их нет


def positions(part, bodies, spec, label):
    """Позиции спецификации: одинаковые детали сводятся в одну позицию с количеством."""
    groups = {}
    for name, piece in pieces(part, bodies, label):
        groups.setdefault(name, []).append(piece)
    assert set(groups) == set(spec), f"{label}: спецификация не совпадает с разбиением: {set(groups) ^ set(spec)}"
    out = []
    for pos, (name, (blank, note)) in enumerate(spec.items(), 1):
        ps = groups[name]
        vols = [p.volume for p in ps]
        assert max(vols) - min(vols) < 0.01 * max(vols), f"{label}: «{name}» — детали разные: {vols}"
        out.append({"pos": pos, "name": name, "qty": len(ps), "blank": blank, "note": note, "piece": ps[0],
                    "mass": ps[0].volume * DENSITY})
    return out


def flat_plane(piece):
    """Плоскость раскроя — плоскость грани, поперёк которой деталь тоньше всего; ось X — вдоль коленвала,
    если лежит в плоскости. Контур — сечение с наибольшей площадью: полуканал башенки его не надрезает."""
    def thickness(n):
        ds = [Vector(v).dot(n) for v in piece.vertices()]
        return max(ds) - min(ds)

    normals = {}
    for f in piece.faces():
        if f.geom_type == GeomType.PLANE:
            n = f.normal_at()
            n = n if next(c for c in (n.X, n.Y, n.Z) if abs(c) > 1e-6) > 0 else -n
            normals[tuple(round(c, 3) for c in n)] = n
    n = min(normals.values(), key=thickness)
    x = Vector(1, 0, 0) if abs(n.X) < 0.9 else Vector(0, 1, 0)
    x = (x - n * x.dot(n)).normalized()
    c = piece.center()
    ds = [Vector(v).dot(n) for v in piece.vertices()]
    lo, hi = min(ds), max(ds)
    best = None
    for k in (0.03, 0.2, 0.5, 0.8, 0.97):
        pl = Plane(c + n * (lo + (hi - lo) * k - c.dot(n)), x_dir=x, z_dir=n)
        cut = piece & (pl * Rectangle(3000, 3000))
        faces = cut.faces() if cut else []
        if faces and (best is None or sum(f.area for f in faces) > sum(f.area for f in best[0])):
            best = (faces, pl)
    face = max(best[0], key=lambda f: f.area)
    return face, best[1], hi - lo


def export_dxf(piece, path):
    face, plane, _ = flat_plane(piece)
    wires = [face.outer_wire()] + [w for w in face.inner_wires() if max(w.bounding_box().size) > SMALL_HOLE]
    dxf = ExportDXF(unit=Unit.MM)
    dxf.add_shape([plane.to_local_coords(w) for w in wires])
    dxf.write(path)


def export_positions(items, out, prefix):
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for it in items:
        stem = f"{prefix}-{it['pos']:02d}"
        export_step(it["piece"], out / f"{stem}.step")
        export_brep(it["piece"], out / f"{stem}.brep")
        flat = it["blank"].startswith(("Плита", "Лист")) and flat_plane(it["piece"])[2] <= float(it["blank"].split()[1]) + 0.1
        if flat:
            export_dxf(it["piece"], out / f"{stem}.dxf")
        else:
            (out / f"{stem}.dxf").unlink(missing_ok=True)
        manifest.append({k: v for k, v in it.items() if k != "piece"} | {"stem": stem, "flat": flat})
    (out / f"{prefix}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    return manifest


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
    export_brep(plate, out / "valley_plate.brep")
    export_brep(rec, out / "receiver.brep")
    for label, part, bodies, spec, prefix in (("плита", plate, plate_bodies(), PLATE_SPEC, "plate"),
                                              ("ресивер", rec, receiver_bodies(), RECEIVER_SPEC, "receiver")):
        items = export_positions(positions(part, bodies, spec, label), out / "parts", prefix)
        bb = part.bounding_box()
        print(f"{label}: {bb.size.X:.0f} × {bb.size.Y:.0f} × {bb.size.Z:.0f} мм, {part.volume * DENSITY:.1f} кг, "
              f"{len(items)} позиций, {sum(i['qty'] for i in items)} деталей")
    print(f"Ресивер: коробка {x1 - x0:.0f} × {receiver.PLENUM_W + 2 * SHEET:.0f} × {h + 2 * SHEET:.0f} мм из листа {SHEET:.0f}")


if __name__ == "__main__":
    main()
