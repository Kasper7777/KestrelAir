# KestrelAir one-shot setup for a new PC (updated 2026-11-04). Double-click Install-KestrelAir.cmd.
# Re-running is safe: everything it replaces is backed up to install-backup-<date>\ first.
param([string]$SpadDirectory = 'C:\Program Files\SPAD.neXt', [string]$FsuipcDirectory = 'C:\FSUIPC7')
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$helpers = Join-Path $root 'helpers'
function Step($text) { Write-Host "`n== $text" -ForegroundColor Cyan }
function Note($text) { Write-Host "   $text" }
function Todo($text) { $script:todo += $text; Write-Host "   TODO: $text" -ForegroundColor Yellow }
$todo = @()

# Elevate (needed for SPAD's Program Files vJoy library and the vJoy installer).
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -NoExit -File `"$PSCommandPath`" -SpadDirectory `"$SpadDirectory`" -FsuipcDirectory `"$FsuipcDirectory`""
    return
}

Step 'Closing SPAD, MSFS, vPilot, BeyondATC and the KestrelAir helpers (they save settings on exit)'
$apps = 'SPAD.neXt', 'FlightSimulator2024', 'FlightSimulator', 'vPilot', 'BeyondATC', 'ka-mouse', 'ka-sfs-watch', 'ka-drone-leds'
$running = Get-Process $apps -ErrorAction SilentlyContinue
if ($running) {
    Note ("Running: " + (($running | Select-Object -ExpandProperty Name -Unique) -join ', '))
    Read-Host '   Save anything you need, then press Enter to close them'
    $running | Stop-Process -Force; Start-Sleep 3
}

Step 'vJoy driver'
$driverDll = 'C:\Program Files\vJoy\x64\vJoyInterface.dll'
if (!(Test-Path $driverDll)) {
    Note 'vJoy is not installed: starting the included vJoy 2.2.2 installer.'
    Start-Process (Join-Path $root 'vJoySetup_v2.2.2.0_Win10_Win11.exe') -Wait
    if (!(Test-Path $driverDll)) { throw 'vJoy did not install. Install it, reboot, then run this setup again.' }
    Todo 'Reboot after this setup finishes (vJoy was just installed).'
}
$spadDll = Join-Path $SpadDirectory 'vJoyInterface.dll'
if (!(Test-Path $spadDll)) { throw "SPAD.neXt not found in $SpadDirectory. Install SPAD first (or pass -SpadDirectory)." }
$backup = Join-Path $root ('install-backup-' + (Get-Date -Format yyyyMMdd-HHmmss))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
if ((Get-FileHash $driverDll).Hash -ne (Get-FileHash $spadDll).Hash) {
    Copy-Item $spadDll (Join-Path $backup 'vJoyInterface.dll')
    Copy-Item $driverDll $spadDll -Force
    Note "SPAD's vJoy library replaced with the one matching the driver."
} else { Note 'SPAD vJoy library already matches.' }

