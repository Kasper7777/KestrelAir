$ErrorActionPreference = 'Stop'
if (Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue) { throw 'Exit SPAD.neXt before updating its profile to prevent cached settings overwriting these bindings.' }
# Mixture: CP3 RX/RY set the documented L:BKSQ_MixtureLeverPosition_1/2 on its 0-1 scale (earlier 0-100
# writes clamped at 1). Divide by 100.0: SPAD's expression engine does integer division for "/ 100",
# which made every lever position 0 or 1.
# Live HID capture 2026-10-31 20:26-20:28:
#   CP3 T2 17/18 -> PRESS/DUMP switch L:var_pressurizationPress 1/0 (writing the manual's
#   L:bksq_PressurizationMode did not move the switch)
#   CP3 T3 19/20 -> door seal inflate (L:var_doorSealPrimaryInflate); lower ID is up, as on the heat switches
#   Throttle rotary 14/15 -> rudder trim left/right; throttle B1 42 -> Shift+C (enter/exit aircraft)
$profileName = 'Baron - GNS 530 + TDS GTNxi 650.xml'
$installed = Join-Path $env:USERPROFILE "Documents\SPAD.neXt\profiles\$profileName"
$workspace = Join-Path $PSScriptRoot "profiles\$profileName"
$backup = Join-Path $PSScriptRoot ('backups\mixture-pressurization-trim-exit-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
$ns = 'http://www.fsgs.com/SPAD'
function Wrap($trigger, $action) { '<EventDefinitions xmlns="' + $ns + '"><EventDefinition Trigger="' + $trigger + '"><EventActions>' + $action + '</EventActions></EventDefinition></EventDefinitions>' }
function Mixture($axis, $engine) { Wrap 'VALUE' ('<EventActionChangeValue TargetDataDefinition="LVAR:BKSQ_MixtureLeverPosition_' + $engine + '" SourceType="Exp" SourceDataDefinition="Min(1.0, Max(0.0, [LOCAL:JOY_0X33440X025C_' + $axis + '] / 100.0))" />') }
function SetValue($target, $value) { Wrap 'PRESS' ('<EventActionChangeValue TargetDataDefinition="' + $target + '" Value="' + $value + '" />') }
function Control($target) { Wrap 'PRESS' ('<EventActionControl TargetDataDefinition="SIMCONNECT:' + $target + '" />') }
$shiftC = Wrap 'PRESS' '<EventActionKeyboard MacroType="PRESSANDRELEASE" TargetWindow="__ACTIVEWINDOW__"><KeyboardMacro Duration="80" Repeat="1" Pause="25"><Keys><Keys>LShiftKey</Keys><Keys>C</Keys></Keys></KeyboardMacro></EventActionKeyboard>'
$bindings = @(
    @{Product='0x025C'; Button='RX_AXIS'; Xml=(Mixture 'RX_AXIS' 1); Replace=$true},
    @{Product='0x025C'; Button='RY_AXIS'; Xml=(Mixture 'RY_AXIS' 2); Replace=$true},
    @{Product='0x025C'; Button='BUTTON_17'; Xml=(SetValue 'LVAR:var_pressurizationPress' 1); Replace=$true},
    @{Product='0x025C'; Button='BUTTON_18'; Xml=(SetValue 'LVAR:var_pressurizationPress' 0); Replace=$true},
    @{Product='0x025C'; Button='BUTTON_19'; Xml=(SetValue 'LVAR:var_doorSealPrimaryInflate' 1); Replace=$true},
    @{Product='0x025C'; Button='BUTTON_20'; Xml=(SetValue 'LVAR:var_doorSealPrimaryInflate' 0); Replace=$true},
    @{Product='0x0194'; Button='BUTTON_14'; Xml=(Control 'RUDDER_TRIM_LEFT'); Replace=$false},
    @{Product='0x0194'; Button='BUTTON_15'; Xml=(Control 'RUDDER_TRIM_RIGHT'); Replace=$false},
    @{Product='0x0194'; Button='BUTTON_42'; Xml=$shiftC; Replace=$false}
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
    Write-Output "Verified $($entry.Label): mixture LVAR 0-1, CP3 T2 press/dump, T3 door seal, throttle rudder trim 14/15, B1 Shift+C; all other XML unchanged."
}
