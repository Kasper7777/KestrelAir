Add-Type @'
using System;using System.IO;using System.Runtime.InteropServices;using Microsoft.Win32.SafeHandles;
public class KCp2Watch {
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern SafeFileHandle CreateFile(string n,uint a,uint s,IntPtr p,uint c,uint f,IntPtr t);
 [DllImport("hid.dll")]static extern bool HidD_GetPreparsedData(SafeFileHandle h,out IntPtr p);
 [DllImport("hid.dll")]static extern bool HidD_FreePreparsedData(IntPtr p);
 [DllImport("hid.dll")]static extern int HidP_GetCaps(IntPtr p,IntPtr caps);
 [DllImport("hid.dll")]static extern int HidP_GetUsages(int type,ushort page,ushort link,[Out]ushort[] usages,ref uint count,IntPtr p,byte[] report,uint length);
 public static void Watch(string path){using(var h=CreateFile(path,0x80000000,3,IntPtr.Zero,3,0x40000000,IntPtr.Zero)){
  if(h.IsInvalid)throw new Exception("CP2 open: "+Marshal.GetLastWin32Error());IntPtr data;
  if(!HidD_GetPreparsedData(h,out data))throw new Exception("No HID descriptor");IntPtr caps=Marshal.AllocHGlobal(64);
  try{HidP_GetCaps(data,caps);int length=(ushort)Marshal.ReadInt16(caps,4);using(var stream=new FileStream(h,FileAccess.Read,4096,true)){
   var until=DateTime.UtcNow.AddSeconds(300);string last="";Console.WriteLine("Watching CP2 button inputs for 35 seconds.");
   while(DateTime.UtcNow<until){var report=new byte[length];var task=stream.ReadAsync(report,0,length);
    while(!task.Wait(100)){if(DateTime.UtcNow>=until)return;}
    var usages=new ushort[128];uint count=128;HidP_GetUsages(0,9,0,usages,ref count,data,report,(uint)task.Result);
    string text=String.Join(",",new ArraySegment<ushort>(usages,0,(int)count));if(text!=last){Console.WriteLine(DateTime.UtcNow.ToString("HH:mm:ss.fff")+" CP2 active HID buttons="+text);last=text;}
   }
  }}finally{Marshal.FreeHGlobal(caps);HidD_FreePreparsedData(data);}
 }}
}
'@
[KCp2Watch]::Watch('\\?\hid#vid_3344&pid_025a&mi_00#a&282a1635&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}')
