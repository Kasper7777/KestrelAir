param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$profilePath = Join-Path $env:USERPROFILE 'Documents\SPAD.neXt\profiles\Baron - GNS 530 + TDS GTNxi 650.xml'
$mappingPath = Join-Path $env:APPDATA 'SPAD.neXt\conf\profiles\c6161017-25ec-4090-8e92-626d02185025.xml'
$ns = 'http://www.fsgs.com/SPAD'
$doc = New-Object System.Xml.XmlDocument
$doc.PreserveWhitespace = $true
$doc.Load($profilePath)
$manager = New-Object System.Xml.XmlNamespaceManager($doc.NameTable)
$manager.AddNamespace('s',$ns)
$right = $doc.SelectSingleNode('//s:Device[@VendorID="0x3344" and @ProductID="0x43F5"]',$manager)
if (!$right) { throw 'Expected original right-stick device not found.' }
$right.SetAttribute('ProductID','0x03F5')
$right.SetAttribute('DeviceIndex','0')
$right.SetAttribute('DevicePath','\\?\hid#vid_3344&pid_03f5&mi_00#a&1aa429cf&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}')
$added = New-Object System.Collections.Generic.List[System.Xml.XmlNode]
function Add-Axis($productId,$inputName,$config,$engine,$inverted,$centered) {
 $events = $doc.SelectSingleNode(('//s:Device[@VendorID="0x3344" and @ProductID="{0}"]/s:DevicePage[@IsDefaultPage="true"]/s:Events' -f $productId),$manager)
 if(!$events) { throw "Missing device $productId" }
 if($events.SelectSingleNode(('s:Event[@BoundTo="{0}"]' -f $inputName),$manager)) { throw "Axis already assigned: $productId $inputName" }
 $event=$doc.CreateElement('Event',$ns); $event.SetAttribute('BoundTo',$inputName)
 $options='<Option Key="USERAWVALUE" Value="True" /><Option Key="MIN" Value="0" /><Option Key="MAX" Value="60000" />'
 if($centered) { $options+='<Option Key="IDLE" Value="30000" />' }
 if($engine) { $options+= '<Option Key="OPTION'+$engine+'" Value="True" />' }
 $options+='<Option Key="INVERTAXIS" Value="'+$inverted.ToString()+'" />'
 $event.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="VALUE"><EventActions><EventActionRangedAxis ConfigID="'+$config+'"><Options>'+$options+'</Options></EventActionRangedAxis></EventActions></EventDefinition></EventDefinitions>'
 [void]$events.AppendChild($event); $added.Add($event)
 Write-Output "$productId $inputName -> $config engine $engine inverted $inverted"
}
Add-Axis '0x03F5' 'X_AXIS' 'LEVER_AILERONS' 0 $false $true
Add-Axis '0x03F5' 'Y_AXIS' 'LEVER_ELEVATOR' 0 $false $true
Add-Axis '0x0194' 'X_AXIS' 'LEVER_NOREVERSE_THROTTLE' 1 $true $false
Add-Axis '0x0194' 'Y_AXIS' 'LEVER_NOREVERSE_THROTTLE' 2 $true $false
Add-Axis '0x025C' 'X_AXIS' 'LEVER_PROPPITCH' 1 $true $false
Add-Axis '0x025C' 'Y_AXIS' 'LEVER_PROPPITCH' 2 $true $false
Add-Axis '0x025C' 'RX_AXIS' 'LEVER_MIXTURE' 1 $true $false
Add-Axis '0x025C' 'RY_AXIS' 'LEVER_MIXTURE' 2 $true $false
$recovered=Get-Content (Join-Path $PSScriptRoot 'recovered-msfs-bindings.json') -Raw | ConvertFrom-Json
$newButtons=New-Object System.Collections.Generic.List[object]
foreach($source in @(@('inputprofile_0227066304','0x0194'),@('inputprofile_0602614400','0x025C'))) {
 $saved=$recovered | Where-Object File -eq $source[0]
 $events=$doc.SelectSingleNode(('//s:Device[@ProductID="{0}"]/s:DevicePage[@IsDefaultPage="true"]/s:Events' -f $source[1]),$manager)
 foreach($actionText in $saved.Actions) {
  [xml]$actionXml=$actionText; $action=$actionXml.Action
  $keys=@($action.SelectNodes('Primary/KEY'))
  if($keys.Count -ne 1 -or $keys[0].Information -notmatch '^Joystick Button (\d+)$') { continue }
  $bound='BUTTON_'+$Matches[1]
  if($events.SelectSingleNode(('s:Event[@BoundTo="{0}"]' -f $bound),$manager)) { continue }
  if($action.ActionName -notmatch '^KEY_') { continue }
  $target='SIMCONNECT:'+($action.ActionName -replace '^KEY_','')
  $event=$doc.CreateElement('Event',$ns);$event.SetAttribute('BoundTo',$bound)
  $event.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions><EventActionControl TargetDataDefinition="'+$target+'" /></EventActions></EventDefinition></EventDefinitions>'
  [void]$events.AppendChild($event)
  $newButtons.Add(@($source[1],$bound))
  Write-Output "$($source[1]) $bound -> $target"
 }
}
# Prove the edit preserves every previously saved action and all unrelated XML.
$verify=$doc.CloneNode($true)
$verifyManager=New-Object System.Xml.XmlNamespaceManager($verify.NameTable);$verifyManager.AddNamespace('s',$ns)
foreach($axis in @(@('0x03F5','X_AXIS'),@('0x03F5','Y_AXIS'),@('0x0194','X_AXIS'),@('0x0194','Y_AXIS'),@('0x025C','X_AXIS'),@('0x025C','Y_AXIS'),@('0x025C','RX_AXIS'),@('0x025C','RY_AXIS'))) {
 $node=$verify.SelectSingleNode(('//s:Device[@ProductID="{0}"]/s:DevicePage/s:Events/s:Event[@BoundTo="{1}"]' -f $axis[0],$axis[1]),$verifyManager);[void]$node.ParentNode.RemoveChild($node)
}
foreach($button in $newButtons) {
 $node=$verify.SelectSingleNode(('//s:Device[@ProductID="{0}"]/s:DevicePage/s:Events/s:Event[@BoundTo="{1}"]' -f $button[0],$button[1]),$verifyManager);[void]$node.ParentNode.RemoveChild($node)
}
$original=New-Object System.Xml.XmlDocument;$original.PreserveWhitespace=$true;$original.Load($profilePath)
$oldRight=$original.SelectSingleNode('//s:Device[@ProductID="0x43F5"]',$manager)
$verifyRight=$verify.SelectSingleNode('//s:Device[@ProductID="0x03F5"]',$verifyManager)
foreach($attribute in @('ProductID','DevicePath','DeviceIndex')) { $verifyRight.SetAttribute($attribute,$oldRight.GetAttribute($attribute)) }
if($verify.OuterXml -ne $original.OuterXml) { throw 'Unrelated XML changed.' }
$mapping=New-Object System.Xml.XmlDocument;$mapping.PreserveWhitespace=$true;$mapping.Load($mappingPath)
$local=$mapping.SelectSingleNode('//LocalDeviceMapping[@DeviceProfileID="3344:43F5:0"]')
if(!$local) { throw 'Expected original local mapping missing.' }
$local.SetAttribute('DeviceProfileID','3344:03F5:0');$local.SetAttribute('DeviceLocalID','3344:03F5:0')
Write-Output 'Validated: all prior actions and unrelated XML preserved.'
if(!$Apply) { Write-Output 'Dry run only; no installed configuration changed.'; return }
if(Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue) { throw 'SPAD must be fully closed before applying.' }
$backup=Join-Path $PSScriptRoot ('backups\firmware-repair-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
[void](New-Item -ItemType Directory -Path $backup)
Copy-Item -LiteralPath $profilePath -Destination (Join-Path $backup 'profile.xml')
Copy-Item -LiteralPath $mappingPath -Destination (Join-Path $backup 'mapping.xml')
$doc.Save($profilePath);$mapping.Save($mappingPath)
Copy-Item -LiteralPath $profilePath -Destination (Join-Path $PSScriptRoot 'profiles\Baron - GNS 530 + TDS GTNxi 650.xml')
Write-Output "Installed SPAD repair. Backup: $backup"
