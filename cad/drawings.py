"""Рабочие чертежи коллектора по ЕСКД: литой (ЗВК.01) и сварной (ЗВК.02) варианты, PDF и SVG для сайта.

Запуск после cast.py и welded.py (берёт их BRep и STEP из cad/out/): uv run python cad/drawings.py
→ docs-site/static/cad/{cast,welded}/: PDF и SVG листов, STEP, DXF деталей сварки, архивы intake-*.zip.
Базы плиты: А — плоскость разъёма с ресивером, Б и В — оси отверстий средних шпилек правого фланца
(линия Б–В параллельна коленвалу). Размеры, не указанные на листе, — по электронной модели (ГОСТ 2.052).
"""
import json
import math
import shutil
import zipfile
from pathlib import Path

from build123d import Align, GeomType, Plane, Vector, import_brep

import receiver
import valley_plate as vp
from welded import flat_plane
from eskd import Section, Sheet, View, num, text_width, to_pdf
from head_flange import (BANK_OFFSET, PORT_H, PORT_PITCH, PORT_R, PORT_W, RUNNER_D, STUD_HOLE, STUDS, flange_normal,
                         flange_point)

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "docs-site" / "static" / "cad"
OUT = ROOT / "cad" / "out"

BASE_B = flange_point(1, STUDS[2][0], 0)  # передняя из средних шпилек правого фланца
BASE_V = flange_point(1, STUDS[3][0], 0)  # задняя
TILT = 90.0 - math.degrees(math.asin(flange_normal(1).Z))  # плоскость фланца к плоскости разъёма
# штриховка под 45° легла бы почти вдоль фланца — ГОСТ 2.306 требует тогда 30° или 60°
PLATE_HATCH = 60.0 if abs(TILT - 45) < 15 else 45.0

# Размеры, взятые с чертежей и промеров сканов, а не с детали: проверяются примеркой макета (docs/plan.md).
UNVERIFIED = "Размеры, отмеченные *, получены с заводских чертежей двигателя и не проверены на машине. " \
             "Перед запуском партии проверить примеркой макета (печатная модель) на головках и блоке."


def xyz(p):
    """Координаты в системе чертежа: X, Y — от оси Б, Z — вниз от плоскости А."""
    return p.X - BASE_B.X, p.Y - BASE_B.Y, vp.SPLIT_Z - p.Z


def plate_holes():
    rows = []
    for side, tag in ((1, "П"), (-1, "Л")):
        for i, (a, c) in enumerate(sorted(STUDS), 1):
            p = flange_point(side, a, c)
            top = Vector(p.X, p.Y, p.Z + vp.seat_rise())
            rows.append((f"Ш{tag}{i}", top, f"⌀{num(STUD_HOLE)} H14 скв., цековка ⌀{num(vp.SEAT_D)}", vp.SEAT_D / 2))
    for side, tag in ((1, "П"), (-1, "Л")):
        for i, (x, y) in enumerate(sorted(vp.pad_bolts(side)), 1):
            rows.append((f"Р{tag}{i}", Vector(x, y, vp.SPLIT_Z), "М8-6Н скв.", 4.0))
    rows.append(("Ф", Vector(*vp.DOWEL, vp.VALLEY_Z), "⌀8 H12 скв.", 4.0))
    return rows


def hole_table(sheet, rows, coords, x0=651.0, y_top=560.0):
    body = [(name, *(num(c) for c in coords(p)), what) for name, p, what, _ in rows]
    sheet.text("Координаты осей отверстий, мм", (x0 + 85, y_top + 2), 3.5, (Align.CENTER, Align.MIN))
    sheet.table(x0, y_top, [("Обозн.", 14), ("X", 17), ("Y", 17), ("Z", 15), ("Отверстие", 107)], body,
                head_h=7, row_h=5.5, h=2.5)


def hole_marks(sheet, view, rows, outward=False):
    """Центровые линии и метки отверстий. Метка — слева за контуром (выноски отверстий уходят вправо), снизу
    или, при outward, с внешней от середины вида стороны: ряды у кромок площадок остаются чистыми."""
    mid = view.box.center().Y
    for name, p, _, r in rows:
        c, r = view(p), r * sheet.scale
        sheet.center(c, r)
        up = outward and c.Y > mid
        sheet.text(name, (c.X - 0.7 * r - 1, c.Y + (1 if up else -1) * (0.7 * r + 0.5)), 2.5,
                   (Align.MAX, Align.MIN if up else Align.MAX))


def rim(sheet, view, p, r, toward):
    """Точка контура отверстия радиуса r, обращённая к полке выноски: стрелка — на контур, не в центр."""
    c = view(p)
    return c + (Vector(toward) - c).normalized() * r * sheet.scale


