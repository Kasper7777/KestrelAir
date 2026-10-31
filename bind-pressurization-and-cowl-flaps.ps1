$ErrorActionPreference = 'Stop'
if (Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue) { throw 'Exit SPAD.neXt before updating its profile to prevent cached settings overwriting these bindings.' }
# Throttle E2 = cabin pressurization controller knob, E1 = rate knob with the arrow beside it.
# Live HID capture 2026-10-31: E1 CCW 55 / CW 56, E2 CCW 58 / CW 59 (the old 49/50, 52/53 shifted by 6).
# Ranges from the Black Square Baron Professional manual: goal -1000..15000 ft, rate 150..2000 ft/min.
# CP2 B1-B4 follow the 3-position gear lever (1-3) in the VIRPIL control order: buttons 4-7.
# Cowl flap values match the working CP3 T2/T3 switches: 16383 open, 0 closed.
$profileName = 'Baron - GNS 530 + TDS GTNxi 650.xml'
$installed = Join-Path $env:USERPROFILE "Documents\SPAD.neXt\profiles\$profileName"
$workspace = Join-Path $PSScriptRoot "profiles\$profileName"
$backup = Join-Path $PSScriptRoot ('backups\pressurization-cowl-flaps-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
$ns = 'http://www.fsgs.com/SPAD'
function Get-Step($lvar, $min, $max, $step) {
    $target = "LVAR:$lvar"
    if ($step -gt 0) { $value = "Min($max, [$target] + $step)" } else { $value = "Max($min, [$target] - $(-$step))" }
    '<EventDefinitions xmlns="' + $ns + '"><EventDefinition Trigger="PRESS"><EventActions><EventActionChangeValue TargetDataDefinition="' + $target + '" SourceType="Exp" ValueOperation="Set" Value="' + $value + '" /></EventActions></EventDefinition></EventDefinitions>'
}
function Get-Cowl($engine, $value) {
    '<EventDefinitions xmlns="' + $ns + '"><EventDefinition Trigger="PRESS"><EventActions><EventActionControl TargetDataDefinition="SIMCONNECT:COWLFLAP' + $engine + '_SET"><Parameter Value="' + $value + '" /></EventActionControl></EventActions></EventDefinition></EventDefinitions>'
}
$bindings = @(
    @{Product='0x0194'; Button='BUTTON_55'; Xml=(Get-Step 'var_pressurizationClimbRate' 150 2000 -50)},
    @{Product='0x0194'; Button='BUTTON_56'; Xml=(Get-Step 'var_pressurizationClimbRate' 150 2000 50)},
    @{Product='0x0194'; Button='BUTTON_58'; Xml=(Get-Step 'var_pressurizationGoal' -1000 15000 -100)},
    @{Product='0x0194'; Button='BUTTON_59'; Xml=(Get-Step 'var_pressurizationGoal' -1000 15000 100)},
    @{Product='0x025A'; Button='BUTTON_4'; Xml=(Get-Cowl 1 16383)},
    @{Product='0x025A'; Button='BUTTON_5'; Xml=(Get-Cowl 2 16383)},
    @{Product='0x025A'; Button='BUTTON_6'; Xml=(Get-Cowl 1 0)},
    @{Product='0x025A'; Button='BUTTON_7'; Xml=(Get-Cowl 2 0)}
)
foreach ($entry in @(@{Path=$installed; Label='installed'}, @{Path=$workspace; Label='workspace'})) {
    $doc = New-Object System.Xml.XmlDocument
    $doc.PreserveWhitespace = $true
    $doc.Load($entry.Path)
    $manager = New-Object System.Xml.XmlNamespaceManager($doc.NameTable)
    $manager.AddNamespace('s', $ns)
    Copy-Item -LiteralPath $entry.Path -Destination (Join-Path $backup ($entry.Label + '.xml'))
    foreach ($binding in $bindings) {
        $events = $doc.SelectSingleNode(('/s:Profile/s:Devices/s:Device[@VendorID="0x3344" and @ProductID="{0}"]/s:DevicePage[@IsDefaultPage="true"]/s:Events' -f $binding.Product), $manager)
        if (!$events) { throw "Device $($binding.Product) default page missing: $($entry.Path)" }
        if ($events.SelectSingleNode(('s:Event[@BoundTo="{0}"]' -f $binding.Button), $manager)) { throw "$($binding.Product) $($binding.Button) already assigned: $($entry.Path)" }
        $event = $doc.CreateElement('Event', $ns)
        $event.SetAttribute('BoundTo', $binding.Button)
        $event.InnerXml = $binding.Xml
        [void]$events.AppendChild($event)
    }
    $doc.Save($entry.Path)
    $check = New-Object System.Xml.XmlDocument
    $check.Load($entry.Path)
    $before = New-Object System.Xml.XmlDocument
    $before.Load((Join-Path $backup ($entry.Label + '.xml')))
    foreach ($binding in $bindings) {
        $added = $check.SelectSingleNode(('/s:Profile/s:Devices/s:Device[@ProductID="{0}"]/s:DevicePage[@IsDefaultPage="true"]/s:Events/s:Event[@BoundTo="{1}"]' -f $binding.Product, $binding.Button), $manager)
        if (!$added -or $added.InnerXml -ne ([xml]('<x xmlns="' + $ns + '">' + $binding.Xml + '</x>')).DocumentElement.InnerXml) { throw "Binding verification failed: $($binding.Product) $($binding.Button)" }
        [void]$added.ParentNode.RemoveChild($added)
    }
    if ($check.DocumentElement.OuterXml -ne $before.DocumentElement.OuterXml) { throw 'Unrelated profile change detected' }
    Write-Output "Verified $($entry.Label): throttle E1 rate / E2 cabin altitude, CP2 B1/B2 cowl flaps open, B3/B4 closed; all other XML unchanged."
}
