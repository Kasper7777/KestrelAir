Add-Type @'
using System;using System.Runtime.InteropServices;using System.Collections.Generic;
public class Cp2Input {
 [StructLayout(LayoutKind.Sequential)] public struct Info {public uint Size,Flags,X,Y,Z,R,U,V,Buttons,ButtonNumber,POV,Reserved1,Reserved2;}
 [DllImport("winmm.dll",CharSet=CharSet.Unicode)] static extern uint joyGetDevCapsW(UIntPtr id,IntPtr caps,uint size);
 [DllImport("winmm.dll")] static extern uint joyGetPosEx(uint id,ref Info info);
 public static void Read(){IntPtr caps=Marshal.AllocHGlobal(728);try {for(uint id=0;id<16;id++){if(joyGetDevCapsW((UIntPtr)id,caps,728)!=0)continue;if((ushort)Marshal.ReadInt16(caps,0)!=0x3344||(ushort)Marshal.ReadInt16(caps,2)!=0x025a)continue;Info v=new Info();v.Size=52;v.Flags=255;uint status=joyGetPosEx(id,ref v);var buttons=new List<int>();for(int n=0;n<32;n++)if((v.Buttons&(1u<<n))!=0)buttons.Add(n+1);Console.WriteLine("CP2 joystick="+id+" status="+status+" pressed="+String.Join(",",buttons));}}finally{Marshal.FreeHGlobal(caps);}}
}
'@
[Cp2Input]::Read()
Add-Type @'
using System;using System.IO;using System.Runtime.InteropServices;using Microsoft.Win32.SafeHandles;
public class Cp2HidInput {
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern SafeFileHandle CreateFile(string n,uint a,uint s,IntPtr p,uint c,uint f,IntPtr t);
 [DllImport("hid.dll")] static extern bool HidD_GetPreparsedData(SafeFileHandle h,out IntPtr p);
 [DllImport("hid.dll")] static extern bool HidD_FreePreparsedData(IntPtr p);
 [DllImport("hid.dll")] static extern int HidP_GetCaps(IntPtr p,IntPtr caps);
 [DllImport("hid.dll")] static extern int HidP_GetUsages(int type,ushort page,ushort link,[Out] ushort[] usages,ref uint count,IntPtr p,byte[] report,uint length);
 [DllImport("hid.dll")] static extern int HidP_GetUsageValue(int type,ushort page,ushort link,ushort usage,out uint value,IntPtr p,byte[] report,uint length);
 public static void Read(){ReadPath(@"\\?\hid#vid_3344&pid_025a&mi_00#a&282a1635&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}");}
 public static void ReadPath(string path){
 using(var h=CreateFile(path,0x80000000,3,IntPtr.Zero,3,0x40000000,IntPtr.Zero)){if(h.IsInvalid)throw new Exception("HID open failed: "+Marshal.GetLastWin32Error());IntPtr p;if(!HidD_GetPreparsedData(h,out p))throw new Exception("HID descriptor unavailable");IntPtr caps=Marshal.AllocHGlobal(64);try{HidP_GetCaps(p,caps);int length=(ushort)Marshal.ReadInt16(caps,4);using(var stream=new FileStream(h,FileAccess.Read,4096,true)){byte[] report=new byte[length];var task=stream.ReadAsync(report,0,length);if(!task.Wait(3000)){Console.WriteLine("No report received; move a switch and retry.");return;}ushort[] usages=new ushort[128];uint count=128;int status=HidP_GetUsages(0,9,0,usages,ref count,p,report,(uint)task.Result);Console.WriteLine(path+" active buttons="+String.Join(",",new ArraySegment<ushort>(usages,0,(int)count)));for(ushort axis=48;axis<=54;axis++){uint value;if(HidP_GetUsageValue(0,1,0,axis,out value,p,report,(uint)task.Result)==0x110000)Console.WriteLine("Axis "+axis+"="+value);}}}finally{Marshal.FreeHGlobal(caps);HidD_FreePreparsedData(p);}}}
}
'@
[Cp2HidInput]::Read()
[Cp2HidInput]::ReadPath('\\?\hid#vid_3344&pid_0194&mi_00#8&1d037022&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}')
[Cp2HidInput]::ReadPath('\\?\hid#vid_3344&pid_025c&mi_00#a&66e0474&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}')
