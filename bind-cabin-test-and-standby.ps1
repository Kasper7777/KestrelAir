$ErrorActionPreference='Stop'
if(Get-Process SPAD.neXt -ErrorAction SilentlyContinue){throw 'Stop SPAD before editing its profile'}
$name='Baron - GNS 530 + TDS GTNxi 650.xml'
$installed=Join-Path $env:USERPROFILE ('Documents\SPAD.neXt\profiles\'+$name)
$workspace=Join-Path $PSScriptRoot ('profiles\'+$name)
$ns='http://www.fsgs.com/SPAD';$doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($installed);$before=$doc.CloneNode($true)
$m=New-Object Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
$base='//s:Device[@VendorID="0x3344" and @ProductID="0x025A"]/s:DevicePage[@IsDefaultPage="true"]/s:Events'
$events=$doc.SelectSingleNode($base,$m);if(!$events){throw 'CP2 device missing'}
foreach($entry in @(@(39,'var_pressurizationTest'),@(40,'var_doorSealStandbyInflate'))){
 $path=$base+'/s:Event[@BoundTo="BUTTON_'+$entry[0]+'"]'
 $e=$doc.SelectSingleNode($path,$m)
 $allowed=@(('LVAR:'+$entry[1]),('LVAR:'+$entry[1]+'_IsDown'))
 if($e){foreach($a in $e.SelectNodes('.//s:EventActions/*',$m)){if($a.LocalName -ne 'EventActionChangeValue' -or $a.GetAttribute('TargetDataDefinition') -notin $allowed){throw 'Existing CP2 button contains an unrelated action'}}}
 else{$e=$doc.CreateElement('Event',$ns);$e.SetAttribute('BoundTo',('BUTTON_'+$entry[0]));[void]$events.AppendChild($e)}
 $e.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions><EventActionChangeValue TargetDataDefinition="LVAR:'+$entry[1]+'_IsDown" Value="1" /><EventActionChangeValue TargetDataDefinition="LVAR:'+$entry[1]+'" Value="1" /></EventActions></EventDefinition><EventDefinition Trigger="RELEASE"><EventActions><EventActionChangeValue TargetDataDefinition="LVAR:'+$entry[1]+'_IsDown" Value="0" /><EventActionChangeValue TargetDataDefinition="LVAR:'+$entry[1]+'" Value="0" /></EventActions></EventDefinition></EventDefinitions>'
}
$check=$doc.CloneNode($true);$baseline=$before.CloneNode($true)
foreach($button in 39,40){foreach($x in $check,$baseline){$e=$x.SelectSingleNode(($base+'/s:Event[@BoundTo="BUTTON_'+$button+'"]'),$m);if($e){[void]$e.ParentNode.RemoveChild($e)}}}
if($check.OuterXml -ne $baseline.OuterXml){throw 'Unrelated profile change detected'}
$backup=Join-Path $PSScriptRoot ('backups\cabin-test-standby-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
[void](New-Item -ItemType Directory $backup)
Copy-Item -LiteralPath $installed -Destination (Join-Path $backup 'installed.xml')
Copy-Item -LiteralPath $workspace -Destination (Join-Path $backup 'workspace.xml')
$doc.Save($installed);$doc.Save($workspace);$doc.Save((Join-Path $backup 'after.xml'))
Write-Output "Verified CP2 B7 pressure test/B8 standby inflate: PRESS=1, RELEASE=0; all other XML preserved. Backup=$backup"