def flange_view(sheet, part, side, at):
    """Местный вид на привалочную плоскость фланца со стороны головки; ось X листа — вдоль коленвала.
    Строится по граням самой плоскости: вырез коробкой оставлял линии среза, которых на детали нет."""
    n, p0 = flange_normal(side), flange_point(side, 0, 0)
    up = Vector(0, -side * n.Z, side * n.Y) * -1 if side > 0 else Vector(0, -side * n.Z, side * n.Y)
    faces = [f for f in part.faces() if f.geom_type == GeomType.PLANE and f.normal_at().dot(n) < -0.999
             and abs((f.center() - p0).dot(n)) < 0.5]
    return View(sheet, faces[0].fuse(*faces[1:]).clean(), n, up, at, p0)


PLATE_REQ_CAST = [
    "Отливка — по электронной модели ЗВК.01.001-ОТЛ (valley_plate_casting.step): припуск 2 мм на обрабатываемые "
    "поверхности. Точность отливки не грубее 9-0-0-9 ГОСТ 26645-85.",
    "Литейные уклоны — по технологии литейщика, не более 1° за счёт тела отливки. Неуказанные литейные радиусы 2...3 мм.",
    "Стенки каналов 4 +1,5/−0,5 мм. Внутренние поверхности каналов литые, не грубее Ra 25; облой и наплывы удалить.",
    "Раковины, трещины, спаи и неслитины не допускаются; на плоскостях А и привалочных плоскостях фланцев — "
    "пористость не допускается.",
]
PLATE_REQ_COMMON = [
    "Неуказанные предельные отклонения размеров обработанных поверхностей — ГОСТ 30893.1-m.",
    "Привалочные плоскости фланцев: плоскостность 0,1, Ra 3,2, угол к плоскости А {tilt}°±15′. Окна фланцев "
    "не должны выступать за окна головки: смещение кромок не более 0,5 мм.",
    "Резьбы — ГОСТ 16093-2004, поле 6Н; на входе фаска 1×45°. Острые кромки притупить R0,5.",
    "Испытать на герметичность: окна и отверстия заглушить, воздух 0,25 МПа, 3 мин под водой. Пропуск воздуха "
    "не допускается.",
    "Фланец левого ряда — зеркальное отражение правого относительно вертикальной продольной плоскости "
    "с его смещением вперёд на {offset}* мм (координаты — в таблице).",
    "Координаты X, Y — от оси отверстия Б, ось X — по линии Б–В; Z — вниз от плоскости А.",
    UNVERIFIED,
]


