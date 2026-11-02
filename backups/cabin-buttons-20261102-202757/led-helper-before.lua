-- State feedback only: SPAD.neXt owns all button actions.
-- VIRPIL feature-report encoding documented by mixMugz/vpc_virpil_fsuipc_led.
-- 00 leaves an LED under firmware control; 80+BBGGRR overrides its color.
local purple, green = 0xB1, 0x8C
local dimWhite, brightWhite, dimRed, brightRed = 0x95, 0xBF, 0x81, 0x83
local panels = {}
ipc.log('KestrelAir LEDs: starting state feedback')
local function openPanel(product, mapping, baseline)
    local handle, rd, featureLength = com.openhid(0x3344, product, 0, 0)
    if handle == 0 then
        ipc.log(string.format('KestrelAir LEDs: cannot open %04X', product))
        return
    end
    com.writefeature(handle,string.char(2,100),featureLength)
    panels[#panels + 1] = {handle=handle, length=featureLength, mapping=mapping,product=product,baseline=baseline or {}}
    ipc.log(string.format('KestrelAir LEDs: opened %04X, feature length %d', product, featureLength))
end
-- CP2 protocol LED 2 = B1; LED 1 = B2.
openPanel(0x025A, {{led=2,offset=0xA010,float=true}, {led=1,offset=0xA018,float=true}},
                 -- CP2 B3/B4 are now unassigned; their PhIDs are 3/2.
                 {[3]=0xB0,[4]=0xB0})
-- VIRPIL PrimaryTypeParams.json supplies zero-based PhID addresses:
-- B1=7, B2=8, B3=6, B4=9. Lua report-array slots are PhID + 1.
openPanel(0x025C, {{led=8,offset=0xA008,off=dimRed,on=brightRed},
                 {led=9,offset=0xA00C,off=dimRed,on=brightRed},
                 {led=7,offset=0xA000,off=dimWhite,on=brightWhite},
                 {led=10,offset=0xA004,off=dimWhite,on=brightWhite}},
                 -- B8-B13 are addresses 0,1,2,3,5,4. Restore all six to the
                 -- original cyan (0/255/255), confirmed in the pre-edit export.
                 {[1]=0xBC,[2]=0xBC,[3]=0xBC,[4]=0xBC,[5]=0xBC,[6]=0xBC})

function KestrelAirPoll()
    for _, panel in ipairs(panels) do
        local leds = {}
        for i=1,17 do leds[i]=panel.baseline[i] or 0 end
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
