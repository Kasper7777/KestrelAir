// ka-front: window helper launched by SPAD.neXt "Run Program" actions from the WarBRD grips.
//   ka-front-vpilot.exe     -> bring the vPilot window to the front
//   ka-front-beyondatc.exe  -> bring the BeyondATC window to the front
//   ka-front.exe <process>  -> same, for any process name (without .exe)
// If the target is already the foreground window, focus goes back to MSFS instead, so one button toggles.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

static class KaFront
{
    delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] static extern int GetWindowTextLength(IntPtr h);
    [DllImport("user32.dll")] static extern IntPtr GetWindow(IntPtr h, uint cmd);
    [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] static extern bool BringWindowToTop(IntPtr h);
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] static extern bool AttachThreadInput(uint a, uint b, bool attach);
    [DllImport("kernel32.dll")] static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
    const int SW_RESTORE = 9, SW_SHOW = 5;
    const uint GW_OWNER = 4, KEYUP = 0x0002;
    const byte VK_MENU = 0x12;

    static readonly Dictionary<string, string[]> Targets = new Dictionary<string, string[]>(StringComparer.OrdinalIgnoreCase)
    {
        { "vpilot", new[] { "vPilot" } },
        { "beyondatc", new[] { "BeyondATC" } },
        { "msfs", new[] { "FlightSimulator2024", "FlightSimulator" } },
    };

    static int Main(string[] args)
    {
        string key = args.Length > 0 ? args[0] : null;
        if (key == null)
        {
            string self = System.IO.Path.GetFileNameWithoutExtension(Environment.GetCommandLineArgs()[0]);
            int dash = self.IndexOf('-', "ka-front".Length);
            key = dash >= 0 ? self.Substring(dash + 1) : "vpilot";
        }
        string[] names;
        if (!Targets.TryGetValue(key, out names)) names = new[] { key };

        IntPtr target = FindWindow(names);
        if (target == IntPtr.Zero) return 1;  // app not running: do nothing

        uint fgPid, targetPid;
        GetWindowThreadProcessId(GetForegroundWindow(), out fgPid);
        GetWindowThreadProcessId(target, out targetPid);
        if (fgPid == targetPid)
        {
            IntPtr sim = FindWindow(Targets["msfs"]);
            if (sim != IntPtr.Zero) Activate(sim);
            return 0;
        }
        Activate(target);
        return 0;
    }

    static IntPtr FindWindow(string[] processNames)
    {
        var pids = new HashSet<uint>();
        foreach (string n in processNames)
            foreach (Process p in Process.GetProcessesByName(n)) pids.Add((uint)p.Id);
        if (pids.Count == 0) return IntPtr.Zero;
        IntPtr best = IntPtr.Zero;
        EnumWindows((h, l) =>
        {
            uint pid;
            GetWindowThreadProcessId(h, out pid);
            if (!pids.Contains(pid) || GetWindow(h, GW_OWNER) != IntPtr.Zero || GetWindowTextLength(h) == 0) return true;
            if (IsWindowVisible(h) || IsIconic(h)) { best = h; return false; }  // EnumWindows is top-down Z order
            return true;
        }, IntPtr.Zero);
        return best;
    }

    static void Activate(IntPtr h)
    {
        if (IsIconic(h)) ShowWindow(h, SW_RESTORE); else ShowWindow(h, SW_SHOW);
        // Windows blocks background processes from taking focus. Try thread attachment first; only if that
        // is refused, tap Alt (the documented way to lift the foreground lock) and try again.
        if (TryActivate(h)) return;
        keybd_event(VK_MENU, 0, 0, UIntPtr.Zero);
        keybd_event(VK_MENU, 0, KEYUP, UIntPtr.Zero);
        TryActivate(h);
    }

    static bool TryActivate(IntPtr h)
    {
        uint dummy;
        uint fgThread = GetWindowThreadProcessId(GetForegroundWindow(), out dummy);
        uint me = GetCurrentThreadId();
        bool attached = fgThread != 0 && fgThread != me && AttachThreadInput(me, fgThread, true);
        BringWindowToTop(h);
        SetForegroundWindow(h);
        if (attached) AttachThreadInput(me, fgThread, false);
        Thread.Sleep(30);
        return GetForegroundWindow() == h;
    }
}
