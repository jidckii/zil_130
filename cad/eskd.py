"""Лист чертежа по ЕСКД: рамка и основная надпись (ГОСТ 2.104, форма 1), виды и сечения в масштабе,
размеры, допуски формы и расположения, шероховатость, технические требования. Координаты листа — мм бумаги.
"""
import math
import subprocess
from pathlib import Path

from build123d import (Align, Circle, Compound, Draft, Edge, ExportSVG, ExtensionLine, LineType, Polyline, Pos,
                       Rectangle, Rot, Text, Vector, make_face)

FONT = "DejaVu Sans"
FORMATS = {"A1": (841.0, 594.0), "A2": (594.0, 420.0), "A3": (420.0, 297.0)}
CAP = 0.72  # высота прописной DejaVu Sans в долях кегля: ЕСКД задаёт шрифт высотой прописной
DRAFT = Draft(font_size=3.5 / CAP, font=FONT, display_units=False, arrow_length=3.5, line_width=0.25,
              extension_gap=1.0, pad_around_text=1.0)
HATCH_STEP = 2.5


def num(v, digits=1):
    s = f"{v:.{digits}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s.replace(".", ",")


class View:
    """Ортогональная проекция детали: точка модели p → лист origin + scale · (p·right, p·up)."""

    def __init__(self, sheet, shape, direction, up, at, ref, hidden=False):
        self.sheet, self.s = sheet, sheet.scale
        self.dir, self.up = Vector(direction).normalized(), Vector(up).normalized()
        self.right = self.dir.cross(self.up)
        self.origin = Vector(at) - self.local(ref) * self.s
        vis, hid = shape.project_to_viewport(self.dir * -5000, self.up, (0, 0, 0))
        sheet.add(self.place(Compound(vis)), "thick")
        if hidden and hid:
            sheet.add(self.place(Compound(hid)), "hidden")
        self.box = self.place(Compound(vis)).bounding_box()

    def local(self, p):
        p = Vector(p)
        return Vector(p.dot(self.right), p.dot(self.up))

    def place(self, shape):
        return Pos(self.origin.X, self.origin.Y) * shape.scale(self.s)

    def __call__(self, p):
        return self.origin + self.local(p) * self.s


class Section:
    """Сечение плоскостью (ГОСТ 2.305): видно со стороны, противоположной нормали плоскости."""

    def __init__(self, sheet, shape, plane, at, ref):
        self.sheet, self.s, self.plane = sheet, sheet.scale, plane
        self.origin = Vector(at) - self.local(ref) * self.s
        cut = shape & (plane * Rectangle(4000, 4000))
        faces = [self.place(plane.to_local_coords(f)) for f in cut.faces()]
        for f in faces:
            sheet.add(f.edges(), "thick")
            sheet.add(hatch(f), "thin")
        self.box = Compound(faces).bounding_box()

    def local(self, p):
        q = self.plane.to_local_coords(Vector(p))
        return Vector(q.X, q.Y)

    def place(self, shape):
        return Pos(self.origin.X, self.origin.Y) * shape.scale(self.s)

    def __call__(self, p):
        return self.origin + self.local(p) * self.s


def text_width(s, h=3.5):
    return Text(s, h / CAP, font=FONT).bounding_box().size.X


def hatch(face, step=HATCH_STEP, angle=45.0):
    bb = face.bounding_box()
    c, r = bb.center(), bb.diagonal / 2 + 1
    d, n = Vector(math.cos(math.radians(angle)), math.sin(math.radians(angle))), Vector(0, 0, 1)
    k = d.cross(n)
    lines = []
    for i in range(-int(r / step), int(r / step) + 1):
        o = c + k * (i * step)
        e = Edge.make_line(o - d * r, o + d * r)
        lines += [x for x in (face & e).edges()] if face.intersect(e) else []
    return lines


