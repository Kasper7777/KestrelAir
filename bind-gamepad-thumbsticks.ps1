param([int]$RightClickButton=0,[int]$LeftClickButton=0,[switch]$DetectClicks)
# WarBRD MiniSticks behave like DualSense sticks: left = walk / cockpit head slide / drone move, right = look / camera / drone rotate, right click = view reset.
# Bindings are native MSFS context actions (copied from Asobo's Dualsense_2024_Transversal.xml), replacing SPAD's SimConnect
# AXIS_PC_* events, which MSFS 2024 receives outside on-foot mode and which crashed it (0xc0000005, 2026-11-02 23:15 and 23:38).
$ErrorActionPreference='Stop'
if(Get-Process FlightSimulator2024,FlightSimulator -ErrorAction SilentlyContinue){throw 'Exit MSFS normally before running.'}
$remote='C:\Program Files (x86)\Steam\userdata\86580337\2537590\remote'
$spadName='Baron - GNS 530 + TDS GTNxi 650.xml'
$spadFiles=@((Join-Path $env:USERPROFILE ('Documents\SPAD.neXt\profiles\'+$spadName)),(Join-Path $PSScriptRoot ('profiles\'+$spadName)))
$ns='http://www.fsgs.com/SPAD'
$backup=Join-Path $PSScriptRoot ('backups\gamepad-thumbsticks-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
[void](New-Item -ItemType Directory $backup)

# 1. Remove the crashing SPAD MiniStick axes (RX/RY on both WarBRD bases); leave every other SPAD event untouched.
$stickPaths=@()
foreach($file in $spadFiles){
 $label=if($file -like "$PSScriptRoot*"){'workspace'}else{'installed'}
 $doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($file)
 $m=New-Object Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
 $stickPaths+=@($doc.SelectNodes('//s:Device[@ProductID="0x03F5"]',$m) | ForEach-Object { $_.DevicePath })
 $axes=@($doc.SelectNodes('//s:Device[@ProductID="0x03F5"]//s:Event[@BoundTo="RX_AXIS" or @BoundTo="RY_AXIS"]',$m))
 if(!$axes.Count){Write-Output "SPAD MiniStick axes already removed: $file";continue}
 if(Get-Process SPAD.neXt -ErrorAction SilentlyContinue){throw 'Stop SPAD before editing (it overwrites the profile on exit).'}
 Copy-Item -LiteralPath $file -Destination (Join-Path $backup "spad-$label.xml")
 $others=@($doc.SelectNodes('//s:Event',$m) | Where-Object { $axes -notcontains $_ } | ForEach-Object { $_.OuterXml })
 foreach($e in $axes){[void]$e.ParentNode.RemoveChild($e)}
 $after=@($doc.SelectNodes('//s:Event',$m) | ForEach-Object { $_.OuterXml })
 if(($others -join "`n") -ne ($after -join "`n")){throw "Unrelated SPAD change detected: $file"}
 $doc.Save($file)
 Write-Output "Removed $($axes.Count) SPAD MiniStick axis events: $file"
}

# 2. Optionally capture the MiniStick click buttons from raw HID (works while SPAD is running).
if($DetectClicks){
Add-Type @'
using System;using System.Collections.Generic;using System.IO;using System.Runtime.InteropServices;using System.Threading.Tasks;using Microsoft.Win32.SafeHandles;
public static class KAThumbClick {
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern SafeFileHandle CreateFile(string n,uint a,uint s,IntPtr p,uint c,uint f,IntPtr t);
 [DllImport("hid.dll")]static extern bool HidD_GetPreparsedData(SafeFileHandle h,out IntPtr p);
 [DllImport("hid.dll")]static extern bool HidD_FreePreparsedData(IntPtr p);
 [DllImport("hid.dll")]static extern int HidP_GetCaps(IntPtr p,IntPtr caps);
 [DllImport("hid.dll")]static extern int HidP_GetUsages(int type,ushort page,ushort link,[Out]ushort[] usages,ref uint count,IntPtr p,byte[] report,uint length);
 // Returns the first button (HID usage = DirectInput/MSFS button number) newly pressed on any device, or 0 on timeout.
 public static int WaitForPress(string[] paths,int seconds){
  int n=paths.Length;var handles=new SafeFileHandle[n];var data=new IntPtr[n];var streams=new FileStream[n];var lengths=new int[n];var buffers=new byte[n][];var reads=new Task<int>[n];var held=new HashSet<ushort>[n];
  try{
   for(int i=0;i<n;i++){handles[i]=CreateFile(paths[i],0x80000000,3,IntPtr.Zero,3,0x40000000,IntPtr.Zero);if(handles[i].IsInvalid)throw new Exception("HID open "+paths[i]+": "+Marshal.GetLastWin32Error());
    if(!HidD_GetPreparsedData(handles[i],out data[i]))throw new Exception("No HID descriptor: "+paths[i]);IntPtr caps=Marshal.AllocHGlobal(64);try{HidP_GetCaps(data[i],caps);lengths[i]=(ushort)Marshal.ReadInt16(caps,4);}finally{Marshal.FreeHGlobal(caps);}
    streams[i]=new FileStream(handles[i],FileAccess.Read,4096,true);buffers[i]=new byte[lengths[i]];reads[i]=streams[i].ReadAsync(buffers[i],0,lengths[i]);}
   var until=DateTime.UtcNow.AddSeconds(seconds);
   while(DateTime.UtcNow<until){int i=Task.WaitAny(reads,100);if(i<0)continue;
    var usages=new ushort[128];uint count=128;
    if(HidP_GetUsages(0,9,0,usages,ref count,data[i],buffers[i],(uint)reads[i].Result)==0x00110000){
     var now=new HashSet<ushort>();for(int k=0;k<count;k++)now.Add(usages[k]);
     if(held[i]!=null)foreach(var u in now)if(!held[i].Contains(u))return u;
     held[i]=now;}
    buffers[i]=new byte[lengths[i]];reads[i]=streams[i].ReadAsync(buffers[i],0,lengths[i]);}
   return 0;
  }finally{for(int i=0;i<n;i++){if(streams[i]!=null)streams[i].Dispose();if(data[i]!=IntPtr.Zero)HidD_FreePreparsedData(data[i]);if(handles[i]!=null)handles[i].Dispose();}}
 }
}
'@
 $paths=[string[]]@($stickPaths | Sort-Object -Unique)
 foreach($side in 'RIGHT','LEFT'){
  Write-Host "Click (press straight down) the $side thumbstick within 20 seconds; touch nothing else."
  $button=[KAThumbClick]::WaitForPress($paths,20)
  if(!$button){throw "No $side thumbstick click detected."}
  Write-Host "$side thumbstick click = Joystick Button $button"
  if($side -eq 'RIGHT'){$RightClickButton=$button}else{$LeftClickButton=$button}
 }
}

# 3. Native MSFS bindings, flags and directions as in Asobo's DualSense defaults (RANALOG_* / LANALOG_* -> MiniStick R-Axis).
$xm=@('Joystick R-Axis X -',768);$xp=@('Joystick R-Axis X +',769);$ym=@('Joystick R-Axis Y -',784);$yp=@('Joystick R-Axis Y +',785)
$x=@('Joystick R-Axis X ',770);$y=@('Joystick R-Axis Y ',786)
function B($context,$action,$flag,$key){[pscustomobject]@{Context=$context;Action=$action;Flag=$flag;Key=$key}}
$right=@(
 (B COCKPIT_GLOBAL_CAMERA KEY_COCKPIT_LOOK_LEFT 1 $xm),(B COCKPIT_GLOBAL_CAMERA KEY_COCKPIT_LOOK_RIGHT 1 $xp),
 (B COCKPIT_GLOBAL_CAMERA KEY_COCKPIT_LOOK_UP 1 $ym),(B COCKPIT_GLOBAL_CAMERA KEY_COCKPIT_LOOK_DOWN 1 $yp),
 (B EXTERNAL_CAMERA KEY_CHASE_LOOK_RIGHT 1 $xm),(B EXTERNAL_CAMERA KEY_CHASE_LOOK_LEFT 1 $xp),
 (B EXTERNAL_CAMERA KEY_CHASE_LOOK_DOWN 1 $ym),(B EXTERNAL_CAMERA KEY_CHASE_LOOK_UP 1 $yp),
 (B PLAYER_CHARACTER_FPV KEY_AXIS_PC_FPV_ROTATION_X 4100 $x),(B PLAYER_CHARACTER_FPV KEY_AXIS_PC_FPV_ROTATION_Y 4228 $y),
 (B DRONE_GLOBAL DRONE_AXIS_ROTATION_Y 4 $x),(B DRONE_GLOBAL DRONE_AXIS_ROTATION_X 132 $y))
$left=@(
 (B PLAYER_CHARACTER_MOVEMENT KEY_PC_MOVE_LEFT 1 $xm),(B PLAYER_CHARACTER_MOVEMENT KEY_PC_MOVE_RIGHT 1 $xp),
 (B PLAYER_CHARACTER_MOVEMENT KEY_PC_MOVE_FORWARD 1 $ym),(B PLAYER_CHARACTER_MOVEMENT KEY_PC_MOVE_BACKWARD 1 $yp),
 (B COCKPIT_GLOBAL_CAMERA_TRANSLATE KEY_COCKPIT_CAMERA_SLIDE_LEFT_LOCKABLE 1 $xm),(B COCKPIT_GLOBAL_CAMERA_TRANSLATE KEY_COCKPIT_CAMERA_SLIDE_RIGHT_LOCKABLE 1 $xp),
 (B COCKPIT_GLOBAL_CAMERA_TRANSLATE KEY_COCKPIT_CAMERA_SLIDE_FRONT_LOCKABLE 1 $ym),(B COCKPIT_GLOBAL_CAMERA_TRANSLATE KEY_COCKPIT_CAMERA_SLIDE_BACK_LOCKABLE 1 $yp),
 (B DRONE_GLOBAL DRONE_AXIS_TRANSLATION_X 4 $x),(B DRONE_GLOBAL DRONE_AXIS_TRANSLATION_Z 4 $y))
if($RightClickButton){$r3=@("Joystick Button $RightClickButton",($RightClickButton-1));$right+=@(
 (B MODES KEY_COCKPIT_RESET 8194 $r3),(B EXTERNAL_CAMERA KEY_CAMERACHASE_RESET 8194 $r3),
 (B PLAYER_CHARACTER_FPV KEY_PC_FPV_LOOK_RESET 2 $r3),(B DRONE_GLOBAL DRONE_RESET_HORIZON 8194 $r3))}
# DualSense L3 only toggles the gamepad assistance overlay, so the left click stays free unless a button is given.
if($LeftClickButton){Write-Output "Left thumbstick click (button $LeftClickButton) left unassigned, as on the DualSense in flight."}

function Parse($text){[xml]('<Root>'+($text -replace '<\?xml[^>]*\?>','')+'</Root>')}
$targets=@(Get-ChildItem -LiteralPath $remote -Filter 'inputprofile_*' | Where-Object {
 $t=[IO.File]::ReadAllText($_.FullName);$t -match 'DeviceName="(Right|Left) VPC WarBRD-D Base"' -and $t -match 'ContextName="PLAYER_CHARACTER_FPV"' })
if(!$targets.Count){throw 'No WarBRD general (camera/on-foot) MSFS profiles found.'}
$encoding=New-Object System.Text.UTF8Encoding($false)
foreach($file in $targets){
 $raw=[IO.File]::ReadAllText($file.FullName)
 $bindings=if($raw -match 'DeviceName="Right '){$right}else{$left}
 $nl=if($raw -match "`r`n"){"`r`n"}else{"`n"}
 $text=$raw
 foreach($b in $bindings){
  $ctx=[regex]::Match($text,'(?s)<Context ContextName="'+$b.Context+'"[^>]*>.*?</Context>')
  if(!$ctx.Success){throw "Missing context $($b.Context) in $($file.Name)"}
  $pattern='(?s)(?<indent>[ \t]*)<Action ActionName="'+$b.Action+'"(?<attrs>[^>]*?)\s*(?:/>|>.*?</Action>)'
  $act=[regex]::Match($ctx.Value,$pattern)
  if(!$act.Success){throw "Missing action $($b.Action) in $($file.Name)"}
  $i=$act.Groups['indent'].Value;$attrs=$act.Groups['attrs'].Value -replace 'Flag="[^"]*"',('Flag="'+$b.Flag+'"')
  $new=$i+'<Action ActionName="'+$b.Action+'"'+$attrs+">$nl$i`t<Primary>$nl$i`t`t<KEY Information=`""+$b.Key[0]+'">'+$b.Key[1]+"</KEY>$nl$i`t</Primary>$nl$i</Action>"
  $text=$text.Substring(0,$ctx.Index)+$ctx.Value.Substring(0,$act.Index)+$new+$ctx.Value.Substring($act.Index+$act.Length)+$text.Substring($ctx.Index+$ctx.Length)
 }
 # Verify: same action list, only the targeted actions changed, each with exactly its intended key.
 $before=Parse $raw;$after=Parse $text
 $ba=@($before.SelectNodes('//Context/Action'));$aa=@($after.SelectNodes('//Context/Action'))
 if($ba.Count -ne $aa.Count){throw "Action count changed: $($file.Name)"}
 for($k=0;$k -lt $ba.Count;$k++){
  $ctxName=$aa[$k].ParentNode.ContextName;$name=$aa[$k].ActionName
  if($ba[$k].ActionName -ne $name -or $ba[$k].ParentNode.ContextName -ne $ctxName){throw "Action order changed: $($file.Name)"}
  $b=$bindings | Where-Object { $_.Context -eq $ctxName -and $_.Action -eq $name }
  if($b){$keys=@($aa[$k].SelectNodes('Primary/KEY'));if($keys.Count -ne 1 -or $keys[0].InnerText -ne [string]$b.Key[1] -or $aa[$k].Flag -ne [string]$b.Flag){throw "Binding not applied: $name in $($file.Name)"}}
  elseif($ba[$k].OuterXml -ne $aa[$k].OuterXml){throw "Unrelated MSFS action changed: $ctxName/$name in $($file.Name)"}
 }
 if($text -eq $raw){Write-Output "Already bound: $($file.Name)";continue}
 Copy-Item -LiteralPath $file.FullName -Destination $backup
 [IO.File]::WriteAllText($file.FullName,$text,$encoding)
 Write-Output "Bound $($bindings.Count) MiniStick actions: $($file.Name) ($([regex]::Match($raw,'DeviceName="([^"]+)"').Groups[1].Value))"
}
if(Get-ChildItem -LiteralPath $backup){Write-Output "Backup=$backup"}else{Remove-Item -LiteralPath $backup}
