param([int]$X=-1,[int]$Y=-1,[string]$Text,[int]$Key=0)
Add-Type -AssemblyName System.Drawing,System.Windows.Forms
Add-Type @'
using System;using System.Runtime.InteropServices;public class KaPointer{
[DllImport("user32.dll")]public static extern bool SetProcessDPIAware();
[DllImport("user32.dll")]public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")]public static extern bool SetCursorPos(int x,int y);
[DllImport("user32.dll")]public static extern void mouse_event(uint f,uint x,uint y,uint d,UIntPtr e);
[DllImport("user32.dll")]public static extern void keybd_event(byte k,byte s,uint f,UIntPtr e);
[DllImport("user32.dll",CharSet=CharSet.Unicode)]public static extern short VkKeyScan(char c);
}
'@
[void][KaPointer]::SetProcessDPIAware()
[void][KaPointer]::SetForegroundWindow((Get-Process FlightSimulator2024).MainWindowHandle)
Start-Sleep -Milliseconds 250
if($X -ge 0){[void][KaPointer]::SetCursorPos($X,$Y);Start-Sleep -Milliseconds 80;[KaPointer]::mouse_event(2,0,0,0,[UIntPtr]::Zero);Start-Sleep -Milliseconds 120;[KaPointer]::mouse_event(4,0,0,0,[UIntPtr]::Zero)}
if($Text){
 [KaPointer]::keybd_event(17,0,0,[UIntPtr]::Zero);[KaPointer]::keybd_event(65,0,0,[UIntPtr]::Zero);Start-Sleep -Milliseconds 100;[KaPointer]::keybd_event(65,0,2,[UIntPtr]::Zero);[KaPointer]::keybd_event(17,0,2,[UIntPtr]::Zero);Start-Sleep -Milliseconds 200
 foreach($character in $Text.ToCharArray()){$vk=[byte]([KaPointer]::VkKeyScan($character) -band 255);[KaPointer]::keybd_event($vk,0,0,[UIntPtr]::Zero);Start-Sleep -Milliseconds 70;[KaPointer]::keybd_event($vk,0,2,[UIntPtr]::Zero);Start-Sleep -Milliseconds 100}
}
if($Key -eq 27){[Windows.Forms.SendKeys]::SendWait('{ESC}')}
elseif($Key -eq 13){[Windows.Forms.SendKeys]::SendWait('{ENTER}')}
elseif($Key){[KaPointer]::keybd_event($Key,0,0,[UIntPtr]::Zero);Start-Sleep -Milliseconds 100;[KaPointer]::keybd_event($Key,0,2,[UIntPtr]::Zero)}
Start-Sleep -Milliseconds 800
$b=New-Object Drawing.Bitmap(2560,1440);$g=[Drawing.Graphics]::FromImage($b);$g.CopyFromScreen(0,0,0,0,$b.Size);$b.Save((Join-Path $PSScriptRoot '..\sim-controls-screen.png'));$g.Dispose();$b.Dispose()
