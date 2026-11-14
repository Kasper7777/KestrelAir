// Kestrel Air Logbook.exe - the button you click.
// Lives in the logbook folder and works wherever the repo is cloned:
//   1. if the logbook is already open, just shows it again
//   2. finds uv (installs it once, with permission, on a new PC)
//   3. starts pipeline/serve.py hidden; it rebuilds from NeoFly + screenshots
//      (or the repo's backup folder) and opens the browser
// Build: powershell -File pipeline\launcher\build.ps1
using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Threading;
using System.Windows.Forms;

static class Launcher
{
    const string Url = "http://127.0.0.1:8787/";
    const string Title = "Kestrel Air Logbook";

    [STAThread]
    static int Main(string[] args)
    {
        string dir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');
        string serve = Path.Combine(dir, @"pipeline\serve.py");
        if (!File.Exists(serve))
        {
            Say("Can't find pipeline\\serve.py.\n\nKeep \"Kestrel Air Logbook.exe\" inside the logbook folder (you can put a shortcut to it anywhere).");
            return 1;
        }
        if (Alive()) { Open(); return 0; }

        string uv = FindUv();
        if (uv == null)
        {
            var ok = MessageBox.Show("First time on this PC: the logbook needs \"uv\", a small free Python runner (astral.sh).\n\nInstall it now? It takes about a minute.",
                Title, MessageBoxButtons.YesNo, MessageBoxIcon.Question);
            if (ok != DialogResult.Yes) return 1;
            var inst = Run("powershell.exe", "-NoProfile -ExecutionPolicy ByPass -Command \"irm https://astral.sh/uv/install.ps1 | iex\"", dir);
            inst.WaitForExit();
            uv = FindUv();
            if (uv == null) { Say("uv didn't install. Check the internet connection and try again."); return 1; }
        }

        var p = Run(uv, "run --no-project --with pillow --with pypdfium2 pythonw \"" + serve + "\"", dir);
        // serve.py opens the browser itself; wait only to catch a failed start
        // (the first run on a new PC downloads Python, so allow a few minutes)
        for (int i = 0; i < 360; i++)
        {
            Thread.Sleep(500);
            if (Alive()) return 0;
            if (p.HasExited) break;
        }
        Say("The logbook didn't start.\n\nDetails: " + Path.Combine(dir, "logbook.log"));
        return 1;
    }

    static Process Run(string exe, string args, string dir)
    {
        return Process.Start(new ProcessStartInfo(exe, args)
        {
            WorkingDirectory = dir, UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden,
        });
    }

    static string FindUv()
    {
        string home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string[] spots = {
            Path.Combine(home, @".local\bin\uv.exe"), Path.Combine(home, @".cargo\bin\uv.exe"),
            Path.Combine(local, @"Microsoft\WinGet\Links\uv.exe"), Path.Combine(local, @"Programs\uv\uv.exe"),
        };
        foreach (string s in spots) if (File.Exists(s)) return s;
        foreach (string d in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(';'))
        {
            try { string c = Path.Combine(d.Trim(), "uv.exe"); if (File.Exists(c)) return c; } catch { }
        }
        return null;
    }

    static bool Alive()
    {
        try
        {
            var r = (HttpWebRequest)WebRequest.Create(Url + "__alive");
            r.Timeout = 800; r.Proxy = null;
            using (var resp = r.GetResponse()) return true;
        }
        catch { return false; }
    }

    static void Open() { try { Process.Start(Url); } catch { } }

    static void Say(string msg) { MessageBox.Show(msg, Title, MessageBoxButtons.OK, MessageBoxIcon.Warning); }
}
