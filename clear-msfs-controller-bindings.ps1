param([switch]$Apply)
$ErrorActionPreference='Stop'
$remotePath='C:\Program Files (x86)\Steam\userdata\86580337\2537590\remote'
$changes=New-Object System.Collections.Generic.List[object]
$preserved=New-Object System.Collections.Generic.List[object]
foreach($file in Get-ChildItem -LiteralPath $remotePath -Filter 'inputprofile_*') {
 $raw=[IO.File]::ReadAllText($file.FullName)
 [xml]$before='<Root>'+($raw -replace '<\?xml[^>]*\?>','')+'</Root>'
 $deviceName=[string]$before.Root.Device.DeviceName
 if($deviceName -notmatch 'VPC|WarBRD|Alpha Flight Controls') {
  $preserved.Add([pscustomobject]@{File=$file.Name;Device=$deviceName;Hash=(Get-FileHash -LiteralPath $file.FullName).Hash});continue
 }
 $boundCount=$before.SelectNodes('//Action[*]').Count
 if(!$boundCount) { continue }
 $pattern='<Action\b(?<attributes>[^>]*?)(?<!/)>(?<body>[\s\S]*?)</Action>'
 $clean=[regex]::Replace($raw,$pattern,'<Action${attributes}/>')
 [xml]$after='<Root>'+($clean -replace '<\?xml[^>]*\?>','')+'</Root>'
 if($after.SelectNodes('//Action[*]').Count -ne 0 -or $after.SelectNodes('//KEY').Count -ne 0) { throw "Assignments remain: $($file.Name)" }
 if($before.SelectNodes('//Action').Count -ne $after.SelectNodes('//Action').Count) { throw 'Action definitions changed.' }
 foreach($action in @($before.SelectNodes('//Action[*]'))) { while($action.HasChildNodes) { [void]$action.RemoveChild($action.FirstChild) }; $action.IsEmpty=$true }
 if($before.OuterXml -ne $after.OuterXml) { throw "Unrelated XML changed: $($file.Name)" }
 $changes.Add([pscustomobject]@{File=$file.Name;Path=$file.FullName;Device=$deviceName;Profile=$after.Root.FriendlyName.InnerText;Removed=$boundCount;BeforeHash=(Get-FileHash -LiteralPath $file.FullName).Hash;Content=$clean})
}
$changes | Select-Object File,Device,Profile,Removed | Format-Table -AutoSize
Write-Output "Profiles: $($changes.Count); bound actions to clear: $(($changes | Measure-Object Removed -Sum).Sum)"
if(!$Apply) { Write-Output 'Dry run; no files changed.';return }
if(Get-Process -Name FlightSimulator2024,FlightSimulator -ErrorAction SilentlyContinue) { throw 'Exit MSFS normally before applying.' }
$backup=Join-Path $PSScriptRoot ('backups\msfs-controller-clear-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
[void](New-Item -ItemType Directory -Path $backup)
foreach($file in Get-ChildItem -LiteralPath $remotePath -Filter 'inputprofile_*') { Copy-Item -LiteralPath $file.FullName -Destination $backup }
foreach($name in @('profile_00','localprofile')) { Copy-Item -LiteralPath (Join-Path $remotePath $name) -Destination $backup }
$encoding=New-Object System.Text.UTF8Encoding($false)
foreach($change in $changes) {
 if((Get-FileHash -LiteralPath $change.Path).Hash -ne $change.BeforeHash) { throw 'Profile changed since inspection.' }
 [IO.File]::WriteAllText($change.Path,$change.Content,$encoding)
 [xml]$check='<Root>'+([IO.File]::ReadAllText($change.Path) -replace '<\?xml[^>]*\?>','')+'</Root>'
 if($check.SelectNodes('//Action[*]|//KEY').Count) { throw "Verification failed: $($change.File)" }
}
foreach($item in $preserved) { if((Get-FileHash -LiteralPath (Join-Path $remotePath $item.File)).Hash -ne $item.Hash) { throw "Preserved file changed: $($item.File)" } }
$changes | Select-Object File,Device,Profile,Removed,BeforeHash | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $backup 'changes.json')
$preserved | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $backup 'preserved.json')
Write-Output "Verified all targeted controller profiles have zero assigned inputs. Keyboard and Tobii files unchanged. Backup: $backup"
