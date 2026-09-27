-- Запуск: lua ecu/zil130_test.lua (из корня репозитория)
local sensors, out = {}, {}
function setTickRate() end
function getSensor(name) return sensors[name] end
function setFuelMult(v) out.fuel = v end
function setBoostTargetMult(v) out.boost = v end

dofile("ecu/zil130.lua")

local function near(a, b) return math.abs(a - b) < 1e-3 end

assert(gasFuelMult(301, 20) == 1)
assert(near(gasFuelMult(351, 20), 301 / 351))
assert(near(gasFuelMult(301, 60), math.sqrt(333.15 / 293.15)))
assert(near(gasFuelMult(235, 20), 301 / 235))
assert(gasFuelMult(nil, 20) == 1)
assert(gasFuelMult(101, 20) == 1)
assert(near(gasFuelMult(301, nil), 1))
assert(gasFuelMult(160, 60) == 1.5)

assert(boostMult(nil) == 0.87)
assert(boostMult(0) == 0.87)
assert(boostMult(2) == 0.87)
assert(boostMult(3) == 1)
assert(boostMult(5) == 1)

sensors = { FuelPressureLow = 351, AuxTemp1 = 20, DetectedGear = 4 }
onTick()
assert(near(out.fuel, 301 / 351) and out.boost == 1)

print("ok")
