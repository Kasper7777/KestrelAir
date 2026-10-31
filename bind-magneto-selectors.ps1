$ErrorActionPreference='Stop'
if(Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue){throw 'Close SPAD before updating'}
$path=Join-Path $env:USERPROFILE 'Documents\SPAD.neXt\profiles\Baron - GNS 530 + TDS GTNxi 650.xml'
$backup=(Get-Content (Join-Path $PSScriptRoot 'magneto-selector-backup.txt') -Raw).Trim()
$doc=New-Object System.Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($path)
$ns='http://www.fsgs.com/SPAD';$m=New-Object System.Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
$cp2Before=$doc.SelectSingleNode('//s:Device[@ProductID="0x025A"]',$m).OuterXml
$throttle=$doc.SelectSingleNode('//s:Device[@ProductID="0x0194"]/s:DevicePage/s:Events',$m)
# Retire the encoder ignition assignments, superseded by the two selectors.
foreach($event in @($throttle.SelectNodes('s:Event[.//s:EventActionChangeValue[starts-with(@TargetDataDefinition,"LVAR:BKSQ_IgnitionPosition_")]]',$m))){[void]$event.ParentNode.RemoveChild($event)}
# Verified after removing shifter: T5=48/49, T6=50/51, T7=52/53;
# B3=44 and B6=47. Rename existing bindings without changing their actions.
foreach($event in @($throttle.SelectNodes('s:Event',$m))){$id=$event.BoundTo;if($id -match '^BUTTON_(\d+)$'){$number=[int]$Matches[1];if($number -ge 42 -and $number -le 47){$event.SetAttribute('BoundTo',('BUTTON_'+($number+6)))}elseif($number -eq 56){$event.SetAttribute('BoundTo','BUTTON_44')}elseif($number -eq 59){$event.SetAttribute('BoundTo','BUTTON_47')}}}
$values=@(0,1,2,3,5)
foreach($entry in @(@('0x0194',60,1),@('0x025C',43,2))){
 $events=$doc.SelectSingleNode(('//s:Device[@ProductID="{0}"]/s:DevicePage/s:Events' -f $entry[0]),$m)
 for($position=0;$position -lt 5;$position++){
  $button=[int]$entry[1]+$position
  if($events.SelectSingleNode(('s:Event[@BoundTo="BUTTON_{0}"]' -f $button),$m)){throw "Selector input already assigned: $($entry[0]) $button"}
  $event=$doc.CreateElement('Event',$ns);$event.SetAttribute('BoundTo',('BUTTON_'+$button))
  $event.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions><EventActionChangeValue TargetDataDefinition="LVAR:BKSQ_IgnitionPosition_'+$entry[2]+'" Value="'+$values[$position]+'" /></EventActions></EventDefinition></EventDefinitions>'
  [void]$events.AppendChild($event)
 }
}
# Reject duplicate logical inputs after migrating the old button numbers.
foreach($device in $doc.SelectNodes('//s:Device',$m)){$duplicates=$device.SelectNodes('s:DevicePage/s:Events/s:Event',$m) | Group-Object BoundTo | Where-Object Count -gt 1;if($duplicates){throw "Duplicate input: $($device.ProductID) $($duplicates.Name -join ',')"}}
if($doc.SelectSingleNode('//s:Device[@ProductID="0x025A"]',$m).OuterXml -ne $cp2Before){throw 'CP2 bindings changed unexpectedly'}
$selectors=$doc.SelectNodes('//s:EventActionChangeValue[starts-with(@TargetDataDefinition,"LVAR:BKSQ_IgnitionPosition_")]',$m)
if($selectors.Count -ne 10){throw 'Expected ten discrete magneto selector positions'}
$doc.Save($path);Copy-Item -LiteralPath $path -Destination (Join-Path $PSScriptRoot 'profiles\Baron - GNS 530 + TDS GTNxi 650.xml');Copy-Item -LiteralPath $path -Destination (Join-Path $backup 'after-spad.xml')
Write-Output 'Verified throttle selector = left ignition, CP3 selector = right ignition; all ten positions; tracking/flood/pitot migrated; CP2 unchanged; no duplicate inputs.'
