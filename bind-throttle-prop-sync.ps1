$ErrorActionPreference='Stop'
if(Get-Process SPAD.neXt -ErrorAction SilentlyContinue){throw 'Stop SPAD before editing its profile'}
$name='Baron - GNS 530 + TDS GTNxi 650.xml'
$installed=Join-Path $env:USERPROFILE ('Documents\SPAD.neXt\profiles\'+$name)
$workspace=Join-Path $PSScriptRoot ('profiles\'+$name)
$backup=Join-Path $PSScriptRoot ('backups\throttle-prop-sync-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
[void](New-Item -ItemType Directory $backup)
Copy-Item -LiteralPath $installed -Destination (Join-Path $backup 'installed.xml')
Copy-Item -LiteralPath $workspace -Destination (Join-Path $backup 'workspace.xml')
$ns='http://www.fsgs.com/SPAD';$doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($installed);$before=$doc.CloneNode($true)
$m=New-Object Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
$base='//s:Device[@VendorID="0x3344" and @ProductID="0x0194"]/s:DevicePage[@IsDefaultPage="true"]/s:Events'
$events=$doc.SelectSingleNode($base,$m);if(!$events){throw 'Throttle device missing'}
foreach($entry in @(@(52,1),@(53,0))){
 $path=$base+'/s:Event[@BoundTo="BUTTON_'+$entry[0]+'"]'
 if($doc.SelectSingleNode($path,$m)){throw 'Expected unused T7 input already assigned'}
 $e=$doc.CreateElement('Event',$ns);$e.SetAttribute('BoundTo',('BUTTON_'+$entry[0]));[void]$events.AppendChild($e)
 $e.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions><EventActionChangeValue TargetDataDefinition="LVAR:var_PropSyncSwitch" Value="'+$entry[1]+'" /></EventActions></EventDefinition></EventDefinitions>'
}
$check=$doc.CloneNode($true)
foreach($button in 52,53){$e=$check.SelectSingleNode(($base+'/s:Event[@BoundTo="BUTTON_'+$button+'"]'),$m);[void]$e.ParentNode.RemoveChild($e)}
if($check.OuterXml -ne $before.OuterXml){throw 'Unrelated profile change detected'}
$doc.Save($installed);$doc.Save($workspace);$doc.Save((Join-Path $backup 'after.xml'))
Write-Output "Verified throttle T7: 52 prop sync ON, 53 OFF; PRESS only; all other XML unchanged. Backup=$backup"
