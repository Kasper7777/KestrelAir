$ErrorActionPreference = 'Stop'
if (Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue) { throw 'Exit SPAD.neXt before updating its profile to prevent cached settings overwriting this binding.' }
# The turbocharged Baron ignores mixture events sent through SimConnect; its own mixture input is the
# advertised input event B:BKSQ_TURBOCHARGEDMIXTURECONTROLLER_1/2 (SPAD log, "new B:"). CP3 RX/RY set it
# on a 0-1 scale: live test showed 0-100 behaving as on/off (anything above 1 is full rich).
$profileName = 'Baron - GNS 530 + TDS GTNxi 650.xml'
$installed = Join-Path $env:USERPROFILE "Documents\SPAD.neXt\profiles\$profileName"
$workspace = Join-Path $PSScriptRoot "profiles\$profileName"
$backup = Join-Path $PSScriptRoot ('backups\cp3-mixture-input-event-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
$ns = 'http://www.fsgs.com/SPAD'
$cp3 = '/s:Profile/s:Devices/s:Device[@VendorID="0x3344" and @ProductID="0x025C"]/s:DevicePage[@IsDefaultPage="true"]/s:Events'
$axes = @(@('RX_AXIS', 1), @('RY_AXIS', 2))
foreach ($entry in @(@{Path=$installed; Label='installed'}, @{Path=$workspace; Label='workspace'})) {
    $doc = New-Object System.Xml.XmlDocument
    $doc.PreserveWhitespace = $true
    $doc.Load($entry.Path)
    $manager = New-Object System.Xml.XmlNamespaceManager($doc.NameTable)
    $manager.AddNamespace('s', $ns)
    $events = $doc.SelectSingleNode($cp3, $manager)
    if (!$events) { throw "CP3 default page missing: $($entry.Path)" }
    Copy-Item -LiteralPath $entry.Path -Destination (Join-Path $backup ($entry.Label + '.xml'))
    foreach ($axis in $axes) {
        $event = $events.SelectSingleNode(('s:Event[@BoundTo="{0}"]' -f $axis[0]), $manager)
        if (!$event) { throw "CP3 $($axis[0]) missing: $($entry.Path)" }
        $event.InnerXml = '<EventDefinitions xmlns="' + $ns + '"><EventDefinition Trigger="VALUE"><EventActions><EventActionChangeValue TargetDataDefinition="B:BKSQ_TURBOCHARGEDMIXTURECONTROLLER_' + $axis[1] + '" SourceType="Exp" ValueOperation="Set" Value="Min(1.0, Max(0.0, [LOCAL:JOY_0X33440X025C_' + $axis[0] + '] / 100.0))" /></EventActions></EventDefinition></EventDefinitions>'
    }
    $doc.Save($entry.Path)
    $check = New-Object System.Xml.XmlDocument
    $check.Load($entry.Path)
    foreach ($axis in $axes) {
        if (!$check.SelectSingleNode(($cp3 + '/s:Event[@BoundTo="{0}"]/s:EventDefinitions/s:EventDefinition[@Trigger="VALUE"]/s:EventActions/s:EventActionChangeValue[@TargetDataDefinition="B:BKSQ_TURBOCHARGEDMIXTURECONTROLLER_{1}" and @SourceType="Exp"]' -f $axis[0], $axis[1]), $manager)) { throw "Binding verification failed: $($axis[0])" }
    }
    $before = New-Object System.Xml.XmlDocument
    $before.Load((Join-Path $backup ($entry.Label + '.xml')))
    foreach ($xml in @($check, $before)) {
        foreach ($axis in $axes) { $node = $xml.SelectSingleNode(($cp3 + '/s:Event[@BoundTo="{0}"]' -f $axis[0]), $manager); [void]$node.ParentNode.RemoveChild($node) }
    }
    if ($check.DocumentElement.OuterXml -ne $before.DocumentElement.OuterXml) { throw 'Unrelated profile change detected' }
    Write-Output "Verified $($entry.Label): CP3 RX/RY -> B:BKSQ_TURBOCHARGEDMIXTURECONTROLLER_1/2 (0-1); all other XML unchanged."
}
