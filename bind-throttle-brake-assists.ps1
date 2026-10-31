$ErrorActionPreference = 'Stop'
if (Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue) { throw 'Exit SPAD.neXt before updating its profile to prevent cached settings overwriting these bindings.' }
# Throttle T1 (34 on / 35 off) -> the Baron's advertised parking brake input event, B:LANDING_GEAR_PARKINGBRAKE,
#   replacing the old PARKING_BRAKES_ON/OFF events.
# Throttle B2 (43) -> Alt+V, the MSFS keyboard binding for KEY_GUI_DISPLAY_ALL_ASSISTANCES_TOGGLE.
# CP3 T4 (21 on / 22 off) -> prop heat again (L:var_PropHeatSwitch), undoing the temporary parking brake.
$profileName = 'Baron - GNS 530 + TDS GTNxi 650.xml'
$installed = Join-Path $env:USERPROFILE "Documents\SPAD.neXt\profiles\$profileName"
$workspace = Join-Path $PSScriptRoot "profiles\$profileName"
$backup = Join-Path $PSScriptRoot ('backups\throttle-brake-assists-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
$ns = 'http://www.fsgs.com/SPAD'
function Wrap($action) { '<EventDefinitions xmlns="' + $ns + '"><EventDefinition Trigger="PRESS"><EventActions>' + $action + '</EventActions></EventDefinition></EventDefinitions>' }
function SetValue($target, $value) { Wrap ('<EventActionChangeValue TargetDataDefinition="' + $target + '" Value="' + $value + '" />') }
$altV = Wrap '<EventActionKeyboard MacroType="PRESSANDRELEASE" TargetWindow="__ACTIVEWINDOW__"><KeyboardMacro Duration="80" Repeat="1" Pause="25"><Keys><Keys>LMenu</Keys><Keys>V</Keys></Keys></KeyboardMacro></EventActionKeyboard>'
$bindings = @(
    @{Product='0x0194'; Button='BUTTON_34'; Xml=(SetValue 'B:LANDING_GEAR_PARKINGBRAKE' 1); Replace=$true},
    @{Product='0x0194'; Button='BUTTON_35'; Xml=(SetValue 'B:LANDING_GEAR_PARKINGBRAKE' 0); Replace=$true},
    @{Product='0x0194'; Button='BUTTON_43'; Xml=$altV; Replace=$false},
    @{Product='0x025C'; Button='BUTTON_21'; Xml=(SetValue 'LVAR:var_PropHeatSwitch' 1); Replace=$true},
    @{Product='0x025C'; Button='BUTTON_22'; Xml=(SetValue 'LVAR:var_PropHeatSwitch' 0); Replace=$true}
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
    Write-Output "Verified $($entry.Label): throttle T1 parking brake, B2 Alt+V visual assists, CP3 T4 prop heat; all other XML unchanged."
}
