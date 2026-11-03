// vPilot half of ka-menu (compiled together with ka-menu.cs).
// vPilot (32-bit WinForms) shows "Controllers In Range" in a native SysTreeView32:
//   Center / Approach/Departure / Tower / ... headings, each with children "CALLSIGN - 123.450".
// The tree lives in another process, so item text is read through memory allocated inside vPilot.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;

static class VPilot
{
    delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr p, EnumProc cb, IntPtr l);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder sb, int n);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, string l);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, StringBuilder l);
    [DllImport("user32.dll")] static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] static extern IntPtr SetFocus(IntPtr h);
    [DllImport("user32.dll")] static extern bool AttachThreadInput(uint a, uint b, bool attach);
    [DllImport("kernel32.dll")] static extern uint GetCurrentThreadId();
    [DllImport("kernel32.dll")] static extern IntPtr OpenProcess(uint a, bool i, uint pid);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
    [DllImport("kernel32.dll")] static extern IntPtr VirtualAllocEx(IntPtr p, IntPtr a, UIntPtr s, uint t, uint pr);
    [DllImport("kernel32.dll")] static extern bool VirtualFreeEx(IntPtr p, IntPtr a, UIntPtr s, uint t);
    [DllImport("kernel32.dll")] static extern bool WriteProcessMemory(IntPtr p, IntPtr a, byte[] b, UIntPtr n, out UIntPtr w);
    [DllImport("kernel32.dll")] static extern bool ReadProcessMemory(IntPtr p, IntPtr a, byte[] b, UIntPtr n, out UIntPtr r);
    [DllImport("kernel32.dll")] static extern bool IsWow64Process(IntPtr p, out bool w);

    const uint TVM_GETNEXTITEM = 0x110A, TVM_SELECTITEM = 0x110B, TVM_ENSUREVISIBLE = 0x1114, TVM_GETITEMW = 0x113E;
    const int TVGN_ROOT = 0, TVGN_NEXT = 1, TVGN_CHILD = 4, TVGN_CARET = 9;
    const uint WM_SETTEXT = 0x000C, WM_GETTEXT = 0x000D, WM_KEYDOWN = 0x0100, WM_KEYUP = 0x0101, WM_CHAR = 0x0102;
    static readonly Regex Freq = new Regex(@"(1[1-3]\d\.\d{2,3})\s*$");

    public static int Run(string mode, Process p)
    {
        IntPtr tree = Child(p.MainWindowHandle, "SysTreeView32");
        if (tree == IntPtr.Zero) return 1;
        IntPtr proc = OpenProcess(0x0438, false, (uint)p.Id);  // query + VM read/write/operation
        try
        {
            bool wow; IsWow64Process(proc, out wow);
            var items = new List<KeyValuePair<IntPtr, string>>();  // controllers only, in display order
            for (IntPtr head = Next(tree, TVGN_ROOT, IntPtr.Zero); head != IntPtr.Zero; head = Next(tree, TVGN_NEXT, head))
                for (IntPtr it = Next(tree, TVGN_CHILD, head); it != IntPtr.Zero; it = Next(tree, TVGN_NEXT, it))
                {
                    string text = Text(tree, proc, wow, it);
                    if (Freq.IsMatch(text)) items.Add(new KeyValuePair<IntPtr, string>(it, text));
                }
            if (items.Count == 0) return 0;
            IntPtr sel = Next(tree, TVGN_CARET, IntPtr.Zero);
            int at = items.FindIndex(kv => kv.Key == sel);

            if (mode == "select")
            {
                if (at < 0) return 0;
                Tune(p.MainWindowHandle, Freq.Match(items[at].Value).Groups[1].Value);
                return 0;
            }
            int to = at < 0 ? 0 : Math.Max(0, Math.Min(items.Count - 1, at + (mode == "next" ? 1 : -1)));
            // Focus the tree so vPilot draws the selection highlight (WinForms hides it when unfocused).
            uint dummy, uiThread = GetWindowThreadProcessId(tree, out dummy), me = GetCurrentThreadId();
            bool attached = AttachThreadInput(me, uiThread, true);
            SetFocus(tree);
            SendMessage(tree, TVM_SELECTITEM, (IntPtr)TVGN_CARET, items[to].Key);
            SendMessage(tree, TVM_ENSUREVISIBLE, IntPtr.Zero, items[to].Key);
            if (attached) AttachThreadInput(me, uiThread, false);
            return 0;
        }
        finally { CloseHandle(proc); }
    }

    // ".com1 <freq>" + Enter in vPilot's visible command box: vPilot's own tune command.
    static void Tune(IntPtr main, string freq)
    {
        IntPtr edit = Child(main, ".EDIT.");
        if (edit == IntPtr.Zero) return;
        var old = new StringBuilder(512);
        SendMessage(edit, WM_GETTEXT, (IntPtr)512, old);
        SendMessage(edit, WM_SETTEXT, IntPtr.Zero, ".com1 " + freq);
        PostMessage(edit, WM_KEYDOWN, (IntPtr)0x0D, (IntPtr)0x001C0001);
        PostMessage(edit, WM_CHAR, (IntPtr)0x0D, (IntPtr)0x001C0001);
        PostMessage(edit, WM_KEYUP, (IntPtr)0x0D, unchecked((IntPtr)0xC01C0001));
        if (old.Length > 0)
        {
            // Put back anything the pilot had half-typed once vPilot has consumed the command.
            System.Threading.Thread.Sleep(300);
            SendMessage(edit, WM_SETTEXT, IntPtr.Zero, old.ToString());
        }
    }

    static IntPtr Next(IntPtr tree, int how, IntPtr item) { return SendMessage(tree, TVM_GETNEXTITEM, (IntPtr)how, item); }

    static IntPtr Child(IntPtr parent, string classPart)
    {
        IntPtr found = IntPtr.Zero;
        EnumChildWindows(parent, (h, l) =>
        {
            var sb = new StringBuilder(256); GetClassName(h, sb, 256);
            if (sb.ToString().Contains(classPart) && IsWindowVisible(h)) { found = h; return false; }
            return true;
        }, IntPtr.Zero);
        return found;
    }

    static string Text(IntPtr tree, IntPtr proc, bool wow, IntPtr item)
    {
        int size = wow ? 40 : 56;  // TVITEMW in a 32-bit vs 64-bit target
        IntPtr mem = VirtualAllocEx(proc, IntPtr.Zero, (UIntPtr)(size + 1024), 0x3000, 0x04);
        if (mem == IntPtr.Zero) return "";
        try
        {
            var buf = new byte[size];
            BitConverter.GetBytes(0x0001).CopyTo(buf, 0);  // TVIF_TEXT
            long textPtr = mem.ToInt64() + size;
            if (wow) { BitConverter.GetBytes(item.ToInt32()).CopyTo(buf, 4); BitConverter.GetBytes((int)textPtr).CopyTo(buf, 16); BitConverter.GetBytes(511).CopyTo(buf, 20); }
            else { BitConverter.GetBytes(item.ToInt64()).CopyTo(buf, 8); BitConverter.GetBytes(textPtr).CopyTo(buf, 24); BitConverter.GetBytes(511).CopyTo(buf, 32); }
            UIntPtr n; WriteProcessMemory(proc, mem, buf, (UIntPtr)size, out n);
            SendMessage(tree, TVM_GETITEMW, IntPtr.Zero, mem);
            var text = new byte[1024]; ReadProcessMemory(proc, (IntPtr)textPtr, text, (UIntPtr)1024, out n);
            string s = Encoding.Unicode.GetString(text); int z = s.IndexOf('\0');
            return z >= 0 ? s.Substring(0, z) : s;
        }
        finally { VirtualFreeEx(proc, mem, UIntPtr.Zero, 0x8000); }
    }
}
