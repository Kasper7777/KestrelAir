param([switch]$Apply)
$ErrorActionPreference='Stop'
$ns='http://www.fsgs.com/SPAD'
$name='Baron - GNS 530 + TDS GTNxi 650.xml'
$installed=Join-Path $env:USERPROFILE ('Documents\SPAD.neXt\profiles\'+$name)
$workspace=Join-Path $PSScriptRoot ('profiles\'+$name)
$backup=Join-Path $PSScriptRoot ('backups\ana-power-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
[void](New-Item -ItemType Directory -Path $backup)
$doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($installed)
$before=$doc.CloneNode($true)
$m=New-Object Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
$changed=New-Object Collections.Generic.List[string]
function Events($product,$index='0'){
 $doc.SelectSingleNode(('//s:Device[@ProductID="{0}" and @DeviceIndex="{1}"]/s:DevicePage[@IsDefaultPage="true"]/s:Events' -f $product,$index),$m)
}
function Set-Button($product,$button,$actions){
 $events=Events $product
 if(!$events){throw "Device missing: $product"}
 $path='//s:Device[@ProductID="'+$product+'" and @DeviceIndex="0"]/s:DevicePage[@IsDefaultPage="true"]/s:Events/s:Event[@BoundTo="BUTTON_'+$button+'"]'
 $changed.Add($path)
 $e=$doc.SelectSingleNode($path,$m)
 if(!$e){$e=$doc.CreateElement('Event',$ns);$e.SetAttribute('BoundTo',('BUTTON_'+$button));[void]$events.AppendChild($e)}
 $e.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions>'+$actions+'</EventActions></EventDefinition></EventDefinitions>'
}
function Control($target,$value){'<EventActionControl TargetDataDefinition="'+$target+'"><Parameter Type="Static" Value="'+$value+'" /></EventActionControl>'}
function Change($target,$expression){'<EventActionChangeValue SourceType="Exp" TargetDataDefinition="'+$target+'" SourceDataDefinition="'+$expression+'" />'}
# Remove both range routes on the right wheel, preserving left stick and all axes.
foreach($button in 21,22){
 $path='//s:Device[@ProductID="0x03F5" and @DeviceIndex="0"]/s:DevicePage/s:Events/s:Event[@BoundTo="BUTTON_'+$button+'"]'
 $changed.Add($path);$e=$doc.SelectSingleNode($path,$m);if($e){[void]$e.ParentNode.RemoveChild($e)}
}
# Restore the manufacturer's top-module ANA roles, including real ADF tuning.
# Apply to both USB identities because the connected module currently reports GC.
foreach($product in '0x1290','0x128F'){
 foreach($pair in @(@(13,'ADF1_WHOLE_INC'),@(14,'ADF1_WHOLE_DEC'),@(21,'ADF_100_INC'),@(22,'ADF_100_DEC'),@(7,'ADF1_RADIO_SWAP'))){Set-Button $product $pair[0] (Control ('SIMCONNECT:'+$pair[1]) 1)}
 Set-Button $product 3 '<EventActionChangeValue TargetDataDefinition="SIMCONNECT:TRANSPONDER STATE:1" Value="4" />'
 Set-Button $product 4 '<EventActionChangeValue TargetDataDefinition="SIMCONNECT:TRANSPONDER STATE:1" Value="3" />'
 Set-Button $product 8 '<EventActionChangeValue TargetDataDefinition="SIMCONNECT:TRANSPONDER STATE:1" Value="1" />'
 # The aircraft advertises INSTRUMENT_HEADING_BUG. Write through that native input.
 Set-Button $product 11 (Change 'B:INSTRUMENT_HEADING_BUG' '([B:INSTRUMENT_HEADING_BUG] + 1) % 360')
 Set-Button $product 12 (Change 'B:INSTRUMENT_HEADING_BUG' '([B:INSTRUMENT_HEADING_BUG] + 359) % 360')
 # ANA outer heading ring is gyro adjustment, never OBS/course.
 Set-Button $product 19 (Control 'SIMCONNECT:GYRO_DRIFT_INC' 1)
 Set-Button $product 20 (Control 'SIMCONNECT:GYRO_DRIFT_DEC' 1)
}
# One button per cowl flap. Existing B3/B4 down actions stay available.
Set-Button '0x025A' 4 (Control 'SIMCONNECT:COWLFLAP1_SET' 0)
Set-Button '0x025A' 5 (Control 'SIMCONNECT:COWLFLAP2_SET' 0)
foreach($pair in @(@(4,1),@(5,2))){
 $e=(Events '0x025A').SelectSingleNode(('s:Event[@BoundTo="BUTTON_{0}"]//s:Parameter' -f $pair[0]),$m)
 $e.SetAttribute('Type','Exp');$e.SetAttribute('Value',('if([SIMCONNECT:RECIP ENG COWL FLAP POSITION:{0}] &gt; 50, 0, 16383)' -f $pair[1]).Replace('&gt;','>'))
}
foreach($spec in @(@(1,'AVIONICS_MASTER_1_SET','AVIONICS MASTER SWITCH:1'),@(2,'AVIONICS_MASTER_2_SET','AVIONICS MASTER SWITCH:2'),@(3,'BATTERY1_SET','ELECTRICAL MASTER BATTERY:1'),@(4,'BATTERY2_SET','ELECTRICAL MASTER BATTERY:2'))){
 Set-Button '0x025C' $spec[0] (Control ('SIMCONNECT:'+$spec[1]) 0)
 $e=(Events '0x025C').SelectSingleNode(('s:Event[@BoundTo="BUTTON_{0}"]//s:Parameter' -f $spec[0]),$m)
 $e.SetAttribute('Type','Exp');$e.SetAttribute('Value',('1 - [SIMCONNECT:{0}]' -f $spec[2]))
}
# Remove precisely the edited events from each side and prove the rest matches.
$check=$doc.CloneNode($true);$baseline=$before.CloneNode($true)
foreach($path in $changed){foreach($x in $check,$baseline){$e=$x.SelectSingleNode($path,$m);if($e){[void]$e.ParentNode.RemoveChild($e)}}}
if($check.OuterXml -ne $baseline.OuterXml){throw 'Unrelated XML change detected'}
Copy-Item -LiteralPath $installed -Destination (Join-Path $backup 'installed.xml')
Copy-Item -LiteralPath $workspace -Destination (Join-Path $backup 'workspace.xml')
$doc.Save((Join-Path $backup 'prepared.xml'))
if($Apply){
 if(Get-Process SPAD.neXt -ErrorAction SilentlyContinue){throw 'SPAD must be stopped to prevent its cached profile overwriting these changes'}
 $doc.Save($installed);$doc.Save($workspace)
}
Write-Output "Verified all unrelated bindings preserved. Prepared profile: $backup\prepared.xml; applied=$Apply"
