param([int]$Seconds = 120, [string]$Log = "$PSScriptRoot\rudder-pedal-watch.txt")
# Read-only logger for the Saitek Pro Flight Rudder Pedals (06A3:0763): X, Y (toe brakes) and Rz (rudder).
# HID path is this PC's; SPAD reads the same raw HID values (X/Y 0..127, Rz 0..511).
Add-Type @'
using System;using System.IO;using System.Runtime.InteropServices;using Microsoft.Win32.SafeHandles;
public class KPedalWatch {
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern SafeFileHandle CreateFile(string n,uint a,uint s,IntPtr p,uint c,uint f,IntPtr t);
 [DllImport("hid.dll")]static extern bool HidD_GetPreparsedData(SafeFileHandle h,out IntPtr p);
 [DllImport("hid.dll")]static extern int HidP_GetCaps(IntPtr p,byte[] caps);
 [DllImport("hid.dll")]static extern int HidP_GetUsageValue(int type,ushort page,ushort link,ushort usage,out uint v,IntPtr p,byte[] r,uint len);
 public static void Watch(string path,int seconds,string log){
  using(var h=CreateFile(path,0x80000000,3,IntPtr.Zero,3,0x40000000,IntPtr.Zero)){
   IntPtr d; HidD_GetPreparsedData(h,out d); var caps=new byte[64]; HidP_GetCaps(d,caps); int len=BitConverter.ToUInt16(caps,4);
   var until=DateTime.UtcNow.AddSeconds(seconds); string last=""; DateTime lastWrite=DateTime.MinValue;
   using(var s=new FileStream(h,FileAccess.Read,4096,true)){
    while(DateTime.UtcNow<until){ var r=new byte[len]; var t=s.ReadAsync(r,0,len); while(!t.Wait(100)){ if(DateTime.UtcNow>=until) return; }
     uint x,y,rz; HidP_GetUsageValue(0,1,0,0x30,out x,d,r,(uint)len); HidP_GetUsageValue(0,1,0,0x31,out y,d,r,(uint)len); HidP_GetUsageValue(0,1,0,0x35,out rz,d,r,(uint)len);
     string text="X="+x+" Y="+y+" Rz="+rz;
     // Log at most every 150 ms so a sweep stays readable.
     if(text!=last && (DateTime.UtcNow-lastWrite).TotalMilliseconds>150){ File.AppendAllText(log,DateTime.Now.ToString("HH:mm:ss.fff")+" "+text+Environment.NewLine); last=text; lastWrite=DateTime.UtcNow; }
    }}}}
}
'@
Set-Content -Path $Log -Value "Pedal watch started $(Get-Date -Format s)" -Encoding utf8
[KPedalWatch]::Watch('\\?\HID#VID_06A3&PID_0763#9&2a71f0e4&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}', $Seconds, $Log)
