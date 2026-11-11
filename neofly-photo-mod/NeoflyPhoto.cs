// NeoflyPhoto - shows your own photo as your NeoFly pilot avatar.
//
// How it works (no NeoFly files are modified, so NeoFly updates don't break it):
//   1. This launcher creates an AppDomain rooted in the NeoFly install folder, using
//      NeoFly's own Neofly.exe.config, and runs the real Neofly.exe inside it.
//   2. Before NeoFly's Main runs, it swaps the ResourceManager behind
//      Neofly.Properties.Resources for a subclass that hands back your photo whenever
//      NeoFly asks for *your* avatar ("avatar_N"). Everything else passes through.
//   3. Your avatar number is followed live from NeoFly's Player object, so it keeps
//      working if you pick a different avatar in the Career panel.
// If anything about NeoFly changes in a future update, the hook logs it and NeoFly
// simply starts with its normal avatars - it never blocks NeoFly from running.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Resources;
using System.Runtime.CompilerServices;
using System.Text.RegularExpressions;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: AssemblyTitle("NeoFly Photo Avatar")]
[assembly: AssemblyVersion("1.0.0.0")]

namespace NeoflyPhoto
{
    public static class Launcher
    {
        const string LayersKey = @"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers";

        [STAThread]
        public static int Main(string[] args)
        {
            string self = Assembly.GetExecutingAssembly().Location;
            string selfDir = Path.GetDirectoryName(self);
            Config cfg = Config.Load(Path.Combine(selfDir, "config.ini"));

            string nfExe = Path.Combine(cfg.NeoflyDir, "Neofly.exe");

            // --repair: silent self-heal (runs at Windows logon). Re-points shortcuts and
            // ProgramStack entries that a NeoFly update or reinstall put back to Neofly.exe.
            if (args.Length > 0 && string.Equals(args[0], "--repair", StringComparison.OrdinalIgnoreCase))
            {
                int n = Shortcuts.Redirect(nfExe, self, cfg.StateDir) + ProgramStack.Redirect(self, cfg.StateDir);
                if (n > 0) Log.Write(cfg.StateDir, "Repair: fixed " + n + " launcher entr" + (n == 1 ? "y" : "ies"));
                return 0;
            }

            // When Windows routes Neofly.exe through us (Image File Execution Options), the
            // original command line arrives as: <path to Neofly.exe> <NeoFly's own args>.
            if (args.Length > 0 && args[0].EndsWith("Neofly.exe", StringComparison.OrdinalIgnoreCase))
            {
                if (File.Exists(args[0])) { nfExe = Path.GetFullPath(args[0]); cfg.NeoflyDir = Path.GetDirectoryName(nfExe); }
                var rest = new string[args.Length - 1];
                Array.Copy(args, 1, rest, 0, rest.Length);
                args = rest;
            }
            if (!File.Exists(nfExe))
            {
                MessageBox.Show("Neofly.exe not found in:\n" + cfg.NeoflyDir + "\n\nSet NeoflyDir in config.ini.",
                    "NeoFly Photo", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 1;
            }

            // NeoFly fixes Windows display scaling by adding a compatibility flag for Neofly.exe.
            // Mirror that flag onto this launcher so NeoFly looks identical when started from here.
            if (MirrorDpiFlags(nfExe, self))
            {
                Process.Start(new ProcessStartInfo(self, JoinArgs(args)) { WorkingDirectory = selfDir, UseShellExecute = false });
                return 0;
            }

            Log.Write(cfg.StateDir, "Launcher start, photo=" + cfg.Photo + (File.Exists(cfg.Photo) ? "" : " (MISSING)"));
            Shortcuts.Redirect(nfExe, self, cfg.StateDir); // NeoFly updates can recreate the stock shortcuts
            ProgramStack.Redirect(self, cfg.StateDir);

            Environment.CurrentDirectory = cfg.NeoflyDir; // NeoFly opens its DB relative to this

            var setup = new AppDomainSetup();
            setup.ApplicationBase = cfg.NeoflyDir.TrimEnd('\\') + "\\";
            setup.ConfigurationFile = nfExe + ".config";
            setup.ApplicationName = "Neofly";
            AppDomain dom = AppDomain.CreateDomain("Neofly", null, setup);

            try
            {
                var hook = (Hook)dom.CreateInstanceFromAndUnwrap(self, typeof(Hook).FullName);
                hook.Install(cfg.Photo, cfg.Avatar, cfg.CropX, cfg.CropY, cfg.StateDir);
            }
            catch (Exception ex)
            {
                Log.Write(cfg.StateDir, "Hook install failed, starting NeoFly unmodified: " + ex);
            }

            DateTime started = DateTime.UtcNow;
            try
            {
                return dom.ExecuteAssembly(nfExe, args);
            }
            catch (Exception ex)
            {
                Log.Write(cfg.StateDir, "NeoFly failed inside the launcher: " + ex);
                // If it died straight away, start NeoFly normally so you're never locked out.
                if (DateTime.UtcNow - started < TimeSpan.FromSeconds(20))
                {
                    if (Ifeo.IsRedirected())
                        MessageBox.Show("NeoFly couldn't start with the photo mod.\nDetails: " + Path.Combine(cfg.StateDir, "NeoflyPhoto.log") +
                            "\n\nTo turn the mod off, run uninstall.ps1 in the mod folder.", "NeoFly Photo", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    else
                        Process.Start(new ProcessStartInfo(nfExe, JoinArgs(args)) { WorkingDirectory = cfg.NeoflyDir, UseShellExecute = false });
                }
                return 1;
            }
        }

        static bool MirrorDpiFlags(string nfExe, string self)
        {
            try
            {
                using (RegistryKey k = Registry.CurrentUser.CreateSubKey(LayersKey))
                {
                    string want = k.GetValue(nfExe) as string;
                    if (string.IsNullOrEmpty(want)) return false;
                    string have = k.GetValue(self) as string;
                    if (string.Equals(want, have, StringComparison.OrdinalIgnoreCase)) return false;
                    k.SetValue(self, want);
                    return true; // flag only applies to a fresh process
                }
            }
            catch { return false; }
        }

        static string JoinArgs(string[] args)
        {
            var parts = new List<string>();
            foreach (string a in args) parts.Add("\"" + a.Replace("\"", "\\\"") + "\"");
            return string.Join(" ", parts.ToArray());
        }
    }

    public class Config
    {
        public string NeoflyDir;
        public string Photo;
        public string Avatar = "auto";
        public double CropX = 0.5, CropY = 0.5;
        public string StateDir;

        public static Config Load(string path)
        {
            var c = new Config();
            string baseDir = Path.GetDirectoryName(path);
            c.NeoflyDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Neofly");
            c.Photo = Path.Combine(baseDir, "photo.jpg");
            c.StateDir = baseDir;
            if (File.Exists(path))
            {
                foreach (string raw in File.ReadAllLines(path))
                {
                    string line = raw.Trim();
                    if (line.Length == 0 || line.StartsWith(";") || line.StartsWith("#")) continue;
                    int eq = line.IndexOf('=');
                    if (eq < 0) continue;
                    string key = line.Substring(0, eq).Trim().ToLowerInvariant();
                    string val = Environment.ExpandEnvironmentVariables(line.Substring(eq + 1).Trim().Trim('"'));
                    if (key == "neoflydir") c.NeoflyDir = Path.GetFullPath(Path.Combine(baseDir, val));
                    else if (key == "photo") c.Photo = Path.GetFullPath(Path.Combine(baseDir, val));
                    else if (key == "avatar") c.Avatar = val;
                    else if (key == "cropx") c.CropX = Clamp01(val, 0.5);
                    else if (key == "cropy") c.CropY = Clamp01(val, 0.5);
                }
            }
            return c;
        }

        static double Clamp01(string s, double dflt)
        {
            double d;
            if (!double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out d)) return dflt;
            return Math.Max(0, Math.Min(1, d));
        }
    }

