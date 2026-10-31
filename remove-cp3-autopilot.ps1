$ErrorActionPreference = 'Stop'
if (Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue) { throw 'Exit SPAD.neXt before updating its profile to prevent cached settings overwriting this change.' }
# The user has a dedicated autopilot panel, so CP3 carries no autopilot controls.
$profileName = 'Baron - GNS 530 + TDS GTNxi 650.xml'
$installed = Join-Path $env:USERPROFILE "Documents\SPAD.neXt\profiles\$profileName"
$workspace = Join-Path $PSScriptRoot "profiles\$profileName"
$backup = Join-Path $PSScriptRoot ('backups\cp3-autopilot-removal-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
$ns = 'http://www.fsgs.com/SPAD'
$cp3 = '/s:Profile/s:Devices/s:Device[@VendorID="0x3344" and @ProductID="0x025C"]/s:DevicePage[@IsDefaultPage="true"]/s:Events'
$autopilot = './/s:EventActionControl[starts-with(@TargetDataDefinition,"SIMCONNECT:AP_")]'
foreach ($entry in @(@{Path=$installed; Label='installed'}, @{Path=$workspace; Label='workspace'})) {
    $doc = New-Object System.Xml.XmlDocument
    $doc.PreserveWhitespace = $true
    $doc.Load($entry.Path)
    $manager = New-Object System.Xml.XmlNamespaceManager($doc.NameTable)
    $manager.AddNamespace('s', $ns)
    $events = $doc.SelectSingleNode($cp3, $manager)
    if (!$events) { throw "CP3 default page missing: $($entry.Path)" }
    Copy-Item -LiteralPath $entry.Path -Destination (Join-Path $backup ($entry.Label + '.xml'))
    $removed = @()
    foreach ($event in @($events.SelectNodes('s:Event', $manager))) {
        $actions = $event.SelectNodes('.//s:EventActions/*', $manager)
        if (!$event.SelectNodes($autopilot, $manager).Count) { continue }
        if ($event.SelectNodes($autopilot, $manager).Count -ne $actions.Count) { throw "$($event.BoundTo) mixes autopilot and other actions: $($entry.Path)" }
        $removed += $event.BoundTo
        [void]$events.RemoveChild($event)
    }
    $doc.Save($entry.Path)
    $check = New-Object System.Xml.XmlDocument
    $check.Load($entry.Path)
    if ($check.SelectSingleNode($cp3, $manager).SelectNodes($autopilot, $manager).Count) { throw 'CP3 autopilot actions remain' }
    $before = New-Object System.Xml.XmlDocument
    $before.Load((Join-Path $backup ($entry.Label + '.xml')))
    $beforeEvents = $before.SelectSingleNode($cp3, $manager)
    foreach ($button in $removed) { [void]$beforeEvents.RemoveChild($beforeEvents.SelectSingleNode(('s:Event[@BoundTo="{0}"]' -f $button), $manager)) }
    if ($check.DocumentElement.OuterXml -ne $before.DocumentElement.OuterXml) { throw 'Unrelated profile change detected' }
    Write-Output "Verified $($entry.Label): removed CP3 autopilot inputs $($removed -join ', '); all other XML unchanged."
}
