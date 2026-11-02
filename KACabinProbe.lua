for _, name in ipairs({'var_pressurizationPress','VAR_PRESSURIZATIONPRESS',
                       'var_doorSealPrimaryInflate','VAR_DOORSEALPRIMARYINFLATE'}) do
    ipc.log(name..'='..tostring(ipc.readLvar(name)))
end
for _, name in ipairs({'VAR_PRESSURIZATIONPRESS','VAR_DOORSEALPRIMARYINFLATE'}) do
    local saved=ipc.readLvar(name)
    assert(saved~=nil,'Cabin state unavailable: '..name)
    local ok,err=pcall(function()
        ipc.writeLvar(name,1-saved)
        ipc.sleep(700)
        assert(ipc.readLvar(name)==1-saved,'State change failed: '..name)
        ipc.log('Verified state change '..name..'='..tostring(1-saved))
    end)
    ipc.writeLvar(name,saved)
    ipc.sleep(700)
    assert(ipc.readLvar(name)==saved,'State restore failed: '..name)
    ipc.log('Restored '..name..'='..tostring(saved))
    if not ok then error(err) end
end
