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
openPanel(0x025A, {{led=2,offset=0xA010,float=true}, {led=1,offset=0xA018,float=true},
                 -- CP2 B5/B6: pressure amber and door seal cyan; PhIDs 16/13.
                 {led=17,lvar='VAR_PRESSURIZATIONPRESS',off=0x85,on=0x8B},
                 {led=14,lvar='VAR_DOORSEALPRIMARYINFLATE',off=0x94,on=0xBC},
                 -- B7 below B5, B8 below B6: PhIDs 15/12, momentary red.
                 {led=16,lvar='VAR_PRESSURIZATIONTEST',off=dimRed,on=brightRed},
                 {led=13,lvar='VAR_DOORSEALSTANDBYINFLATE',off=dimRed,on=brightRed},
                 -- Citation X only: B9/B10 = physical addresses 14/11.
                 {led=15,offset=0xA020,float=true,threshold=0,citationOnly=true,off=dimWhite,on=brightWhite},
                 {led=12,offset=0xA028,float=true,threshold=0,citationOnly=true,off=dimWhite,on=brightWhite}},
                 -- B3/B4 are unassigned again, shown in blue at PhIDs 3/2.
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
-- Throttle B4: PhID 3, report slot 4. Other throttle LEDs remain under firmware control.
-- FSUIPC 026D is CAMERA STATE (byte); only state 4 is the drone camera.
-- Neon green off; hot pink (red 3, green 0, blue 2) on.
openPanel(0x0194, {{led=4,offset=0x026D,byte=true,equals=4,off=0x8C,on=0xA3}})

local lastDroneState
local function releaseStickKeysOnCameraChange()
    local drone = ipc.readUB(0x026D) == 4
    if lastDroneState ~= nil and drone ~= lastDroneState then
        -- Keyboard holds belong to the on-foot/cockpit mapping. Native drone axes
        -- take over in drone mode; never carry a held key across that boundary.
        for _, key in ipairs({37,38,39,40,65,68,83,87}) do
            ipc.keypressplus(key,0,2)
        end
    end
    lastDroneState = drone
end

function KestrelAirPoll()
    releaseStickKeysOnCameraChange()
    local title = ipc.readSTR(0x3D00,256)
    local citation = title == 'Citation X' or title == 'Citation X Winglets'
    for _, panel in ipairs(panels) do
        local leds = {}
        for i=1,17 do leds[i]=panel.baseline[i] or 0 end
        for _, binding in ipairs(panel.mapping) do
            if not binding.citationOnly or citation then
            local state
            if binding.lvar then
                local ok,value=pcall(ipc.readLvar,binding.lvar)
                state=(ok and value) or 0
            elseif binding.byte then state=ipc.readUB(binding.offset)
            elseif binding.float then state=ipc.readDBL(binding.offset)
            else state=ipc.readSD(binding.offset) end
            local active
            if binding.equals ~= nil then active = state == binding.equals
            else active = state > (binding.threshold or 0.5) end
            leds[binding.led] = active and (binding.on or green) or (binding.off or purple)
            if binding.last ~= leds[binding.led] then
                ipc.log(string.format('KestrelAir LEDs: %04X slot %d state %.3f color %02X',
                    panel.product,binding.led,state,leds[binding.led]))
                binding.last=leds[binding.led]
            end
            else
                -- Zero releases these LEDs back to the stored firmware colours.
                binding.last=nil
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
event.timer(100,'KestrelAirPoll')
event.terminate('KestrelAirStop')
KestrelAirPoll()
