# One-time, permanent install: tells Windows to run every start of Neofly.exe through
# NeoflyPhoto.exe (Image File Execution Options). Works for any shortcut, taskbar pin,
# NeoFly's own restarts and future NeoFly updates - nothing in NeoFly's folder is touched.
# Needs admin once (UAC prompt). Undo with uninstall.ps1.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe  = Join-Path $here 'NeoflyPhoto.exe'
$key  = 'HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\Neofly.exe'
if (-not (Test-Path $exe)) { & (Join-Path $here 'build.ps1') }
$cmd  = "reg add `"$key`" /v Debugger /t REG_SZ /d `"\`"$exe\`"`" /f"
$p = Start-Process cmd.exe -ArgumentList "/c $cmd" -Verb RunAs -Wait -PassThru -WindowStyle Hidden
if ($p.ExitCode -eq 0) { "Installed: every NeoFly launch now uses your photo." } else { "Install failed or was cancelled (exit $($p.ExitCode))." }
