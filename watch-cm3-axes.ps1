param([int]$Seconds = 150, [string]$Log = "$PSScriptRoot\cm3-axis-watch.txt")
# Read-only: logs every axis on the VIRPIL MongoosT-50CM3 throttle (3344:0194) when it moves noticeably.
Add-Type @'
using System;using System.IO;using System.Runtime.InteropServices;using Microsoft.Win32.SafeHandles;
public class KCm3Watch {
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern SafeFileHandle CreateFile(string n,uint a,uint s,IntPtr p,uint c,uint f,IntPtr t);
 [DllImport("hid.dll")]static extern bool HidD_GetPreparsedData(SafeFileHandle h,out IntPtr p);
 [DllImport("hid.dll")]static extern int HidP_GetCaps(IntPtr p,byte[] caps);
 [DllImport("hid.dll")]static extern int HidP_GetUsageValue(int type,ushort page,ushort link,ushort usage,out uint v,IntPtr p,byte[] r,uint len);
 public static void Watch(string path,int seconds,string log){
  string[] names={"X","Y","Z","Rx","Ry","Rz","Slider0","Slider1","Dial"};
  using(var h=CreateFile(path,0x80000000,3,IntPtr.Zero,3,0x40000000,IntPtr.Zero)){
   IntPtr d; HidD_GetPreparsedData(h,out d); var caps=new byte[64]; HidP_GetCaps(d,caps); int len=BitConverter.ToUInt16(caps,4);
   var last=new long[9]; for(int i=0;i<9;i++) last[i]=-1; var until=DateTime.UtcNow.AddSeconds(seconds);
   using(var s=new FileStream(h,FileAccess.Read,4096,true)){
    while(DateTime.UtcNow<until){ var r=new byte[len]; var t=s.ReadAsync(r,0,len); while(!t.Wait(100)){ if(DateTime.UtcNow>=until) return; }
     for(int i=0;i<9;i++){ uint v; if(HidP_GetUsageValue(0,1,0,(ushort)(0x30+i),out v,d,r,(uint)t.Result)!=0x110000) continue;
      if(last[i]<0){ last[i]=v; File.AppendAllText(log,"start "+names[i]+"="+v+Environment.NewLine); continue; }
      if(Math.Abs((long)v-last[i])>300){ File.AppendAllText(log,DateTime.Now.ToString("HH:mm:ss.fff")+" "+names[i]+"="+v+Environment.NewLine); last[i]=v; } } }}}}
}
'@
Set-Content -Path $Log -Value "CM3 axis watch started $(Get-Date -Format s)" -Encoding utf8
[KCm3Watch]::Watch('\\?\hid#vid_3344&pid_0194&mi_00#8&1d037022&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}', $Seconds, $Log)