class Sheet:
    def __init__(self, fmt, name, code, scale, material, mass, sheet=1, sheets=1, org="Проект ЗИЛ-130 V8",
                 author="Медведев Е."):
        self.w, self.h = FORMATS[fmt]
        self.scale = scale
        self.layers = {"thick": [], "thin": [], "fill": [], "hidden": [], "axis": []}
        self.frame()
        self.title_block(name, code, scale, material, mass, sheet, sheets, org, author)
        self.code = code

    def add(self, shapes, layer):
        if isinstance(shapes, (list, tuple)):
            self.layers[layer] += list(shapes)
        elif shapes is not None:
            self.layers[layer].append(shapes)

    def line(self, *pts, layer="thin"):
        self.add(Polyline(*[Vector(p) for p in pts]), layer)

    def rect(self, x0, y0, x1, y1, layer="thin"):
        self.line((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0), layer=layer)

    def text(self, s, at, h=3.5, align=(Align.MIN, Align.MIN), angle=0.0):
        t = Pos(*at) * Rot(0, 0, angle) * Text(s, h / CAP, font=FONT, align=align)
        self.add(t, "fill")
        return t.bounding_box()

    def frame(self):
        self.rect(0, 0, self.w, self.h)
        self.rect(20, 5, self.w - 5, self.h - 5, "thick")

    def title_block(self, name, code, scale, material, mass, sheet, sheets, org, author):
        x0, y0 = self.w - 5 - 185, 5.0
        self.tb = (x0, y0)
        T = lambda x, y, s, h=3.5, al=(Align.MIN, Align.CENTER): self.text(s, (x0 + x, y0 + y), h, al)
        self.rect(x0, y0, x0 + 185, y0 + 55, "thick")
        L = lambda a, b, layer="thin": self.line((x0 + a[0], y0 + a[1]), (x0 + b[0], y0 + b[1]), layer=layer)
        for y in range(5, 55, 5):
            L((0, y), (65, y), "thick" if y in (30, 35) else "thin")
        for x in (7, 17, 40, 55):
            L((x, 30 if x in (7,) else 0), (x, 55), "thick")
        L((7, 0), (7, 30), "thin")
        L((65, 0), (65, 55), "thick")
        L((65, 40), (185, 40), "thick")
        L((65, 15), (185, 15), "thick")
        L((135, 0), (135, 40), "thick")
        L((135, 35), (185, 35), "thick")
        L((135, 20), (185, 20), "thick")
        for x in (140, 145, 150):
            L((x, 20), (x, 35), "thin")
        L((150, 35), (150, 40), "thick")
        L((155, 20), (155, 40), "thick")
        L((167, 20), (167, 40), "thick")
        L((155, 15), (155, 20), "thin")
        for i, s in enumerate(("Изм.", "Лист", "№ докум.", "Подп.", "Дата")):
            T((0, 7, 17, 40, 55)[i] + 0.8, 32.5, s, 2.5)
        for i, s in enumerate(("Разраб.", "Пров.", "Т.контр.", "", "Н.контр.", "Утв.")):
            T(0.8, 27.5 - 5 * i, s, 2.5)
        T(17.8, 27.5, author, 2.5)
        T(100, 47.5, code, 7, (Align.CENTER, Align.CENTER))
        for i, s in enumerate(name.split("\n")):
            T(100, 27.5 + 3.5 * (len(name.split("\n")) - 1) - 7 * i, s, 5, (Align.CENTER, Align.CENTER))
        for s, x in (("Лит.", 145), ("Масса", 161), ("Масштаб", 176)):
            T(x, 37.5, s, 2.5, (Align.CENTER, Align.CENTER))
        T(161, 27.5, mass, 3.5, (Align.CENTER, Align.CENTER))
        T(176, 27.5, f"1:{num(scale and 1 / scale)}" if scale < 1 else f"{num(scale)}:1", 3.5, (Align.CENTER, Align.CENTER))
        T(136, 17.5, f"Лист {sheet}", 2.5)
        T(156, 17.5, f"Листов {sheets}", 2.5)
        T(100, 7.5, material, 3.5 if len(material) < 40 else 2.5, (Align.CENTER, Align.CENTER))
        T(160, 7.5, org, 2.5, (Align.CENTER, Align.CENTER))
        # графа 26: обозначение, повёрнутое на 180°, в левом верхнем углу
        self.rect(20, self.h - 19, 90, self.h - 5, "thick")
        self.text(code, (55, self.h - 12), 5, (Align.CENTER, Align.CENTER), 180)

    # --- размеры и обозначения ---

    def balloon(self, target, at, text, r=5.0):
        """Номер позиции (ГОСТ 2.109): полка с номером на выносной линии с точкой на детали."""
        target, at = Vector(target), Vector(at)
        self.add(Pos(target.X, target.Y) * Circle(0.7), "fill")
        right = at.X >= target.X
        end = at + Vector(2 * r if right else -2 * r, 0)
        self.line(target, at, end)
        self.text(text, ((at.X + end.X) / 2, at.Y + 1), 5, (Align.CENTER, Align.MIN))

    def dim(self, view, a, b, offset, direction=None, label=None, tol="", prefix="", mark=False):
        """offset > 0 — справа по ходу от a к b; direction — (1,0) или (0,1) на листе; mark — «*» к размеру."""
        pa, pb = view(a), view(b)
        if label is None:
            d = Vector(direction) if direction else (pb - pa).normalized()
            label = num(abs((pb - pa).dot(d)) / self.scale)
        label = prefix + label + tol + ("*" if mark else "")
        self.add(ExtensionLine([pa, pb], offset, DRAFT, label=label, measurement_direction=direction), "fill")

    def arrow(self, tip, direction, size=3.5):
        d = Vector(direction).normalized()
        n = Vector(-d.Y, d.X)
        tip = Vector(tip)
        base = tip - d * size
        self.add(make_face(Polyline(tip, base + n * size / 6, base - n * size / 6, close=True)), "fill")

    def leader(self, target, shelf, text, h=3.5, arrow=True, below=None):
        """Выноска: стрелка (или точка) у target, линия к полке, надпись над полкой; below — строка под полкой."""
        target, shelf = Vector(target), Vector(shelf)
        right = shelf.X >= target.X
        bb = self.text(text, (shelf.X + (1 if right else -1), shelf.Y + 1),
                       h, (Align.MIN if right else Align.MAX, Align.MIN))
        end = Vector(bb.max.X + 1 if right else bb.min.X - 1, shelf.Y)
        if below:
            b2 = self.text(below, (shelf.X + (1 if right else -1), shelf.Y - 1), h,
                           (Align.MIN if right else Align.MAX, Align.MAX))
            end = Vector(max(end.X, b2.max.X + 1) if right else min(end.X, b2.min.X - 1), shelf.Y)
        self.line(target, shelf, end)
        if arrow:
            self.arrow(target, target - shelf)
        else:
            self.add(Pos(target.X, target.Y) * Circle(0.6), "fill")
        return end

    def tolerance(self, at, symbol, value, base="", target=None):
        """Рамка допуска формы/расположения (ГОСТ 2.308). symbol: ⏥ ∥ ⊥ ∠ или «pos» (позиционный)."""
        x, y = Vector(at).X, Vector(at).Y
        hgt, cells = 7.0, [symbol, value] + ([base] if base else [])
        widths = [8.0, max(12.0, 2.2 * len(value) + 4)] + ([max(7.0, 3.2 * len(base) + 3)] if base else [])
        cx = x
        for cell, w in zip(cells, widths):
            self.rect(cx, y, cx + w, y + hgt)
            if cell == "pos":
                self.add(Pos(cx + w / 2, y + hgt / 2) * Circle(1.8).edges(), "thin")
                self.line((cx + w / 2 - 3, y + hgt / 2), (cx + w / 2 + 3, y + hgt / 2))
                self.line((cx + w / 2, y + hgt / 2 - 3), (cx + w / 2, y + hgt / 2 + 3))
            else:
                self.text(cell, (cx + w / 2, y + hgt / 2), 3.5, (Align.CENTER, Align.CENTER))
            cx += w
        if target is not None:
            t = Vector(target)
            start = Vector(x, y + hgt / 2) if t.X < x else Vector(cx, y + hgt / 2)
            self.line(start, (t.X, start.Y), t)
            self.arrow(t, t - Vector(t.X, start.Y) if abs(t.Y - start.Y) > 1e-6 else t - start)
        return cx

    def datum(self, target, direction, letter):
        """Обозначение базы: зачернённый треугольник на поверхности, линия и рамка с буквой."""
        t, d = Vector(target), Vector(direction).normalized()
        n = Vector(-d.Y, d.X)
        self.add(make_face(Polyline(t + n * 2.5, t - n * 2.5, t + d * 4.3, close=True)), "fill")
        c = t + d * 12
        self.line(t + d * 4.3, c - d * 3.5)
        self.rect(c.X - 3.5, c.Y - 3.5, c.X + 3.5, c.Y + 3.5)
        self.text(letter, (c.X, c.Y), 3.5, (Align.CENTER, Align.CENTER))

    def roughness(self, at, value, angle=0.0):
        """Знак шероховатости с удалением слоя материала (ГОСТ 2.309), вершина в at."""
        h = 3.5
        pts = [(-h * 0.6, h), (0, 0), (h * 1.2, h * 2), (h * 1.2 + 3.2 * len(value) * 0.55, h * 2)]
        rot = lambda p: Vector(*at) + Vector(p[0] * math.cos(math.radians(angle)) - p[1] * math.sin(math.radians(angle)),
                                           p[0] * math.sin(math.radians(angle)) + p[1] * math.cos(math.radians(angle)))
        self.line(*[rot(p) for p in pts])
        self.line(rot((-h * 0.6, h)), rot((h * 0.6, h)))
        upright = angle % 360
        if 90 < upright <= 270:
            self.text(value, rot((h * 1.4 + 3.2 * len(value) * 0.55, h * 2 - 0.8)), 3.5, (Align.MIN, Align.MIN),
                      angle - 180)
        else:
            self.text(value, rot((h * 1.4, h * 2 + 0.8)), 3.5, (Align.MIN, Align.MIN), angle)

    def general_roughness(self, value):
        """Неуказанная шероховатость в правом верхнем углу: «Ra … (√)»."""
        x, y = self.w - 45, self.h - 20
        self.roughness((x, y), value)
        self.text("(", (x + 26, y + 4), 5, (Align.MIN, Align.CENTER))
        self.line((x + 31, y + 5), (x + 33, y + 3), (x + 36, y + 9))
        self.text(")", (x + 37, y + 4), 5, (Align.MIN, Align.CENTER))

    def cut_mark(self, view, a, b, letter, towards):
        """След секущей плоскости: утолщённые штрихи у концов, стрелки взгляда и буквы."""
        pa, pb = view(a), view(b)
        d = (pb - pa).normalized()
        t = Vector(towards).normalized()
        for p, s in ((pa, 1), (pb, -1)):
            self.line(p - d * s * 3, p + d * s * 8, layer="thick")
            q = p - d * s * 3
            self.line(q, q + t * 9)
            self.arrow(q + t * 9, t)
            self.text(letter, q + t * 7 - d * s * 4, 5, (Align.CENTER, Align.CENTER))

    def angle(self, vertex, a0, a1, r, label):
        """Угловой размер: дуга радиуса r (мм листа) от направления a0 до a1 (градусы, против часовой)."""
        from build123d import CenterArc
        v = Vector(vertex)
        self.add(CenterArc(v, r, a0, a1 - a0), "thin")
        for ang, sgn in ((a0, 1), (a1, -1)):
            p = v + Vector(math.cos(math.radians(ang)), math.sin(math.radians(ang))) * r
            t = Vector(-math.sin(math.radians(ang)), math.cos(math.radians(ang))) * sgn
            self.arrow(p, -t)
            self.line(v, v + Vector(math.cos(math.radians(ang)), math.sin(math.radians(ang))) * (r + 3))
        mid = math.radians((a0 + a1) / 2)
        self.text(label, v + Vector(math.cos(mid), math.sin(mid)) * (r + 4), 3.5, (Align.CENTER, Align.CENTER))

    def axis(self, a, b):
        self.add(Polyline(Vector(a), Vector(b)), "axis")

    def center(self, p, r):
        p = Vector(p)
        self.axis(p - Vector(r + 3, 0), p + Vector(r + 3, 0))
        self.axis(p - Vector(0, r + 3), p + Vector(0, r + 3))

    def caption(self, text, at, h=5.0):
        self.text(text, at, h, (Align.CENTER, Align.MIN))

    def requirements(self, lines, width=185.0, top=None):
        """Технические требования над основной надписью; строки длиннее ширины переносятся по словам."""
        x0, y0 = self.tb[0], self.tb[1] + 55 + 10
        out = []
        for i, s in enumerate(lines, 1):
            cur = f"{i}."
            for w in s.split():
                if text_width(f"{cur} {w}") > width:
                    out.append(cur)
                    cur = "   "
                cur += " " + w
            out.append(cur)
        for i, s in enumerate(reversed(out)):
            self.text(s, (x0, y0 + 6 * i), 3.5)
        return y0 + 6 * len(out)

    def table(self, x0, y_top, cols, rows, head_h=15.0, row_h=8.0, h=3.5):
        """Таблица с шапкой: cols = [(заголовок, ширина)], rows — строки значений."""
        x = x0
        width = sum(w for _, w in cols)
        self.rect(x0, y_top - head_h - row_h * len(rows), x0 + width, y_top, "thick")
        self.line((x0, y_top - head_h), (x0 + width, y_top - head_h), layer="thick")
        for (title, w) in cols:
            self.line((x, y_top), (x, y_top - head_h - row_h * len(rows)), layer="thick")
            for j, part in enumerate(title.split("\n")):
                self.text(part, (x + w / 2, y_top - head_h / 2 + 2.2 * (len(title.split("\n")) - 1) - 4.4 * j), 2.5,
                          (Align.CENTER, Align.CENTER))
            x += w
        for i, row in enumerate(rows):
            y = y_top - head_h - row_h * (i + 1)
            self.line((x0, y), (x0 + width, y))
            x = x0
            for (title, w), v in zip(cols, row):
                al = Align.MIN if w > 40 else Align.CENTER
                self.text(str(v), (x + 1.5 if al == Align.MIN else x + w / 2, y + row_h / 2), h, (al, Align.CENTER))
                x += w

    def save(self, svg_path):
        svg = ExportSVG(margin=0, line_weight=0.25, precision=3)
        svg.add_layer("thick", line_weight=0.7)
        svg.add_layer("thin", line_weight=0.25)
        svg.add_layer("hidden", line_weight=0.25, line_type=LineType.HIDDEN)
        svg.add_layer("axis", line_weight=0.25, line_type=LineType.DASHDOT)
        svg.add_layer("fill", fill_color=(0, 0, 0), line_weight=0.05)
        for name, shapes in self.layers.items():
            if shapes:
                svg.add_shape(shapes, layer=name)
        svg_path = Path(svg_path)
        svg.write(svg_path)
        fix_page(svg_path, self.w, self.h)
        return svg_path


def to_pdf(svgs, pdf):
    """Листы одного документа — в один многостраничный PDF в натуральную величину."""
    subprocess.run(["rsvg-convert", "-f", "pdf", "-o", str(pdf), *map(str, svgs)], check=True)


def fix_page(path, w, h):
    """ExportSVG обрезает лист по габариту содержимого; рамка формата занимает весь лист, но толщина
    линий раздувает его на доли мм — выставляем точный формат, чтобы PDF печатался в масштабе."""
    import re
    s = path.read_text()
    s = re.sub(r'width="[\d.]+mm" height="[\d.]+mm" viewBox="[^"]*"',
               f'width="{w}mm" height="{h}mm" viewBox="0 {-h} {w} {h}"', s, count=1)
    path.write_text(s)
