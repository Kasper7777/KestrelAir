param([switch]$Apply)
$ErrorActionPreference='Stop'
$name='Baron - GNS 530 + TDS GTNxi 650.xml'
$installed=Join-Path $env:USERPROFILE ('Documents\SPAD.neXt\profiles\'+$name)
$workspace=Join-Path $PSScriptRoot ('profiles\'+$name)
$ns='http://www.fsgs.com/SPAD'
$doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($installed);$before=$doc.CloneNode($true)
$m=New-Object Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
$paths=New-Object Collections.Generic.List[string]
function PathFor($product,$button){'//s:Device[@VendorID="0x3344" and @ProductID="'+$product+'"]/s:DevicePage[@IsDefaultPage="true"]/s:Events/s:Event[@BoundTo="BUTTON_'+$button+'"]'}
function SetPress($product,$button,$action){
 $path=PathFor $product $button;$paths.Add($path);$e=$doc.SelectSingleNode($path,$m)
 if(!$e){$events=$doc.SelectSingleNode(('//s:Device[@ProductID="'+$product+'"]/s:DevicePage[@IsDefaultPage="true"]/s:Events'),$m);$e=$doc.CreateElement('Event',$ns);$e.SetAttribute('BoundTo',('BUTTON_'+$button));[void]$events.AppendChild($e)}
 $e.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions>'+$action+'</EventActions></EventDefinition></EventDefinitions>'
}
function Change($target,$expression){'<EventActionChangeValue SourceType="Exp" TargetDataDefinition="'+$target+'" SourceDataDefinition="'+$expression+'" />'}
# Use authoritative switch/position state, matching LED feedback, rather than B input readback.
SetPress '0x025A' 4 (Change 'B:ENGINE_COWLFLAPS_LEFT' 'if([SIMCONNECT:RECIP ENG COWL FLAP POSITION:1] > 0.5, 0, 1)')
SetPress '0x025A' 5 (Change 'B:ENGINE_COWLFLAPS_RIGHT' 'if([SIMCONNECT:RECIP ENG COWL FLAP POSITION:2] > 0.5, 0, 1)')
SetPress '0x025C' 1 (Change 'B:ELECTRICAL_BATTERY_1' '1 - [SIMCONNECT:ELECTRICAL MASTER BATTERY:1]')
SetPress '0x025C' 3 (Change 'B:ELECTRICAL_AVIONICS_BUS_1' '1 - [SIMCONNECT:AVIONICS MASTER SWITCH:1]')
# VIRPIL profile order: gear 1-3, B1-B4 4-7, encoders 8-16,
# T1-T10 17-36, then B5-B10 37-42. Relocate previous mistaken IDs first.
foreach($entry in @(@(8,37,'var_pressurizationPress'),@(9,38,'var_doorSealPrimaryInflate'))){
 $oldPath=PathFor '0x025A' $entry[0];$newPath=PathFor '0x025A' $entry[1];$paths.Add($oldPath);$paths.Add($newPath)
 $e=$doc.SelectSingleNode($oldPath,$m)
 if(!$e -or $e.InnerXml -notmatch $entry[2]){throw 'Expected cabin binding missing from mistaken encoder ID'}
 if($doc.SelectSingleNode($newPath,$m)){throw 'Actual cabin button already assigned'}
 $e.SetAttribute('BoundTo',('BUTTON_'+$entry[1]))
}
foreach($entry in @(@(9,'ELEV_TRIM_DN'),@(10,'ELEV_TRIM_UP'),@(12,'RUDDER_TRIM_LEFT'),@(13,'RUDDER_TRIM_RIGHT'),@(15,'AILERON_TRIM_LEFT'),@(16,'AILERON_TRIM_RIGHT'))){
 $path=PathFor '0x025A' $entry[0]
 if($doc.SelectSingleNode($path,$m)){throw 'Unexpected pre-existing encoder assignment'}
 SetPress '0x025A' $entry[0] ('<EventActionControl TargetDataDefinition="SIMCONNECT:'+$entry[1]+'"><Parameter Type="Static" Value="0" /></EventActionControl>')
}
$check=$doc.CloneNode($true);$baseline=$before.CloneNode($true)
foreach($path in $paths){foreach($x in $check,$baseline){$e=$x.SelectSingleNode($path,$m);if($e){[void]$e.ParentNode.RemoveChild($e)}}}
if($check.OuterXml -ne $baseline.OuterXml){throw 'Unrelated profile change detected'}
$backup=Join-Path $PSScriptRoot ('backups\single-press-cp2-trim-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
[void](New-Item -ItemType Directory $backup)
Copy-Item -LiteralPath $installed -Destination (Join-Path $backup 'installed.xml')
Copy-Item -LiteralPath $workspace -Destination (Join-Path $backup 'workspace.xml')
$doc.Save((Join-Path $backup 'prepared.xml'))
if($Apply){if(Get-Process SPAD.neXt -ErrorAction SilentlyContinue){throw 'Stop SPAD before applying'};$doc.Save($installed);$doc.Save($workspace)}
Write-Output "Verified actual-state toggles; CP2 E1 elevator/E2 rudder/E3 aileron; actual B5/B6 cabin IDs corrected; unrelated XML preserved. Applied=$Apply. Backup=$backup"
