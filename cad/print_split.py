"""Разрезка плиты развала и ресивера на куски под стол 256×256×256 (Bambu Lab P1S/P2S, Creality K2 и т. п.).

Запуск: uv run python cad/print_split.py  → cad/out/print/*.stl
Куски стыкуются на штифты Ø3 (пруток или гвоздь без шляпки, 20 мм) и клей.
"""
import itertools
from pathlib import Path

import numpy as np
from matplotlib.path import Path as Poly2D

from build123d import Box, Compound, Cylinder, Plane, Pos, export_stl, section

import receiver
import valley_plate
from head_flange import BASE

BED = 250.0  # стол 256 минус поля
PIN_D, PIN_DEPTH, PIN_WALL = 3.3, 10.0, 1.8  # отверстие под пруток Ø3, глубина в каждую сторону
PIN_R = PIN_D / 2 + PIN_WALL
PINS_PER_REGION, PIN_SPACING = 2, 25.0
# Резы между парами каналов и мимо опор шпилек (valley_plate.exits, STUDS); поперёк — по полу развала.
CUTS = {
    "valley_plate": {"X": (118.0, 258.0), "Y": (-5.0,)},
    "receiver": {"X": (188.0,), "Y": (0.0,)},
}
AXES = {"X": 0, "Y": 1}


def cut_plane(axis, at):
    if axis == "X":
        return Plane((at, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
    return Plane((0, at, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0))


def pin_sites(part, axis, at, other_cuts):
    """Точки на стыке, где вокруг отверстия под штифт остаётся стенка PIN_WALL: отдельно на каждом сплошном участке
    сечения, иначе отрезок, связанный с соседями только через рез (площадка между парами), останется без штифтов."""
    keep = [i for i in range(3) if i != AXES[axis]]
    other = "Y" if axis == "X" else "X"
    groups = {}
    for fi, face in enumerate(section(part, cut_plane(axis, at)).faces()):
        wires = [face.outer_wire()] + face.inner_wires()
        rings = [np.array([tuple(w @ t) for t in np.linspace(0, 1, max(16, int(w.length / 0.5)))])[:, keep]
                 for w in wires]
        border = np.vstack(rings)
        lo, hi = border.min(0), border.max(0)
        grid = np.array(list(itertools.product(*(np.arange(a, b, 1.5) for a, b in zip(lo, hi)))))
        if not len(grid):
            continue
        inside = Poly2D(rings[0]).contains_points(grid)
        for ring in rings[1:]:
            inside &= ~Poly2D(ring).contains_points(grid)
        grid = grid[inside]
        clear = np.sqrt(((grid[:, None, :] - border[None, :, :]) ** 2).sum(-1)).min(1)
        grid, clear = grid[clear >= PIN_R], clear[clear >= PIN_R]
        # От другого реза — на глубину штифта: иначе штифт уйдёт в третий кусок или пересечётся с поперечным штифтом.
        o = keep.index(AXES[other])
        away = np.all(np.abs(grid[:, [o]] - np.array(other_cuts)[None, :]) >= PIN_DEPTH + PIN_R, axis=1) if other_cuts else True
        grid, clear = grid[away], clear[away]
        cell = np.searchsorted(np.array(other_cuts), grid[:, o]) if other_cuts else np.zeros(len(grid), int)
        for c in set(cell.tolist()):
            g = groups.setdefault((c, fi), ([], []))
            g[0].append(grid[cell == c])
            g[1].append(clear[cell == c])
    sites = {}
    for c, (pts, clr) in groups.items():
        pts, clr = np.vstack(pts), np.concatenate(clr)
        order = [pts[clr.argmax()]]
        while len(order) < 4 * PINS_PER_REGION:
            d = np.min([np.linalg.norm(pts - q, axis=1) for q in order], axis=0)
            if d.max() < PIN_SPACING:
                break
            order.append(pts[d.argmax()])
        sites[c] = []
        for q in order:
            xyz = [0.0, 0.0, 0.0]
            xyz[AXES[axis]] = at
            for k, v in zip(keep, q):
                xyz[k] = float(v)
            sites[c].append(tuple(xyz))
    return sites


def drill_pins(part, cuts):
    """Штифты на каждом куске стыка; где материала на глубину штифта нет — кусок стыка только на клею."""
    holes, missing = [], []
    for axis, positions in cuts.items():
        other = list(cuts.get("Y" if axis == "X" else "X", ()))
        normal = (1, 0, 0) if axis == "X" else (0, 1, 0)
        for at in positions:
            sites = pin_sites(part, axis, at, other)
            taken = {c: 0 for c in range(len(other) + 1)}
            for (c, _), candidates in sites.items():
                n = 0
                for p in candidates:
                    pl = Plane(p, z_dir=normal) * Pos(0, 0, -PIN_DEPTH)
                    if (pl * Cylinder(PIN_R, 2 * PIN_DEPTH, align=BASE) - part).volume < 1:
                        holes.append(pl * Cylinder(PIN_D / 2, 2 * PIN_DEPTH, align=BASE))
                        n += 1
                        if n == PINS_PER_REGION:
                            break
                taken[c] += n
            missing += [f"{axis}={at:.0f} кусок {c + 1}" for c, n in taken.items() if not n]
    return (part - holes if holes else part), len(holes), missing


def pieces(part, cuts):
    bb = part.bounding_box()
    edges = {a: [tuple(bb.min)[i] - 1, *sorted(cuts.get(a, ())), tuple(bb.max)[i] + 1] for a, i in AXES.items()}
    for (x0, x1), (y0, y1) in itertools.product(zip(edges["X"], edges["X"][1:]), zip(edges["Y"], edges["Y"][1:])):
        cell = Pos((x0 + x1) / 2, (y0 + y1) / 2, bb.min.Z - 1) * Box(x1 - x0, y1 - y0, bb.max.Z - bb.min.Z + 2, align=BASE)
        piece = part & cell
        if piece and piece.volume > 1:
            yield piece


if __name__ == "__main__":
    out = Path(__file__).parent / "out" / "print"
    out.mkdir(parents=True, exist_ok=True)
    for name, build in (("valley_plate", lambda: valley_plate.build()[0]), ("receiver", lambda: receiver.build()[0])):
        part, n_pins, missing = drill_pins(build(), CUTS[name])
        print(f"{name}: штифтов {n_pins}" + (f", стыки без штифтов (только клей): {', '.join(missing)}" if missing else ""))
        for i, piece in enumerate(pieces(part, CUTS[name]), 1):
            size = sorted(tuple(piece.bounding_box().size))
            assert size[-1] <= BED, f"{name}_{i} не влезает на стол: {size}"
            export_stl(Compound(piece.solids()), out / f"{name}_{i}.stl", tolerance=0.05, angular_tolerance=0.2)
            print(f"  {name}_{i}: {size[2]:.0f} × {size[1]:.0f} × {size[0]:.0f} мм, "
                  f"{len(piece.solids())} тел, PLA ~{piece.volume * 1.24e-3:.0f} г")
