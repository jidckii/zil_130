-- ЗИЛ-130 на метане, rusEFI: поправка форсунок по давлению и температуре газа,
-- ограничение наддува в 1-й, 2-й и нейтрали. Сверено с rusefi 009fa2f (2026-09-27).
-- Базовая библиотека Lua в rusEFI не подключена (lua.cpp), есть только math.

-- Расход форсунок в прошивке задан при этих условиях: 2,0 бар в рампе над атмосферой, газ 20 °C.
local P_REF_KPA = 301
local T_REF_C = 20
-- Рампа держит MAP + 200 кПа: от 220 (торможение двигателем) до 351 (+0,5 бар) — множитель 0,81–1,46.
local MULT_MIN, MULT_MAX = 0.75, 1.5
local RAIL_DEAD_KPA = 150

-- (101 + 30) / (101 + 50): таблица цели на +0,5 бар режется до +0,3.
local LOW_GEAR_BOOST_MULT = 0.87

-- Форсунка газа работает в критическом режиме (Pвых/Pвх < 0,53 во всём диапазоне MAP):
-- массовый расход ∝ Pрампы_абс / √T, а не √Δp, как считает ICM_SensedRailPressure.
function gasFuelMult(railKpa, gasTempC)
  if railKpa == nil or railKpa < RAIL_DEAD_KPA then
    return 1
  end
  local t = gasTempC or T_REF_C
  local m = (P_REF_KPA / railKpa) * math.sqrt((t + 273.15) / (T_REF_C + 273.15))
  return math.min(MULT_MAX, math.max(MULT_MIN, m))
end

-- Задний ход (7,09) детектор передач принимает за 1-ю (7,44), нет VSS — за нейтраль:
-- в обоих случаях наддув ограничен.
-- ponytail: множитель режет всю таблицу цели, а не только верх; если мешает на частичной
-- нагрузке — перейти на потолок через getOutput("boostControlTarget") и setBoostTargetAdd.
function boostMult(gear)
  if gear ~= nil and gear >= 3 then
    return 1
  end
  return LOW_GEAR_BOOST_MULT
end

setTickRate(20)

function onTick()
  setFuelMult(gasFuelMult(getSensor("FuelPressureLow"), getSensor("AuxTemp1")))
  setBoostTargetMult(boostMult(getSensor("DetectedGear")))
end
