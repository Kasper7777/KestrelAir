$ErrorActionPreference='Stop'
Copy-Item 'C:\FSUIPC7\KestrelAirLEDs.lua' (Join-Path $PSScriptRoot 'backups\citation-leds-before-title-trim.lua')
Get-Process FSUIPC7 -ErrorAction SilentlyContinue | Stop-Process -Force
Copy-Item (Join-Path $PSScriptRoot 'KestrelAirLEDs.lua') 'C:\FSUIPC7\KestrelAirLEDs.lua'
Start-Process 'C:\FSUIPC7\FSUIPC7.exe' -ArgumentList '-auto' -WorkingDirectory 'C:\FSUIPC7' -WindowStyle Hidden
