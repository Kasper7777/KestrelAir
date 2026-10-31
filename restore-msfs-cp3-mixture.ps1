$ErrorActionPreference = 'Stop'
# The turbocharged Black Square Baron intercepts mixture through MSFS's own hardware bindings; SimConnect
# events sent by SPAD never move it (manual, mixture FAQ). Mixture worked until the MSFS controller bindings
# were cleared, so this restores exactly the two original CP3 "All Planez" actions:
# KEY_MIXTURE1_SET on R-Axis X and KEY_MIXTURE2_SET on R-Axis Y. It also removes SPAD's CP3 RX/RY mixture
# bindings so the two do not fight.
if (Get-Process -Name FlightSimulator2024,FlightSimulator -ErrorAction SilentlyContinue) { throw 'Exit MSFS normally before applying; it reads and rewrites controller profiles itself.' }
if (Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue) { throw 'Exit SPAD.neXt before updating its profile to prevent cached settings overwriting this change.' }
$remote = 'C:\Program Files (x86)\Steam\userdata\86580337\2537590\remote\inputprofile_0602614400'
$original = Join-Path $PSScriptRoot 'backups\msfs-controller-clear-20261031-182055\inputprofile_0602614400'
$profileName = 'Baron - GNS 530 + TDS GTNxi 650.xml'
$installed = Join-Path $env:USERPROFILE "Documents\SPAD.neXt\profiles\$profileName"
$workspace = Join-Path $PSScriptRoot "profiles\$profileName"
$backup = Join-Path $PSScriptRoot ('backups\msfs-cp3-mixture-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null

$raw = [IO.File]::ReadAllText($remote)
$source = [IO.File]::ReadAllText($original)
if (!$raw.Contains('DeviceName="VPC Control Panel #3"') -or !$raw.Contains('>All Planez<')) { throw 'Unexpected MSFS profile device' }
Copy-Item -LiteralPath $remote -Destination $backup
$updated = $raw
foreach ($action in 'KEY_MIXTURE1_SET', 'KEY_MIXTURE2_SET') {
    $bound = [regex]::Match($source, '<Action ActionName="' + $action + '"[^>]*?(?<!/)>[\s\S]*?</Action>')
    if (!$bound.Success) { throw "$action missing from original backup" }
    $empty = [regex]::Matches($updated, '<Action ActionName="' + $action + '"[^>]*/>')
    if ($empty.Count -ne 1) {
        if ($updated.Contains($bound.Value)) { Write-Output "$action already restored"; continue }
        throw "$action not found as a single empty action"
    }
    $updated = $updated.Replace($empty[0].Value, $bound.Value)
}
[xml]$before = '<Root>' + ($raw -replace '<\?xml[^>]*\?>', '') + '</Root>'
[xml]$after = '<Root>' + ($updated -replace '<\?xml[^>]*\?>', '') + '</Root>'
foreach ($doc in $before, $after) {
    foreach ($node in @($doc.SelectNodes('//Action[@ActionName="KEY_MIXTURE1_SET" or @ActionName="KEY_MIXTURE2_SET"]'))) { $node.RemoveAll(); $node.SetAttribute('ActionName', 'x') }
}
if ($before.OuterXml -ne $after.OuterXml) { throw 'Unrelated MSFS binding change detected' }
[IO.File]::WriteAllText($remote, $updated, (New-Object System.Text.UTF8Encoding($false)))
$check = [IO.File]::ReadAllText($remote)
if (!$check.Contains('<KEY Information="Joystick R-Axis X ">770</KEY>') -or !$check.Contains('<KEY Information="Joystick R-Axis Y ">786</KEY>') -or ([regex]::Matches($check, '<KEY ')).Count -ne 2) { throw 'MSFS mixture binding verification failed' }
Write-Output 'Verified MSFS: CP3 R-Axis X -> MIXTURE1_SET, R-Axis Y -> MIXTURE2_SET; no other MSFS bindings changed.'

$ns = 'http://www.fsgs.com/SPAD'
$cp3 = '/s:Profile/s:Devices/s:Device[@VendorID="0x3344" and @ProductID="0x025C"]/s:DevicePage[@IsDefaultPage="true"]/s:Events'
foreach ($entry in @(@{Path=$installed; Label='installed'}, @{Path=$workspace; Label='workspace'})) {
    $doc = New-Object System.Xml.XmlDocument
    $doc.PreserveWhitespace = $true
    $doc.Load($entry.Path)
    $manager = New-Object System.Xml.XmlNamespaceManager($doc.NameTable)
    $manager.AddNamespace('s', $ns)
    $events = $doc.SelectSingleNode($cp3, $manager)
    if (!$events) { throw "CP3 default page missing: $($entry.Path)" }
    Copy-Item -LiteralPath $entry.Path -Destination (Join-Path $backup ($entry.Label + '.xml'))
    foreach ($axis in 'RX_AXIS', 'RY_AXIS') {
        $event = $events.SelectSingleNode(('s:Event[@BoundTo="{0}"]' -f $axis), $manager)
        if ($event) { [void]$events.RemoveChild($event) }
    }
    $doc.Save($entry.Path)
    $check = New-Object System.Xml.XmlDocument
    $check.Load($entry.Path)
    if ($check.SelectNodes($cp3 + '/s:Event[@BoundTo="RX_AXIS" or @BoundTo="RY_AXIS"]', $manager).Count) { throw 'SPAD CP3 mixture bindings remain' }
    $before = New-Object System.Xml.XmlDocument
    $before.Load((Join-Path $backup ($entry.Label + '.xml')))
    foreach ($node in @($before.SelectNodes($cp3 + '/s:Event[@BoundTo="RX_AXIS" or @BoundTo="RY_AXIS"]', $manager))) { [void]$node.ParentNode.RemoveChild($node) }
    if ($check.DocumentElement.OuterXml -ne $before.DocumentElement.OuterXml) { throw 'Unrelated profile change detected' }
    Write-Output "Verified $($entry.Label): SPAD CP3 RX/RY mixture bindings removed; all other XML unchanged."
}
