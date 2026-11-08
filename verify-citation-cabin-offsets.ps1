$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\SPAD.neXt\FSUIPCClient.dll'
[FSUIPC.FSUIPCConnection]::Open()
try {
    $title = New-Object 'FSUIPC.Offset[string]' -ArgumentList 0x3D00,256
    $name = New-Object 'FSUIPC.Offset[string]' -ArgumentList 0x3160,24
    $entry = New-Object 'FSUIPC.Offset[double]' -ArgumentList 0xA020
    $overhead = New-Object 'FSUIPC.Offset[double]' -ArgumentList 0xA028
    [FSUIPC.FSUIPCConnection]::Process()
    @{Title=$title.Value;Name=$name.Value;Entry=$entry.Value;Overhead=$overhead.Value} | ConvertTo-Json | Set-Content (Join-Path $PSScriptRoot 'citation-cabin-offsets.json')
} finally { [FSUIPC.FSUIPCConnection]::Close() }
