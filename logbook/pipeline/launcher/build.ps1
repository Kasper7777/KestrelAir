# Builds "Kestrel Air Logbook.exe" (with the kestrel icon) into the logbook folder,
# using the C# compiler that ships with Windows. The built exe is kept in the repo,
# so a fresh clone works without running this.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $here '..\..')
$csc  = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$exe  = Join-Path $root 'Kestrel Air Logbook.exe'
& $csc /nologo /target:winexe /platform:anycpu /optimize+ "/out:$exe" "/win32icon:$(Join-Path $root 'app.ico')" `
    /r:System.Windows.Forms.dll (Join-Path $here 'Launcher.cs')
if ($LASTEXITCODE) { throw "csc failed ($LASTEXITCODE)" }
Write-Host "built $exe"
