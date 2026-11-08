$ErrorActionPreference = 'Stop'
$backup = Join-Path $PSScriptRoot ('backups\citation-cabin-install-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
$profile = 'C:\Users\Aero\Documents\SPAD.neXt\profiles\Citation X - FlightFX C750.xml'
$offsets = Get-Content 'C:\FSUIPC7\myOffsets.txt' -Raw
foreach ($item in @(@{Address='0xA020';Index=22},@{Address='0xA028';Index=23})) {
    $line = ($offsets -split "`r?`n" | Where-Object { $_ -match ('^' + $item.Address + ',') })
    if ($line -and $line -ne ($item.Address + ', 8, LIGHT POTENTIOMETER:' + $item.Index + ', F64, Percent')) { throw "Offset conflict at $($item.Address)" }
}
Copy-Item -LiteralPath $profile -Destination $backup
Copy-Item -LiteralPath 'C:\FSUIPC7\myOffsets.txt' -Destination $backup
Copy-Item -LiteralPath 'C:\FSUIPC7\KestrelAirLEDs.lua' -Destination $backup
$processes = Get-CimInstance Win32_Process -Filter "Name='SPAD.neXt.exe' OR Name='FSUIPC7.exe'"
$processes | Select-Object Name,ExecutablePath,CommandLine | ConvertTo-Json | Set-Content (Join-Path $backup 'processes.json')
# Prevent SPAD's cached profile from overwriting the patch on exit.
Get-Process SPAD.neXt -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process FSUIPC7 -ErrorAction SilentlyContinue | Stop-Process -Force
& 'C:\Users\Aero\AppData\Roaming\uv\python\cpython-3.14.3-windows-x86_64-none\python.exe' (Join-Path $PSScriptRoot 'bind-citation-cabin-lights.py') --installed
if ($LASTEXITCODE -ne 0) { throw 'Profile patch failed' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'KestrelAirLEDs.lua') -Destination 'C:\FSUIPC7\KestrelAirLEDs.lua'
foreach ($item in @(@{Address='0xA020';Index=22},@{Address='0xA028';Index=23})) {
    if ($offsets -notmatch $item.Address) { Add-Content 'C:\FSUIPC7\myOffsets.txt' ($item.Address + ', 8, LIGHT POTENTIOMETER:' + $item.Index + ', F64, Percent') }
}
Start-Process -FilePath 'C:\FSUIPC7\FSUIPC7.exe' -WorkingDirectory 'C:\FSUIPC7' -WindowStyle Hidden
$spad = $processes | Where-Object Name -eq 'SPAD.neXt.exe' | Select-Object -First 1
$spadPath = if ($spad.ExecutablePath) { $spad.ExecutablePath } else { 'C:\Program Files\SPAD.neXt\SPAD.neXt.exe' }
Start-Process -FilePath $spadPath -WorkingDirectory (Split-Path $spadPath) -WindowStyle Hidden
Write-Output "Installed and restarted SPAD/FSUIPC. Backups: $backup"
