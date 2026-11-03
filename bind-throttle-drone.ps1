param([switch]$Apply)
$ErrorActionPreference='Stop'
if($Apply -and (Get-Process SPAD.neXt -ErrorAction SilentlyContinue)){throw 'Exit SPAD before applying'}
$name='Baron - GNS 530 + TDS GTNxi 650.xml'
$files=@((Join-Path $env:USERPROFILE ('Documents\SPAD.neXt\profiles\'+$name)),(Join-Path $PSScriptRoot ('profiles\'+$name)))
$backup=Join-Path $PSScriptRoot ('backups\throttle-drone-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
$prepared=@()
foreach($file in $files){
 $doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($file);$before=$doc.CloneNode($true)
 $ns='http://www.fsgs.com/SPAD';$m=New-Object Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
 # Current firmware has unshifted B1-B6 at logical inputs 42-47; B4 is input 45.
 $base='//s:Device[@VendorID="0x3344" and @ProductID="0x0194"]/s:DevicePage[@IsDefaultPage="true"]/s:Events'
 $events=$doc.SelectSingleNode($base,$m);if(!$events){throw 'Throttle missing'}
 $path=$base+'/s:Event[@BoundTo="BUTTON_45"]'
 $e=$doc.SelectSingleNode($path,$m)
 if(!$e){$e=$doc.CreateElement('Event',$ns);$e.SetAttribute('BoundTo','BUTTON_45');[void]$events.AppendChild($e)}
 $e.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions><EventActionKeyboard MacroType="PRESSANDRELEASE" TargetWindow="__ACTIVEWINDOW__"><KeyboardMacro Duration="80" Repeat="1" Pause="25"><Keys><Keys>LShiftKey</Keys><Keys>X</Keys></Keys></KeyboardMacro></EventActionKeyboard></EventActions></EventDefinition></EventDefinitions>'
 $check=$doc.CloneNode($true);$baseline=$before.CloneNode($true)
 foreach($x in $check,$baseline){$n=$x.SelectSingleNode($path,$m);if($n){[void]$n.ParentNode.RemoveChild($n)}}
 if($check.OuterXml -ne $baseline.OuterXml){throw 'Unrelated profile change'}
 $prepared+=@{Path=$file;Doc=$doc}
}
if($Apply){
 [void](New-Item -ItemType Directory $backup)
 for($i=0;$i -lt $prepared.Count;$i++){
  Copy-Item -LiteralPath $prepared[$i].Path -Destination (Join-Path $backup ('before-'+$i+'.xml'))
  $prepared[$i].Doc.Save($prepared[$i].Path)
 }
}
Write-Output "Verified B4/input 45: one Shift+X on press, no release toggle; unrelated XML preserved. Applied=$Apply Backup=$backup"