def plate_sheet(part, code, name, material, mass, requirements, sheets=1):
    s = Sheet("A1", name, code, 0.5, material, mass, sheets=sheets)
    s.general_roughness("Ra 12,5")
    lo, hi = part.bounding_box().min, part.bounding_box().max
    main = View(s, part, (0, 1, 0), (0, 0, 1), (200, 505), (190, 0, 380))
    View(s, part, (1, 0, 0), (0, 0, 1), (490, 505), (0, 0, 380))
    top = View(s, part, (0, 0, -1), (0, 1, 0), (200, 315), (190, 0, 0))

    s.dim(main, (lo.X, 0, lo.Z), (hi.X, 0, lo.Z), 10, (1, 0))
    s.dim(main, (hi.X, 0, lo.Z), (hi.X, 0, hi.Z), 12, (0, 1))
    s.dim(main, (hi.X, 0, vp.VALLEY_Z), (hi.X, 0, vp.SPLIT_Z), 24, (0, 1), mark=True, tol=" ±0,3")
    s.dim(top, (lo.X, lo.Y, 0), (lo.X, hi.Y, 0), -10, (0, 1))

    pad_top = Vector(BASE_B.X + 230, 0, vp.SPLIT_Z)
    s.datum(main(pad_top), (0, 1), "А")
    s.tolerance((main(pad_top).X + 30, main(pad_top).Y + 12), "⏥", "0,1", target=main(pad_top + Vector(70, 0, 0)))
    s.roughness(main(pad_top + Vector(-120, 0, 0)), "Ra 3,2")
    s.leader(main(Vector(vp.DOWEL[0] + 20, 0, vp.VALLEY_Z)), main(Vector(vp.DOWEL[0] + 20, 0, lo.Z)) + Vector(25, -12),
             "Опора на блок", below="Ra 6,3", arrow=True)

    holes = plate_holes()
    hole_marks(s, top, holes, outward=True)
    x, y, d, _ = vp.NECK
    s.center(top(Vector(x, y, 0)), d / 2 * s.scale)
    for p, letter in ((BASE_B, "Б"), (BASE_V, "В")):
        c = top(p)
        s.datum(c + Vector(STUD_HOLE / 4, 0), (1, 1), letter)
    s.dim(top, BASE_B, BASE_V, -(hi.Y - BASE_B.Y) * 0.5 - 14, (1, 0), tol=" ±0,1")
    left_b = flange_point(-1, STUDS[2][0], 0)
    s.dim(top, (left_b.X, lo.Y, 0), (BASE_B.X, lo.Y, 0), 10, (1, 0), mark=True, tol=" ±0,2")
    end = s.leader(top(flange_point(1, STUDS[5][0], 0)) + Vector(1.9, 1.9), top(BASE_B) + Vector(150, 22),
                   f"14 отв. ⌀{num(STUD_HOLE)} H14", below=f"цековка ⌀{num(vp.SEAT_D)}, Ra 6,3")
    s.tolerance((end.X, end.Y - 3.5), "pos", "⌀0,5", "АБВ")
    shelf = top(BASE_B) + Vector(150, -85)
    end = s.leader(rim(s, top, Vector(*vp.pad_bolts(1)[2], 0), 3.4, shelf), shelf, "12 отв. М8-6Н скв.",
                   below="фаска 1×45°")
    s.tolerance((end.X, end.Y - 3.5), "pos", "⌀0,3", "АБВ")
    s.leader(top(Vector(*vp.DOWEL, 0)) + Vector(1.4, -1.4), top(Vector(*vp.DOWEL, 0)) + Vector(30, -12),
             "Отв. Ф ⌀8 H12", below="под штифт блока")
    x, y, d, _ = vp.NECK
    s.leader(top(Vector(x, y - d / 2, 0)), top(Vector(x, y, 0)) + Vector(40, -40), f"⌀{num(d)} H11", below="горловина")

    # сечение А–А между шпильками: оба фланца, угол и высота плоскости фланца на оси Б
    xs = 150.0  # между шпильками и каналами обоих рядов
    plane = Plane((xs, 0, 0), x_dir=(0, -1, 0), z_dir=(-1, 0, 0))
    a = Section(s, part, plane, (505, 310), (xs, 0, 380), PLATE_HATCH)
    s.cut_mark(main, (xs, 0, hi.Z + 8), (xs, 0, lo.Z - 8), "А", (-1, 0))
    s.caption("А–А", (a.box.center().X, a.box.max.Y + 8))
    p_r, p_l = flange_point(1, 0, 0), flange_point(-1, 0, 0)
    pr, pl = Vector(xs, p_r.Y, p_r.Z), Vector(xs, p_l.Y, p_l.Z)
    s.axis(a(pr) + Vector(0, 12), a(pr) - Vector(0, 12))
    s.axis(a(pl) + Vector(0, 12), a(pl) - Vector(0, 12))
    s.dim(a, pr, pl, 30, (1, 0), label=num(2 * p_r.Y, 2), tol=" ±0,2")
    s.dim(a, (xs, p_r.Y, vp.SPLIT_Z), pr, 22, (0, 1), label=num(vp.SPLIT_Z - p_r.Z, 2), tol=" ±0,2")
    s.dim(a, (xs, p_l.Y, vp.SPLIT_Z), pl, -22, (0, 1), label=num(vp.SPLIT_Z - p_l.Z, 2), tol=" ±0,2")
    s.angle(a(pr), 180 + TILT, 180, 22, f"{num(TILT)}°")
    s.roughness(a(pr) + Vector(-8, -7), "Ra 3,2", 180 + TILT + 90 - 90)
    s.tolerance((a.box.min.X - 5, a.box.min.Y - 28), "⏥", "0,1",
                target=a(pr + (flange_point(1, 0, 25) - flange_point(1, 0, 0))))
    n = flange_normal(1)
    tip = a(pr + (flange_point(1, 0, 30) - p_r) - n * 2)
    d = (a(pr + n) - a(pr)).normalized()
    s.line(tip - d * 16, tip)
    s.arrow(tip, d)
    s.text("Г", tip - d * 20, 5, (Align.CENTER, Align.CENTER))

    # сечение Б–Б по оси канала правого ряда: стенка и выход ⌀42 в плоскость разъёма
    port, xc = vp.exits(1)[1]
    plane = Plane((xc, 0, 0), x_dir=(0, -1, 0), z_dir=(-1, 0, 0))
    b = Section(s, part, plane, (505, 150), (xc, 0, 380), PLATE_HATCH)
    s.cut_mark(top, (xc, hi.Y + 5, 0), (xc, BASE_B.Y - 60, 0), "Б", (1, 0))
    s.caption("Б–Б", (b.box.center().X, b.box.max.Y + 8))
    z = vp.SPLIT_Z - 8
    s.dim(b, (xc, vp.EXIT_Y + RUNNER_D / 2, z), (xc, vp.EXIT_Y - RUNNER_D / 2, z), -14, (1, 0),
          prefix="⌀", tol=" ±0,5")
    # вид на фланец правого ряда со стороны головки
    g = flange_view(s, part, 1, (200, 110))
    s.caption("Г", (g.box.center().X, g.box.max.Y + 8))
    ports = [flange_point(1, pair + d * PORT_PITCH / 2, 0) for pair in (-vp.PITCH, vp.PITCH) for d in (-1, 1)]
    chain = [BASE_B] + ports + [BASE_V]
    for p, q in zip(chain, chain[1:]):
        s.dim(g, p, q, -(g(p).Y - g.box.min.Y + 8), (1, 0), label=num(abs(q.X - p.X), 2))
    w = flange_point(1, 0, PORT_H / 2) - flange_point(1, 0, 0)
    s.dim(g, ports[0] + w, ports[0] - w, 10, (0, 1))
    u = flange_point(1, PORT_W / 2, 0) - flange_point(1, 0, 0)
    s.dim(g, ports[1] - u - w, ports[1] + u - w, g.box.max.Y + 8 - g(ports[1] - w).Y, (1, 0))
    s.axis(g(BASE_B) - Vector(8, 0), g(BASE_V) + Vector(8, 0))
    for p in ports:
        s.axis(g(p + w) + Vector(0, 3), g(p - w) - Vector(0, 3))
    for along, across in STUDS:
        s.center(g(flange_point(1, along, across)), STUD_HOLE / 2 / abs(flange_normal(1).Z) * s.scale)
    for (along, across), (bore, _) in zip(sorted(vp.WATER), (vp.WATER_FRONT, vp.WATER_REAR)):
        s.center(g(flange_point(1, along, across)), bore / 2 * s.scale)
    s.leader(g(ports[2] + w * 0.6 + u), (g.box.max.X + 5, g.box.min.Y - 10), f"4 окна R{num(PORT_R)}",
             below="ось окон — по линии Б–В")
    for side in (-1,):
        port, x = vp.exits(side)[2]
        boss = vp.gas_fitting(side, port, x, hole=False)
        s.leader(top(boss.center()), top(boss.center()) + Vector(60, -40), "8 отв. М8×1-6Н",
                 below="оси — по эл. модели")
        (fb, rb), _ = vp.water(side)
        s.leader(top(fb.center()), top(fb.center()) + Vector(90, -32), f"⌀{num(vp.WATER_FRONT[1])}, проход "
                 f"⌀{num(vp.WATER_FRONT[0])}", below="2 штуцера воды")
        s.leader(top(rb.center()), top(rb.center()) + Vector(15, -38), f"⌀{num(vp.WATER_REAR[1])}, проход "
                 f"⌀{num(vp.WATER_REAR[0])}", below="2 штуцера воды")
    bx, by, bd, bod, _ = vp.BREATHER
    s.leader(top(Vector(bx, by, 0)), top(Vector(bx, by, 0)) + Vector(35, -8), f"⌀{num(bod)}, проход ⌀{num(bd)}",
             below="штуцер сапуна")
    hole_table(s, plate_holes(), xyz)
    s.requirements([r.format(tilt=num(TILT), offset=num(BANK_OFFSET)) for r in requirements])
    return s


