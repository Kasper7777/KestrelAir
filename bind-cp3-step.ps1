$ErrorActionPreference = 'Stop'
if (Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue) { throw 'Exit SPAD.neXt before updating its profile to prevent cached settings overwriting this binding.' }
$profileName = 'Baron - GNS 530 + TDS GTNxi 650.xml'
$installed = Join-Path $env:USERPROFILE "Documents\SPAD.neXt\profiles\$profileName"
$workspace = Join-Path $PSScriptRoot "profiles\$profileName"
$backup = Join-Path $PSScriptRoot ('backups\cp3-step-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
$ns = 'http://www.fsgs.com/SPAD'
foreach ($entry in @(@{Path=$installed; Label='installed'}, @{Path=$workspace; Label='workspace'})) {
    $doc = New-Object System.Xml.XmlDocument
    $doc.PreserveWhitespace = $true
    $doc.Load($entry.Path)
    $manager = New-Object System.Xml.XmlNamespaceManager($doc.NameTable)
    $manager.AddNamespace('s', $ns)
    $events = $doc.SelectSingleNode('/s:Profile/s:Devices/s:Device[@VendorID="0x3344" and @ProductID="0x025C"]/s:DevicePage[@IsDefaultPage="true"]/s:Events', $manager)
    if (!$events) { throw "CP3 default page missing: $($entry.Path)" }
    $existing = $events.SelectSingleNode('s:Event[@BoundTo="BUTTON_6"]', $manager)
    if ($existing) {
        if ($existing.EventDefinitions.EventDefinition.EventActions.EventActionControl.TargetDataDefinition -eq 'H:bksq_JpiButton_1_L_Short') {
            Write-Output "Already bound: $($entry.Label)"
            continue
        }
        throw "Button 6 already assigned: $($entry.Path)"
    }
    Copy-Item -LiteralPath $entry.Path -Destination (Join-Path $backup ($entry.Label + '.xml'))
    $event = $doc.CreateElement('Event', $ns)
    $event.SetAttribute('BoundTo', 'BUTTON_6')
    $event.InnerXml = '<EventDefinitions xmlns="http://www.fsgs.com/SPAD"><EventDefinition Trigger="PRESS"><EventActions><EventActionControl TargetDataDefinition="H:bksq_JpiButton_1_L_Short" /></EventActions></EventDefinition></EventDefinitions>'
    [void]$events.AppendChild($event)
    $doc.Save($entry.Path)
    $check = New-Object System.Xml.XmlDocument
    $check.Load($entry.Path)
    $added = $check.SelectSingleNode('/s:Profile/s:Devices/s:Device[@ProductID="0x025C"]/s:DevicePage/s:Events/s:Event[@BoundTo="BUTTON_6"]', $manager)
    if ($added.EventDefinitions.EventDefinition.EventActions.EventActionControl.TargetDataDefinition -ne 'H:bksq_JpiButton_1_L_Short') { throw 'Binding verification failed' }
    [void]$added.ParentNode.RemoveChild($added)
    $before = New-Object System.Xml.XmlDocument
    $before.Load((Join-Path $backup ($entry.Label + '.xml')))
    if ($check.DocumentElement.OuterXml -ne $before.DocumentElement.OuterXml) { throw 'Unrelated profile change detected' }
    Write-Output "Verified $($entry.Label): CP3 button 6 PRESS -> H:bksq_JpiButton_1_L_Short; all other XML unchanged."
}
Write-Output "Backup: $backup"
