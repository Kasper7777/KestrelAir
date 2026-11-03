param([int]$Deflect=30,[switch]$InvertVertical,[int]$ClickButton=1,[switch]$DryRun,[string]$InstalledPath,[string]$WorkspacePath)
# Stick clicks (HID button 1 on each grip, read over raw HID 2026-11-03): right = left mouse button held at the centre of
# the sim window via SPAD "Run external program" (.tools\ka-click\ka-click-down.exe / -up.exe), i.e. the PlayStation Cross
# role of operating what is in the middle of the view; left = Shift+Space, MSFS's view reset in every camera context.
$clickTool=Join-Path $PSScriptRoot '.tools\ka-click'
# WarBRD MiniSticks as PlayStation sticks, entirely inside SPAD: while a stick is deflected SPAD holds the MSFS keyboard key
# that the DualSense stick maps to (arrows = look in cockpit / external / on foot; W A S D = walk on foot), and releases it at
# centre. MSFS applies its own keyboard context, so nothing is sent to the sim through SimConnect. The previous SimConnect
# AXIS_PC_* events crashed MSFS 2024 (0xc0000005, three times on 2026-11-02/03); they are removed here.
# Axis "VALUE" events expose the value that raised them as EVENT:VALUE (SPAD changelog 0.9.13.34 / 0.9.16).
$ErrorActionPreference='Stop'
$name='Baron - GNS 530 + TDS GTNxi 650.xml'
if(!$InstalledPath){$InstalledPath=Join-Path $env:USERPROFILE ('Documents\SPAD.neXt\profiles\'+$name)}
if(!$WorkspacePath){$WorkspacePath=Join-Path $PSScriptRoot ('profiles\'+$name)}
if(!$DryRun -and (Get-Process SPAD.neXt -ErrorAction SilentlyContinue)){throw 'Exit SPAD.neXt first; it rewrites the profile when it closes.'}
$ns='http://www.fsgs.com/SPAD'
# EVENT:VALUE carries the raw device value for these axes (0..60000, rest 30000 measured over HID; the 20/80 % thresholds
# of the first attempt matched "Greater 80" permanently and held Right/Down/D/S, spad.log 2026-11-03 00:22-00:27).
$rawMax=60000
$low=[int](($rawMax/100)*(50-$Deflect));$high=[int](($rawMax/100)*(50+$Deflect))
# Device index 0 = right stick (cp2-and-flight-controls.md). Keys are System.Windows.Forms.Keys names.
# Pairs are (low raw value, high raw value). Pushing these MiniSticks up raises RY (live check 2026-11-03), so low = down.
$plan=@{
 0=@{RX_AXIS=@('Left','Right');RY_AXIS=@('Down','Up')}
 1=@{RX_AXIS=@('A','D');RY_AXIS=@('S','W')}
}
if($InvertVertical){foreach($i in 0,1){$plan[$i].RY_AXIS=@($plan[$i].RY_AXIS[1],$plan[$i].RY_AXIS[0])}}
function KeyAction($mode,$keys,$duration=80){
 '<EventActionKeyboard MacroType="'+$mode+'" TargetWindow="__ACTIVEWINDOW__"><KeyboardMacro Duration="'+$duration+'" Repeat="1" Pause="25"><Keys>'+(($keys | ForEach-Object { '<Keys>'+$_+'</Keys>' }) -join '')+'</Keys></KeyboardMacro></EventActionKeyboard>'
}
function Cond($comparator,$value,$source='EVENT:VALUE'){'<EventCondition ConditionComparator="'+$comparator+'" ConditionTargetValue="'+$value+'" ConditionValueSource="'+$source+'" />'}
function AxisXml($lowKey,$highKey,$state){
 # Below the deflection threshold hold the low key, above it hold the high key, in the middle release both.
 # A profile variable remembers the current zone (-1/0/1) so keys are only sent when the zone changes: the MiniStick
 # jitters at rest on every HID report, and firing two 80 ms keyboard macros per report (3422/min, spad.log 00:54)
 # backed up SPAD's workers and lagged every other control.
 $set={param($v)'<EventActionChangeValue TargetDataDefinition="'+$state+'" Value="'+$v+'" />'}
 '<EventDefinitions xmlns="'+$ns+'">'+
 '<EventDefinition Trigger="VALUE"><EventConditions>'+(Cond 'Less' $low)+(Cond 'Unequal' -1 $state)+'</EventConditions><EventActions>'+(& $set -1)+(KeyAction 'RELEASE' $highKey 20)+(KeyAction 'PRESS' $lowKey 20)+'</EventActions></EventDefinition>'+
 '<EventDefinition Trigger="VALUE"><EventConditions>'+(Cond 'Greater' $high)+(Cond 'Unequal' 1 $state)+'</EventConditions><EventActions>'+(& $set 1)+(KeyAction 'RELEASE' $lowKey 20)+(KeyAction 'PRESS' $highKey 20)+'</EventActions></EventDefinition>'+
 '<EventDefinition Trigger="VALUE"><EventConditions>'+(Cond 'GreaterOrEqual' $low)+(Cond 'LessOrEqual' $high)+(Cond 'Unequal' 0 $state)+'</EventConditions><EventActions>'+(& $set 0)+(KeyAction 'RELEASE' $lowKey 20)+(KeyAction 'RELEASE' $highKey 20)+'</EventActions></EventDefinition>'+
 '</EventDefinitions>'
}
$backup=Join-Path $PSScriptRoot ('backups\thumbstick-keys-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
if(!$DryRun){[void](New-Item -ItemType Directory $backup)}
foreach($file in $InstalledPath,$WorkspacePath){
 $label=if($file -eq $WorkspacePath){'workspace'}else{'installed'}
 $doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($file)
 $m=New-Object Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
 $before=$doc.CloneNode($true)
 $touched=0
 foreach($index in 0,1){
  $dev=$doc.SelectSingleNode('//s:Device[@VendorID="0x3344" and @ProductID="0x03F5" and @DeviceIndex="'+$index+'"]',$m)
  if(!$dev){throw "Stick $index missing in $label profile"}
  $events=$dev.SelectSingleNode('s:DevicePage[@IsDefaultPage="true"]/s:Events',$m)
  foreach($axis in 'RX_AXIS','RY_AXIS'){
   foreach($old in @($events.SelectNodes('s:Event[@BoundTo="'+$axis+'"]',$m))){[void]$events.RemoveChild($old)}
   $state='PROFILE:KA_STICK'+$index+'_'+$axis.Substring(0,2)
   $vars=$doc.SelectSingleNode('/s:Profile/s:Variables',$m)
   if(!$vars.SelectSingleNode('s:Variable[@Name="'+$state+'"]',$m)){
    $v=$doc.CreateElement('Variable',$ns);$v.SetAttribute('Name',$state);$v.SetAttribute('Value','0');$v.SetAttribute('ValueType','Decimal');[void]$vars.AppendChild($v)}
   $e=$doc.CreateElement('Event',$ns);$e.SetAttribute('BoundTo',$axis);[void]$events.AppendChild($e)
   $e.InnerXml=AxisXml $plan[$index].$axis[0] $plan[$index].$axis[1] $state
   $touched++
  }
  if($ClickButton){
   $bound='BUTTON_'+$ClickButton
   foreach($old in @($events.SelectNodes('s:Event[@BoundTo="'+$bound+'"]',$m))){
    if($old.SelectNodes('.//s:EventActionCommand[@CommandName="SPAD_neXt.RunProgram" or s:Parameter/@Value="SPAD_neXt.RunProgram"]|.//s:Keys[s:Keys="Space"]',$m).Count -eq 0){throw "Stick $index $bound already has an unrelated assignment"}
    [void]$events.RemoveChild($old)}
   $e=$doc.CreateElement('Event',$ns);$e.SetAttribute('BoundTo',$bound);[void]$events.AppendChild($e)
   if($index -eq 0){
    foreach($n in 'ka-click-down.exe','ka-click-up.exe'){if(!(Test-Path (Join-Path $clickTool $n))){throw "Missing $n; compile .tools\ka-click\ka-click.cs first"}}
    # SPAD's own serialized form (seen after it re-saved the profile): command name in Parameter, executable in Parameter1.
    $run={param($exe)'<EventActionCommand><Parameter Value="SPAD_neXt.RunProgram" /><Parameter1 Value="'+[Security.SecurityElement]::Escape((Join-Path $clickTool $exe))+'" /></EventActionCommand>'}
    $e.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions>'+(& $run 'ka-click-down.exe')+'</EventActions></EventDefinition><EventDefinition Trigger="RELEASE"><EventActions>'+(& $run 'ka-click-up.exe')+'</EventActions></EventDefinition></EventDefinitions>'
   }else{
    $e.InnerXml='<EventDefinitions xmlns="'+$ns+'"><EventDefinition Trigger="PRESS"><EventActions>'+(KeyAction 'PRESSANDRELEASE' @('LShiftKey','Space'))+'</EventActions></EventDefinition></EventDefinitions>'
   }
   $touched++
  }
 }
 # Everything outside the replaced stick events must be byte-identical.
 $strip={param($d)$c=$d.CloneNode($true);$mm=New-Object Xml.XmlNamespaceManager($c.NameTable);$mm.AddNamespace('s',$ns)
  foreach($x in @($c.SelectNodes('//s:Device[@ProductID="0x03F5"]//s:Event[@BoundTo="RX_AXIS" or @BoundTo="RY_AXIS"'+$(if($ClickButton){' or @BoundTo="BUTTON_'+$ClickButton+'"'})+']|/s:Profile/s:Variables/s:Variable[starts-with(@Name,"PROFILE:KA_STICK")]',$mm))){[void]$x.ParentNode.RemoveChild($x)};$c.OuterXml}
 if((& $strip $doc) -ne (& $strip $before)){throw "Unrelated change detected in $label profile"}
 if($doc.SelectNodes('//s:Device[@ProductID="0x03F5"]//s:EventActionCustomAxis',$m).Count){throw 'SimConnect on-foot axis actions still present'}
 if($DryRun){$doc.Save((Join-Path $PSScriptRoot ('thumbstick-keys-dryrun-'+$label+'.xml')));Write-Output "Dry run: $touched stick events written to thumbstick-keys-dryrun-$label.xml";continue}
 Copy-Item -LiteralPath $file -Destination (Join-Path $backup "$label-before.xml")
 $doc.Save($file)
 Write-Output "$label profile: replaced $touched stick events ($file)"
}
if(!$DryRun){Write-Output "Backup=$backup"}
