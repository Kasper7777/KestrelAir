$ErrorActionPreference = 'Stop'
if (Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue) { throw 'Exit SPAD.neXt before updating its profile to prevent cached settings overwriting this binding.' }
# The turbocharged Baron only accepts K:MIXTURE1_SET/MIXTURE2_SET for mixture (AXIS_MIXTURE is ignored).
# The working setup was MSFS's own CP3 binding (recovered-msfs-bindings.json, "All Planez": RX/RY ->
# KEY_MIXTURE1/2_SET), which sends the full axis range -16383..16383; SPAD now sends the same.
$profileName = 'Baron - GNS 530 + TDS GTNxi 650.xml'
$installed = Join-Path $env:USERPROFILE "Documents\SPAD.neXt\profiles\$profileName"
$workspace = Join-Path $PSScriptRoot "profiles\$profileName"
$backup = Join-Path $PSScriptRoot ('backups\cp3-mixture-levers-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
$ns = 'http://www.fsgs.com/SPAD'
$cp3 = '/s:Profile/s:Devices/s:Device[@VendorID="0x3344" and @ProductID="0x025C"]/s:DevicePage[@IsDefaultPage="true"]/s:Events'
$axes = @(@('RX_AXIS','MIXTURE1_SET'), @('RY_AXIS','MIXTURE2_SET'))
function Get-MixtureXml($axis, $target) {
    '<EventDefinitions xmlns="' + $ns + '"><EventDefinition Trigger="VALUE"><EventActions><EventActionControl TargetDataDefinition="SIMCONNECT:' + $target + '"><Parameter Type="Exp" Value="Round(Min(100, Max(0, [LOCAL:JOY_0X33440X025C_' + $axis + '])) * 327.66 - 16383, 0)" /></EventActionControl></EventActions></EventDefinition></EventDefinitions>'
}
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
        $event.InnerXml = Get-MixtureXml $axis[0] $axis[1]
    }
    $doc.Save($entry.Path)
    $check = New-Object System.Xml.XmlDocument
    $check.Load($entry.Path)
    $checkEvents = $check.SelectSingleNode($cp3, $manager)
    foreach ($axis in $axes) {
        $action = $checkEvents.SelectSingleNode(('s:Event[@BoundTo="{0}"]/s:EventDefinitions/s:EventDefinition[@Trigger="VALUE"]/s:EventActions/s:EventActionControl[@TargetDataDefinition="SIMCONNECT:{1}"]' -f $axis[0], $axis[1]), $manager)
        if (!$action -or $action.Parameter.Value -notmatch ('^Round\(Min\(100, Max\(0, \[LOCAL:JOY_0X33440X025C_{0}\]\)\) \* 327\.66 - 16383, 0\)$' -f $axis[0])) { throw "Binding verification failed: $($axis[0])" }
    }
    if ($check.SelectNodes('//s:EventActionRangedAxis[@ConfigID="LEVER_MIXTURE"] | //s:EventActionChangeValue[starts-with(@TargetDataDefinition,"LVAR:BKSQ_MixtureLeverPosition_")]', $manager).Count) { throw 'Superseded mixture actions remain' }
    $before = New-Object System.Xml.XmlDocument
    $before.Load((Join-Path $backup ($entry.Label + '.xml')))
    foreach ($xml in @($check, $before)) {
        foreach ($axis in 'RX_AXIS','RY_AXIS') {
            $node = $xml.SelectSingleNode(($cp3 + '/s:Event[@BoundTo="{0}"]' -f $axis), $manager)
            [void]$node.ParentNode.RemoveChild($node)
        }
    }
    if ($check.DocumentElement.OuterXml -ne $before.DocumentElement.OuterXml) { throw 'Unrelated profile change detected' }
    Write-Output "Verified $($entry.Label): CP3 RX/RY -> MIXTURE1_SET/MIXTURE2_SET -16383..16383; all other XML unchanged."
}
