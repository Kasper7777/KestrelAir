$ErrorActionPreference='Stop'
if(Get-Process SPAD.neXt -ErrorAction SilentlyContinue){throw 'Stop SPAD before editing'}
$name='Baron - GNS 530 + TDS GTNxi 650.xml'
$installed=Join-Path $env:USERPROFILE ('Documents\SPAD.neXt\profiles\'+$name)
$workspace=Join-Path $PSScriptRoot ('profiles\'+$name)
$backup=Join-Path $PSScriptRoot ('backups\onfoot-thumbsticks-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
[void](New-Item -ItemType Directory $backup)
Copy-Item -LiteralPath $installed -Destination (Join-Path $backup 'installed.xml')
Copy-Item -LiteralPath $workspace -Destination (Join-Path $backup 'workspace.xml')
$ns='http://www.fsgs.com/SPAD';$doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($installed);$before=$doc.CloneNode($true)
$m=New-Object Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
foreach($index in 0,1){
 $base='//s:Device[@VendorID="0x3344" and @ProductID="0x03F5" and @DeviceIndex="'+$index+'"]/s:DevicePage[@IsDefaultPage="true"]/s:Events'
 $events=$doc.SelectSingleNode($base,$m);if(!$events){throw "Missing stick $index"}
 foreach($axis in 'RX_AXIS','RY_AXIS'){
  if($events.SelectSingleNode('s:Event[@BoundTo="'+$axis+'"]',$m)){throw "Axis already assigned: $index $axis"}
  # SDK: movement X=strafe/Z=forward; FPV rotation X=pitch/Y=yaw.
  if($index -eq 1){$target=if($axis -eq 'RX_AXIS'){'AXIS_PC_MOVE_X'}else{'AXIS_PC_MOVE_Z'}}else{$target=if($axis -eq 'RX_AXIS'){'AXIS_PC_FPV_ROTATION_Y'}else{'AXIS_PC_FPV_ROTATION_X'}}
  $invert=if($axis -eq 'RY_AXIS'){'True'}else{'False'}
  $e=$doc.CreateElement('Event',$ns);$e.SetAttribute('BoundTo',$axis);[void]$events.AppendChild($e)
  $parts=@()
  foreach($range in @(@(0,45,-16383,0),@(45,55,0,0),@(55,100,0,16383))){
   $parts+='<EventActionCustomAxis TargetDataDefinition="SIMCONNECT:'+$target+'" Value="0"><Options><Option Key="ALWAYSACTIVE" Value="False" /><Option Key="RANGEFROM" Value="'+$range[0]+'" /><Option Key="RANGETO" Value="'+$range[1]+'" /><Option Key="USETRIGGERVALUE" Value="True" /><Option Key="USEMAPPING" Value="True" /><Option Key="MAPFROM" Value="'+$range[2]+'" /><Option Key="MAPTO" Value="'+$range[3]+'" /><Option Key="USERAWVALUE" Value="False" /><Option Key="INVERTAXIS" Value="'+$invert+'" /></Options></EventActionCustomAxis>'
  }
  $e.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="VALUE"><EventActions>'+($parts -join '')+'</EventActions></EventDefinition></EventDefinitions>'
 }
}
$check=$doc.CloneNode($true)
foreach($e in @($check.SelectNodes('//s:Device[@ProductID="0x03F5"]//s:Event[@BoundTo="RX_AXIS" or @BoundTo="RY_AXIS"]',$m))){[void]$e.ParentNode.RemoveChild($e)}
if($check.OuterXml -ne $before.OuterXml){throw 'Unrelated change detected'}
$doc.Save($installed);$doc.Save($workspace);$doc.Save((Join-Path $backup 'after.xml'))
Write-Output "Added four analog thumbstick axes only. Backup=$backup"
