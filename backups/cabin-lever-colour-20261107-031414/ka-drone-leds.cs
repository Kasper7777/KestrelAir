// ka-walk-leds: either grip flip lever raised disables flight inputs through L:KA_WALK_MODE and paints both
// grips hot pink. With both lowered, drone camera is sky blue; otherwise stored firmware colours return.
//
// Reads CAMERA STATE through the running sim's SimConnect_internal.dll (same approach as ka-sfs-watch) and
// writes VIRPIL's LED feature report (report 2, command 102, then one byte per LED: 00 = firmware colour,
// 80 + BBGGRR override; protocol as used by KestrelAirLEDs.lua) to each grip's vendor interface
// (VID 3344 PID 03F5 MI_01). Both grips are found by enumeration, so no per-PC paths.
// Runs hidden, single instance. Log: %TEMP%\ka-drone-leds.log.
//   ka-drone-leds.exe --test   -> blue for 15 s, then back to normal, and exit.
// Build: csc -target:winexe -platform:x64 -out:ka-walk-leds.exe ka-drone-leds.cs
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using Microsoft.Win32.SafeHandles;

static class KaDroneLeds
{
    // VIRPIL Configurator (ATmegaHandler.RealTimeSetLEDs / CombineLEDs, decompiled 2026-11-04): the ring the user
    // colours on the "WarBRD-D Base" page is the ALPHA Prime grip's 9 LEDs (PhID 0-8) on shift-register chain 1,
    // driven by command 103 (102 = base-PCB LEDs, which the WarBRD-D doesn't have). Grip LEDs are RGB type:
    // byte = 0x40 | BBGGRR (GRB-type panel LEDs use 0x80). 0x00 = leave to firmware.
    const byte SkyBlue = 0x78;  // 0x40 + BB=11 GG=10 RR=00
    const byte HotPink = 0x63; // full red, medium blue, no green (2-bit RGB)
    static volatile int RaisedGrips = 1; // fail closed until both HID readers have reported
    static readonly Dictionary<string, bool> Levers = new Dictionary<string, bool>();
    const int GripLeds = 9;

