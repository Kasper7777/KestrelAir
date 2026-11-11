# Optional: run NeoflyPhoto.exe --repair silently at every Windows logon. It re-points NeoFly
# shortcuts and ProgramStack items back to the photo launcher if a NeoFly update reset them.
# No admin needed. Undo: delete "NeoFly Photo Repair.lnk" from shell:startup.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$sh  = New-Object -ComObject WScript.Shell
$lnk = $sh.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Startup')) 'NeoFly Photo Repair.lnk'))
$lnk.TargetPath = Join-Path $here 'NeoflyPhoto.exe'
$lnk.Arguments = '--repair'
$lnk.WorkingDirectory = $here
$lnk.Description = 'Keeps NeoFly launching with the photo avatar after updates'
$lnk.Save()
"Auto-repair at logon installed."
