$ErrorActionPreference = 'Stop'
if (Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue) { throw 'Exit SPAD.neXt before updating its profile to prevent cached settings overwriting these bindings.' }
# CP3 B8-B13 (buttons 8-13) send the user's MSFS keyboard camera bindings (MSFS must have focus).
# Instrument view numbers verified by screenshot in the Black Square Baron, 2026-10-31:
#   Shift+1 pilot instrument panel, Shift+2 co-pilot instrument panel, Shift+3 pilot lower panel,
#   Shift+4 co-pilot lower panel, Shift+5 middle/throttle quadrant.
# Shift+Space (KEY_COCKPIT_RESET, "Reset position") verified to return from an instrument view to the pilot view.
# B8 pilot instruments, B9 pilot lower, B10 co-pilot instruments, B11 co-pilot lower, B12 throttle area, B13 reset.
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
    @{Button='BUTTON_9'; Xml=(Keys 'LShiftKey','D3')},
    @{Button='BUTTON_10'; Xml=(Keys 'LShiftKey','D2')},
    @{Button='BUTTON_11'; Xml=(Keys 'LShiftKey','D4')},
    @{Button='BUTTON_12'; Xml=(Keys 'LShiftKey','D5')},
    @{Button='BUTTON_13'; Xml=(Keys 'LShiftKey','Space')}
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
        $event = $events.SelectSingleNode(('s:Event[@BoundTo="{0}"]' -f $binding.Button), $manager)
        if (!$event) { $event = $doc.CreateElement('Event', $ns); $event.SetAttribute('BoundTo', $binding.Button); [void]$events.AppendChild($event) }
        $event.InnerXml = $binding.Xml
    }
    $doc.Save($entry.Path)
    $check = New-Object System.Xml.XmlDocument
    $check.Load($entry.Path)
    $before = New-Object System.Xml.XmlDocument
    $before.Load((Join-Path $backup ($entry.Label + '.xml')))
    foreach ($binding in $bindings) {
        $path = $cp3 + ('/s:Event[@BoundTo="{0}"]' -f $binding.Button)
        $added = $check.SelectSingleNode($path, $manager)
        if (!$added -or $added.InnerXml -ne ([xml]('<x xmlns="' + $ns + '">' + $binding.Xml + '</x>')).DocumentElement.InnerXml) { throw "Binding verification failed: $($binding.Button)" }
        [void]$added.ParentNode.RemoveChild($added)
        $old = $before.SelectSingleNode($path, $manager)
        if ($old) { [void]$old.ParentNode.RemoveChild($old) }
    }
    if ($check.DocumentElement.OuterXml -ne $before.DocumentElement.OuterXml) { throw 'Unrelated profile change detected' }
    Write-Output "Verified $($entry.Label): CP3 B8-B13 views (pilot inst, pilot lower, co-pilot inst, co-pilot lower, throttle, reset); all other XML unchanged."
}
