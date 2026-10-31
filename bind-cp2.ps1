param([switch]$Apply)
$ErrorActionPreference='Stop'
$profileName='Baron - GNS 530 + TDS GTNxi 650.xml'
$installed=Join-Path $env:USERPROFILE ('Documents\SPAD.neXt\profiles\'+$profileName)
$backupPath=(Get-Content (Join-Path $PSScriptRoot 'cp2-backup-path.txt') -Raw).Trim()
$ns='http://www.fsgs.com/SPAD'
$doc=New-Object System.Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($installed)
$manager=New-Object System.Xml.XmlNamespaceManager($doc.NameTable);$manager.AddNamespace('s',$ns)
$before=$doc.CloneNode($true)
$devices=$doc.SelectSingleNode('/s:Profile/s:Devices',$manager)
$existing=$doc.SelectSingleNode('//s:Device[@VendorID="0x3344" and @ProductID="0x025A"]',$manager)
if($existing -and $existing.SelectNodes('.//s:Event',$manager).Count) {throw 'CP2 already contains bindings; refusing to overwrite.'}
if($existing){[void]$devices.RemoveChild($existing)}
$device=$doc.CreateElement('Device',$ns)
$device.SetAttribute('VendorID','0x3344');$device.SetAttribute('ProductID','0x025A')
$device.SetAttribute('DevicePath','\\?\hid#vid_3344&pid_025a&mi_00#a&282a1635&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}')
$device.SetAttribute('Serial','');$device.SetAttribute('DeviceIndex','0');$device.SetAttribute('Version','3')
$device.InnerXml='<DevicePage xmlns="'+$ns+'" ID="72c73483-060e-4a22-94be-a6d0c6e32179" IsDefaultPage="true" Name="Default"><Events /></DevicePage>'
$events=$device.SelectSingleNode('s:DevicePage/s:Events',$manager)
function Add-Input($button,$action,$releaseAction) {
 $event=$doc.CreateElement('Event',$ns);$event.SetAttribute('BoundTo',('BUTTON_'+$button))
 $xml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions>'+$action+'</EventActions></EventDefinition>'
 if($releaseAction){$xml+='<EventDefinition Trigger="RELEASE"><EventActions>'+$releaseAction+'</EventActions></EventDefinition>'}
 $event.InnerXml=$xml+'</EventDefinitions>';[void]$events.AppendChild($event)
}
Add-Input 1 '<EventActionChangeValue TargetDataDefinition="B:LANDING_GEAR_GEAR" Value="0" />' $null
Add-Input 3 '<EventActionChangeValue TargetDataDefinition="B:LANDING_GEAR_GEAR" Value="1" />' $null
$lights=@('NAV_LIGHTS_SET','BEACON_LIGHTS_SET','STROBES_SET','TAXI_LIGHTS_SET','LANDING_LIGHTS_SET','PANEL_LIGHTS_SET')
for($i=0;$i -lt 6;$i++){
 $on='<EventActionControl TargetDataDefinition="SIMCONNECT:'+$lights[$i]+'"><Parameter Value="1" /></EventActionControl>'
 $off='<EventActionControl TargetDataDefinition="SIMCONNECT:'+$lights[$i]+'"><Parameter Value="0" /></EventActionControl>'
 Add-Input (17+2*$i) $on $off
 Add-Input (18+2*$i) $off $null
}
foreach($entry in @(@(29,30,1),@(31,32,2))){
 $on='<EventActionControl TargetDataDefinition="B:ELECTRICAL_ALTERNATOR_'+$entry[2]+'_On" />'
 $off='<EventActionControl TargetDataDefinition="B:ELECTRICAL_ALTERNATOR_'+$entry[2]+'_Off" />'
 Add-Input $entry[0] $on $off;Add-Input $entry[1] $off $null
}
[void]$devices.AppendChild($device)
if($events.SelectNodes('s:Event',$manager).Count -ne 18){throw 'Expected 18 mapped inputs.'}
if($events.SelectNodes('s:Event/s:EventDefinitions/s:EventDefinition',$manager).Count -ne 26){throw 'Expected 26 press/release actions.'}
if($events.SelectSingleNode('s:Event[@BoundTo="BUTTON_2"]',$manager)){throw 'Gear centre must remain unassigned.'}
$check=$doc.CloneNode($true);$checkDevice=$check.SelectSingleNode('//s:Device[@VendorID="0x3344" and @ProductID="0x025A"]',$manager);[void]$checkDevice.ParentNode.RemoveChild($checkDevice)
if($existing){$originalCp2=$before.SelectSingleNode('//s:Device[@VendorID="0x3344" and @ProductID="0x025A"]',$manager);[void]$originalCp2.ParentNode.RemoveChild($originalCp2)}
if($check.OuterXml -ne $before.OuterXml){throw 'An unrelated profile binding changed.'}
$mappingPath=Join-Path $env:APPDATA 'SPAD.neXt\conf\profiles\c6161017-25ec-4090-8e92-626d02185025.xml'
$mapping=New-Object System.Xml.XmlDocument;$mapping.PreserveWhitespace=$true;$mapping.Load($mappingPath)
$local=$mapping.SelectSingleNode('//LocalDeviceMapping[@DeviceProfileID="3344:025A:0"]')
if(!$local){$local=$mapping.CreateElement('LocalDeviceMapping');$local.SetAttribute('DeviceProfileID','3344:025A:0');[void]$mapping.DocumentElement.Mapping.AppendChild($local)}
$local.SetAttribute('DeviceLocalID','3344:025A:0')
Write-Output 'Verified CP2: gear lever, six light switches, left/right alternators. All prior device bindings unchanged.'
if(!$Apply){Write-Output 'Dry run only.';return}
if(Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue){throw 'Close SPAD before applying.'}
if(!(Test-Path -LiteralPath $backupPath)){throw 'Project backup missing.'}
Copy-Item -LiteralPath $installed -Destination (Join-Path $backupPath 'before-cp2-profile.xml')
Copy-Item -LiteralPath $mappingPath -Destination (Join-Path $backupPath 'before-cp2-mapping.xml')
$doc.Save($installed);$mapping.Save($mappingPath)
Copy-Item -LiteralPath $installed -Destination (Join-Path $PSScriptRoot ('profiles\'+$profileName))
Copy-Item -LiteralPath $installed -Destination (Join-Path $backupPath 'after-cp2-profile.xml')
Write-Output "Installed. Project backup: $backupPath"
