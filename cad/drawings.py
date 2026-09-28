"""Чертежи коллектора для мастерской: три вида с основными размерами (SVG) и STEP в архиве для сайта.

Запуск: uv run python cad/drawings.py  → docs-site/static/cad/intake-step.zip, docs-site/static/img/drawings/*.svg
Размеры на листах — габаритные и присоединительные, для оценки цены; полная геометрия — в STEP.
Оси модели: X назад вдоль коленвала, Y вправо, Z вверх от оси коленвала.
"""
import sys
import zipfile
from pathlib import Path

from build123d import Compound, Draft, ExportSVG, ExtensionLine, Pos, Text, Vector, export_step, import_step

import receiver
import valley_plate
from head_flange import PLENUM_VOL, RUNNER_D, STUD_HOLE, WALL

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "docs-site" / "static"
GAP = 90.0  # между видами на листе
DRAFT = Draft(font_size=9.0, font="DejaVu Sans", decimal_precision=0, display_units=False, arrow_length=4.0,
              line_width=0.35, extension_gap=3.0)
# Камеры: откуда смотрим и что на листе вверху. Раскладка по ЕСКД: вид сверху под главным, вид слева — справа.
VIEWS = {
    "главный": ((0, -5000, 0), (0, 0, 1)),  # слева от машины: X вправо на листе, Z вверх
    "сверху": ((0, 0, 5000), (0, 1, 0)),  # X вправо, Y вверх
    "слева": ((-5000, 0, 0), (0, 0, 1)),  # спереди по ходу: −Y вправо, Z вверх
}


def to_sheet(view, p):
    """Точка модели (X, Y, Z) → точка на листе в осях того же вида, до сдвига вида по листу."""
    x, y, z = p
    return {"главный": (x, z), "сверху": (x, y), "слева": (-y, z)}[view]


class Sheet:
    def __init__(self, part, title):
        self.part = part
        self.center = part.bounding_box().center()
        self.shapes, self.notes, self.offsets = [], [], {}
        views = {v: project(part, v) for v in VIEWS}
        bb = {v: views[v].bounding_box() for v in VIEWS}
        main = bb["главный"]
        self.offsets["главный"] = Vector(0, 0)
        self.offsets["сверху"] = Vector(0, main.min.Y - GAP - bb["сверху"].max.Y)
        self.offsets["слева"] = Vector(main.max.X + GAP - bb["слева"].min.X, 0)
        for v in VIEWS:
            self.shapes.append(Pos(*self.offsets[v]) * views[v])
            self.label(f"Вид {v}" if v != "главный" else "Главный вид",
                       (bb[v].center().X + self.offsets[v].X, bb[v].max.Y + self.offsets[v].Y + 45))
        self.label(title, (main.center().X, main.max.Y + 90), 14)
        self.bottom = bb["сверху"].min.Y + self.offsets["сверху"].Y

    def point(self, view, p):
        c = to_sheet(view, self.center)
        x, y = to_sheet(view, p)
        # project() смотрит на центр габарита: он же начало координат вида.
        return self.offsets[view] + Vector(x - c[0], y - c[1])

    def dim(self, view, a, b, offset, vertical=False):
        """offset > 0 — справа по ходу от a к b: у линии слева направо это вниз."""
        self.notes.append(ExtensionLine([self.point(view, a), self.point(view, b)], offset, DRAFT,
                                        measurement_direction=(0, 1) if vertical else None))

    def label(self, text, at, size=11.0):
        self.notes.append(Pos(*at) * Text(text, size, font="DejaVu Sans"))

    def footnote(self, lines):
        x = self.shapes[0].bounding_box().center().X
        for i, line in enumerate(lines):
            self.label(line, (x, self.bottom - 70 - 16 * i), 10)

    def save(self, path):
        svg = ExportSVG(margin=10, line_weight=0.35)
        svg.add_layer("notes", fill_color="black", line_weight=0.25)
        svg.add_shape(self.shapes)
        svg.add_shape(self.notes, layer="notes")
        svg.write(path)


def project(part, view):
    origin, up = VIEWS[view]
    c = part.bounding_box().center()
    visible, _ = part.project_to_viewport(c + Vector(origin), up, c)
    return Compound(visible)


