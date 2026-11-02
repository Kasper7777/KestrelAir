param([ValidateRange(1,10)][int]$PressureButton,[ValidateRange(1,10)][int]$SealButton,[switch]$Apply)
$ErrorActionPreference='Stop'
if(!$PressureButton -or !$SealButton -or $PressureButton -eq $SealButton){throw 'Specify two distinct confirmed CP2 buttons'}
$name='Baron - GNS 530 + TDS GTNxi 650.xml'
$installed=Join-Path $env:USERPROFILE ('Documents\SPAD.neXt\profiles\'+$name)
$workspace=Join-Path $PSScriptRoot ('profiles\'+$name)
$ns='http://www.fsgs.com/SPAD'
$doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($installed);$before=$doc.CloneNode($true)
$m=New-Object Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
function PathFor($product,$button){'//s:Device[@VendorID="0x3344" and @ProductID="'+$product+'"]/s:DevicePage[@IsDefaultPage="true"]/s:Events/s:Event[@BoundTo="BUTTON_'+$button+'"]'}
$paths=New-Object Collections.Generic.List[string]
foreach($button in 17,18,19,20){
 $path=PathFor '0x025C' $button;$paths.Add($path);$e=$doc.SelectSingleNode($path,$m)
 if(!$e){throw "Expected CP3 switch input missing: $button"}
 if($e.InnerXml -notmatch 'var_pressurizationPress|var_doorSealPrimaryInflate'){throw "Unexpected CP3 switch binding: $button"}
 [void]$e.ParentNode.RemoveChild($e)
}
foreach($entry in @(@($PressureButton,'var_pressurizationPress'),@($SealButton,'var_doorSealPrimaryInflate'))){
 $logical=$entry[0]+3;$path=PathFor '0x025A' $logical;$paths.Add($path)
 $e=$doc.SelectSingleNode($path,$m)
 if($e){throw "CP2 B$($entry[0]) already assigned; refusing to replace an unrelated action"}
 $events=$doc.SelectSingleNode('//s:Device[@ProductID="0x025A"]/s:DevicePage[@IsDefaultPage="true"]/s:Events',$m)
 $e=$doc.CreateElement('Event',$ns);$e.SetAttribute('BoundTo',('BUTTON_'+$logical));[void]$events.AppendChild($e)
 $e.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions><EventActionChangeValue SourceType="Exp" TargetDataDefinition="LVAR:'+$entry[1]+'" SourceDataDefinition="1 - [LVAR:'+$entry[1]+']" /></EventActions></EventDefinition></EventDefinitions>'
}
# Reuse the existing, indexed and state-guarded pitot commands on CP3 T2/T3.
foreach($pair in @(@(17,50),@(18,51),@(19,52),@(20,53))){
 $source=$before.SelectSingleNode((PathFor '0x0194' $pair[1]),$m)
 if(!$source -or $source.InnerXml -notmatch 'PITOT_HEAT_TOGGLE'){throw 'Expected indexed pitot binding missing'}
 $events=$doc.SelectSingleNode('//s:Device[@ProductID="0x025C"]/s:DevicePage[@IsDefaultPage="true"]/s:Events',$m)
 $e=$doc.CreateElement('Event',$ns);$e.SetAttribute('BoundTo',('BUTTON_'+$pair[0]));$e.InnerXml=$source.InnerXml;[void]$events.AppendChild($e)
 $parameter=$e.SelectSingleNode('.//s:Parameter',$m);$parameter.SetAttribute('Type','Static')
}
# CP2 T1=strobe, T2=beacon unchanged, T3=nav.
foreach($entry in @(@(17,'B:LIGHTING_STROBE_1',1),@(18,'B:LIGHTING_STROBE_1',0),@(21,'B:LIGHTING_NAV_1',1),@(22,'B:LIGHTING_NAV_1',0))){
 $path=PathFor '0x025A' $entry[0];$paths.Add($path);$e=$doc.SelectSingleNode($path,$m)
 if(!$e){throw 'Expected CP2 light switch missing'}
 $e.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions><EventActionChangeValue TargetDataDefinition="'+$entry[1]+'" Value="'+$entry[2]+'" /></EventActions></EventDefinition></EventDefinitions>'
}
# CP3 T8 now controls propeller heat.
foreach($entry in @(@(29,1),@(30,0))){
 $path=PathFor '0x025C' $entry[0];$paths.Add($path);$e=$doc.SelectSingleNode($path,$m)
 if(!$e){throw 'Expected CP3 T8 input missing'}
 $e.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions><EventActionChangeValue TargetDataDefinition="LVAR:var_PropHeatSwitch" Value="'+$entry[1]+'" /></EventActions></EventDefinition></EventDefinitions>'
}
$check=$doc.CloneNode($true);$baseline=$before.CloneNode($true)
foreach($path in $paths){foreach($x in $check,$baseline){$e=$x.SelectSingleNode($path,$m);if($e){[void]$e.ParentNode.RemoveChild($e)}}}
if($check.OuterXml -ne $baseline.OuterXml){throw 'Unrelated profile change detected'}
$backup=Join-Path $PSScriptRoot ('backups\cabin-buttons-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
[void](New-Item -ItemType Directory $backup)
Copy-Item -LiteralPath $installed -Destination (Join-Path $backup 'installed.xml')
Copy-Item -LiteralPath $workspace -Destination (Join-Path $backup 'workspace.xml')
$doc.Save((Join-Path $backup 'prepared.xml'))
if($Apply){if(Get-Process SPAD.neXt -ErrorAction SilentlyContinue){throw 'Stop SPAD before applying'};$doc.Save($installed);$doc.Save($workspace)}
Write-Output "CP2 B$PressureButton pressure, B$SealButton door seal; T1 strobe/T3 nav. CP3 T2/T3 left/right pitot, T8 prop heat. Unrelated XML preserved. Applied=$Apply. Backup=$backup"
