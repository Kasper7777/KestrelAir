' Kestrel Air Logbook - double-click (or use the desktop shortcut).
' Rebuilds from NeoFly + your MSFS screenshots and opens the map in your browser.
' Runs hidden; it stops by itself a few minutes after you close the tab.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
here = fso.GetParentFolderName(WScript.ScriptFullName)
uv = sh.ExpandEnvironmentStrings("%USERPROFILE%\.local\bin\uv.exe")
If Not fso.FileExists(uv) Then uv = "uv"
sh.CurrentDirectory = here
sh.Run """" & uv & """ run --no-project --with pillow pythonw """ & here & "\pipeline\serve.py""", 0, False
