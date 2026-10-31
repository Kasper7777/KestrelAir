Add-Type @'
using System; using System.Runtime.InteropServices; using Microsoft.Win32.SafeHandles;
public class HidRanges {
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern SafeFileHandle CreateFile(string n,uint a,uint s,IntPtr p,uint c,uint f,IntPtr t);
 [DllImport("hid.dll")] static extern bool HidD_GetPreparsedData(SafeFileHandle h,out IntPtr p);
 [DllImport("hid.dll")] static extern bool HidD_FreePreparsedData(IntPtr p);
 [DllImport("hid.dll")] static extern int HidP_GetValueCaps(int type,IntPtr caps,ref ushort count,IntPtr p);
 public static void Inspect(string path) {
  using(var h=CreateFile(path,0,3,IntPtr.Zero,3,0,IntPtr.Zero)) { if(h.IsInvalid) throw new Exception("Open HID: "+Marshal.GetLastWin32Error()); IntPtr p; if(!HidD_GetPreparsedData(h,out p))throw new Exception("Preparsed data unavailable");
   IntPtr b=Marshal.AllocHGlobal(72*256); try {ushort count=256;int status=HidP_GetValueCaps(0,b,ref count,p);Console.WriteLine("Status "+status.ToString("X")+" Count "+count);for(int i=0;i<count;i++){var q=IntPtr.Add(b,i*72);Console.WriteLine("Page="+Marshal.ReadInt16(q,0)+" Usage="+Marshal.ReadInt16(q,56)+" Min="+Marshal.ReadInt32(q,40)+" Max="+Marshal.ReadInt32(q,44));}} finally{Marshal.FreeHGlobal(b);HidD_FreePreparsedData(p);}
  }
 }
}
'@
$paths = @(
 '\\?\hid#vid_3344&pid_03f5&mi_00#a&1aa429cf&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}',
 '\\?\hid#vid_3344&pid_0194&mi_00#8&1d037022&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}',
 '\\?\hid#vid_3344&pid_025c&mi_00#a&66e0474&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}'
)
foreach($devicePath in $paths) { $devicePath; [HidRanges]::Inspect($devicePath) }
