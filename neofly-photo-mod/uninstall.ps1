# Removes the photo mod: NeoFly launches normally again and shortcuts point back at Neofly.exe.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe  = Join-Path $here 'NeoflyPhoto.exe'
$nf   = Join-Path $env:LOCALAPPDATA 'Programs\Neofly\Neofly.exe'
$key  = 'HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\Neofly.exe'
Start-Process cmd.exe -ArgumentList "/c reg delete `"$key`" /f" -Verb RunAs -Wait -WindowStyle Hidden
$sh = New-Object -ComObject WScript.Shell
foreach ($root in [Environment]::GetFolderPath('DesktopDirectory'), [Environment]::GetFolderPath('Programs'),
                  (Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch')) {
    Get-ChildItem $root -Recurse -Filter *.lnk -ErrorAction SilentlyContinue | ForEach-Object {
        $s = $sh.CreateShortcut($_.FullName)
        if ($s.TargetPath -ieq $exe) { $s.TargetPath = $nf; $s.WorkingDirectory = Split-Path $nf; $s.Save(); "Restored $($_.FullName)" }
    }
}
"Uninstalled."
