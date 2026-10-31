$ErrorActionPreference = 'Stop'
if (Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue) { throw 'Exit SPAD.neXt before updating its profile to prevent cached settings overwriting these bindings.' }
# CP3 B8-B13 (buttons 8-13, freed when the autopilot bindings were removed) send the user's MSFS keyboard
# camera bindings: top row B8-B10 instrument views 1-3 (Shift+1/2/3); bottom row B11 instrument view 4
# (lower left panel), B12 instrument view 5 (middle), B13 pilot view by setting the camera directly
# (CAMERA STATE 2 = cockpit, CAMERA SUBSTATE 2 = pilot view). Shift+Space only re-centred the current camera,
# and Shift+F10 (default view toggle) moved the camera elsewhere.
$profileName = 'Baron - GNS 530 + TDS GTNxi 650.xml'
$installed = Join-Path $env:USERPROFILE "Documents\SPAD.neXt\profiles\$profileName"
$workspace = Join-Path $PSScriptRoot "profiles\$profileName"
$backup = Join-Path $PSScriptRoot ('backups\cp3-views-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
$ns = 'http://www.fsgs.com/SPAD'
function Keys([string[]]$keys) {
    '<EventDefinitions xmlns="' + $ns + '"><EventDefinition Trigger="PRESS"><EventActions><EventActionKeyboard MacroType="PRESSANDRELEASE" TargetWindow="__ACTIVEWINDOW__"><KeyboardMacro Duration="80" Repeat="1" Pause="25"><Keys>' + (($keys | ForEach-Object { "<Keys>$_</Keys>" }) -join '') + '</Keys></KeyboardMacro></EventActionKeyboard></EventActions></EventDefinition></EventDefinitions>'
}
$bindings = @(
    @{Button='BUTTON_8'; Xml=(Keys 'LShiftKey','D1')},
    @{Button='BUTTON_9'; Xml=(Keys 'LShiftKey','D2')},
    @{Button='BUTTON_10'; Xml=(Keys 'LShiftKey','D3')},
    @{Button='BUTTON_11'; Xml=(Keys 'LShiftKey','D4')},
    @{Button='BUTTON_12'; Xml=(Keys 'LShiftKey','D5')},
    @{Button='BUTTON_13'; Xml=('<EventDefinitions xmlns="' + $ns + '"><EventDefinition Trigger="PRESS"><EventActions><EventActionChangeValue TargetDataDefinition="SIMCONNECT:CAMERA STATE" Value="2" /><EventActionChangeValue TargetDataDefinition="SIMCONNECT:CAMERA SUBSTATE" Value="2" /></EventActions></EventDefinition></EventDefinitions>')}
)
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
    foreach ($binding in $bindings) {
        if ($events.SelectSingleNode(('s:Event[@BoundTo="{0}"]' -f $binding.Button), $manager)) { throw "CP3 $($binding.Button) already assigned: $($entry.Path)" }
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
        $added = $check.SelectSingleNode(($cp3 + '/s:Event[@BoundTo="{0}"]' -f $binding.Button), $manager)
        if (!$added -or $added.InnerXml -ne ([xml]('<x xmlns="' + $ns + '">' + $binding.Xml + '</x>')).DocumentElement.InnerXml) { throw "Binding verification failed: $($binding.Button)" }
        [void]$added.ParentNode.RemoveChild($added)
    }
    if ($check.DocumentElement.OuterXml -ne $before.DocumentElement.OuterXml) { throw 'Unrelated profile change detected' }
    Write-Output "Verified $($entry.Label): CP3 B8-B10 instrument views 1-3, B11-B12 instrument views 4-5, B13 pilot view; all other XML unchanged."
}
