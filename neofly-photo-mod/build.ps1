# Builds NeoflyPhoto.exe with the C# compiler that ships with Windows (.NET Framework 4.x)
# and points your existing NeoFly shortcuts (Desktop, Start Menu, taskbar pin) at it.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$csc  = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$nf   = Join-Path $env:LOCALAPPDATA 'Programs\Neofly\Neofly.exe'
$exe  = Join-Path $here 'NeoflyPhoto.exe'
$ico  = Join-Path $here 'neofly.ico'

Add-Type -AssemblyName System.Drawing
if ((Test-Path $nf) -and -not (Test-Path $ico)) {
    $icon = [System.Drawing.Icon]::ExtractAssociatedIcon($nf)
    $fs = [IO.File]::Create($ico); $icon.Save($fs); $fs.Close()
}

$cscArgs = @('/nologo', '/target:winexe', '/platform:anycpu', '/optimize+', "/out:$exe",
    '/r:System.Drawing.dll', '/r:System.Windows.Forms.dll')
if (Test-Path $ico) { $cscArgs += "/win32icon:$ico" }
$cscArgs += (Join-Path $here 'NeoflyPhoto.cs')
& $csc @cscArgs
if ($LASTEXITCODE -ne 0) { throw "csc failed ($LASTEXITCODE)" }
"Built $exe"

# Retarget every shortcut that opens Neofly.exe (same code the launcher runs on each start).
$asm = [Reflection.Assembly]::Load([IO.File]::ReadAllBytes($exe))
$n = $asm.GetType('NeoflyPhoto.Shortcuts').GetMethod('Redirect').Invoke($null, [object[]]@([string]$nf, [string]$exe, [string]$here))
"Shortcuts redirected: $n"

# Remove the separate shortcuts made by the first version.
foreach ($old in @((Join-Path ([Environment]::GetFolderPath('Desktop')) 'NeoFly (My Photo).lnk'),
                   (Join-Path ([Environment]::GetFolderPath('Programs')) 'Neofly4\NeoFly (My Photo).lnk'))) {
    if (Test-Path $old) { Remove-Item $old; "Removed $old" }
}
