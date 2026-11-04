// ka-mouse: turns the VIRPIL MongoosT-50CM3 throttle's right-grip mini-stick into a mouse (2026-11-04).
//   Mini-stick (HID Rx/Ry, 0..60000, centre 30000) -> moves the Windows pointer, so MSFS shows its cursor.
//   Button 11 (front hat press), 8 and 13 (push down) -> left mouse button, held while pressed (drag works).
//   Button 9 (pull up) -> right mouse button.
// Button numbers and axes were recorded live on 2026-11-04 (watch-cm3-all.ps1). None are bound in SPAD or MSFS.
// Runs hidden in the background (single instance). Optional ka-mouse.ini next to the exe:
//   Speed=1400   (pixels per second at full deflection)   Deadzone=2500   InvertX=0   InvertY=0   Path=<HID path>
// Log: %TEMP%\ka-mouse.log. Build: csc -target:winexe -out:ka-mouse.exe ka-mouse.cs
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using Microsoft.Win32.SafeHandles;

static class KaMouse
{
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern SafeFileHandle CreateFile(string n, uint a, uint s, IntPtr p, uint c, uint f, IntPtr t);
    [DllImport("hid.dll")] static extern bool HidD_GetPreparsedData(SafeFileHandle h, out IntPtr p);
    [DllImport("hid.dll")] static extern int HidP_GetCaps(IntPtr p, byte[] caps);
    [DllImport("hid.dll")] static extern int HidP_GetUsageValue(int type, ushort page, ushort link, ushort usage, out uint v, IntPtr p, byte[] r, uint len);
    [DllImport("hid.dll")] static extern int HidP_GetUsages(int type, ushort page, ushort link, [Out] ushort[] u, ref uint c, IntPtr p, byte[] r, uint len);

    [StructLayout(LayoutKind.Sequential)] struct MOUSEINPUT { public int dx, dy; public uint mouseData, dwFlags, time; public IntPtr dwExtraInfo; }
    [StructLayout(LayoutKind.Sequential)] struct INPUT { public uint type; public MOUSEINPUT mi; }
    [DllImport("user32.dll", SetLastError = true)] static extern uint SendInput(uint n, INPUT[] inputs, int size);
    const uint MOVE = 0x0001, LEFTDOWN = 0x0002, LEFTUP = 0x0004, RIGHTDOWN = 0x0008, RIGHTUP = 0x0010;
    const int HIDP_STATUS_SUCCESS = 0x110000;

    static readonly int[] LeftButtons = { 11, 8, 13 };
    static readonly int[] RightButtons = { 9 };
    static string DevicePath = @"\\?\hid#vid_3344&pid_0194&mi_00#8&1d037022&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}";
    static double Speed = 1400, Deadzone = 2500;
    static bool InvertX, InvertY;
    static volatile int rx = 30000, ry = 30000;
    static readonly string LogPath = Path.Combine(Path.GetTempPath(), "ka-mouse.log");

    static int Main()
    {
        bool created;
        using (var mutex = new Mutex(true, "KestrelAir.ka-mouse", out created))
        {
            if (!created) return 0;
            LoadIni();
            Log("started");
            new Thread(MoveLoop) { IsBackground = true }.Start();
            while (true)
            {
                try { ReadDevice(); }
                catch (Exception e) { Log("device: " + e.Message); }
                rx = ry = 30000;
                Thread.Sleep(3000);  // throttle unplugged or not yet present: retry
            }
        }
    }

    static void LoadIni()
    {
        string ini = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "ka-mouse.ini");
        if (!File.Exists(ini)) return;
        foreach (string line in File.ReadAllLines(ini))
        {
            int eq = line.IndexOf('=');
            if (eq < 0) continue;
            string k = line.Substring(0, eq).Trim().ToLowerInvariant(), v = line.Substring(eq + 1).Trim();
            double d;
            if (k == "path") DevicePath = v;
            else if (k == "speed" && double.TryParse(v, out d)) Speed = d;
            else if (k == "deadzone" && double.TryParse(v, out d)) Deadzone = d;
            else if (k == "invertx") InvertX = v == "1";
            else if (k == "inverty") InvertY = v == "1";
        }
    }

    static void ReadDevice()
    {
        using (var h = CreateFile(DevicePath, 0x80000000, 3, IntPtr.Zero, 3, 0x40000000, IntPtr.Zero))
        {
            if (h.IsInvalid) throw new IOException("open failed " + Marshal.GetLastWin32Error());
            IntPtr pp; HidD_GetPreparsedData(h, out pp);
            var caps = new byte[64]; HidP_GetCaps(pp, caps);
            int len = BitConverter.ToUInt16(caps, 4);
            var held = new HashSet<int>();
            bool left = false, right = false;
            Log("throttle open");
            using (var s = new FileStream(h, FileAccess.Read, 4096, true))
            {
                while (true)
                {
                    var r = new byte[len];
                    int n = s.Read(r, 0, len);
                    if (n <= 0) throw new IOException("read ended");
                    uint v;
                    if (HidP_GetUsageValue(0, 1, 0, 0x33, out v, pp, r, (uint)n) == HIDP_STATUS_SUCCESS) rx = (int)v;
                    if (HidP_GetUsageValue(0, 1, 0, 0x34, out v, pp, r, (uint)n) == HIDP_STATUS_SUCCESS) ry = (int)v;
                    var u = new ushort[256]; uint c = 256;
                    if (HidP_GetUsages(0, 9, 0, u, ref c, pp, r, (uint)n) != HIDP_STATUS_SUCCESS) continue;
                    held.Clear();
                    for (int i = 0; i < c; i++) held.Add(u[i]);
                    bool l = false, rt = false;
                    foreach (int b in LeftButtons) l |= held.Contains(b);
                    foreach (int b in RightButtons) rt |= held.Contains(b);
                    if (l != left) { Send(0, 0, l ? LEFTDOWN : LEFTUP); left = l; }
                    if (rt != right) { Send(0, 0, rt ? RIGHTDOWN : RIGHTUP); right = rt; }
                }
            }
        }
    }

    // 100 Hz: pointer speed grows with the square of deflection beyond the dead zone, for fine aiming near centre.
    static void MoveLoop()
    {
        double fx = 0, fy = 0;
        while (true)
        {
            Thread.Sleep(10);
            double vx = Axis(rx), vy = -Axis(ry);  // stick up (high Ry) moves the pointer up
            if (InvertX) vx = -vx;
            if (InvertY) vy = -vy;
            fx += vx * Speed / 100; fy += vy * Speed / 100;
            int dx = (int)fx, dy = (int)fy;
            if (dx == 0 && dy == 0) continue;
            fx -= dx; fy -= dy;
            Send(dx, dy, MOVE);
        }
    }

    static double Axis(int raw)
    {
        double d = raw - 30000.0, a = Math.Abs(d);
        if (a <= Deadzone) return 0;
        double t = Math.Min(1.0, (a - Deadzone) / (30000.0 - Deadzone));
        return Math.Sign(d) * t * t;
    }

    static void Send(int dx, int dy, uint flags)
    {
        var input = new INPUT[1];
        input[0].type = 0;
        input[0].mi = new MOUSEINPUT { dx = dx, dy = dy, dwFlags = flags };
        SendInput(1, input, Marshal.SizeOf(typeof(INPUT)));
    }

    static void Log(string s)
    {
        try { File.AppendAllText(LogPath, DateTime.Now.ToString("s") + " " + s + Environment.NewLine); } catch { }
    }
}
