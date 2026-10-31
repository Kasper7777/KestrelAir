$ErrorActionPreference='Stop'
if(Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue){throw 'SPAD must be closed'}
$path=Join-Path $env:USERPROFILE 'Documents\SPAD.neXt\profiles\Baron - GNS 530 + TDS GTNxi 650.xml'
$backup=Join-Path $PSScriptRoot ('backups\cp3-layout-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
[void](New-Item -ItemType Directory -Path $backup);Copy-Item -LiteralPath $path -Destination (Join-Path $backup 'before.xml')
$doc=New-Object System.Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($path)
$before=$doc.CloneNode($true);$ns='http://www.fsgs.com/SPAD';$m=New-Object System.Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
$events=$doc.SelectSingleNode('//s:Device[@ProductID="0x025C"]/s:DevicePage/s:Events',$m)
# The physical OFF position was read live: CP3 button 47.
$values=@(5,3,2,1,0)
for($i=0;$i -lt 5;$i++){
 $event=$events.SelectSingleNode(('s:Event[@BoundTo="BUTTON_{0}"]' -f (43+$i)),$m)
 if(!$event){throw 'Expected CP3 magneto input missing'}
 $event.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions><EventActionChangeValue TargetDataDefinition="LVAR:BKSQ_IgnitionPosition_2" Value="'+$values[$i]+'" /></EventActions></EventDefinition></EventDefinitions>'
}
$assignments=@(
 @(21,22,'LVAR:var_PropHeatSwitch'),
 @(23,24,'LVAR:var_FuelVentHeatSwitch'),
 @(25,26,'LVAR:var_StallWarningHeatSwitch'),
 @(27,28,'LVAR:var_windshieldHeatSwitch'),
 @(29,30,'B:LIGHTING_WING_1')
)
foreach($assignment in $assignments){
 foreach($state in 0,1){
  $button=$assignment[1];if($state -eq 1){$button=$assignment[0]}
  $event=$events.SelectSingleNode(('s:Event[@BoundTo="BUTTON_{0}"]' -f $button),$m)
  if(!$event){$event=$doc.CreateElement('Event',$ns);$event.SetAttribute('BoundTo',('BUTTON_'+$button));[void]$events.AppendChild($event)}
  $event.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions><EventActionChangeValue TargetDataDefinition="'+$assignment[2]+'" Value="'+$state+'" /></EventActions></EventDefinition></EventDefinitions>'
 }
}
# Restore changed inputs in a comparison copy, proving every other device,
# fuel-pump control, cowl flap, axis and Tobii assignment is untouched.
$check=$doc.CloneNode($true)
foreach($button in @(21..30)+@(43..47)){
 $xpath='//s:Device[@ProductID="0x025C"]/s:DevicePage/s:Events/s:Event[@BoundTo="BUTTON_'+$button+'"]'
 $new=$check.SelectSingleNode($xpath,$m);$old=$before.SelectSingleNode($xpath,$m)
 if($old){[void]$new.ParentNode.ReplaceChild($check.ImportNode($old,$true),$new)}else{[void]$new.ParentNode.RemoveChild($new)}
}
if($check.OuterXml -ne $before.OuterXml){throw 'An unrelated binding changed'}
if($events.SelectNodes('s:Event[@BoundTo="BUTTON_47"]//s:EventActionChangeValue[@Value="0"]',$m).Count -ne 1){throw 'Physical OFF input does not set OFF'}
foreach($device in $doc.SelectNodes('//s:Device',$m)){if($device.SelectNodes('s:DevicePage/s:Events/s:Event',$m) | Group-Object BoundTo | Where-Object Count -gt 1){throw 'Duplicate logical input'}}
$doc.Save($path);Copy-Item -LiteralPath $path -Destination (Join-Path $PSScriptRoot 'profiles\Baron - GNS 530 + TDS GTNxi 650.xml');Copy-Item -LiteralPath $path -Destination (Join-Path $backup 'after.xml')
Write-Output "Verified reversed CP3 selector (47=OFF), five distinct switch functions, and all other bindings unchanged. Backup: $backup"
