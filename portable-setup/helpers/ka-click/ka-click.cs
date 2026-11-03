// ka-click: mouse helper launched by SPAD.neXt "Run Program" actions.
//   ka-click down   -> move the pointer to the centre of the foreground window and press the left button
//   ka-click up     -> release the left button
//   ka-click click  -> down + up
// Gives a WarBRD MiniStick click the role of the PlayStation Cross button: operate what is in the middle of the view.
using System;
using System.Runtime.InteropServices;
using System.Threading;

static class KaClick
{
    [StructLayout(LayoutKind.Sequential)] struct RECT { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)] struct POINT { public int X, Y; }
    [StructLayout(LayoutKind.Sequential)] struct MOUSEINPUT { public int dx, dy; public uint mouseData, dwFlags, time; public IntPtr dwExtraInfo; }
    [StructLayout(LayoutKind.Sequential)] struct INPUT { public uint type; public MOUSEINPUT mi; }
    [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] static extern bool GetClientRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] static extern bool ClientToScreen(IntPtr h, ref POINT p);
    [DllImport("user32.dll")] static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll", SetLastError = true)] static extern uint SendInput(uint n, INPUT[] inputs, int size);
    const uint LEFTDOWN = 0x0002, LEFTUP = 0x0004;

    static int Main(string[] args)
    {
        // Mode comes from the first argument, or from the executable's own name (ka-click-down.exe / ka-click-up.exe),
        // so SPAD's Run Program action needs only a path and no argument field.
        string mode = args.Length > 0 ? args[0].ToLowerInvariant() : "click";
        if (args.Length == 0)
        {
            string self = System.IO.Path.GetFileNameWithoutExtension(Environment.GetCommandLineArgs()[0]).ToLowerInvariant();
            if (self.EndsWith("-down")) mode = "down"; else if (self.EndsWith("-up")) mode = "up";
        }
        if (mode == "down" || mode == "click")
        {
            IntPtr h = GetForegroundWindow();
            RECT r; POINT p = new POINT();
            if (h != IntPtr.Zero && GetClientRect(h, out r))
            {
                p.X = (r.Right - r.Left) / 2; p.Y = (r.Bottom - r.Top) / 2;
                ClientToScreen(h, ref p);
                SetCursorPos(p.X, p.Y);
                Thread.Sleep(30); // let the sim register the hover before the press
            }
            Send(LEFTDOWN);
        }
        if (mode == "up" || mode == "click")
        {
            if (mode == "click") Thread.Sleep(60);
            Send(LEFTUP);
        }
        return 0;
    }

    static void Send(uint flag)
    {
        var i = new INPUT[1];
        i[0].type = 0; i[0].mi.dwFlags = flag;
        SendInput(1, i, Marshal.SizeOf(typeof(INPUT)));
    }
}
