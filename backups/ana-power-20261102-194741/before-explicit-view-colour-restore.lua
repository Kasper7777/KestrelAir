-- State feedback only: SPAD.neXt owns all button actions.
-- VIRPIL feature-report encoding documented by mixMugz/vpc_virpil_fsuipc_led.
-- 00 leaves an LED under firmware control; 80+BBGGRR overrides its color.
local purple, green = 0xB1, 0x8C
local dimWhite, brightWhite, dimRed, brightRed = 0x95, 0xBF, 0x81, 0x83
local panels = {}
ipc.log('KestrelAir LEDs: starting state feedback')
local function openPanel(product, mapping)
    local handle, rd, featureLength = com.openhid(0x3344, product, 0, 0)
    if handle == 0 then
        ipc.log(string.format('KestrelAir LEDs: cannot open %04X', product))
        return
    end
    com.writefeature(handle,string.char(2,100),featureLength)
    panels[#panels + 1] = {handle=handle, length=featureLength, mapping=mapping,product=product}
    ipc.log(string.format('KestrelAir LEDs: opened %04X, feature length %d', product, featureLength))
end
-- CP2 protocol LED 2 = B1; LED 1 = B2.
openPanel(0x025A, {{led=2,offset=0xA010,float=true}, {led=1,offset=0xA018,float=true}})
-- CP3 LED slots 1-4 belong to B8-B11; B1-B4 are slots 5-8.
openPanel(0x025C, {{led=5,offset=0xA008,off=dimRed,on=brightRed},
                 {led=6,offset=0xA00C,off=dimRed,on=brightRed},
                 {led=7,offset=0xA000,off=dimWhite,on=brightWhite},
                 {led=8,offset=0xA004,off=dimWhite,on=brightWhite}})

function KestrelAirPoll()
    for _, panel in ipairs(panels) do
        local leds = {}
        for i=1,17 do leds[i]=0 end
        for _, binding in ipairs(panel.mapping) do
            local state
            if binding.float then state=ipc.readDBL(binding.offset)
            else state=ipc.readSD(binding.offset) end
            leds[binding.led] = state > 0.5 and (binding.on or green) or (binding.off or purple)
            if binding.last ~= leds[binding.led] then
                ipc.log(string.format('KestrelAir LEDs: %04X slot %d state %.3f color %02X',
                    panel.product,binding.led,state,leds[binding.led]))
                binding.last=leds[binding.led]
            end
        end
        local packet=string.char(2,102,0,0,0)..string.char(unpack(leds))
        -- Refresh even if unchanged: the configurator/firmware can reset LEDs.
        local written=com.writefeature(panel.handle,packet,panel.length)
        if written == 0 and not panel.warned then
            ipc.log('KestrelAir LEDs: feature report write failed')
            panel.warned=true
        end
    end
end
function KestrelAirStop()
    for _, panel in ipairs(panels) do
        com.writefeature(panel.handle,string.char(2,100),panel.length)
        com.close(panel.handle)
    end
end
event.timer(250,'KestrelAirPoll')
event.terminate('KestrelAirStop')
KestrelAirPoll()
