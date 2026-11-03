param([int]$Seconds = 240, [string]$Log = "$PSScriptRoot\warbrd-button-watch.txt", [switch]$IncludeVJoy)
# Read-only HID watcher for both WarBRD-D grips; logs pressed button numbers (HID usage = SPAD BUTTON_n).
# HID paths below are this PC's grips (see firmware-repair-notes.md); on another PC read them from Device Manager first.
Add-Type @'
using System;using System.IO;using System.Threading;using System.Runtime.InteropServices;using Microsoft.Win32.SafeHandles;
public class KWarbrdWatch {
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern SafeFileHandle CreateFile(string n,uint a,uint s,IntPtr p,uint c,uint f,IntPtr t);
 [DllImport("hid.dll")]static extern bool HidD_GetPreparsedData(SafeFileHandle h,out IntPtr p);
 [DllImport("hid.dll")]static extern int HidP_GetCaps(IntPtr p,IntPtr caps);
 [DllImport("hid.dll")]static extern int HidP_GetUsages(int type,ushort page,ushort link,[Out]ushort[] usages,ref uint count,IntPtr p,byte[] report,uint length);
 static object gate=new object();
 public static void Watch(string name,string path,int seconds,string log){
  using(var h=CreateFile(path,0x80000000,3,IntPtr.Zero,3,0x40000000,IntPtr.Zero)){
   if(h.IsInvalid){Write(log,name+" open failed "+Marshal.GetLastWin32Error());return;}
   IntPtr data;HidD_GetPreparsedData(h,out data);IntPtr caps=Marshal.AllocHGlobal(64);HidP_GetCaps(data,caps);
   int length=(ushort)Marshal.ReadInt16(caps,4);var until=DateTime.UtcNow.AddSeconds(seconds);string last="";
   using(var stream=new FileStream(h,FileAccess.Read,4096,true)){
    while(DateTime.UtcNow<until){var report=new byte[length];var task=stream.ReadAsync(report,0,length);
     while(!task.Wait(100)){if(DateTime.UtcNow>=until)return;}
     var usages=new ushort[128];uint count=128;HidP_GetUsages(0,9,0,usages,ref count,data,report,(uint)task.Result);
     string text=String.Join(",",new ArraySegment<ushort>(usages,0,(int)count));
     if(text!=last){Write(log,DateTime.Now.ToString("HH:mm:ss.fff")+" "+name+" buttons=["+text+"]");last=text;}
    }}}
 }
 static void Write(string log,string s){lock(gate){File.AppendAllText(log,s+Environment.NewLine);Console.WriteLine(s);}}
 public static void Both(string r,string l,string v,int seconds,string log){
  var a=new Thread(()=>Watch("RIGHT",r,seconds,log));var b=new Thread(()=>Watch("LEFT",l,seconds,log));a.Start();b.Start();
  Thread c=null;if(!String.IsNullOrEmpty(v)){c=new Thread(()=>Watch("VJOY",v,seconds,log));c.Start();}
  a.Join();b.Join();if(c!=null)c.Join();}
}
'@
# -IncludeVJoy also logs vJoy device 1 buttons, to confirm SPAD's grip -> vJoy routing end to end.
$vjoy = if ($IncludeVJoy) { '\\?\HID#HIDCLASS#1&2d595ca7&1&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}' } else { '' }
Set-Content -Path $Log -Value "WarBRD watch started $(Get-Date -Format s)" -Encoding utf8
[KWarbrdWatch]::Both('\\?\hid#vid_3344&pid_03f5&mi_00#a&1aa429cf&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}',
                     '\\?\hid#vid_3344&pid_03f5&mi_00#a&22ba5017&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}', $vjoy, $Seconds, $Log)
