$ErrorActionPreference='Stop'
if(Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue){throw 'Close SPAD before updating.'}
$path=Join-Path $env:USERPROFILE 'Documents\SPAD.neXt\profiles\Baron - GNS 530 + TDS GTNxi 650.xml'
$backup=(Get-Content (Join-Path $PSScriptRoot 'cp2-backup-path.txt') -Raw).Trim()
Copy-Item -LiteralPath $path -Destination (Join-Path $backup 'before-axis-tracking-fix.xml')
$doc=New-Object System.Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($path)
$ns='http://www.fsgs.com/SPAD';$m=New-Object System.Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
$cp2Before=$doc.SelectSingleNode('//s:Device[@ProductID="0x025A"]',$m).OuterXml
$corrected=0
foreach($action in $doc.SelectNodes('//s:EventActionRangedAxis[@ConfigID="LEVER_NOREVERSE_THROTTLE" or @ConfigID="LEVER_PROPPITCH"]',$m)){
 $option=$action.SelectSingleNode('s:Options/s:Option[@Key="INVERTAXIS"]',$m)
 if(!$option){throw 'Missing inversion setting'}
 $option.SetAttribute('Value','False');$corrected++
}
if($corrected -ne 4){throw 'Expected four reversed throttle/propeller axes'}
foreach($entry in @(@('RX_AXIS',1),@('RY_AXIS',2))){
 $actions=$doc.SelectSingleNode(('//s:Device[@ProductID="0x025C"]/s:DevicePage/s:Events/s:Event[@BoundTo="{0}"]/s:EventDefinitions/s:EventDefinition[@Trigger="VALUE"]/s:EventActions' -f $entry[0]),$m)
 if(!$actions){throw 'Mixture input missing'}
 $actions.InnerXml='<EventActionChangeValue xmlns="'+$ns+'" TargetDataDefinition="LVAR:BKSQ_MixtureLeverPosition_'+$entry[1]+'" Value="0" SourceType="Static" ValueOperation="SetEventValue_AxisPercent" />'
}
# Configurator 2 verified B3 in mode 1 = 56, B6 in mode 1 = 59.
# Replace the obsolete pre-firmware commands on these two newly reassigned inputs.
$events=$doc.SelectSingleNode('//s:Device[@ProductID="0x0194"]/s:DevicePage/s:Events',$m)
foreach($entry in @(@(56,'HEAD_TRACKING_TOGGLE'),@(59,'EYE_TRACKING_RESET'))){
 $event=$events.SelectSingleNode(('s:Event[@BoundTo="BUTTON_{0}"]' -f $entry[0]),$m)
 if(!$event){$event=$doc.CreateElement('Event',$ns);$event.SetAttribute('BoundTo',('BUTTON_'+$entry[0]));[void]$events.AppendChild($event)}
 $event.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions><EventActionControl TargetDataDefinition="SIMCONNECT:'+$entry[1]+'" /></EventActions></EventDefinition></EventDefinitions>'
}
if($doc.SelectSingleNode('//s:Device[@ProductID="0x025A"]',$m).OuterXml -ne $cp2Before){throw 'CP2 assignments changed unexpectedly'}
if($doc.SelectNodes('//s:EventActionRangedAxis[@ConfigID="LEVER_MIXTURE"]',$m).Count){throw 'Generic mixture actions remain'}
if($doc.SelectNodes('//s:EventActionChangeValue[starts-with(@TargetDataDefinition,"LVAR:BKSQ_MixtureLeverPosition_") and @ValueOperation="SetEventValue_AxisPercent"]',$m).Count -ne 2){throw 'Mixture actions not installed correctly'}
$doc.Save($path)
Copy-Item -LiteralPath $path -Destination (Join-Path $PSScriptRoot 'profiles\Baron - GNS 530 + TDS GTNxi 650.xml')
Copy-Item -LiteralPath $path -Destination (Join-Path $backup 'final-spad-profile.xml')
Write-Output 'Verified: four axis directions corrected, two documented Black Square mixture controls, mode-1 B3/B6 tracking controls, and CP2 assignments preserved.'
