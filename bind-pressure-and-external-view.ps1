$ErrorActionPreference='Stop'
if(Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue){throw 'SPAD must be closed'}
$path=Join-Path $env:USERPROFILE 'Documents\SPAD.neXt\profiles\Baron - GNS 530 + TDS GTNxi 650.xml'
$backup=Join-Path $PSScriptRoot ('backups\pressure-external-view-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
[void](New-Item -ItemType Directory -Path $backup);Copy-Item -LiteralPath $path -Destination (Join-Path $backup 'before.xml')
$doc=New-Object System.Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($path);$before=$doc.CloneNode($true)
$ns='http://www.fsgs.com/SPAD';$m=New-Object System.Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
function Set-Event($product,$button,$action){
 $events=$doc.SelectSingleNode(('//s:Device[@ProductID="{0}"]/s:DevicePage/s:Events' -f $product),$m)
 $event=$events.SelectSingleNode(('s:Event[@BoundTo="BUTTON_{0}"]' -f $button),$m)
 if(!$event){$event=$doc.CreateElement('Event',$ns);$event.SetAttribute('BoundTo',('BUTTON_'+$button));[void]$events.AppendChild($event)}
 $event.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions>'+$action+'</EventActions></EventDefinition></EventDefinitions>'
}
Set-Event '0x025C' 13 '<EventActionKeyboard MacroType="PRESSANDRELEASE" TargetWindow="__ACTIVEWINDOW__"><KeyboardMacro Duration="80" Repeat="1" Pause="25"><Keys><Keys>Back</Keys></Keys></KeyboardMacro></EventActionKeyboard>'
$bindings=@(
 @(55,'LVAR:var_pressurizationClimbRate','Max(150, [LVAR:var_pressurizationClimbRate] - 50)'),
 @(56,'LVAR:var_pressurizationClimbRate','Min(2000, [LVAR:var_pressurizationClimbRate] + 50)'),
 @(58,'LVAR:var_pressurizationGoal','Max(-1000, [LVAR:var_pressurizationGoal] - 100)'),
 @(59,'LVAR:var_pressurizationGoal','Min(15000, [LVAR:var_pressurizationGoal] + 100)')
)
foreach($entry in $bindings){
 $action=$doc.CreateElement('EventActionChangeValue',$ns);$action.SetAttribute('SourceType','Exp');$action.SetAttribute('TargetDataDefinition',$entry[1]);$action.SetAttribute('SourceDataDefinition',$entry[2])
 Set-Event '0x0194' $entry[0] $action.OuterXml
}
# Compare the complete profile with only these five changes reversed.
$check=$doc.CloneNode($true)
foreach($entry in @(@('0x025C',13),@('0x0194',55),@('0x0194',56),@('0x0194',58),@('0x0194',59))){
 $xpath='//s:Device[@ProductID="'+$entry[0]+'"] /s:DevicePage/s:Events/s:Event[@BoundTo="BUTTON_'+$entry[1]+'"]'
 $new=$check.SelectSingleNode($xpath,$m);$old=$before.SelectSingleNode($xpath,$m)
 if($old){[void]$new.ParentNode.ReplaceChild($check.ImportNode($old,$true),$new)}else{[void]$new.ParentNode.RemoveChild($new)}
}
if($check.OuterXml -ne $before.OuterXml){throw 'An unrelated binding changed; refusing to save'}
# Evaluate each actual pressure expression at both limits and a midrange value.
[void][Reflection.Assembly]::LoadFrom('C:\Program Files\SPAD.neXt\NCalcLib.dll')
foreach($entry in $bindings){$reference='['+$entry[1]+']';$samples=@(150,1000,2000);$minimum=150;$maximum=2000;if($entry[1] -like '*Goal'){$samples=@(-1000,5000,15000);$minimum=-1000;$maximum=15000};foreach($sample in $samples){$expression=New-Object NCalc.Expression($entry[2].Replace($reference,[string]$sample));$result=[double]$expression.Evaluate();if($result -lt $minimum -or $result -gt $maximum){throw 'Pressure limit check failed'}}}
$doc.Save($path);Copy-Item -LiteralPath $path -Destination (Join-Path $PSScriptRoot 'profiles\Baron - GNS 530 + TDS GTNxi 650.xml');Copy-Item -LiteralPath $path -Destination (Join-Path $backup 'after.xml')
Write-Output "Verified: B13 external-view shortcut, E1 pressure rate and E2 cabin altitude; B8-B12, mixtures and every other binding unchanged. Backup: $backup"
