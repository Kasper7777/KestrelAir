param([ValidateSet('CP2','CP3','Throttle','None')][string]$SwitchPanel='None',[switch]$Apply)
$ErrorActionPreference='Stop'
$name='Baron - GNS 530 + TDS GTNxi 650.xml'
$installed=Join-Path $env:USERPROFILE ('Documents\SPAD.neXt\profiles\'+$name)
$workspace=Join-Path $PSScriptRoot ('profiles\'+$name)
$ns='http://www.fsgs.com/SPAD'
$doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($installed)
$before=$doc.CloneNode($true)
$m=New-Object Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
$paths=New-Object Collections.Generic.List[string]
function EventPath($product,$button){'//s:Device[@VendorID="0x3344" and @ProductID="'+$product+'"]/s:DevicePage[@IsDefaultPage="true"]/s:Events/s:Event[@BoundTo="BUTTON_'+$button+'"]'}
foreach($button in 6,7){$path=EventPath '0x025A' $button;$paths.Add($path);$e=$doc.SelectSingleNode($path,$m);if($e){[void]$e.ParentNode.RemoveChild($e)}}
if($SwitchPanel -ne 'None'){
$product='0x025A';$t3=@(21,22);$t4=@(23,24)
if($SwitchPanel -eq 'CP3'){$product='0x025C';$t3=@(19,20);$t4=@(21,22)}
if($SwitchPanel -eq 'Throttle'){$product='0x0194';$t3=@(38,39);$t4=@(40,41)}
foreach($button in $t3){$path=EventPath $product $button;$paths.Add($path);$e=$doc.SelectSingleNode($path,$m);if($e){[void]$e.ParentNode.RemoveChild($e)}}
for($state=0;$state -le 1;$state++){
 $path=EventPath $product $t4[$state];$paths.Add($path)
 $e=$doc.SelectSingleNode($path,$m)
 if(!$e){throw "Expected switch input missing: $product $($t4[$state])"}
 $e.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions><EventActionChangeValue TargetDataDefinition="B:LANDING_GEAR_PARKINGBRAKE" Value="'+$state+'" /></EventActions></EventDefinition></EventDefinitions>'
}
}
$check=$doc.CloneNode($true);$baseline=$before.CloneNode($true)
foreach($path in $paths){foreach($x in $check,$baseline){$e=$x.SelectSingleNode($path,$m);if($e){[void]$e.ParentNode.RemoveChild($e)}}}
if($check.OuterXml -ne $baseline.OuterXml){throw 'Unrelated XML changed'}
$backup=Join-Path $PSScriptRoot ('backups\spares-parking-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
[void](New-Item -ItemType Directory $backup)
Copy-Item -LiteralPath $installed -Destination (Join-Path $backup 'installed.xml')
Copy-Item -LiteralPath $workspace -Destination (Join-Path $backup 'workspace.xml')
$doc.Save((Join-Path $backup 'prepared.xml'))
if($Apply){
 if(Get-Process SPAD.neXt -ErrorAction SilentlyContinue){throw 'Stop SPAD before applying'}
 $doc.Save($installed);$doc.Save($workspace)
}
Write-Output "Verified CP2 B3/B4 clear; switch panel=$SwitchPanel (None leaves switches unchanged). All unrelated XML preserved. Applied=$Apply. Backup=$backup"