REC_B = Vector(*sorted(vp.pad_bolts(1))[1], vp.SPLIT_Z)  # передний наружный болт правой площадки
REC_V = Vector(*sorted(vp.pad_bolts(1))[5], vp.SPLIT_Z)  # задний наружный


def rxyz(p):
    """Ресивер: X, Y — от оси Б, Z — вверх от плоскости А."""
    return p.X - REC_B.X, p.Y - REC_B.Y, p.Z - vp.SPLIT_Z


def receiver_holes(wall):
    _, _, _, (x0, _, h, top) = receiver.plenum(wall)
    rows = []
    for side, tag in ((1, "П"), (-1, "Л")):
        for i, (x, y) in enumerate(sorted(vp.pad_bolts(side)), 1):
            rows.append((f"Р{tag}{i}", Vector(x, y, vp.SPLIT_Z), f"⌀{num(receiver.BOLT_CLEAR)} H14 скв.",
                         receiver.BOLT_CLEAR / 2))
    threads = {"ДАД": "М12×1,5-6Н", "ДТВ": "М12×1,5-6Н", "газовый редуктор": "М12×1,5-6Н", "РХХ": "М22×1,5-6Н",
               "картерные газы": "М12×1,5-6Н"}
    for i, (name, (x, y, tap)) in enumerate(receiver.PORTS.items(), 1):
        rows.append((f"Т{i}", Vector(x0 + x, y, top + 10), f"{threads[name]} скв., {name}", tap / 2 + 6))
    return rows


