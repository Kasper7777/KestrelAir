// ka-key: send a key combination as hardware scan codes, launched by SPAD.neXt "Run Program" actions.
// MSFS 2024 ignores a modifier (Shift/Alt/Ctrl) that arrives as a virtual key with no scan code, which is
// how SPAD's keyboard macros send it, so Alt+8 reaches the sim as a bare 8.  Measured 2026-11-04: VK-only
// Shift+N left the camera unchanged, the same combination as scan codes changed the view every time.
//
// The combination comes from the arguments or, so SPAD needs only a path, from the exe's own name:
//   ka-key-alt-8.exe   -> Alt+8      ka-key-shift-5.exe -> Shift+5      ka-key-ctrl-shift-f.exe -> Ctrl+Shift+F
// Modifiers go down first, then the key is held 120 ms, then everything is released in reverse order.
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Threading;

static class KaKey
{
    [StructLayout(LayoutKind.Sequential)] struct KEYBDINPUT { public ushort wVk, wScan; public uint dwFlags, time; public IntPtr dwExtraInfo; }
    [StructLayout(LayoutKind.Sequential)] struct MOUSEINPUT { public int dx, dy; public uint mouseData, dwFlags, time; public IntPtr dwExtraInfo; }
    [StructLayout(LayoutKind.Explicit)] struct UNION { [FieldOffset(0)] public KEYBDINPUT ki; [FieldOffset(0)] public MOUSEINPUT mi; }
    [StructLayout(LayoutKind.Sequential)] struct INPUT { public uint type; public UNION u; }
    [DllImport("user32.dll", SetLastError = true)] static extern uint SendInput(uint n, INPUT[] inputs, int size);
    const uint SCANCODE = 0x0008, KEYUP = 0x0002;

    static readonly Dictionary<string, ushort> Scan = new Dictionary<string, ushort>(StringComparer.OrdinalIgnoreCase)
    {
        {"shift", 0x2A}, {"alt", 0x38}, {"ctrl", 0x1D},
        {"1", 0x02}, {"2", 0x03}, {"3", 0x04}, {"4", 0x05}, {"5", 0x06}, {"6", 0x07}, {"7", 0x08}, {"8", 0x09}, {"9", 0x0A}, {"0", 0x0B},
        {"q", 0x10}, {"w", 0x11}, {"e", 0x12}, {"r", 0x13}, {"t", 0x14}, {"y", 0x15}, {"u", 0x16}, {"i", 0x17}, {"o", 0x18}, {"p", 0x19},
        {"a", 0x1E}, {"s", 0x1F}, {"d", 0x20}, {"f", 0x21}, {"g", 0x22}, {"h", 0x23}, {"j", 0x24}, {"k", 0x25}, {"l", 0x26},
        {"z", 0x2C}, {"x", 0x2D}, {"c", 0x2E}, {"v", 0x2F}, {"b", 0x30}, {"n", 0x31}, {"m", 0x32},
        {"back", 0x0E}, {"tab", 0x0F}, {"enter", 0x1C}, {"space", 0x39}, {"esc", 0x01},
    };

    static int Main(string[] args)
    {
        var parts = new List<string>(args);
        if (parts.Count == 0)
        {
            string self = System.IO.Path.GetFileNameWithoutExtension(Environment.GetCommandLineArgs()[0]).ToLowerInvariant();
            if (self.StartsWith("ka-key-")) parts.AddRange(self.Substring(7).Split('-'));
        }
        var codes = new List<ushort>();
        foreach (var p in parts) { ushort sc; if (!Scan.TryGetValue(p, out sc)) return 2; codes.Add(sc); }
        if (codes.Count == 0) return 1;
        for (int i = 0; i < codes.Count; i++) { Send(codes[i], false); Thread.Sleep(i == codes.Count - 1 ? 120 : 40); }
        for (int i = codes.Count - 1; i >= 0; i--) { Send(codes[i], true); if (i > 0) Thread.Sleep(30); }
        return 0;
    }

    static void Send(ushort scan, bool up)
    {
        var i = new INPUT[1];
        i[0].type = 1; i[0].u.ki.wScan = scan; i[0].u.ki.dwFlags = SCANCODE | (up ? KEYUP : 0);
        SendInput(1, i, Marshal.SizeOf(typeof(INPUT)));
    }
}
