// ka-menu: drive BeyondATC's reply-option list from a WarBRD grip wheel (launched by SPAD "Run Program").
// When vPilot is the foreground window the same three exes drive vPilot instead:
//   next/prev selects the next/previous controller in "Controllers In Range" (category headings skipped),
//   select types ".com1 <frequency>" into vPilot's command box and presses Enter (vPilot's own tune command).
//   ka-menu-next.exe    wheel down  -> pointer to the next reply row (scrolls the list at the bottom edge)
//   ka-menu-prev.exe    wheel up    -> pointer to the previous reply row (scrolls at the top edge)
//   ka-menu-select.exe  wheel press -> click the highlighted reply, then put the pointer and focus back
// BeyondATC's reply list is mouse-only (no keyboard/joystick navigation), so the helper moves the real
// pointer over the list; BeyondATC's own hover highlight shows the current choice.
//
// Geometry is measured in client pixels of a 719x649 BeyondATC window and scaled by client height.
// Override in ka-menu.ini next to the exe (key=value): RowPitch, FirstRowFromBottom, Rows, X, Scale.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;

static class KaMenu
{
    [StructLayout(LayoutKind.Sequential)] struct RECT { public int L, T, R, B; }
    [StructLayout(LayoutKind.Sequential)] struct POINT { public int X, Y; }
    [StructLayout(LayoutKind.Sequential)] struct MOUSEINPUT { public int dx, dy; public uint mouseData, dwFlags, time; public IntPtr extra; }
    [StructLayout(LayoutKind.Sequential)] struct INPUT { public uint type; public MOUSEINPUT mi; }
    delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] static extern IntPtr GetWindow(IntPtr h, uint cmd);
    [DllImport("user32.dll")] static extern int GetWindowTextLength(IntPtr h);
    [DllImport("user32.dll")] static extern bool GetClientRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] static extern bool ClientToScreen(IntPtr h, ref POINT p);
    [DllImport("user32.dll")] static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] static extern bool IsWindow(IntPtr h);
    [DllImport("user32.dll")] static extern bool AttachThreadInput(uint a, uint b, bool attach);
    [DllImport("kernel32.dll")] static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] static extern uint SendInput(uint n, INPUT[] i, int size);
    [DllImport("user32.dll")] static extern IntPtr SetThreadDpiAwarenessContext(IntPtr c);
    const uint LEFTDOWN = 0x0002, LEFTUP = 0x0004, WHEEL = 0x0800;

    static double RowPitch = 18.6, FirstRowFromBottom = 101, ListX = 120, Scale = 0;
    static int Rows = 4;
    static readonly string StateFile = Path.Combine(Path.GetTempPath(), "ka-menu-state.txt");

    static int Main(string[] args)
    {
        SetThreadDpiAwarenessContext((IntPtr)(-4));  // per-monitor v2: work in physical pixels
        string mode = args.Length > 0 ? args[0] : Path.GetFileNameWithoutExtension(Environment.GetCommandLineArgs()[0]);
        mode = mode.ToLowerInvariant();
        mode = mode.EndsWith("next") ? "next" : mode.EndsWith("prev") ? "prev" : mode.EndsWith("select") ? "select" : mode;
        LoadIni();
        using (var mutex = new Mutex(false, "Local\\KestrelAir.ka-menu"))
        {
            // Fast wheel spins launch several copies at once; run them one at a time.
            try { mutex.WaitOne(2000); } catch (AbandonedMutexException) { }
            try { return Run(mode); } finally { try { mutex.ReleaseMutex(); } catch { } }
        }
    }

    static int Run(string mode)
    {
        // vPilot in front: the wheel drives vPilot's "Controllers In Range" list instead of BeyondATC.
        uint fgPid; GetWindowThreadProcessId(GetForegroundWindow(), out fgPid);
        foreach (Process p in Process.GetProcessesByName("vPilot"))
            if ((uint)p.Id == fgPid) return VPilot.Run(mode, p);

        IntPtr win = FindWindow("BeyondATC");
        if (win == IntPtr.Zero) return 1;
        RECT c; GetClientRect(win, out c);
        double s = Scale > 0 ? Scale : c.B / 649.0;
        POINT origin = new POINT(); ClientToScreen(win, ref origin);
        int x = origin.X + (int)Math.Round(ListX * s);
        Func<int, int> rowY = i => origin.Y + c.B - (int)Math.Round((FirstRowFromBottom - i * RowPitch) * s);
        int top = rowY(0) - (int)(RowPitch * s / 2), bottom = rowY(Rows - 1) + (int)(RowPitch * s / 2);

        POINT cur; GetCursorPos(out cur);
        bool inList = cur.X >= origin.X && cur.X <= origin.X + (int)(240 * s) && cur.Y >= top && cur.Y <= bottom;
        int row = inList ? (int)Math.Round((cur.Y - rowY(0)) / (RowPitch * s)) : -1;

        if (mode == "select")
        {
            if (!inList) return 0;  // nothing highlighted yet: ignore stray presses
            Mouse(LEFTDOWN, 0); Thread.Sleep(40); Mouse(LEFTUP, 0); Thread.Sleep(80);
            RestoreHome();
            return 0;
        }

        if (!inList)
        {
            SaveHome(cur);
            SetCursorPos(x, rowY(0));  // start on the first visible reply
            return 0;
        }
        int next = row + (mode == "next" ? 1 : -1);
        if (next < 0) { SetCursorPos(x, rowY(0)); Mouse(WHEEL, 120); }
        else if (next >= Rows) { SetCursorPos(x, rowY(Rows - 1)); Mouse(WHEEL, unchecked((uint)-120)); }
        else SetCursorPos(x, rowY(next));
        return 0;
    }

    static void Mouse(uint flags, uint data)
    {
        var input = new INPUT { type = 0, mi = new MOUSEINPUT { dwFlags = flags, mouseData = data } };
        SendInput(1, new[] { input }, Marshal.SizeOf(typeof(INPUT)));
    }

    static void SaveHome(POINT p)
    {
        try { File.WriteAllText(StateFile, p.X + " " + p.Y + " " + GetForegroundWindow().ToInt64()); } catch { }
    }

    static void RestoreHome()
    {
        string[] parts;
        try { parts = File.ReadAllText(StateFile).Split(' '); File.Delete(StateFile); } catch { return; }
        if (parts.Length < 3) return;
        SetCursorPos(int.Parse(parts[0]), int.Parse(parts[1]));
        IntPtr prev = new IntPtr(long.Parse(parts[2]));
        if (prev == IntPtr.Zero || !IsWindow(prev)) return;
        uint dummy;
        uint fg = GetWindowThreadProcessId(GetForegroundWindow(), out dummy), me = GetCurrentThreadId();
        bool attached = fg != 0 && fg != me && AttachThreadInput(me, fg, true);
        SetForegroundWindow(prev);
        if (attached) AttachThreadInput(me, fg, false);
    }

    static IntPtr FindWindow(string process)
    {
        var pids = new HashSet<uint>();
        foreach (Process p in Process.GetProcessesByName(process)) pids.Add((uint)p.Id);
        IntPtr found = IntPtr.Zero;
        if (pids.Count == 0) return found;
        EnumWindows((h, l) =>
        {
            uint pid; GetWindowThreadProcessId(h, out pid);
            if (pids.Contains(pid) && GetWindow(h, 4) == IntPtr.Zero && GetWindowTextLength(h) > 0 && IsWindowVisible(h) && !IsIconic(h))
            { found = h; return false; }
            return true;
        }, IntPtr.Zero);
        return found;
    }

    static void LoadIni()
    {
        string ini = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "ka-menu.ini");
        if (!File.Exists(ini)) return;
        foreach (string line in File.ReadAllLines(ini))
        {
            string[] kv = line.Split('=');
            if (kv.Length != 2) continue;
            double v;
            if (!double.TryParse(kv[1].Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out v)) continue;
            switch (kv[0].Trim().ToLowerInvariant())
            {
                case "rowpitch": RowPitch = v; break;
                case "firstrowfrombottom": FirstRowFromBottom = v; break;
                case "rows": Rows = (int)v; break;
                case "x": ListX = v; break;
                case "scale": Scale = v; break;
            }
        }
    }
}
