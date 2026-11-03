param([switch]$Apply)
$ErrorActionPreference='Stop'
if($Apply -and (Get-Process SPAD.neXt,FlightSimulator2024 -ErrorAction SilentlyContinue)){throw 'Close MSFS and SPAD before applying'}
$remote='C:\Program Files (x86)\Steam\userdata\86580337\2537590\remote'
$backup=Join-Path $PSScriptRoot ('backups\dji-thumbsticks-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
$changes=@()
foreach($f in Get-ChildItem -LiteralPath $remote -Filter 'inputprofile_*'){
 $raw=[IO.File]::ReadAllText($f.FullName)
 [xml]$doc='<Root>'+($raw -replace '<\?xml[^>]*\?>','')+'</Root>'
 $dev=$doc.Root.Device
 if($dev.DeviceName -notin @('Left VPC WarBRD-D Base','Right VPC WarBRD-D Base') -or $doc.Root.FriendlyName.InnerText -notlike '*general*'){continue}
 # Native drone-context assignments: rX/rY are the grip MiniStick axes.
 # Existing native profiles confirm input IDs 770/786; Flag 4 is an axis.
 $plan=if($dev.DeviceName -like 'Left*'){@(@('DRONE_AXIS_ROTATION_Y',770,'X'),@('DRONE_AXIS_TRANSLATION_Y',786,'Y'))}else{@(@('DRONE_AXIS_TRANSLATION_X',770,'X'),@('DRONE_AXIS_TRANSLATION_Z',786,'Y'))}
 $patched=$raw
 foreach($entry in $plan){
  $action=$doc.SelectSingleNode('//Context[@ContextName="DRONE_GLOBAL"]/Action[@ActionName="'+$entry[0]+'"]')
  if(!$action -or $action.HasChildNodes){throw "Expected unused drone axis missing or assigned: $($f.Name) $($entry[0])"}
  $pattern='<Action\b[^>]*ActionName="'+$entry[0]+'"[^>]*/>'
  if([regex]::Matches($patched,$pattern).Count -ne 1){throw 'Ambiguous native action'}
  $new=$action.CloneNode($true);$new.SetAttribute('Flag','4')
  $primary=$doc.CreateElement('Primary');$key=$doc.CreateElement('KEY');$key.SetAttribute('Information',('Joystick R-Axis '+$entry[2]+' '));$key.InnerText=[string]$entry[1];[void]$primary.AppendChild($key);[void]$new.AppendChild($primary)
  $patched=[regex]::Replace($patched,$pattern,$new.OuterXml)
 }
 # Reverse just the two action edits and compare the complete original bytes.
 $check=$patched
 foreach($entry in $plan){$original=$doc.SelectSingleNode('//Action[@ActionName="'+$entry[0]+'"]');$pattern='<Action\b[^>]*ActionName="'+$entry[0]+'"[^>]*>.*?</Action>';$sourcePattern='<Action\b[^>]*ActionName="'+$entry[0]+'"[^>]*/>';$source=[regex]::Match($raw,$sourcePattern).Value;$check=[regex]::Replace($check,$pattern,$source)}
 if($check -cne $raw){throw 'Unrelated native profile change'}
 $changes+=@{Path=$f.FullName;Content=$patched;Name=$f.Name}
}
if($changes.Count -ne 3){throw "Expected three current WarBRD general profiles; found $($changes.Count)"}
$ns='http://www.fsgs.com/SPAD';$name='Baron - GNS 530 + TDS GTNxi 650.xml'
foreach($file in @((Join-Path $env:USERPROFILE ('Documents\SPAD.neXt\profiles\'+$name)),(Join-Path $PSScriptRoot ('profiles\'+$name)))){
 $doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($file);$before=$doc.CloneNode($true)
 $m=New-Object Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
 $xpath='//s:Device[@ProductID="0x03F5"]//s:Event[@BoundTo="RX_AXIS" or @BoundTo="RY_AXIS"]'
 $axes=$doc.SelectNodes($xpath,$m);if($axes.Count -ne 4){throw 'Expected four thumbstick axes'}
 foreach($axis in $axes){
  $definitions=$axis.SelectSingleNode('s:EventDefinitions',$m)
  foreach($definition in $definitions.SelectNodes('s:EventDefinition',$m)){
   $condition=$doc.CreateElement('EventCondition',$ns);$condition.SetAttribute('ConditionComparator','Unequal');$condition.SetAttribute('ConditionTargetValue','4');$condition.SetAttribute('ConditionValueSource','SIMCONNECT:CAMERA STATE');[void]$definition.SelectSingleNode('s:EventConditions',$m).AppendChild($condition)
  }
  $center=$definitions.SelectNodes('s:EventDefinition',$m)[2].CloneNode($true)
  $conditions=$center.SelectSingleNode('s:EventConditions',$m)
  foreach($condition in @($conditions.SelectNodes('s:EventCondition',$m))){if($condition.GetAttribute('ConditionValueSource') -eq 'EVENT:VALUE'){[void]$conditions.RemoveChild($condition)}}
  $camera=$conditions.SelectSingleNode('s:EventCondition[@ConditionValueSource="SIMCONNECT:CAMERA STATE"]',$m);$camera.SetAttribute('ConditionComparator','Equals')
  [void]$definitions.AppendChild($center)
 }
 $check=$doc.CloneNode($true);$baseline=$before.CloneNode($true)
 foreach($x in $check,$baseline){foreach($node in @($x.SelectNodes($xpath,$m))){[void]$node.ParentNode.RemoveChild($node)}}
 if($check.OuterXml -cne $baseline.OuterXml){throw 'Unrelated SPAD profile change'}
 # Validate comparator spellings against the installed SPAD enum, not just XML syntax.
 $interfaces=[Reflection.Assembly]::LoadFrom('C:\Program Files\SPAD.neXt\SPAD.Interfaces.dll')
 $comparatorType=$interfaces.GetTypes() | Where-Object Name -eq 'SPADEventValueComparator'
 $validComparators=[Enum]::GetNames($comparatorType)
 foreach($condition in $doc.SelectNodes('//s:EventCondition[@ConditionComparator]',$m)){
  if($condition.GetAttribute('ConditionComparator') -cnotin $validComparators){throw ('Invalid SPAD comparator: '+$condition.GetAttribute('ConditionComparator'))}
 }
 $changes+=@{Path=$file;Content=$doc.OuterXml;Name=('spad-'+$changes.Count+'.xml')}
}
if($Apply){
 [void](New-Item -ItemType Directory $backup)
 foreach($change in $changes){Copy-Item -LiteralPath $change.Path -Destination (Join-Path $backup $change.Name)}
 foreach($change in $changes){[IO.File]::WriteAllText($change.Path,$change.Content,(New-Object Text.UTF8Encoding($false)))}
}
Write-Output "Verified three native drone profiles, four SPAD drone exclusions and release branches; unrelated content preserved. Applied=$Apply Backup=$backup"
