// ka-sfs-watch: tell SPAD whether SimFlight's SFS Monitor owns the RotAIR / PulsAIR panels.
// Every second it checks for SFSmonitor*.exe and writes L:KA_SFS_MONITOR into MSFS (1 = running, 0 = not).
// The SPAD profiles' panel events carry the condition "LVAR:KA_SFS_MONITOR Unequal 1" (gate-sfs-panels.py),
// so SPAD drives the panels only while SFS Monitor is closed.
//
// Runs hidden from the Windows Startup folder; one instance only. It waits for MSFS, connects through the
// running sim's own SimConnect_internal.dll, re-writes the value every 2 s (L-vars reset when an aircraft
// loads) and reconnects after the sim restarts. Log: %TEMP%\ka-sfs-watch.log (state changes only).
// "ka-sfs-watch.exe --once" prints the current state and exits.
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;

static class KaSfsWatch
{
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] static extern IntPtr LoadLibrary(string path);
    [DllImport("kernel32.dll", CharSet = CharSet.Ansi)] static extern IntPtr GetProcAddress(IntPtr mod, string name);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int OpenFn(out IntPtr h, string name, IntPtr hwnd, uint msg, IntPtr ev, uint cfg);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int CloseFn(IntPtr h);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int AddDefFn(IntPtr h, uint def, string var, string units, uint type, float eps, uint id);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int SetDataFn(IntPtr h, uint def, uint obj, uint flags, uint count, uint size, ref double data);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int DispatchFn(IntPtr h, out IntPtr data, out uint size);

    static OpenFn Open; static CloseFn Close; static AddDefFn AddDef; static SetDataFn SetData; static DispatchFn Next;
    static readonly string Log = Path.Combine(Path.GetTempPath(), "ka-sfs-watch.log");

    static int Main(string[] args)
    {
        if (args.Length > 0 && args[0] == "--once") { Console.WriteLine("SFS Monitor running: " + SfsRunning()); return 0; }
        bool first;
        using (var single = new Mutex(true, "Local\\KestrelAir.ka-sfs-watch", out first))
        {
            if (!first) return 0;
            Write("started");
            IntPtr h = IntPtr.Zero; int lastSent = -1; DateTime lastWrite = DateTime.MinValue;
            while (true)
            {
                int state = SfsRunning() ? 1 : 0;
                if (state != lastSent) Write("SFS Monitor " + (state == 1 ? "running -> SPAD panels off" : "closed -> SPAD panels on"));
                if (h == IntPtr.Zero) h = Connect();
                if (h != IntPtr.Zero && (state != lastSent || (DateTime.UtcNow - lastWrite).TotalSeconds >= 2))
                {
                    double v = state;
                    if (SetData(h, 1, 0, 0, 0, 8, ref v) != 0 || !Drain(h)) { Write("sim connection lost"); try { Close(h); } catch { } h = IntPtr.Zero; lastSent = -1; }
                    else { lastSent = state; lastWrite = DateTime.UtcNow; }
                }
                else if (h != IntPtr.Zero && !Drain(h)) { Write("sim closed"); try { Close(h); } catch { } h = IntPtr.Zero; lastSent = -1; }
                Thread.Sleep(1000);
            }
        }
    }

    static bool SfsRunning()
    {
        foreach (Process p in Process.GetProcesses())
            if (p.ProcessName.StartsWith("SFSmonitor", StringComparison.OrdinalIgnoreCase)) return true;
        return false;
    }

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
            if (mod == IntPtr.Zero) { Write("cannot load " + dll); return IntPtr.Zero; }
            Open = Get<OpenFn>(mod, "SimConnect_Open"); Close = Get<CloseFn>(mod, "SimConnect_Close");
            AddDef = Get<AddDefFn>(mod, "SimConnect_AddToDataDefinition"); SetData = Get<SetDataFn>(mod, "SimConnect_SetDataOnSimObject");
            Next = Get<DispatchFn>(mod, "SimConnect_GetNextDispatch");
        }
        IntPtr h;
        if (Open(out h, "KestrelAir SFS watch", IntPtr.Zero, 0, IntPtr.Zero, 0) != 0) return IntPtr.Zero;
        if (AddDef(h, 1, "L:KA_SFS_MONITOR", "number", 4, 0, 0xffffffff) != 0) { Close(h); return IntPtr.Zero; }
        Write("connected to MSFS");
        return h;
    }

    // Empty the SimConnect queue; false when the sim has said goodbye (SIMCONNECT_RECV_ID_QUIT = 3).
    static bool Drain(IntPtr h)
    {
        IntPtr data; uint size;
        for (int i = 0; i < 50 && Next(h, out data, out size) == 0; i++)
            if (size >= 12 && Marshal.ReadInt32(data, 8) == 3) return false;
        return true;
    }

    static T Get<T>(IntPtr mod, string name) { return (T)(object)Marshal.GetDelegateForFunctionPointer(GetProcAddress(mod, name), typeof(T)); }

    static void Write(string s) { try { File.AppendAllText(Log, DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss ") + s + Environment.NewLine); } catch { } }
}
