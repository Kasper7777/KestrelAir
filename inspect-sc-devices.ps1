# Read-only DirectInput enumeration, including each controller's HID path.
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class SCDevices {
 [DllImport("dinput8.dll")] static extern int DirectInput8Create(IntPtr h,uint v,ref Guid iid,out IntPtr p,IntPtr outer);
 [DllImport("kernel32.dll")] static extern IntPtr GetModuleHandle(string name);
 [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int EnumCallback(IntPtr info,IntPtr context);
 [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int EnumDevices(IntPtr self,uint type,EnumCallback cb,IntPtr ctx,uint flags);
 [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int CreateDevice(IntPtr self,ref Guid id,out IntPtr device,IntPtr outer);
 [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int GetProperty(IntPtr self,IntPtr prop,IntPtr data);
 static T Method<T>(IntPtr p,int slot) {return (T)(object)Marshal.GetDelegateForFunctionPointer(Marshal.ReadIntPtr(Marshal.ReadIntPtr(p),slot*IntPtr.Size),typeof(T));}
 public static void Run(){
  Guid iid=new Guid("BF798031-483A-4DA2-AA99-5D64ED369700");IntPtr di;
  int hr=DirectInput8Create(GetModuleHandle(null),0x800,ref iid,out di,IntPtr.Zero);if(hr!=0)Marshal.ThrowExceptionForHR(hr);
  int index=0;
  EnumCallback cb=(info,ctx)=>{
   Guid id=(Guid)Marshal.PtrToStructure(IntPtr.Add(info,4),typeof(Guid));
   string name=Marshal.PtrToStringUni(IntPtr.Add(info,40));IntPtr dev;string path="";
   if(Method<CreateDevice>(di,3)(di,ref id,out dev,IntPtr.Zero)==0){
    IntPtr data=Marshal.AllocHGlobal(552);for(int j=0;j<552;j++)Marshal.WriteByte(data,j,0);
    Marshal.WriteInt32(data,0,552);Marshal.WriteInt32(data,4,16);
    int result=Method<GetProperty>(dev,5)(dev,new IntPtr(12),data);
    if(result==0)path=Marshal.PtrToStringUni(IntPtr.Add(data,32));else path="GetProperty HRESULT="+result;
    Marshal.FreeHGlobal(data);Marshal.Release(dev);
   }
   Console.WriteLine("js"+(++index)+" | "+name+" | "+id+" | "+path);return 1;
  };
  Method<EnumDevices>(di,4)(di,4,cb,IntPtr.Zero,1);GC.KeepAlive(cb);Marshal.Release(di);
 }
}
'@
[SCDevices]::Run()
