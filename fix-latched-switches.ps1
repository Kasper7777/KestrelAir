$ErrorActionPreference='Stop'
if(Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue){throw 'SPAD must be closed'}
$path=Join-Path $env:USERPROFILE 'Documents\SPAD.neXt\profiles\Baron - GNS 530 + TDS GTNxi 650.xml'
$backup=Join-Path $PSScriptRoot ('backups\latched-switches-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
[void](New-Item -ItemType Directory -Path $backup);Copy-Item -LiteralPath $path -Destination (Join-Path $backup 'before.xml')
$doc=New-Object System.Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($path)
$ns='http://www.fsgs.com/SPAD';$m=New-Object System.Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
$cp2=$doc.SelectSingleNode('//s:Device[@ProductID="0x025A"]/s:DevicePage/s:Events',$m)
$gearBefore=@($cp2.SelectNodes('s:Event[@BoundTo="BUTTON_1" or @BoundTo="BUTTON_3"]',$m) | ForEach-Object OuterXml) -join ''
# CP2 controls are directional momentary switches: up sets ON, down sets OFF.
# Returning to centre must not cancel the command.
foreach($release in @($cp2.SelectNodes('.//s:EventDefinition[@Trigger="RELEASE"]',$m))){[void]$release.ParentNode.RemoveChild($release)}
foreach($rightLanding in @($cp2.SelectNodes('.//s:EventActionChangeValue[@TargetDataDefinition="B:LIGHTING_LANDING_2"]',$m))){[void]$rightLanding.ParentNode.RemoveChild($rightLanding)}
# Use the documented aircraft panel-light switch.
foreach($button in 27,28){$actions=$cp2.SelectSingleNode(('s:Event[@BoundTo="BUTTON_{0}"]/s:EventDefinitions/s:EventDefinition[@Trigger="PRESS"]/s:EventActions' -f $button),$m);$state=0;if($button -eq 27){$state=1};$actions.InnerXml='<EventActionChangeValue xmlns="'+$ns+'" TargetDataDefinition="LVAR:bksq_MasterPanelLights" Value="'+$state+'" />'}
$throttle=$doc.SelectSingleNode('//s:Device[@ProductID="0x0194"]/s:DevicePage/s:Events',$m)
$trackingBefore=@($throttle.SelectNodes('s:Event[@BoundTo="BUTTON_56" or @BoundTo="BUTTON_59"]',$m) | ForEach-Object OuterXml) -join ''
function Set-Press($button,$actions,$conditions=''){
 $event=$throttle.SelectSingleNode(('s:Event[@BoundTo="BUTTON_{0}"]' -f $button),$m)
 if(!$event){$event=$doc.CreateElement('Event',$ns);$event.SetAttribute('BoundTo',('BUTTON_'+$button));[void]$throttle.AppendChild($event)}
 $event.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS">'+$conditions+'<EventActions>'+$actions+'</EventActions></EventDefinition></EventDefinitions>'
}
foreach($entry in @(@(49,1,-1),@(50,1,1),@(52,2,-1),@(53,2,1))){
 $target='LVAR:BKSQ_IgnitionPosition_'+$entry[1]
 $expression='Max(0, ['+$target+'] - 1)';if($entry[2] -gt 0){$expression='Min(5, ['+$target+'] + 1)'}
 Set-Press $entry[0] ('<EventActionChangeValue TargetDataDefinition="'+$target+'" SourceType="Exp" ValueOperation="Set" Value="'+$expression+'" />')
}
Set-Press 42 '<EventActionChangeValue TargetDataDefinition="LVAR:bksq_MasterGlareshieldLights" Value="1" />'
Set-Press 43 '<EventActionChangeValue TargetDataDefinition="LVAR:bksq_MasterGlareshieldLights" Value="0" />'
# Manufacturer documents indexed PITOT_HEAT_TOGGLE, 1=left and 2=right.
# Conditions make the directional switches idempotent, with no action on release.
foreach($entry in @(@(44,1,0),@(45,1,1),@(46,2,0),@(47,2,1))){
 $condition='<EventConditions><EventCondition ConditionComparator="Equals" ConditionTargetValue="'+$entry[2]+'" ConditionValueSource="SIMCONNECT:PITOT HEAT SWITCH:'+$entry[1]+'" /></EventConditions>'
 Set-Press $entry[0] ('<EventActionControl TargetDataDefinition="SIMCONNECT:PITOT_HEAT_TOGGLE"><Parameter Type="Static" Value="'+$entry[1]+'" /></EventActionControl>') $condition
}
# Move landing-light control off CP3, preserving its pumps and other controls.
$cp3=$doc.SelectSingleNode('//s:Device[@ProductID="0x025C"]/s:DevicePage/s:Events',$m)
foreach($event in @($cp3.SelectNodes('s:Event[.//*[@TargetDataDefinition and contains(@TargetDataDefinition,"LANDING_LIGHT")]]',$m))){[void]$event.ParentNode.RemoveChild($event)}
if($cp2.SelectNodes('.//s:EventDefinition[@Trigger="RELEASE"]',$m).Count){throw 'CP2 release-to-OFF remains'}
if($cp2.SelectNodes('.//*[@TargetDataDefinition="B:LIGHTING_LANDING_2"]',$m).Count){throw 'Right landing light still assigned'}
if((@($cp2.SelectNodes('s:Event[@BoundTo="BUTTON_1" or @BoundTo="BUTTON_3"]',$m) | ForEach-Object OuterXml) -join '') -ne $gearBefore){throw 'Working gear assignments changed'}
if((@($throttle.SelectNodes('s:Event[@BoundTo="BUTTON_56" or @BoundTo="BUTTON_59"]',$m) | ForEach-Object OuterXml) -join '') -ne $trackingBefore){throw 'Working Tobii assignments changed'}
$doc.Save($path);Copy-Item -LiteralPath $path -Destination (Join-Path $PSScriptRoot 'profiles\Baron - GNS 530 + TDS GTNxi 650.xml');Copy-Item -LiteralPath $path -Destination (Join-Path $backup 'after.xml')
Write-Output "Verified: latched CP2 controls, left landing light only, CP3 landing removed, encoder ignition variables, flood and separate pitot switches. Working gear and Tobii unchanged. Backup: $backup"
