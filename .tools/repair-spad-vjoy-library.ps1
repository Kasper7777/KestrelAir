$ErrorActionPreference='Stop'
$workspace=Split-Path $PSScriptRoot
$source='C:\Program Files\vJoy\x64\vJoyInterface.dll'
$target='C:\Program Files\SPAD.neXt\vJoyInterface.dll'
$backup=Join-Path $workspace ('backups\spad-vjoy-library-admin-'+(Get-Date -Format yyyyMMdd-HHmmss))
if(!(Test-Path -LiteralPath $source)){throw 'Installed vJoy library missing'}
Get-Process -Name SPAD.neXt -ErrorAction SilentlyContinue | Stop-Process
Start-Sleep -Seconds 2
New-Item -ItemType Directory -Path $backup | Out-Null
Copy-Item -LiteralPath $target -Destination $backup
Copy-Item -LiteralPath $source -Destination $target -Force
if((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath $target).Hash){throw 'Library copy verification failed'}
"Matching vJoy DLL installed. Original: $backup" | Set-Content (Join-Path $workspace 'spad-vjoy-library-repair.txt')