def receiver_sheet(part, code, name, material, mass, wall, requirements, sheets=1):
    s = Sheet("A1", name, code, 0.5, material, mass, sheets=sheets)
    s.general_roughness("Ra 12,5")
    lo, hi = part.bounding_box().min, part.bounding_box().max
    x0, x1, h, top_z = receiver.plenum(wall)[3]
    main = View(s, part, (0, 1, 0), (0, 0, 1), (230, 470), (190, 0, 490))
    left = View(s, part, (1, 0, 0), (0, 0, 1), (500, 470), (0, 0, 490))
    top = View(s, part, (0, 0, -1), (0, 1, 0), (230, 300), (190, 0, 0))

    s.dim(main, (lo.X, 0, lo.Z), (hi.X, 0, lo.Z), 10, (1, 0))
    s.dim(main, (hi.X, 0, vp.SPLIT_Z), (hi.X, 0, hi.Z), 12, (0, 1))
    s.dim(top, (lo.X, lo.Y, 0), (lo.X, hi.Y, 0), -10, (0, 1))
    bottom = Vector(REC_B.X + 100, 0, vp.SPLIT_Z)
    s.datum(main(bottom), (0, -1), "А")
    s.tolerance((main(bottom).X + 25, main(bottom).Y - 22), "⏥", "0,1", target=main(bottom + Vector(60, 0, 0)))
    s.roughness(main(bottom + Vector(160, 0, 0)), "Ra 3,2", 180)

    holes = receiver_holes(wall)
    hole_marks(s, top, holes)
    for p, letter in ((REC_B, "Б"), (REC_V, "В")):
        s.datum(top(p) + Vector(-1.6, 1.6), (-1, 1), letter)
    s.dim(top, REC_B, REC_V, -(hi.Y - REC_B.Y) * 0.5 - 14, (1, 0), tol=" ±0,1")
    shelf = top(REC_B) + Vector(150, 40)
    end = s.leader(rim(s, top, Vector(*sorted(vp.pad_bolts(1))[3], 0), receiver.BOLT_CLEAR / 2, shelf), shelf,
                   f"12 отв. ⌀{num(receiver.BOLT_CLEAR)} H14", below="Ra 12,5")
    s.tolerance((end.X, end.Y - 3.5), "pos", "⌀0,3", "АБВ")
    t1 = holes[12][1]
    shelf = top(REC_B) + Vector(60, -150)
    end = s.leader(rim(s, top, t1, 5.1, shelf), shelf, "4 отв. М12×1,5-6Н",
                   below="1 отв. М22×1,5-6Н (Т4)")
    s.tolerance((end.X, end.Y - 3.5), "pos", "⌀0,5", "АБВ")

    # площадка дросселя: вид слева спереди по ходу
    zc = receiver.PLENUM_Z0 + wall + h / 2
    half = receiver.THROTTLE_BOLTS / 2
    face_x = x0 - receiver.THROTTLE_PAD_T
    c = Vector(face_x, 0, zc)
    s.center(left(c), receiver.THROTTLE_OPENING / 4)
    bolts = [Vector(face_x, dy, zc + dz) for dy in (-half, half) for dz in (-half, half)]
    for p in bolts:
        s.center(left(p), 4 * s.scale)
    s.dim(left, (face_x, half, zc + half), (face_x, -half, zc + half), -(hi.Z - zc - half) * 0.5 - 10, (1, 0))
    s.dim(left, (face_x, -half, zc - half), (face_x, -half, zc + half), (hi.Y - half) * 0.5 + 10, (0, 1))
    s.dim(left, (face_x, 0, vp.SPLIT_Z), (face_x, 0, zc), -((hi.Y) * 0.5 + 12), (0, 1), tol=" ±0,3")
    s.leader(left(c + Vector(0, receiver.THROTTLE_OPENING / 2, 0)), left(c) + Vector(-40, -42),
             f"⌀{num(receiver.THROTTLE_OPENING)} +0,5", below="окно дросселя")
    shelf = left(c) + Vector(55, 45)
    end = s.leader(rim(s, left, c + Vector(0, half, half), 4, shelf), shelf, "4 отв. М8-6Н скв.",
                   below="фаска 1×45°")
    s.tolerance((end.X, end.Y - 3.5), "pos", "⌀0,3", "А")
    s.dim(main, (face_x, 0, lo.Z), REC_B + Vector(0, -REC_B.Y, 0), 22, (1, 0), tol=" ±0,3")
    face = Vector(face_x, 0, zc - 30)
    s.tolerance((main(face).X - 45, main(face).Y - 25), "⊥", "0,1", "А", target=main(face))
    s.roughness(main(Vector(face_x, 0, zc + 25)), "Ra 3,2", 90)

    # сечение по оси раннера правого ряда
    _, xr = vp.exits(1)[1]
    plane = Plane((xr, 0, 0), x_dir=(0, -1, 0), z_dir=(-1, 0, 0))
    a = Section(s, part, plane, (500, 290), (xr, 0, 490))
    s.cut_mark(top, (xr, hi.Y + 5, 0), (xr, lo.Y - 5, 0), "А", (1, 0))
    s.caption("А–А", (a.box.center().X, a.box.max.Y + 8))
    s.dim(a, (xr, vp.EXIT_Y + RUNNER_D / 2, vp.SPLIT_Z + 6), (xr, vp.EXIT_Y - RUNNER_D / 2, vp.SPLIT_Z + 6), 14,
          (1, 0), prefix="⌀", tol=" ±0,5")
    s.dim(a, (xr, -receiver.PLENUM_W / 2, top_z - wall), (xr, receiver.PLENUM_W / 2, top_z - wall), -16, (1, 0),
          label=num(receiver.PLENUM_W))
    s.dim(a, (xr, -receiver.PLENUM_W / 2, receiver.PLENUM_Z0 + wall), (xr, -receiver.PLENUM_W / 2, top_z - wall),
          -12, (0, 1), label=num(h))
    hole_table(s, receiver_holes(wall), rxyz)
    s.requirements(requirements)
    return s


