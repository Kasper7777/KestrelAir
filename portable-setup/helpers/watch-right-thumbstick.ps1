param([int]$Seconds = 180, [string]$Log = "$PSScriptRoot\right-thumbstick-watch.txt")
# Read-only: logs the right WarBRD grip's MiniStick (HID Rx 0x33 / Ry 0x34, 0..60000) next to the vJoy
# camera axes SPAD feeds from it (X 0x30, Y 0x31, Ry 0x34, Rz 0x35, 0..32767). HID paths are this PC's.
Add-Type @'
using System;using System.IO;using System.Threading;using System.Runtime.InteropServices;using Microsoft.Win32.SafeHandles;
public class KThumbWatch {
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern SafeFileHandle CreateFile(string n,uint a,uint s,IntPtr p,uint c,uint f,IntPtr t);
 [DllImport("hid.dll")]static extern bool HidD_GetPreparsedData(SafeFileHandle h,out IntPtr p);
 [DllImport("hid.dll")]static extern int HidP_GetCaps(IntPtr p,byte[] caps);
 [DllImport("hid.dll")]static extern int HidP_GetUsageValue(int type,ushort page,ushort link,ushort usage,out uint v,IntPtr p,byte[] r,uint len);
 static object gate=new object(); public static volatile string Grip="?", VJoy="?";
 static void Run(string path,ushort[] usages,string[] names,bool isGrip,int seconds){
  using(var h=CreateFile(path,0x80000000,3,IntPtr.Zero,3,0x40000000,IntPtr.Zero)){
   IntPtr d; HidD_GetPreparsedData(h,out d); var caps=new byte[64]; HidP_GetCaps(d,caps); int len=BitConverter.ToUInt16(caps,4);
   var until=DateTime.UtcNow.AddSeconds(seconds);
   using(var s=new FileStream(h,FileAccess.Read,4096,true)){
    while(DateTime.UtcNow<until){ var r=new byte[len]; var t=s.ReadAsync(r,0,len); while(!t.Wait(100)){ if(DateTime.UtcNow>=until) return; }
     var parts=new string[usages.Length];
     for(int i=0;i<usages.Length;i++){ uint v; int st=HidP_GetUsageValue(0,1,0,usages[i],out v,d,r,(uint)t.Result); parts[i]=names[i]+"="+(st==0x110000?v.ToString():"--"); }
     if(isGrip) Grip=String.Join(" ",parts); else VJoy=String.Join(" ",parts); }}}}
 public static void Watch(string grip,string vjoy,int seconds,string log){
  var a=new Thread(()=>Run(grip,new ushort[]{0x33,0x34},new[]{"gripRx","gripRy"},true,seconds));
  var b=new Thread(()=>Run(vjoy,new ushort[]{0x30,0x31,0x34,0x35},new[]{"vjX","vjY","vjRy","vjRz"},false,seconds));
  a.IsBackground=b.IsBackground=true; a.Start(); b.Start(); string last="";
  var until=DateTime.UtcNow.AddSeconds(seconds);
  while(DateTime.UtcNow<until){ string line=Grip+" | "+VJoy; if(line!=last){ File.AppendAllText(log,DateTime.Now.ToString("HH:mm:ss.fff")+" "+line+Environment.NewLine); last=line; } Thread.Sleep(150); } }
}
'@
Set-Content -Path $Log -Value "Right thumbstick watch started $(Get-Date -Format s)" -Encoding utf8
[KThumbWatch]::Watch('\\?\hid#vid_3344&pid_03f5&mi_00#a&1aa429cf&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}',
                     '\\?\HID#HIDCLASS#1&2d595ca7&1&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}', $Seconds, $Log)
