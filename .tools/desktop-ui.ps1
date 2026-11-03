param([string]$ProcessName='FlightSimulator2024',[int]$X=-9999,[int]$Y=-9999,[string]$Keys='', [string]$Capture='current-screen.png',[int]$Wheel=0,[switch]$RelativeHome)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing,System.Windows.Forms
Add-Type -ReferencedAssemblies System.Drawing,System.Windows.Forms @'
using System;
using System.Threading;
using System.Runtime.InteropServices;
using System.Drawing;
using System.Windows.Forms;
public class KADesktopUI {
 [DllImport("user32.dll")] static extern IntPtr OpenInputDesktop(uint f,bool inherit,uint access);
 [DllImport("user32.dll")] static extern bool SetThreadDesktop(IntPtr h);
 [DllImport("user32.dll")] static extern bool CloseDesktop(IntPtr h);
 [DllImport("user32.dll")] static extern bool SetCursorPos(int x,int y);
 [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
 delegate bool EnumProc(IntPtr h,IntPtr l);
 [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc p,IntPtr l);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h,out uint pid);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] static extern bool AttachThreadInput(uint from,uint to,bool attach);
 [DllImport("kernel32.dll")] static extern uint GetCurrentThreadId();
 [DllImport("user32.dll")] static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
 [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] static extern IntPtr WindowFromPoint(Point p);
 [DllImport("user32.dll")] static extern bool GetCursorPos(out Point p);
 [DllImport("user32.dll")] static extern short GetAsyncKeyState(int key);
 [DllImport("user32.dll")] static extern void keybd_event(byte vk,byte scan,uint flags,UIntPtr extra);
 [DllImport("user32.dll")] static extern short VkKeyScan(char c);
 [DllImport("user32.dll")] static extern uint MapVirtualKey(uint code,uint type);
 static void Key(byte vk){byte scan=(byte)MapVirtualKey(vk,0);keybd_event(vk,scan,0,UIntPtr.Zero);Thread.Sleep(500);keybd_event(vk,scan,2,UIntPtr.Zero);Thread.Sleep(40);}
 [DllImport("user32.dll")] static extern void mouse_event(uint flags,uint x,uint y,uint data,UIntPtr extra);
 public static void Run(int targetPid,int x,int y,string keys,string path,int wheel,bool relativeHome) {
  Exception error=null;
  var t=new Thread(()=>{var desk=OpenInputDesktop(0,false,0x1FF);try {
   if(!SetThreadDesktop(desk)) throw new Exception("Cannot attach input desktop");
   SetThreadDpiAwarenessContext(new IntPtr(-4));
   foreach(int key in new[]{1,2,4,16,17,18,91}) if(GetAsyncKeyState(key)<0)Console.WriteLine("Held mouse/modifier="+key);
   IntPtr h=IntPtr.Zero;
   EnumWindows((w,l)=>{uint pid;GetWindowThreadProcessId(w,out pid);if(pid==targetPid && IsWindowVisible(w)){h=w;return false;}return true;},IntPtr.Zero);
   if(h!=IntPtr.Zero) {uint foregroundPid;uint other=GetWindowThreadProcessId(GetForegroundWindow(),out foregroundPid);uint own=GetCurrentThreadId();bool attached=other!=own && AttachThreadInput(own,other,true);bool focused=SetForegroundWindow(h);if(attached)AttachThreadInput(own,other,false);if(!focused){keybd_event(18,56,0,UIntPtr.Zero);keybd_event(18,56,2,UIntPtr.Zero);focused=SetForegroundWindow(h);}Console.WriteLine("Foreground="+focused+" handle="+h);Thread.Sleep(250);if(!focused && GetForegroundWindow()!=h && (x!=-9999 || keys.Length>0 || wheel!=0))throw new Exception("Simulator could not receive focus; no input sent");}
   if(relativeHome && x!=-9999){mouse_event(1,unchecked((uint)-10000),unchecked((uint)-10000),0,UIntPtr.Zero);Thread.Sleep(300);SetCursorPos(0,0);mouse_event(1,(uint)x,(uint)y,0,UIntPtr.Zero);Thread.Sleep(300);mouse_event(2,0,0,0,UIntPtr.Zero);Thread.Sleep(700);mouse_event(4,0,0,0,UIntPtr.Zero);x=-9999;}
   if(x!=-9999) {var screen=SystemInformation.VirtualScreen;mouse_event(0xC001,(uint)((x-screen.Left)*65535L/(screen.Width-1)),(uint)((y-screen.Top)*65535L/(screen.Height-1)),0,UIntPtr.Zero);mouse_event(1,1,0,0,UIntPtr.Zero);Thread.Sleep(60);mouse_event(1,unchecked((uint)-1),0,0,UIntPtr.Zero);Thread.Sleep(250);Point actual;GetCursorPos(out actual);Console.WriteLine("Cursor="+actual+" Desktop="+screen+" PointWindow="+WindowFromPoint(new Point(x,y))+" Foreground="+GetForegroundWindow());mouse_event(2,0,0,0,UIntPtr.Zero);Thread.Sleep(700);mouse_event(4,0,0,0,UIntPtr.Zero);Thread.Sleep(500);}
   if(keys=="{ESC}")Key(27);
   else if(keys=="{ENTER}")Key(13);
   else if(keys.Length>0 && keys.IndexOfAny(new[]{'{','}','%','^'})<0) {foreach(char c in keys){short v=VkKeyScan(c);bool shift=(v&256)!=0;if(shift)keybd_event(16,42,0,UIntPtr.Zero);Key((byte)(v&255));if(shift)keybd_event(16,42,2,UIntPtr.Zero);}}
   else if(keys.Length>0) SendKeys.SendWait(keys);
   if(keys.Length>0)Thread.Sleep(700);
   if(wheel!=0) {mouse_event(0x800,0,0,unchecked((uint)(wheel*120)),UIntPtr.Zero);Thread.Sleep(700);}
   Thread.Sleep(5000);
   if(path.Length>0) using(var b=new Bitmap(2560,1440)) {using(var g=Graphics.FromImage(b)) g.CopyFromScreen(0,0,0,0,b.Size);using(var small=new Bitmap(b,1280,720)) small.Save(path);}
  }catch(Exception e){error=e;}finally{CloseDesktop(desk);}});
  t.SetApartmentState(ApartmentState.STA);t.Start();t.Join();if(error!=null)throw error;
 }
}
'@
$targetPid=0
if($ProcessName){$p=Get-Process -Name $ProcessName | Select-Object -First 1;$targetPid=$p.Id}
$path=if($Capture){Join-Path (Split-Path $PSScriptRoot) $Capture}else{''}
[KADesktopUI]::Run($targetPid,$X,$Y,$Keys,$path,$Wheel,$RelativeHome)