def overall(sheet):
    lo, hi = sheet.part.bounding_box().min, sheet.part.bounding_box().max
    sheet.dim("главный", (lo.X, 0, lo.Z), (hi.X, 0, lo.Z), 25)
    sheet.dim("главный", (lo.X, 0, lo.Z), (lo.X, 0, hi.Z), -25)
    sheet.dim("сверху", (lo.X, hi.Y, 0), (lo.X, lo.Y, 0), 25)
    return lo, hi


def pad_bolt_dims(sheet, lo, hi):
    """Разметка болтов М8 на площадках разъёма — одна и та же у плиты и ресивера; левый ряд сдвинут вперёд."""
    left, right = sorted(valley_plate.pad_bolts(-1)), sorted(valley_plate.pad_bolts(1))
    xs = sorted({x for x, _ in left})
    y_out, y_in = max(y for _, y in right), min(y for _, y in right)
    for a, b in zip(xs, xs[1:]):
        sheet.dim("сверху", (a, -y_out, 0), (b, -y_out, 0), -(y_out + lo.Y) + 20)
    x_r, x_l = max(x for x, _ in right), max(x for x, _ in left)
    for y, off in ((y_out, 25), (y_in, 55)):
        sheet.dim("сверху", (x_r, y, 0), (x_l, -y, 0), -(hi.X - x_r + off), vertical=True)


def plate_sheet(part):
    s = Sheet(part, "Плита развала (нижний этаж), мм")
    lo, hi = overall(s)
    pad_bolt_dims(s, lo, hi)
    s.dim("главный", (hi.X, 0, valley_plate.VALLEY_Z), (hi.X, 0, valley_plate.SPLIT_Z), 25)
    s.footnote([f"Площадки разъёма: 12 отв. под М8. Фланцы головок: 14 отв. Ø{STUD_HOLE:.0f} под шпильки М10.",
                f"8 каналов Ø{RUNNER_D:.0f}, 8 штуцеров газовых форсунок М8×1. Опора на блок +{valley_plate.VALLEY_Z:.0f}, "
                f"разъём +{valley_plate.SPLIT_Z:.0f} мм от оси коленвала.",
                "Полная геометрия — STEP; чертёж для оценки стоимости."])
    return s


def receiver_sheet(part):
    s = Sheet(part, "Ресивер с раннерами (верхний этаж), мм")
    lo, hi = overall(s)
    pad_bolt_dims(s, lo, hi)
    _, _, _, (x0, _, h, top) = receiver.plenum()
    zc, half = receiver.PLENUM_Z0 + WALL + h / 2, receiver.THROTTLE_BOLTS / 2
    s.dim("слева", (x0, half, zc + half), (x0, -half, zc + half), -(hi.Z - zc - half + 20))
    s.dim("слева", (x0, -half, zc - half), (x0, -half, zc + half), 25)
    s.footnote([f"Площадка дросселя ЗМЗ-406: окно Ø{receiver.THROTTLE_OPENING:.0f}, 4 × М8. "
                f"Площадки разъёма: 12 отв. Ø{receiver.BOLT_CLEAR:.0f} под болты М8.",
                f"8 раннеров Ø{RUNNER_D:.0f}, объём ресивера {f'{PLENUM_VOL / 1e6:.1f}'.replace('.', ',')} л. "
                "Сверху резьбы М12×1,5 (4 шт.) и М22×1,5 (РХХ).",
                "Полная геометрия — STEP; чертёж для оценки стоимости."])
    return s


def build_parts():
    if "--from-out" in sys.argv:  # быстрый прогон по уже собранным cad/out/*.step
        out = ROOT / "cad" / "out"
        return import_step(out / "valley_plate.step"), import_step(out / "receiver.step")
    plate, _ = valley_plate.build()
    part, *_ = receiver.build()
    return plate, part


if __name__ == "__main__":
    plate, rec = build_parts()
    drawings = STATIC / "img" / "drawings"
    drawings.mkdir(parents=True, exist_ok=True)
    plate_sheet(plate).save(drawings / "valley-plate.svg")
    receiver_sheet(rec).save(drawings / "receiver.svg")
    tmp = ROOT / "cad" / "out"
    tmp.mkdir(exist_ok=True)
    steps = {"valley_plate.step": plate, "receiver.step": rec, "intake_assembly.step": Compound([plate, rec])}
    (STATIC / "cad").mkdir(exist_ok=True)
    with zipfile.ZipFile(STATIC / "cad" / "intake-step.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for name, shape in steps.items():
            export_step(shape, tmp / name)
            z.write(tmp / name, name)
    print("Чертежи и STEP записаны в", STATIC.relative_to(ROOT))
