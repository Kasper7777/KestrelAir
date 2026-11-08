$ErrorActionPreference='Stop'
$backup = Join-Path $PSScriptRoot ('backups\citation-irs-install-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
$profile = 'C:\Users\Aero\Documents\SPAD.neXt\profiles\Citation X - FlightFX C750.xml'
Copy-Item -LiteralPath $profile -Destination $backup
# Close without saving the cached profile over the patch.
Get-Process SPAD.neXt -ErrorAction SilentlyContinue | Stop-Process -Force
& 'C:\Users\Aero\AppData\Roaming\uv\python\cpython-3.14.3-windows-x86_64-none\python.exe' (Join-Path $PSScriptRoot 'bind-citation-irs-selectors.py') --installed
if ($LASTEXITCODE -ne 0) { throw 'IRS profile patch failed' }
Start-Process 'C:\Program Files\SPAD.neXt\SPAD.neXt.exe' -WorkingDirectory 'C:\Program Files\SPAD.neXt' -WindowStyle Hidden
Write-Output "Installed. Backup: $backup"
