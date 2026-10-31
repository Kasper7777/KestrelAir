$ErrorActionPreference = 'Stop'
if (Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue) { throw 'Exit SPAD.neXt before updating its profile to prevent cached settings overwriting these bindings.' }
# Flaps: the throttle flap lever is its Z axis (recovered MSFS binding: KEY_AXIS_FLAPS_SET on L-Axis Z,
# not reversed). Lever forward (60000) = flaps up (-16383), back = full down (+16383).
# CP2 cowl flaps: live test showed 16383 drives them down, so B1/B2 (4/5) now send 0 (up) and B3/B4 (6/7) 16383.
$profileName = 'Baron - GNS 530 + TDS GTNxi 650.xml'
$installed = Join-Path $env:USERPROFILE "Documents\SPAD.neXt\profiles\$profileName"
$workspace = Join-Path $PSScriptRoot "profiles\$profileName"
$backup = Join-Path $PSScriptRoot ('backups\flaps-cowls-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
$ns = 'http://www.fsgs.com/SPAD'
function Wrap($trigger, $action) { '<EventDefinitions xmlns="' + $ns + '"><EventDefinition Trigger="' + $trigger + '"><EventActions>' + $action + '</EventActions></EventDefinition></EventDefinitions>' }
function Cowl($engine, $value) { Wrap 'PRESS' ('<EventActionControl TargetDataDefinition="SIMCONNECT:COWLFLAP' + $engine + '_SET"><Parameter Value="' + $value + '" /></EventActionControl>') }
$flaps = Wrap 'VALUE' '<EventActionControl TargetDataDefinition="SIMCONNECT:AXIS_FLAPS_SET"><Parameter Type="Exp" Value="Round((100 - Min(100, Max(0, [LOCAL:JOY_0X33440X0194_Z_AXIS]))) * 327.66 - 16383, 0)" /></EventActionControl>'
$bindings = @(
    @{Product='0x0194'; Button='Z_AXIS'; Xml=$flaps; Replace=$false},
    @{Product='0x025A'; Button='BUTTON_4'; Xml=(Cowl 1 0); Replace=$true},
    @{Product='0x025A'; Button='BUTTON_5'; Xml=(Cowl 2 0); Replace=$true},
    @{Product='0x025A'; Button='BUTTON_6'; Xml=(Cowl 1 16383); Replace=$true},
    @{Product='0x025A'; Button='BUTTON_7'; Xml=(Cowl 2 16383); Replace=$true}
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
        $event = $events.SelectSingleNode(('s:Event[@BoundTo="{0}"]' -f $binding.Button), $manager)
        if ($event -and !$binding.Replace) { throw "$($binding.Product) $($binding.Button) already assigned: $($entry.Path)" }
        if (!$event -and $binding.Replace) { throw "$($binding.Product) $($binding.Button) expected existing binding: $($entry.Path)" }
        if (!$event) { $event = $doc.CreateElement('Event', $ns); $event.SetAttribute('BoundTo', $binding.Button); [void]$events.AppendChild($event) }
        $event.InnerXml = $binding.Xml
    }
    $doc.Save($entry.Path)
    $check = New-Object System.Xml.XmlDocument
    $check.Load($entry.Path)
    $before = New-Object System.Xml.XmlDocument
    $before.Load((Join-Path $backup ($entry.Label + '.xml')))
    foreach ($binding in $bindings) {
        $path = '/s:Profile/s:Devices/s:Device[@ProductID="{0}"]/s:DevicePage[@IsDefaultPage="true"]/s:Events/s:Event[@BoundTo="{1}"]' -f $binding.Product, $binding.Button
        $added = $check.SelectSingleNode($path, $manager)
        if (!$added -or $added.InnerXml -ne ([xml]('<x xmlns="' + $ns + '">' + $binding.Xml + '</x>')).DocumentElement.InnerXml) { throw "Binding verification failed: $($binding.Product) $($binding.Button)" }
        [void]$added.ParentNode.RemoveChild($added)
        $old = $before.SelectSingleNode($path, $manager)
        if ($old) { [void]$old.ParentNode.RemoveChild($old) }
    }
    if ($check.DocumentElement.OuterXml -ne $before.DocumentElement.OuterXml) { throw 'Unrelated profile change detected' }
    Write-Output "Verified $($entry.Label): throttle Z flaps (forward up), CP2 B1/B2 cowl flaps up, B3/B4 down; all other XML unchanged."
}
