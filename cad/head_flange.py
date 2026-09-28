"""Фланцы впуска головок ЗИЛ-130/375 и общие параметры коллектора — основа для valley_plate.py и receiver.py.

Оси: X вдоль коленвала назад от оси 1-го цилиндра, Y вправо, Z вверх от оси коленвала.
"""
import math

from build123d import Align, Vector

PITCH = 135.0  # межцилиндровое [D73 дж.8]
RUNNER_D = 42.0  # calc/results.md: 40–45
PLENUM_VOL = 5.0e6  # мм³; calc/results.md: 4,2–7,0 л
WALL = 3.0  # пластиковый макет

BANK_OFFSET = 29.0  # левый ряд вперёд на ширину головки шатуна [BD л.1 вид сверху], [D73 дж.21]

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
STUD_HOLE = 11.0

FLANGE_T = 12.0
HEAD_CENTER = 1.5 * PITCH  # середина между цилиндрами 2–3
BASE = (Align.CENTER, Align.CENTER, Align.MIN)


def flange_normal(side):
    t = math.radians(FLANGE_TILT)
    return Vector(0, -side * math.cos(t), math.sin(t))


def flange_point(side, along, across):
    """Точка на плоскости фланца; across > 0 — к нижней кромке (к блоку)."""
    t = math.radians(FLANGE_TILT)
    to_block = Vector(0, -side * math.sin(t), -math.cos(t))
    shift = 0.0 if side > 0 else -BANK_OFFSET
    return Vector(HEAD_CENTER + shift + along, side * FLANGE_Y, FLANGE_Z) + to_block * across
