local items={
 {name='left cowl',input='ENGINE_COWLFLAPS_LEFT',offset=0xA010,float=true},
 {name='right cowl',input='ENGINE_COWLFLAPS_RIGHT',offset=0xA018,float=true},
 {name='battery 1',input='ELECTRICAL_BATTERY_1',offset=0xA008},
 {name='avionics 1',input='ELECTRICAL_AVIONICS_BUS_1',offset=0xA000}
}
for _, item in ipairs(items) do
 local function read() if item.float then return ipc.readDBL(item.offset) else return ipc.readSD(item.offset) end end
 local saved=read()
 local ok,err=pcall(function()
  for press=1,2 do
   local before=read()
   local desired=before>0.5 and 0 or 1
   ipc.execInputEvent(item.input,desired)
   ipc.sleep(500)
   local after=read()
   local actual=after>0.5 and 1 or 0
   assert(actual==desired,'Single command did not toggle '..item.name)
   ipc.log(string.format('PASS %s press %d: %.4f -> %.4f',item.name,press,before,after))
  end
 end)
 local restore=saved
 if item.float then restore=saved/100 end
 ipc.execInputEvent(item.input,restore)
 ipc.sleep(300)
 ipc.log(string.format('Restored %s to %.4f',item.name,read()))
 if not ok then error(err) end
end