REC_REQ_CAST = [
    "Отливка — по электронной модели ЗВК.01.002-ОТЛ (receiver_casting.step): припуск 2 мм на обрабатываемые "
    "поверхности. Точность отливки не грубее 9-0-0-9 ГОСТ 26645-85.",
    "Литейные уклоны — по технологии литейщика, не более 1° за счёт тела отливки. Неуказанные литейные радиусы 2...3 мм.",
    "Стенки ресивера и раннеров 4 +1,5/−0,5 мм. Внутренние поверхности литые, не грубее Ra 25; облой и наплывы "
    "удалить.",
    "Раковины, трещины, спаи и неслитины не допускаются; на плоскости А и площадке дросселя пористость не допускается.",
]
REC_REQ_COMMON = [
    "Неуказанные предельные отклонения размеров обработанных поверхностей — ГОСТ 30893.1-m.",
    "Резьбы — ГОСТ 16093-2004, поле 6Н; на входе фаска 1×45°. Торцы бобышек резьб Т1...Т5 — Ra 6,3, "
    "перпендикулярно оси резьбы. Острые кромки притупить R0,5.",
    "Отверстия Р совместно с плитой развала: смещение раннеров относительно каналов плиты при сборке не более 0,5 мм.",
    "Испытать на герметичность: окна заглушить, воздух 0,25 МПа, 3 мин под водой. Пропуск воздуха не допускается.",
    "Координаты X, Y — от оси отверстия Б, ось X — по линии Б–В; Z — вверх от плоскости А.",
]


def model_req(code, stem):
    return (f"Размеры, не указанные на чертеже, и геометрия каналов — по электронной модели {code} ({stem}.step, "
            "ГОСТ 2.052). При расхождении действует чертёж.")


WELD_REQ = [
    "Сварка — ГОСТ 14806-80, аргонодуговая неплавящимся электродом на переменном токе, проволока СвАМг5 "
    "ГОСТ 7871-2019. Швы — по таблице на листе 2.",
    "Кромки и полуканалы перед сваркой обезжирить и зачистить от оксидной плёнки не ранее чем за 4 ч до сварки.",
    "Собирать в кондукторе по плоскостям фланцев и разъёма: оси каналов — по окнам фланцев и отверстиям ⌀42 "
    "площадок, смещение не более 1 мм. Наплывы швов внутри каналов у окон и у площадок зачистить заподлицо.",
    "Плоскости, отверстия и резьбы по чертежу обрабатывать после сварки. Детали, кроме плит башенок, "
    "раскраивать по DXF; мелкие отверстия в DXF не входят и сверлятся после сварки.",
]


def welds_table(sheet, rows, x0=651.0, y_top=0.0):
    sheet.text("Сварные швы", (x0 + 92, y_top + 2), 3.5, (Align.CENTER, Align.MIN))
    sheet.table(x0, y_top, [("Обозн.", 12), ("Что соединяет", 72), ("Шов", 72), ("Герметичн.", 29)], rows,
                head_h=7, row_h=6, h=2.5)
    return y_top - 7 - 6 * len(rows)


PLATE_WELDS = [
    ("Ш1", "Плиты башенок между собой (5–10)", "стыковой по контуру, V-разделка 4", "да"),
    ("Ш2", "Башенки к фланцам (1, 2)", "угловой по контуру, катет 5", "да"),
    ("Ш3", "Башенки к площадкам разъёма (3)", "угловой по контуру, катет 5", "да"),
    ("Ш4", "Пол (4) к фланцам", "угловой двусторонний, катет 5", "нет"),
    ("Ш5", "Опоры гаек (11) к фланцам", "угловой по контуру, катет 4", "нет"),
    ("Ш6", "Бобышки, штуцеры, горловина (12–16)", "угловой по контуру, катет 4", "да"),
    ("Ш7", "Маслоуловитель (17) к полу", "угловой по контуру, катет 3", "да"),
]
RECEIVER_WELDS = [
    ("Ш1", "Плиты башенок между собой (9–14)", "стыковой по контуру, V-разделка 4", "да"),
    ("Ш2", "Стенки коробки между собой (3–8)", "угловой снаружи, катет 4", "да"),
    ("Ш3", "Башенки к стенкам (5, 6)", "угловой по контуру, катет 5", "да"),
    ("Ш4", "Башенки к площадкам разъёма (1)", "угловой по контуру, катет 5", "да"),
    ("Ш5", "Площадка дросселя (2) к стенке (7)", "угловой по контуру, катет 4", "да"),
    ("Ш6", "Бобышки (15, 16) к крышке", "угловой по контуру, катет 4", "да"),
]


