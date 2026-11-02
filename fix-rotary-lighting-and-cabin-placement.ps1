param([switch]$Apply)
$ErrorActionPreference='Stop'
$name='Baron - GNS 530 + TDS GTNxi 650.xml'
$installed=Join-Path $env:USERPROFILE ('Documents\SPAD.neXt\profiles\'+$name)
$workspace=Join-Path $PSScriptRoot ('profiles\'+$name)
$ns='http://www.fsgs.com/SPAD'
$doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($installed);$before=$doc.CloneNode($true)
$m=New-Object Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
$paths=New-Object Collections.Generic.List[string]
function PathFor($product,$button){'//s:Device[@VendorID="0x16D0" or @VendorID="0x3344"][@ProductID="'+$product+'"]/s:DevicePage[@IsDefaultPage="true"]/s:Events/s:Event[@BoundTo="BUTTON_'+$button+'"]'}
function ReplacePress($product,$button,$action){
 $path=PathFor $product $button;$paths.Add($path);$event=$doc.SelectSingleNode($path,$m)
 if(!$event){throw "Expected input missing: $product $button"}
 $event.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions>'+$action+'</EventActions></EventDefinition></EventDefinitions>'
}
function Command($target,$value){'<EventActionControl TargetDataDefinition="SIMCONNECT:'+$target+'"><Parameter Type="Static" Value="'+$value+'" /></EventActionControl>'}
# Atomic one-step commands: no readback-to-set feedback loop or unit conversion.
foreach($product in '0x1290','0x128F'){
 ReplacePress $product 11 (Command 'HEADING_BUG_INC' 1)
 ReplacePress $product 12 (Command 'HEADING_BUG_DEC' 1)
}
foreach($product in '0x13E4','0x13E3'){
 ReplacePress $product 11 (Command 'VOR1_OBI_INC' 0)
 ReplacePress $product 12 (Command 'VOR1_OBI_DEC' 0)
}
# T5 flood stays unchanged; T6 becomes panel lighting; T7 is now unused.
foreach($entry in @(@(50,1),@(51,0))){ReplacePress '0x0194' $entry[0] ('<EventActionChangeValue TargetDataDefinition="LVAR:bksq_MasterPanelLights" Value="'+$entry[1]+'" />')}
foreach($button in 52,53){$path=PathFor '0x0194' $button;$paths.Add($path);$e=$doc.SelectSingleNode($path,$m);if(!$e){throw 'Expected third throttle switch missing'};[void]$e.ParentNode.RemoveChild($e)}
# CP2 B3/B4 -> B5/B6. Logical IDs are printed button + 3.
foreach($entry in @(@(6,8,'var_pressurizationPress'),@(7,9,'var_doorSealPrimaryInflate'))){
 $oldPath=PathFor '0x025A' $entry[0];$newPath=PathFor '0x025A' $entry[1];$paths.Add($oldPath);$paths.Add($newPath)
 $e=$doc.SelectSingleNode($oldPath,$m)
 if(!$e -or $e.InnerXml -notmatch $entry[2]){throw 'Expected cabin control source missing'}
 if($doc.SelectSingleNode($newPath,$m)){throw 'New CP2 button already assigned'}
 $e.SetAttribute('BoundTo',('BUTTON_'+$entry[1]))
}
$check=$doc.CloneNode($true);$baseline=$before.CloneNode($true)
foreach($path in $paths){foreach($x in $check,$baseline){$e=$x.SelectSingleNode($path,$m);if($e){[void]$e.ParentNode.RemoveChild($e)}}}
if($check.OuterXml -ne $baseline.OuterXml){throw 'Unrelated profile change detected'}
$backup=Join-Path $PSScriptRoot ('backups\rotary-lighting-cabin-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
[void](New-Item -ItemType Directory $backup)
Copy-Item -LiteralPath $installed -Destination (Join-Path $backup 'installed.xml')
Copy-Item -LiteralPath $workspace -Destination (Join-Path $backup 'workspace.xml')
$doc.Save((Join-Path $backup 'prepared.xml'))
if($Apply){if(Get-Process SPAD.neXt -ErrorAction SilentlyContinue){throw 'Stop SPAD before applying'};$doc.Save($installed);$doc.Save($workspace)}
Write-Output "Verified: one-degree heading/course; throttle T6 panel/T7 clear; CP2 B5 pressure/B6 seal, B3/B4 clear; all unrelated XML preserved. Applied=$Apply. Backup=$backup"
