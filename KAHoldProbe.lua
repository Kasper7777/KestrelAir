for _, name in ipairs({'var_pressurizationTest','var_doorSealStandbyInflate'}) do
 local heldName=name..'_IsDown'
 local saved=ipc.readLvar(name)
 local savedHeld=ipc.readLvar(heldName)
 assert(saved~=nil,'Momentary state unavailable: '..name)
 assert(savedHeld~=nil,'Held flag unavailable: '..heldName)
 local ok,err=pcall(function()
  ipc.writeLvar(heldName,1)
  ipc.writeLvar(name,1)
  ipc.sleep(700)
  ipc.log(name..' held main='..tostring(ipc.readLvar(name))..' IsDown='..tostring(ipc.readLvar(heldName)))
  assert(ipc.readLvar(name)==1,'Press did not engage: '..name)
  ipc.log('PASS held '..name..'=1')
  ipc.writeLvar(heldName,0)
  ipc.writeLvar(name,0)
  ipc.sleep(700)
  assert(ipc.readLvar(name)==0,'Release did not disengage: '..name)
  ipc.log('PASS released '..name..'=0')
 end)
 ipc.writeLvar(heldName,savedHeld)
 ipc.writeLvar(name,saved)
 ipc.log('Restored '..name..'='..tostring(saved))
 if not ok then error(err) end
end