Step 'SPAD profiles (all 9, with helper paths pointed at this folder)'
$target = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SPAD.neXt\profiles'
New-Item -ItemType Directory -Path $target -Force | Out-Null
$exeDirs = @{ 'ka-click' = 'ka-click'; 'ka-front' = 'ka-front'; 'ka-menu' = 'ka-front'; 'ka-mouse' = 'ka-mouse'; 'ka-drone' = 'ka-drone-leds' }
foreach ($file in Get-ChildItem (Join-Path $root 'profiles') -Filter '*.xml') {
    $destination = Join-Path $target $file.Name
    if (Test-Path -LiteralPath $destination) { Copy-Item -LiteralPath $destination -Destination $backup }
    $doc = [xml](Get-Content -LiteralPath $file.FullName -Raw)
    foreach ($node in $doc.SelectNodes('//*[@Value]')) {
        $old = $node.GetAttribute('Value')
        if ($old -match '((ka-click|ka-front|ka-menu|ka-mouse|ka-drone)(-[a-z]+)?)\.exe$') {
            $path = Join-Path (Join-Path $helpers $exeDirs[$Matches[2]]) ($Matches[1] + '.exe')
            if (!(Test-Path $path)) { throw "Missing helper $path" }
            # ka-click lives in an expression string (doubled backslashes); RunProgram paths are plain.
            $node.SetAttribute('Value', $(if ($old.Contains('\\')) { $path.Replace('\', '\\') } else { $path }))
        }
    }
    $doc.Save($destination)
    Note $file.Name
}

# ka-mouse and ka-drone-leds are started by SPAD itself (throttle mouse buttons / B4), not Windows Startup.
Step 'Throttle mouse: find the throttle on this PC; SFS Monitor watcher: start at logon'
$cm3 = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
    Where-Object { $_.InstanceId -like 'HID\VID_3344&PID_0194&MI_00*' } | Select-Object -First 1
if ($cm3) {
    $hidPath = '\\?\' + $cm3.InstanceId.Replace('\', '#').ToLower() + '#{4d1e55b2-f16f-11cf-88cb-001111000030}'
    $ini = Join-Path $helpers 'ka-mouse\ka-mouse.ini'
    $kept = if (Test-Path $ini) { Get-Content $ini | Where-Object { $_ -notmatch '^\s*Path\s*=' } } else { @() }
    Set-Content $ini (@("Path=$hidPath") + $kept) -Encoding ascii
    Note "Throttle found: $hidPath"
} else { Todo 'VIRPIL CM3 throttle not connected: plug it in and run this setup again so the mini-stick mouse can find it.' }
$startup = [Environment]::GetFolderPath('Startup')
$shell = New-Object -ComObject WScript.Shell
foreach ($exe in @('ka-sfs\ka-sfs-watch.exe')) {
    $full = Join-Path $helpers $exe
    $lnk = $shell.CreateShortcut((Join-Path $startup ([IO.Path]::GetFileNameWithoutExtension($full) + '.lnk')))
    $lnk.TargetPath = $full; $lnk.WorkingDirectory = Split-Path $full; $lnk.Save()
    Start-Process explorer.exe $full  # start now, un-elevated, like at logon
    Note "${exe}: added to Startup and started"
}

Step 'MSFS control presets (vJoy look/drone, rudder pedals)'
$presets = 'KestrelAir-vJoy-GeneralControls-v2.2-OnFoot.xml', 'KestrelAir-RudderPedals-SPAD.xml'
$remotes = @(Get-ChildItem 'C:\Program Files (x86)\Steam\userdata\*\2537590\remote' -Directory -ErrorAction SilentlyContinue)
foreach ($r in $remotes) {
    foreach ($p in $presets) {
        $dest = Join-Path $r.FullName ('inputprofile_' + $p.ToLower())
        if (!(Test-Path $dest)) { Copy-Item (Join-Path $root $p) $dest }
    }
    Note "Presets placed in $($r.FullName)"
}
if ($remotes) {
    Todo 'MSFS > Controls > vJoy Device > General controls: pick "KestrelAir SPAD Cameras v2.2". Saitek Rudder Pedals > Airplanes: pick "KestrelAir Pedals via SPAD". (If a name is missing from the list: gear > Import > the same-named file in this folder.)'
} else {
    Todo "MSFS > Controls > vJoy Device > General controls > gear > Import > $root\KestrelAir-vJoy-GeneralControls-v2.2-OnFoot.xml. Saitek Rudder Pedals > Airplanes > gear > Import > KestrelAir-RudderPedals-SPAD.xml."
}
Todo 'MSFS keyboard General Controls: Shift+X = Toggle Drone Camera (throttle B4).'

Step 'vPilot and BeyondATC push-to-talk buttons'
$python = Get-Command python, py -ErrorAction SilentlyContinue | Where-Object { $_.Source -notlike '*WindowsApps*' } | Select-Object -First 1
if ($python) {
    & $python.Source (Join-Path $helpers 'configure-atc-apps.py')
    if ($LASTEXITCODE -ne 0) { Todo 'configure-atc-apps.py failed (are vPilot and BeyondATC installed and run once?). See helpers\stick-atc-buttons.md.' }
} else { Todo 'Python not found: in vPilot and BeyondATC bind PTT by pressing the grip buttons with SPAD running (helpers\stick-atc-buttons.md).' }

Step 'FSUIPC LED helper'
if (Test-Path $FsuipcDirectory) {
    $luaTarget = Join-Path $FsuipcDirectory 'KestrelAirLEDs.lua'
    if (Test-Path $luaTarget) { Copy-Item $luaTarget $backup }
    Copy-Item (Join-Path $helpers 'KestrelAirLEDs.lua') $luaTarget -Force
    $init = Join-Path $FsuipcDirectory 'ipcInit.lua'
    $text = if (Test-Path $init) { Copy-Item $init $backup; Get-Content $init -Raw } else { '' }
    if ($text -notmatch 'KestrelAirLEDs\.lua') {
        [IO.File]::WriteAllText($init, $text + "`r`ndofile('" + $luaTarget.Replace('\', '\\') + "')`r`n")
    }
    Note 'Installed.'
    Todo "New FSUIPC install only: merge helpers\KestrelAir-myOffsets.txt into $FsuipcDirectory\myOffsets.txt."
} else { Todo "FSUIPC not found at ${FsuipcDirectory}: install it and run this setup again (or pass -FsuipcDirectory)." }

Step 'Done'
Note "Backup of anything replaced: $backup"
Write-Host "`nStill to do by hand:" -ForegroundColor Yellow
$todo += 'Start SPAD and pick each profile once with its aircraft. If the sticks act swapped, SPAD is asking which identical WarBRD grip is the right one (right = DeviceIndex 0).'
$i = 1; foreach ($t in $todo) { Write-Host "  $i. $t"; $i++ }