    // ---- HID ----
    [StructLayout(LayoutKind.Sequential)] struct SP_DEVICE_INTERFACE_DATA { public int cbSize; public Guid g; public int flags; public IntPtr reserved; }
    [DllImport("hid.dll")] static extern void HidD_GetHidGuid(out Guid g);
    [DllImport("hid.dll")] static extern bool HidD_SetFeature(SafeFileHandle h, byte[] buf, int len);
    [DllImport("hid.dll")] static extern int HidP_GetUsages(int type, ushort page, ushort link, ushort[] usages, ref uint count, IntPtr pp, byte[] report, uint length);
    [DllImport("hid.dll")] static extern bool HidD_GetPreparsedData(SafeFileHandle h, out IntPtr p);
    [DllImport("hid.dll")] static extern bool HidD_FreePreparsedData(IntPtr p);
    [DllImport("hid.dll")] static extern int HidP_GetCaps(IntPtr p, byte[] caps);
    [DllImport("setupapi.dll", CharSet = CharSet.Unicode)] static extern IntPtr SetupDiGetClassDevs(ref Guid g, string e, IntPtr w, int flags);
    [DllImport("setupapi.dll")] static extern bool SetupDiEnumDeviceInterfaces(IntPtr set, IntPtr info, ref Guid g, int i, ref SP_DEVICE_INTERFACE_DATA d);
    [DllImport("setupapi.dll", CharSet = CharSet.Unicode)] static extern bool SetupDiGetDeviceInterfaceDetail(IntPtr set, ref SP_DEVICE_INTERFACE_DATA d, IntPtr detail, int size, out int req, IntPtr info);
    [DllImport("setupapi.dll")] static extern bool SetupDiDestroyDeviceInfoList(IntPtr set);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] static extern SafeFileHandle CreateFile(string n, uint a, uint s, IntPtr p, uint c, uint f, IntPtr t);

    // ---- SimConnect ----
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)] static extern IntPtr LoadLibrary(string path);
    [DllImport("kernel32.dll", CharSet = CharSet.Ansi)] static extern IntPtr GetProcAddress(IntPtr mod, string name);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int OpenFn(out IntPtr h, string name, IntPtr hwnd, uint msg, IntPtr ev, uint cfg);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int CloseFn(IntPtr h);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int AddDefFn(IntPtr h, uint def, string var, string units, uint type, float eps, uint id);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int RequestFn(IntPtr h, uint req, uint def, uint obj, uint period, uint flags, uint origin, uint interval, uint limit);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int DispatchFn(IntPtr h, out IntPtr data, out uint size);
    static OpenFn Open; static CloseFn Close; static AddDefFn AddDef; static RequestFn Request; static DispatchFn Next;
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int SetDataFn(IntPtr h, uint def, uint obj, uint flags, uint count, uint size, ref double value);
    static SetDataFn SetData;

    static void StartLeverReaders()
    {
        foreach (string path in GripLedPaths("mi_00"))
        {
            var thread = new Thread(() => ReadLever(path)); thread.IsBackground = true; thread.Start();
        }
    }
    static void ReadLever(string path)
    {
        // Enumerate MI_00 separately: interface instance identifiers can differ from MI_01.
        while (true)
        {
            try
            {
                using (var handle = CreateFile(path, 0x80000000, 3, IntPtr.Zero, 3, 0x40000000, IntPtr.Zero))
                {
                    if (handle.IsInvalid) throw new IOException("Cannot read grip");
                    IntPtr pp; if (!HidD_GetPreparsedData(handle, out pp)) throw new IOException("No descriptor");
                    try
                    {
                        byte[] caps = new byte[64]; HidP_GetCaps(pp, caps); int length = BitConverter.ToUInt16(caps, 4);
                        using (var stream = new FileStream(handle, FileAccess.Read, 4096, true))
                        while (true)
                        {
                            byte[] report = new byte[length]; int got = stream.ReadAsync(report, 0, length).Result;
                            if (got == 0) throw new IOException("Grip disconnected");
                            ushort[] buttons = new ushort[128]; uint count = 128;
                            if (HidP_GetUsages(0, 9, 0, buttons, ref count, pp, report, (uint)got) != 0x110000) continue;
                            bool raised = false; for (int i = 0; i < count; i++) if (buttons[i] == 2) raised = true;
                            lock (Levers) { Levers[path] = raised; RaisedGrips = Levers.Count < 2 || Levers.ContainsValue(true) ? 1 : 0; }
                        }
                    }
                    finally { HidD_FreePreparsedData(pp); }
                }
            }
            catch { lock (Levers) { Levers.Remove(path); RaisedGrips = 1; } Thread.Sleep(2000); }
        }
    }

    static readonly string LogPath = Path.Combine(Path.GetTempPath(), "ka-drone-leds.log");

    static int Main(string[] args)
    {
        if (args.Length > 0 && args[0] == "--probe")
        {
            StartLeverReaders(); Thread.Sleep(3000);
            lock (Levers) { Log("probe: connected grips=" + Levers.Count + " walk=" + RaisedGrips); }
            return 0;
        }
        if (args.Length > 0 && args[0] == "--test")
        {
            Console.WriteLine("grips: " + SetGrips(true));
            Thread.Sleep(15000);
            SetGrips(false);
            return 0;
        }
        bool first;
        using (new Mutex(true, "Local\\KestrelAir.ka-walk-leds", out first))
        {
            if (!first) return 0;
            Log("started");
            StartLeverReaders();
            IntPtr h = IntPtr.Zero;
            int state = -1;
            int shown = -1;
            DateTime lastWrite = DateTime.MinValue;
            while (true)
            {
                if (h == IntPtr.Zero) { h = Connect(); state = -1; }
                if (h != IntPtr.Zero && !Poll(h, ref state)) { Log("sim closed"); try { Close(h); } catch { } h = IntPtr.Zero; state = -1; }
                bool drone = state == 4;
                double walk = RaisedGrips;
                if (h != IntPtr.Zero) SetData(h, 2, 0, 0, 0, 8, ref walk);
                int colour = walk == 1 ? HotPink : drone ? SkyBlue : 0;
                // Re-send every 2 s as well: the VIRPIL configurator or a replug can reset the LEDs.
                if (shown != colour || (colour != 0 && (DateTime.UtcNow - lastWrite).TotalSeconds >= 2))
                {
                    int n = SetGrips(colour != 0, (byte)colour);
                    if (shown != colour) Log((walk == 1 ? "walk -> hot pink" : drone ? "drone -> sky blue" : "flight -> firmware colours") + " on " + n + " grip(s)");
                    shown = colour; lastWrite = DateTime.UtcNow;
                }
                Thread.Sleep(100);
            }
        }
    }

    // ---- LEDs ----
    static readonly Dictionary<string, SafeFileHandle> LedHandles = new Dictionary<string, SafeFileHandle>();
    static int SetGrips(bool drone, byte colour = SkyBlue)
    {
        int count = 0;
        foreach (string path in GripLedPaths())
        {
            try
            {
                SafeFileHandle h;
                if (!LedHandles.TryGetValue(path, out h) || h.IsInvalid)
                {
                    h = CreateFile(path, 0xC0000000, 3, IntPtr.Zero, 3, 0, IntPtr.Zero);
                    if (!h.IsInvalid) LedHandles[path] = h;
                }
                {
                    if (h.IsInvalid) continue;
                    IntPtr pp; HidD_GetPreparsedData(h, out pp);
                    var caps = new byte[64]; HidP_GetCaps(pp, caps); HidD_FreePreparsedData(pp);
                    int len = BitConverter.ToUInt16(caps, 8);
                    if (len < 25) continue;
                    bool ok;
                    if (drone)
                    {
                        // Like the Configurator's live preview: all five banks (102-106), zeros everywhere except
                        // the grip chain, so an unexpected bank order on the device can't paint anything else.
                        ok = true;
                        for (byte cmd = 102; cmd <= 106; cmd++)
                        {
                            var pkt = new byte[len]; pkt[0] = 2; pkt[1] = cmd;
                            if (cmd == 103) for (int i = 0; i < GripLeds; i++) pkt[5 + i] = colour;
                            ok &= HidD_SetFeature(h, pkt, len);
                        }
                    }
                    else
                    {
                        var reset = new byte[len]; reset[0] = 2; reset[1] = 100;  // RealTimeResetLEDs: back to stored colours
                        ok = HidD_SetFeature(h, reset, len);
                    }
                    if (ok) count++;
                }
            }
            catch { }
        }
        return count;
    }

    static List<string> GripLedPaths(string which = "mi_01")
    {
        var list = new List<string>();
        Guid g; HidD_GetHidGuid(out g);
        IntPtr set = SetupDiGetClassDevs(ref g, null, IntPtr.Zero, 0x12);  // PRESENT | DEVICEINTERFACE
        var d = new SP_DEVICE_INTERFACE_DATA(); d.cbSize = Marshal.SizeOf(d);
        for (int i = 0; SetupDiEnumDeviceInterfaces(set, IntPtr.Zero, ref g, i, ref d); i++)
        {
            int req; SetupDiGetDeviceInterfaceDetail(set, ref d, IntPtr.Zero, 0, out req, IntPtr.Zero);
            IntPtr buf = Marshal.AllocHGlobal(req);
            Marshal.WriteInt32(buf, IntPtr.Size == 8 ? 8 : 6);
            if (SetupDiGetDeviceInterfaceDetail(set, ref d, buf, req, out req, IntPtr.Zero))
            {
                string p = Marshal.PtrToStringUni(buf + 4);
                if (p.ToLowerInvariant().Contains("vid_3344&pid_03f5&" + which)) list.Add(p);
            }
            Marshal.FreeHGlobal(buf);
        }
        SetupDiDestroyDeviceInfoList(set);
        return list;
    }

    // ---- Sim ----
    static IntPtr Connect()
    {
        Process sim = null;
        foreach (string n in new[] { "FlightSimulator2024", "FlightSimulator" })
        { var ps = Process.GetProcessesByName(n); if (ps.Length > 0) { sim = ps[0]; break; } }
        if (sim == null) return IntPtr.Zero;
        if (Open == null)
        {
            string dll;
            try { dll = Path.Combine(Path.GetDirectoryName(sim.MainModule.FileName), "SimConnect_internal.dll"); }
            catch { return IntPtr.Zero; }
            IntPtr mod = LoadLibrary(dll);
            if (mod == IntPtr.Zero) { Log("cannot load " + dll); return IntPtr.Zero; }
            Open = Get<OpenFn>(mod, "SimConnect_Open"); Close = Get<CloseFn>(mod, "SimConnect_Close");
            AddDef = Get<AddDefFn>(mod, "SimConnect_AddToDataDefinition");
            Request = Get<RequestFn>(mod, "SimConnect_RequestDataOnSimObject");
            Next = Get<DispatchFn>(mod, "SimConnect_GetNextDispatch");
            SetData = Get<SetDataFn>(mod, "SimConnect_SetDataOnSimObject");
        }
        IntPtr h;
        if (Open(out h, "KestrelAir drone LEDs", IntPtr.Zero, 0, IntPtr.Zero, 0) != 0) return IntPtr.Zero;
        // INT32 data type = 1; period SIM_FRAME = 3; flag CHANGED = 1.
        if (AddDef(h, 1, "CAMERA STATE", "number", 1, 0, 0xffffffff) != 0 || Request(h, 1, 1, 0, 3, 1, 0, 0, 0) != 0)
        { Close(h); return IntPtr.Zero; }
        if (AddDef(h, 2, "L:KA_WALK_MODE", "number", 4, 0, 0xffffffff) != 0) { Close(h); return IntPtr.Zero; }
        Log("connected to MSFS");
        return h;
    }

    // Reads queued messages; updates state from SIMOBJECT_DATA (id 8, value at byte 40). False on QUIT (id 3).
    static bool Poll(IntPtr h, ref int state)
    {
        IntPtr data; uint size;
        for (int i = 0; i < 50 && Next(h, out data, out size) == 0; i++)
        {
            if (size < 12) continue;
            int id = Marshal.ReadInt32(data, 8);
            if (id == 3) return false;
            if (id == 8 && size >= 44) state = Marshal.ReadInt32(data, 40);
        }
        return true;
    }

    static T Get<T>(IntPtr mod, string name) { return (T)(object)Marshal.GetDelegateForFunctionPointer(GetProcAddress(mod, name), typeof(T)); }
    static void Log(string s) { try { File.AppendAllText(LogPath, DateTime.Now.ToString("s") + " " + s + Environment.NewLine); } catch { } }
}