    // Points every NeoFly shortcut (Desktop, Start Menu, taskbar pins) at this launcher.
    public static class Shortcuts
    {
        public static int Redirect(string nfExe, string self, string logDir)
        {
            int changed = 0;
            try
            {
                Type shType = Type.GetTypeFromProgID("WScript.Shell");
                object sh = Activator.CreateInstance(shType);
                string appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
                string[] roots = {
                    Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),
                    Environment.GetFolderPath(Environment.SpecialFolder.Programs),
                    Path.Combine(appData, @"Microsoft\Internet Explorer\Quick Launch"),
                };
                foreach (string root in roots)
                {
                    if (!Directory.Exists(root)) continue;
                    foreach (string lnk in Directory.GetFiles(root, "*.lnk", SearchOption.AllDirectories))
                    {
                        try
                        {
                            object s = shType.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, sh, new object[] { lnk });
                            Type st = s.GetType();
                            string target = st.InvokeMember("TargetPath", BindingFlags.GetProperty, null, s, null) as string;
                            if (!string.Equals(target, nfExe, StringComparison.OrdinalIgnoreCase)) continue;
                            st.InvokeMember("TargetPath", BindingFlags.SetProperty, null, s, new object[] { self });
                            st.InvokeMember("WorkingDirectory", BindingFlags.SetProperty, null, s, new object[] { Path.GetDirectoryName(self) });
                            st.InvokeMember("IconLocation", BindingFlags.SetProperty, null, s, new object[] { nfExe + ",0" });
                            st.InvokeMember("Save", BindingFlags.InvokeMethod, null, s, null);
                            changed++;
                            Log.Write(logDir, "Shortcut now uses the photo mod: " + lnk);
                        }
                        catch { }
                    }
                }
            }
            catch (Exception ex) { Log.Write(logDir, "Shortcut fix failed: " + ex.Message); }
            return changed;
        }
    }

    // Points ProgramStack items that start Neofly.exe at this launcher instead
    // (%APPDATA%\Kestrel Kinetics\ProgramStack\stacks.json). Text-level edit so the rest of the
    // file is untouched; WindowProcessName follows, because NeoFly now runs inside NeoflyPhoto.exe.
    public static class ProgramStack
    {
        public static int Redirect(string self, string logDir)
        {
            try
            {
                string f = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                    @"Kestrel Kinetics\ProgramStack\stacks.json");
                if (!File.Exists(f)) return 0;
                string text = File.ReadAllText(f);
                string selfJ = self.Replace("\\", "\\\\");
                string dirJ = Path.GetDirectoryName(self).Replace("\\", "\\\\");
                int n = 0;
                // One item object = { ... } with no nested braces.
                string fixedText = Regex.Replace(text, "\\{[^{}]*\"Target\"\\s*:\\s*\"[^\"]*\\\\\\\\Neofly\\.exe\"[^{}]*\\}", m =>
                {
                    n++;
                    string s = m.Value;
                    s = Regex.Replace(s, "(\"Target\"\\s*:\\s*)\"[^\"]*\"", r => r.Groups[1].Value + "\"" + selfJ + "\"");
                    s = Regex.Replace(s, "(\"WorkingDirectory\"\\s*:\\s*)\"[^\"]*\"", r => r.Groups[1].Value + "\"" + dirJ + "\"");
                    s = Regex.Replace(s, "(\"WindowProcessName\"\\s*:\\s*)\"Neofly\"", r => r.Groups[1].Value + "\"NeoflyPhoto\"", RegexOptions.IgnoreCase);
                    return s;
                }, RegexOptions.IgnoreCase);
                if (n == 0) return 0;
                File.Copy(f, f + ".bak", true);
                File.WriteAllText(f, fixedText, new System.Text.UTF8Encoding(false));
                Log.Write(logDir, "ProgramStack now uses the photo mod (" + n + " item" + (n == 1 ? "" : "s") + ")" +
                    (Process.GetProcessesByName("ProgramStack").Length > 0 ? " - restart ProgramStack to pick it up" : ""));
                return n;
            }
            catch (Exception ex) { Log.Write(logDir, "ProgramStack fix failed: " + ex.Message); return 0; }
        }
    }

    static class Ifeo
    {
        public static bool IsRedirected()
        {
            try
            {
                using (RegistryKey k = Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\Neofly.exe"))
                    return k != null && k.GetValue("Debugger") != null;
            }
            catch { return false; }
        }
    }

    static class Log
    {
        public static void Write(string dir, string msg)
        {
            try { File.AppendAllText(Path.Combine(dir, "NeoflyPhoto.log"), DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "  " + msg + Environment.NewLine); }
            catch { }
        }
    }

    // Lives inside the NeoFly AppDomain.
    public class Hook : MarshalByRefObject
    {
        internal static PhotoSource Photo;
        internal static string StateDir;
        bool done;

        public void Install(string photo, string avatarSetting, double cropX, double cropY, string stateDir)
        {
            StateDir = stateDir;
            Photo = new PhotoSource(photo, cropX, cropY);
            PlayerAvatar.Init(avatarSetting, stateDir);
            AppDomain.CurrentDomain.AssemblyLoad += OnAssemblyLoad;
            foreach (Assembly a in AppDomain.CurrentDomain.GetAssemblies()) TryPatch(a);
        }

        void OnAssemblyLoad(object sender, AssemblyLoadEventArgs e) { TryPatch(e.LoadedAssembly); }

        void TryPatch(Assembly asm)
        {
            if (done || !string.Equals(asm.GetName().Name, "Neofly", StringComparison.OrdinalIgnoreCase)) return;
            done = true;
            try
            {
                Type res = asm.GetType("Neofly.Properties.Resources", false);
                if (res == null)
                    foreach (Type t in SafeTypes(asm))
                        if (t.Name == "Resources" && t.Namespace != null && t.Namespace.EndsWith(".Properties")) { res = t; break; }
                if (res == null) { Log.Write(StateDir, "Resources class not found - NeoFly runs unmodified."); return; }

                FieldInfo field = null;
                foreach (FieldInfo f in res.GetFields(BindingFlags.Static | BindingFlags.NonPublic | BindingFlags.Public))
                    if (typeof(ResourceManager).IsAssignableFrom(f.FieldType)) { field = f; break; }
                if (field == null) { Log.Write(StateDir, "ResourceManager field not found - NeoFly runs unmodified."); return; }

                field.SetValue(null, new AvatarResourceManager(res.FullName, asm));
                Log.Write(StateDir, "Hooked " + asm.GetName().Name + " " + asm.GetName().Version + " (" + res.FullName + "." + field.Name + ")");
            }
            catch (Exception ex) { Log.Write(StateDir, "Patch failed - NeoFly runs unmodified: " + ex); }
        }

        internal static IEnumerable<Type> SafeTypes(Assembly a)
        {
            try { return a.GetTypes(); }
            catch (ReflectionTypeLoadException ex)
            {
                var l = new List<Type>();
                foreach (Type t in ex.Types) if (t != null) l.Add(t);
                return l;
            }
        }

        public override object InitializeLifetimeService() { return null; }
    }

    public class AvatarResourceManager : ResourceManager
    {
        static readonly Regex AvatarName = new Regex(@"^avatar_\d+$", RegexOptions.IgnoreCase);

        public AvatarResourceManager(string baseName, Assembly asm) : base(baseName, asm) { }

        public override object GetObject(string name) { return GetObject(name, null); }

        public override object GetObject(string name, CultureInfo culture)
        {
            object original = base.GetObject(name, culture);
            try
            {
                if (name != null && AvatarName.IsMatch(name) && PlayerAvatar.IsPlayer(name))
                {
                    Size size = new Size(250, 352);
                    Image img = original as Image;
                    if (img != null) size = img.Size;
                    Bitmap mine = Hook.Photo.Render(size);
                    if (mine != null)
                    {
                        if (img != null) img.Dispose();
                        return mine;
                    }
                }
            }
            catch (Exception ex) { Log.Write(Hook.StateDir, "GetObject(" + name + "): " + ex.Message); }
            return original;
        }
    }

    // Works out which "avatar_N" belongs to the logged-in pilot.
    static class PlayerAvatar
    {
        static string fixedName;      // from config, if set
        static string lastKnown;      // persisted so the login screen shows the photo too
        static string stateFile;
        static object holder;         // object with a Player-typed field (e.g. ApplicationController)
        static FieldInfo holderField;
        static DateTime nextSearch = DateTime.MinValue;
        static readonly object gate = new object();

        public static void Init(string setting, string stateDir)
        {
            stateFile = Path.Combine(stateDir, "last-avatar.txt");
            fixedName = Normalize(setting);
            try { if (File.Exists(stateFile)) lastKnown = Normalize(File.ReadAllText(stateFile).Trim()); } catch { }
        }

        static string Normalize(string s)
        {
            if (string.IsNullOrEmpty(s) || s.Equals("auto", StringComparison.OrdinalIgnoreCase)) return null;
            int n;
            if (int.TryParse(s, out n)) return "avatar_" + n;
            return s.ToLowerInvariant().StartsWith("avatar_") ? s.ToLowerInvariant() : null;
        }

        public static bool IsPlayer(string name)
        {
            string mine = fixedName ?? Current() ?? lastKnown;
            return mine != null && string.Equals(mine, name, StringComparison.OrdinalIgnoreCase);
        }

        static string Current()
        {
            lock (gate)
            {
                object player = null;
                if (holder != null) { try { player = holderField.GetValue(holder); } catch { holder = null; } }
                if (player == null && DateTime.UtcNow >= nextSearch)
                {
                    nextSearch = DateTime.UtcNow.AddSeconds(1);
                    Find();
                    if (holder != null) { try { player = holderField.GetValue(holder); } catch { } }
                }
                if (player == null) return null;

                PropertyInfo p = player.GetType().GetProperty("Avatar");
                string av = p == null ? null : Normalize(p.GetValue(player, null) as string);
                if (av != null && av != lastKnown)
                {
                    lastKnown = av;
                    try { File.WriteAllText(stateFile, av); } catch { }
                }
                return av;
            }
        }

        // Breadth-first walk from NeoFly's open windows through NeoFly-owned objects
        // until something holding a Neofly...Player field turns up.
        static void Find()
        {
            var queue = new Queue<KeyValuePair<object, int>>();
            var seen = new HashSet<object>(RefEq.Instance);
            try
            {
                FormCollection forms = Application.OpenForms;
                for (int i = 0; i < forms.Count; i++) queue.Enqueue(new KeyValuePair<object, int>(forms[i], 0));
            }
            catch { return; }

            int budget = 20000;
            while (queue.Count > 0 && budget-- > 0)
            {
                var item = queue.Dequeue();
                object o = item.Key;
                if (o == null || !seen.Add(o)) continue;

                var del = o as Delegate;
                if (del != null)
                {
                    foreach (Delegate d in del.GetInvocationList())
                        if (d.Target != null) queue.Enqueue(new KeyValuePair<object, int>(d.Target, item.Value + 1));
                    continue;
                }

                for (Type t = o.GetType(); t != null && t != typeof(object); t = t.BaseType)
                {
                    if (!IsNeofly(t) && item.Value > 0) break;
                    foreach (FieldInfo f in t.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly))
                    {
                        Type ft = f.FieldType;
                        if (ft.IsPrimitive || ft.IsEnum || ft == typeof(string) || ft.IsPointer) continue;
                        if (ft.Name == "Player" && IsNeofly(ft) && ft.GetProperty("Avatar") != null)
                        {
                            object v;
                            try { v = f.GetValue(o); } catch { continue; }
                            if (v != null) { holder = o; holderField = f; return; }
                            continue;
                        }
                        if (item.Value >= 6) continue;
                        if (!(IsNeofly(ft) || typeof(Delegate).IsAssignableFrom(ft) || ft.IsInterface || ft == typeof(object))) continue;
                        object child;
                        try { child = f.GetValue(o); } catch { continue; }
                        if (child != null && !child.GetType().IsValueType) queue.Enqueue(new KeyValuePair<object, int>(child, item.Value + 1));
                    }
                }
            }
        }

        static bool IsNeofly(Type t) { return t.Namespace != null && t.Namespace.StartsWith("Neofly", StringComparison.Ordinal); }

        class RefEq : IEqualityComparer<object>
        {
            public static readonly RefEq Instance = new RefEq();
            public new bool Equals(object a, object b) { return ReferenceEquals(a, b); }
            public int GetHashCode(object o) { return RuntimeHelpers.GetHashCode(o); }
        }
    }

    // Loads the photo (re-reading it if the file changes) and renders it cropped to the
    // exact size of the avatar it replaces.
    class PhotoSource
    {
        readonly string path;
        readonly double cropX, cropY;
        Bitmap photo;
        DateTime stamp;
        readonly object gate = new object();

        public PhotoSource(string path, double cropX, double cropY) { this.path = path; this.cropX = cropX; this.cropY = cropY; }

        public Bitmap Render(Size size)
        {
            lock (gate)
            {
                Bitmap src = Load();
                if (src == null || size.Width <= 0 || size.Height <= 0) return null;

                double target = (double)size.Width / size.Height;
                double srcAspect = (double)src.Width / src.Height;
                RectangleF crop;
                if (srcAspect > target)
                {
                    float w = (float)(src.Height * target);
                    crop = new RectangleF((float)((src.Width - w) * cropX), 0, w, src.Height);
                }
                else
                {
                    float h = (float)(src.Width / target);
                    crop = new RectangleF(0, (float)((src.Height - h) * cropY), src.Width, h);
                }

                var bmp = new Bitmap(size.Width, size.Height, PixelFormat.Format32bppArgb);
                using (Graphics g = Graphics.FromImage(bmp))
                using (var ia = new ImageAttributes())
                {
                    g.InterpolationMode = InterpolationMode.HighQualityBicubic;
                    g.PixelOffsetMode = PixelOffsetMode.HighQuality;
                    g.SmoothingMode = SmoothingMode.HighQuality;
                    g.CompositingQuality = CompositingQuality.HighQuality;
                    ia.SetWrapMode(WrapMode.TileFlipXY); // no dark fringe on the edges
                    g.DrawImage(src, new Rectangle(0, 0, size.Width, size.Height),
                        crop.X, crop.Y, crop.Width, crop.Height, GraphicsUnit.Pixel, ia);
                }
                return bmp;
            }
        }

        Bitmap Load()
        {
            try
            {
                if (!File.Exists(path)) { Log.Write(Hook.StateDir, "Photo not found: " + path); return photo; }
                DateTime t = File.GetLastWriteTimeUtc(path);
                if (photo != null && t == stamp) return photo;
                byte[] bytes = File.ReadAllBytes(path); // read fully so the file is never locked
                using (var ms = new MemoryStream(bytes))
                using (Image img = Image.FromStream(ms))
                {
                    var copy = new Bitmap(img.Width, img.Height, PixelFormat.Format32bppArgb);
                    using (Graphics g = Graphics.FromImage(copy)) g.DrawImage(img, 0, 0, img.Width, img.Height);
                    if (photo != null) photo.Dispose();
                    photo = copy;
                    stamp = t;
                }
            }
            catch (Exception ex) { Log.Write(Hook.StateDir, "Photo load failed: " + ex.Message); }
            return photo;
        }
    }
}