def composition_sheet(assembly, items, pieces, welds, code, name, mass):
    """Лист 2 сборочного чертежа: аксонометрия с номерами позиций, спецификация и таблица швов."""
    s = Sheet("A1", name, code, 0.5, "", mass, sheet=2, sheets=2)
    d = Vector(1, 1, -0.8).normalized()
    up = (Vector(0, 0, 1) - d * d.Z).normalized()
    c = assembly.bounding_box().center()
    iso = View(s, assembly, d, up, (300, 330), c)
    s.caption("Аксонометрия (детали — в масштабе 1:2)", (iso.box.center().X, iso.box.max.Y + 25))
    marks = []
    for it in items:
        p = pieces[it["stem"]]
        marks.append((iso(p.center()), str(it["pos"])))
    left = sorted([m for m in marks if m[0].X < iso.box.center().X], key=lambda m: -m[0].Y)
    right = sorted([m for m in marks if m[0].X >= iso.box.center().X], key=lambda m: -m[0].Y)
    for group, x in ((left, iso.box.min.X - 30), (right, iso.box.max.X + 20)):
        y0, y1 = iso.box.max.Y + 10, iso.box.min.Y - 10
        slots = [Vector(x, y0 - (y0 - y1) * (k + 0.5) / max(len(group), 1)) for k in range(len(group))]
        for (target, label), at in zip(group, untangle([t for t, _ in group], slots)):
            s.balloon(target, at, label)
    rows = [(str(it["pos"]), it["name"], str(it["qty"]), it["blank"], it["note"]) for it in items]
    s.text("Спецификация", (651 + 92, 575 + 2), 3.5, (Align.CENTER, Align.MIN))
    s.table(651, 575, [("Поз.", 8), ("Наименование", 55), ("Кол.", 8), ("Заготовка", 56), ("Примечание", 58)],
            rows, head_h=7, row_h=6, h=2.2)
    y = 575 - 7 - 6 * len(rows) - 14
    welds_table(s, welds, y_top=y)
    s.requirements(["Номера позиций совпадают с именами файлов STEP и DXF деталей: {0}-NN.".format(
        items[0]["stem"].rsplit("-", 1)[0]), "Массы деталей и заготовки — в спецификации; катеты швов — не менее "
        "указанных."])
    return s


def crosses(a, b, c, d):
    side = lambda p, q, r: (q - p).cross(r - p).Z
    return side(a, b, c) * side(a, b, d) < 0 and side(c, d, a) * side(c, d, b) < 0


def untangle(targets, slots):
    """Выноски позиций не пересекаются (ГОСТ 2.109): меняем местами полки у пересекающихся пар.
    Каждый обмен укорачивает суммарную длину выносок, поэтому цикл конечен."""
    slots = list(slots)
    tangled = True
    while tangled:
        tangled = False
        for i in range(len(targets)):
            for j in range(i + 1, len(targets)):
                if crosses(targets[i], slots[i], targets[j], slots[j]):
                    slots[i], slots[j] = slots[j], slots[i]
                    tangled = True
    return slots


def details_sheet(items, pieces, code, name, scale=0.5):
    """Деталировка: каждая позиция — вид на плоскость раскроя (плитные) или сбоку (прутки) с габаритами."""
    s = Sheet("A1", name, code, scale, "АМг5", "", sheet=1, sheets=1)
    s.requirements(["Контур плитных и листовых деталей — по DXF, толщина — по заготовке; полуканалы башенок, "
                    "фаски и торцы под сварку — по STEP позиции.",
                    "Габариты на листе — справочные, для раскроя заготовок. Неуказанные предельные отклонения — "
                    "ГОСТ 30893.1-m."])
    x, y_row, row_h = 30.0, 575.0, 0.0
    for it in items:
        piece = pieces[it["stem"]]
        _, plane, _ = flat_plane(piece)
        n = plane.z_dir
        if it["flat"]:
            direction, up = -n, plane.y_dir
        else:
            direction = (Vector(1, 0, 0) - n * n.X).normalized() if abs(n.X) < 0.9 else Vector(0, 1, 0)
            up = n
        probe = View(Sheet("A3", "", "", scale, "", ""), piece, direction, up, (0, 0), piece.center())
        w, h = probe.box.size.X, probe.box.size.Y
        labels = [f"Поз. {it['pos']}. {it['name']}, {it['qty']} шт.", it["blank"],
                  f"{it['note'] + '; ' if it['note'] else ''}{it['stem']}.step" + (", .dxf" if it["flat"] else "")]
        cell_w = max(w + 28, max(text_width(t, 3.0 if i == 0 else 2.5) for i, t in enumerate(labels)) + 14)
        cell_h = h + 40
        if x + cell_w > 836:
            x, y_row, row_h = 30.0, y_row - row_h, 0.0
        if y_row - cell_h < 70 and x + cell_w > 640:
            x, y_row, row_h = 30.0, y_row - row_h, 0.0
        at = Vector(x + 14 + w / 2, y_row - 8 - h / 2)
        v = View(s, piece, direction, up, at, piece.center())
        b = v.box
        ident = lambda p: Vector(p)
        s.dim(ident, (b.min.X, b.min.Y), (b.max.X, b.min.Y), 7, (1, 0), label=num(w / scale))
        s.dim(ident, (b.max.X, b.min.Y), (b.max.X, b.max.Y), 7, (0, 1), label=num(h / scale))
        ty = b.min.Y - 16
        for i, t in enumerate(labels):
            s.text(t, (x + 4, ty - (0 if i == 0 else 0.5 + 4.5 * i)), 3.0 if i == 0 else 2.5)
        x += cell_w
        row_h = max(row_h, cell_h)
    return s


