-- Start LED feedback when FSUIPC connects, including before Ready To Fly.
-- The helper reads standard simulator offsets and does not need the WASM bridge.
dofile('C:\\FSUIPC7\\KestrelAirLEDs.lua')
