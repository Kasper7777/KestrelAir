param([string]$SpadDirectory='C:\Program Files\SPAD.neXt',[string]$FsuipcDirectory='C:\FSUIPC7')
$ErrorActionPreference='Stop'
$principal=[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if(!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Run this setup from an administrator PowerShell window.'}
if(Get-Process SPAD.neXt,FlightSimulator2024 -ErrorAction SilentlyContinue){throw 'Close SPAD and MSFS before installing this backed-up setup.'}
$target=Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SPAD.neXt\profiles'
$backup=Join-Path $PSScriptRoot ('install-backup-'+(Get-Date -Format yyyyMMdd-HHmmss))
New-Item -ItemType Directory -Path $backup,$target -Force | Out-Null
$clickRoot=Join-Path $PSScriptRoot 'helpers\ka-click'
foreach($file in Get-ChildItem (Join-Path $PSScriptRoot 'profiles') -Filter '*.xml'){
 $destination=Join-Path $target $file.Name
 if(Test-Path -LiteralPath $destination){Copy-Item -LiteralPath $destination -Destination $backup}
 $doc=[xml](Get-Content -LiteralPath $file.FullName -Raw)
 foreach($parameter in $doc.SelectNodes('//*[@Value]')){
  $old=$parameter.GetAttribute('Value')
  if($old -match 'ka-click-(down|up)\.exe$'){
   $leaf='ka-click-'+$Matches[1]+'.exe'
   # SPAD expression-string paths use doubled backslashes.
   $parameter.SetAttribute('Value',(Join-Path $clickRoot $leaf).Replace('\','\\'))
  }
 }
 $doc.Save($destination)
}
$driverDll='C:\Program Files\vJoy\x64\vJoyInterface.dll'
if(!(Test-Path -LiteralPath $driverDll)){throw 'Install the included signed vJoy package and reboot first.'}
$spadDll=Join-Path $SpadDirectory 'vJoyInterface.dll'
if(!(Test-Path -LiteralPath $spadDll)){throw 'SPAD installation was not found.'}
if((Get-FileHash $driverDll).Hash -ne (Get-FileHash $spadDll).Hash){
 Copy-Item -LiteralPath $spadDll -Destination (Join-Path $backup 'vJoyInterface.dll')
 Copy-Item -LiteralPath $driverDll -Destination $spadDll -Force
}
if(Test-Path -LiteralPath $FsuipcDirectory){
 $luaTarget=Join-Path $FsuipcDirectory 'KestrelAirLEDs.lua'
 if(Test-Path -LiteralPath $luaTarget){Copy-Item -LiteralPath $luaTarget -Destination $backup}
 Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'helpers\KestrelAirLEDs.lua') -Destination $luaTarget
 $init=Join-Path $FsuipcDirectory 'ipcInit.lua'
 $text=if(Test-Path -LiteralPath $init){Copy-Item -LiteralPath $init -Destination $backup;Get-Content -LiteralPath $init -Raw}else{''}
 if($text -notmatch 'KestrelAirLEDs\.lua'){
  $escaped=$luaTarget.Replace('\','\\').Replace("'","\'")
  [IO.File]::WriteAllText($init,($text+"`r`ndofile('"+$escaped+"')`r`n"))
 }
 Write-Output 'LED helper installed. Merge the supplied read-only offsets into FSUIPC myOffsets.txt if this is a new PC.'
}
Write-Output "Profiles installed. Backup: $backup"
Write-Output 'In MSFS select vJoy Device > General controls > gear > Import, select KestrelAir-vJoy-GeneralControls.xml, then Apply to all aircraft.'
Write-Output 'B4 uses Shift+X: assign Shift+X to Toggle Drone Camera in the MSFS keyboard General Controls profile.'
Write-Output 'Select each SPAD profile once with its matching aircraft. Different PCs may require identifying which identical WarBRD grip is right.'
