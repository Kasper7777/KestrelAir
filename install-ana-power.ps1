$ErrorActionPreference='Stop'
$backup=Join-Path $PSScriptRoot ('backups\ana-power-runtime-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
[void](New-Item -ItemType Directory -Path $backup)
$fs='C:\FSUIPC7'
if(Test-Path "$fs\myOffsets.txt"){throw 'Existing myOffsets.txt requires a merge; refusing to overwrite'}
Copy-Item "$fs\FSUIPC7.ini" (Join-Path $backup 'FSUIPC7.ini')
$spad=Get-Process SPAD.neXt -ErrorAction SilentlyContinue
$fsuipc=Get-Process FSUIPC7 -ErrorAction SilentlyContinue
if($fsuipc){
 [void]$fsuipc.CloseMainWindow()
 if(!$fsuipc.WaitForExit(3000)){Stop-Process -Id $fsuipc.Id;Wait-Process -Id $fsuipc.Id -ErrorAction SilentlyContinue}
}
# Preserve the current INI after FSUIPC's normal shutdown/save.
Copy-Item "$fs\FSUIPC7.ini" (Join-Path $backup 'FSUIPC7-after-close.ini')
if($spad){Stop-Process -Id $spad.Id;Wait-Process -Id $spad.Id -ErrorAction SilentlyContinue}
try {
 & (Join-Path $PSScriptRoot 'update-ana-and-power.ps1') -Apply
 Copy-Item (Join-Path $PSScriptRoot 'KestrelAirLEDs.lua') "$fs\KestrelAirLEDs.lua"
 Copy-Item (Join-Path $PSScriptRoot 'KestrelAir-myOffsets.txt') "$fs\myOffsets.txt"
 $ini=[IO.File]::ReadAllText("$fs\FSUIPC7.ini")
 if($ini -match '(?m)^\[Auto\]\s*$'){throw 'Existing Auto section requires a merge'}
 if(Test-Path "$fs\ipcInit.lua"){throw 'Existing ipcInit.lua requires a merge'}
 Copy-Item (Join-Path $PSScriptRoot 'ipcInit.lua') "$fs\ipcInit.lua"
 [IO.File]::WriteAllText("$fs\FSUIPC7.ini",$ini,[Text.Encoding]::ASCII)
} finally {
 if($fsuipc){Start-Process "$fs\FSUIPC7.exe" -WindowStyle Hidden}
 if($spad){Start-Process 'C:\Program Files\SPAD.neXt\SPAD.neXt.exe' -WindowStyle Hidden}
}
Write-Output "Installed SPAD controls and FSUIPC LED feedback. Backup: $backup"
