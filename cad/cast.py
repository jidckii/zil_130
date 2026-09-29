"""Литейный вариант коллектора: деталь после обработки и заготовка-отливка для плиты развала и ресивера.

Запуск: uv run python cad/cast.py  → cad/out/cast/{valley_plate,receiver}{,_casting}.step, cast_assembly.step
и BRep обработанных деталей для чертежей (drawings.py).
Геометрия та же, что у макета (valley_plate.py, receiver.py); меняются стенка и припуски. Уклоны не заложены:
для ЛВМ и печатного песка они не нужны, под ХТС с деревянной оснасткой их добавляет литейка.
"""
from pathlib import Path

from build123d import Compound, export_brep, export_step

import receiver
import valley_plate

# Для АК9 в песке и ЛВМ 4 мм — рабочий минимум. При 5 мм крайние раннеры закрывают торцевой головке
# крайние болты площадок (receiver.check): если литейка попросит 5, разносить болты в pad_bolts.
WALL = 4.0
STOCK = 2.0  # припуск на фрезеровку фланцев головок, разъёма, опоры на блок и площадок
DENSITY = 2.68e-6  # АК9, кг/мм³


def main():
    plate, _ = valley_plate.build(WALL)
    rec, air, throttle, _, _ = receiver.build(WALL)
    assert plate.is_valid and len(plate.solids()) == 1, "плита невалидна или развалилась на части"
    receiver.check(rec, air, throttle, plate)
    blanks = {"valley_plate": valley_plate.build(WALL, STOCK, drill=False)[0],
              "receiver": receiver.build(WALL, STOCK, drill=False)[0]}
    out = Path(__file__).parent / "out" / "cast"
    out.mkdir(parents=True, exist_ok=True)
    for name, part in (("valley_plate", plate), ("receiver", rec)):
        blank = blanks[name]
        assert blank.is_valid and len(blank.solids()) == 1, f"{name}: отливка невалидна"
        assert blank.volume > part.volume, f"{name}: у отливки нет припуска"
        export_step(part, out / f"{name}.step")
        export_brep(part, out / f"{name}.brep")
        export_step(blank, out / f"{name}_casting.step")
        bb = blank.bounding_box()
        print(f"{name}: отливка {bb.size.X:.0f} × {bb.size.Y:.0f} × {bb.size.Z:.0f} мм, "
              f"{blank.volume * DENSITY:.1f} кг, после обработки {part.volume * DENSITY:.1f} кг")
    export_step(Compound([plate, rec]), out / "cast_assembly.step")


if __name__ == "__main__":
    main()