def cast_docs(out, site):
    plate = import_brep(out / "valley_plate.brep")
    rec = import_brep(out / "receiver.brep")
    density = 2.68e-6
    s = plate_sheet(plate, "ЗВК.01.001", "Плита развала\nлитая", "АК9ч ГОСТ 1583-93", num(plate.volume * density),
                    PLATE_REQ_CAST + [model_req("ЗВК.01.001", "valley-plate")] + PLATE_REQ_COMMON)
    to_pdf([s.save(site / "valley-plate.svg")], site / "valley-plate.pdf")
    s = receiver_sheet(rec, "ЗВК.01.002", "Ресивер\nлитой", "АК9ч ГОСТ 1583-93", num(rec.volume * density), 4.0,
                       REC_REQ_CAST + [model_req("ЗВК.01.002", "receiver")] + REC_REQ_COMMON)
    to_pdf([s.save(site / "receiver.svg")], site / "receiver.pdf")
    for src, dst in (("valley_plate", "valley-plate"), ("valley_plate_casting", "valley-plate-casting"),
                     ("receiver", "receiver"), ("receiver_casting", "receiver-casting"), ("cast_assembly", "assembly")):
        shutil.copy(out / f"{src}.step", site / f"{dst}.step")


def welded_docs(out, site):
    import welded
    density = welded.DENSITY
    parts_dir = site / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    for kind, code, title, stem, sheet_fn, welds, extra in (
            ("plate", "ЗВК.02.100", "Плита развала\nсварная", "valley-plate", plate_sheet, PLATE_WELDS,
             [model_req("ЗВК.02.100", "valley-plate")] + PLATE_REQ_COMMON),
            ("receiver", "ЗВК.02.200", "Ресивер\nсварной", "receiver", None, RECEIVER_WELDS,
             [model_req("ЗВК.02.200", "receiver")] + REC_REQ_COMMON)):
        part = import_brep(out / f"{stem.replace('-', '_')}.brep")
        items = json.loads((out / "parts" / f"{kind}.json").read_text())
        pieces = {it["stem"]: import_brep(out / "parts" / f"{it['stem']}.brep") for it in items}
        mass = num(part.volume * density)
        if kind == "plate":
            s1 = plate_sheet(part, code + " СБ", title, "", mass, WELD_REQ + extra, sheets=2)
        else:
            s1 = receiver_sheet(part, code + " СБ", title, "", mass, welded.SHEET, WELD_REQ + extra, sheets=2)
        s2 = composition_sheet(part, items, pieces, welds, code + " СБ", title, mass)
        svgs = [s1.save(site / f"{stem}-sb-1.svg"), s2.save(site / f"{stem}-sb-2.svg")]
        to_pdf(svgs, site / f"{stem}-sb.pdf")
        d = details_sheet(items, pieces, code + " Д", title.split("\n")[0] + "\nдетали")
        to_pdf([d.save(site / f"{stem}-parts.svg")], site / f"{stem}-parts.pdf")
        for it in items:
            for ext in ("step", "dxf") if it["flat"] else ("step",):
                shutil.copy(out / "parts" / f"{it['stem']}.{ext}", parts_dir)
        shutil.copy(out / f"{stem.replace('-', '_')}.step", site / f"{stem}.step")
    shutil.copy(out / "welded_assembly.step", site / "assembly.step")


def pack(site, name):
    with zipfile.ZipFile(site / name, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(site.rglob("*")):
            if f.suffix in (".step", ".dxf", ".pdf"):
                z.write(f, f.relative_to(site))


if __name__ == "__main__":
    for variant, fn in (("cast", cast_docs), ("welded", welded_docs)):
        site = STATIC / variant
        shutil.rmtree(site, ignore_errors=True)
        site.mkdir(parents=True)
        fn(OUT / variant, site)
        pack(site, f"intake-{variant}.zip")
    print("Чертежи, STEP и DXF записаны в", STATIC.relative_to(ROOT))
