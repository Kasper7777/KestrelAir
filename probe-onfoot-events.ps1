$ErrorActionPreference='Stop'
Add-Type @'
using System;using System.Runtime.InteropServices;using System.Threading;
public static class FootProbe {
 const string D=@"D:\SteamLibrary\steamapps\common\MSFS2024\SimConnect_internal.dll";
 [DllImport(D)]static extern int SimConnect_Open(out IntPtr h,string name,IntPtr w,uint m,IntPtr e,uint c);
 [DllImport(D)]static extern int SimConnect_MapClientEventToSimEvent(IntPtr h,uint id,string name);
 [DllImport(D)]static extern int SimConnect_TransmitClientEvent(IntPtr h,uint obj,uint id,uint data,uint group,uint flags);
 [DllImport(D)]static extern int SimConnect_GetNextDispatch(IntPtr h,out IntPtr p,out uint size);
 [DllImport(D)]static extern int SimConnect_Close(IntPtr h);
 public static void Run(){IntPtr h;if(SimConnect_Open(out h,"KestrelAir neutral on-foot event validation",IntPtr.Zero,0,IntPtr.Zero,0)!=0)throw new Exception("SimConnect open failed");try{
 string[] names={"AXIS_PC_MOVE_X","AXIS_PC_MOVE_Z","AXIS_PC_FPV_ROTATION_X","AXIS_PC_FPV_ROTATION_Y"};
 for(uint i=0;i<names.Length;i++){Console.WriteLine(names[i]+" map="+SimConnect_MapClientEventToSimEvent(h,100+i,names[i]));Console.WriteLine("neutral="+SimConnect_TransmitClientEvent(h,0,100+i,0,1,16));}
 DateTime end=DateTime.UtcNow.AddSeconds(3);while(DateTime.UtcNow<end){IntPtr p;uint size;if(SimConnect_GetNextDispatch(h,out p,out size)==0 && Marshal.ReadInt32(p,8)==1)throw new Exception("SimConnect exception="+Marshal.ReadInt32(p,12)+" send="+Marshal.ReadInt32(p,16));Thread.Sleep(10);}Console.WriteLine("All four native events accepted; neutral only.");
 }finally{SimConnect_Close(h);}}
}
'@
[FootProbe]::Run()
