$ErrorActionPreference = 'Stop'
[xml]$original = Get-Content (Join-Path $PSScriptRoot 'backups\SPAD.neXt-20261024-170138\profiles\Baron.xml')
$ids = @{}
$report = @()
foreach ($file in Get-ChildItem (Join-Path $PSScriptRoot 'profiles') -Filter '*.xml') {
    [xml]$profile = Get-Content -LiteralPath $file.FullName
    $id = $profile.Profile.ProfileInformation.ProfileID
    if ($ids.ContainsKey($id) -or $id -eq $original.Profile.ProfileInformation.ProfileID) { throw "Duplicate identity: $file" }
    $ids[$id] = $true
    $oldDevices = @($original.Profile.Devices.Device)
    $devices = @($profile.Profile.Devices.Device)
    for ($i=0; $i -lt $oldDevices.Count; $i++) {
        if ($oldDevices[$i].OuterXml -cne $devices[$i].OuterXml) { throw "Original hardware changed: $file" }
    }
    if ($profile.Profile.Options.OuterXml -cne $original.Profile.Options.OuterXml) { throw "Options changed: $file" }
    $sfs = @($devices | Where-Object VendorID -eq '0x16D0')
    if ($sfs.Count -ne 6) { throw "Missing SFS hardware/mode: $file" }
    foreach ($d in $sfs) {
        $maxButton = switch ($d.ProductID) { '0x1290' {40}; '0x13E4' {40}; '0x128F' {40}; '0x13E3' {40}; '0x14CA' {24}; '0x14CB' {37}; default { throw 'Unexpected PID' } }
        if (!$d.DevicePath.ToLowerInvariant().Contains('pid_' + $d.ProductID.Substring(2).ToLowerInvariant())) { throw 'Device path mismatch' }
        $bound = @{}
        foreach ($event in $d.DevicePage.Events.Event) {
            if ($bound.ContainsKey($event.BoundTo)) { throw "Duplicate input node: $file" }
            $bound[$event.BoundTo] = $true
            $number = [int]$event.BoundTo.Replace('BUTTON_','')
            if ($number -lt 1 -or $number -gt $maxButton) { throw "Invalid hardware button: $file" }
            $triggers = @{}
            foreach ($def in $event.EventDefinitions.EventDefinition) {
                if ($triggers.ContainsKey($def.Trigger)) { throw "Double action trigger: $file" }
                $triggers[$def.Trigger] = $true
                if ($def.Trigger -notin @('PRESS','RELEASE')) { throw 'Unexpected trigger' }
                foreach ($action in $def.EventActions.ChildNodes) {
                    if (!$action.TargetDataDefinition) { throw 'Missing action target' }
                    if ($action.TargetDataDefinition -match 'TDSGTNXI.+(?:Key|CRSR)$' -and $def.Trigger -eq 'PRESS') {
                        $release = @($event.EventDefinitions.EventDefinition | Where-Object Trigger -eq 'RELEASE')
                        if ($release.Count -ne 1 -or $release[0].EventActions.EventActionChangeValue.Value -ne '0') { throw 'TDS key missing release' }
                    }
                }
            }
        }
    }
    $secondary = $file.Name -match '\+'
    if ($secondary) {
        foreach ($rot in $sfs | Where-Object ProductID -in @('0x13E4','0x13E3')) {
        foreach ($button in @(3,4,13,14,15,16,23,24)) {
            if (!($rot.DevicePage.Events.Event | Where-Object BoundTo -eq "BUTTON_$button")) { throw 'Missing dual-GPS encoder input' }
        }
        foreach ($pair in @(@(13,'B:AS530_RANGE_ZOOM_Inc'),@(14,'B:AS530_RANGE_ZOOM_Dec'))) {
            $event = $rot.DevicePage.Events.Event | Where-Object BoundTo -eq "BUTTON_$($pair[0])"
            if ($event.EventDefinitions.EventDefinition.EventActions.EventActionControl.TargetDataDefinition -cne $pair[1]) { throw 'GNS 530 range input missing or reassigned' }
        }
        $fmsCases = @(@(15,'RightSmallKnob_Right'),@(16,'RightSmallKnob_Left'),@(23,'RightLargeKnob_Right'),@(24,'RightLargeKnob_Left'),@(4,'RightSmallKnob_Push'))
        if ($rot.ProductID -eq '0x13E3') { $fmsCases += @(@(34,'RightSmallKnob_Right'),@(35,'RightSmallKnob_Left'),@(36,'RightLargeKnob_Right'),@(37,'RightLargeKnob_Left'),@(38,'RightSmallKnob_Push')) }
        foreach ($case in $fmsCases) {
            $event = $rot.DevicePage.Events.Event | Where-Object BoundTo -eq "BUTTON_$($case[0])"
            if ($event.EventDefinitions.EventDefinition.EventActions.EventActionControl.TargetDataDefinition -cne "MSFS:AS530_$($case[1])") { throw 'FMS does not match manufacturer SPAD control definition' }
        }
        }
        $adf = $sfs | Where-Object ProductID -eq '0x1290'
        foreach ($button in @(3,13,14,21,22)) {
            $event = $adf.DevicePage.Events.Event | Where-Object BoundTo -eq "BUTTON_$button"
            if (!($event.EventDefinitions.EventDefinition.EventActions.EventActionChangeValue.TargetDataDefinition -match 'TDSGTNXI650U2_')) { throw 'GTN 650 encoder missing' }
        }
    }
    $report += "$($file.BaseName): PASS (original devices/options preserved; six SFS sections covering GC/ANA and PulsAIR; range in both modes; valid inputs; unique ID; key releases)"
}
if ($ids.Count -ne 1) { throw 'Expected only the GNS 530 + TDS GTNxi 650 profile' }
$liveOriginal = Join-Path $env:USERPROFILE 'Documents\SPAD.neXt\profiles\Baron.xml'
if ((Get-FileHash $liveOriginal).Hash -ne (Get-FileHash (Join-Path $PSScriptRoot 'backups\SPAD.neXt-20261024-170138\profiles\Baron.xml')).Hash) { throw 'Original Baron changed' }
$report += 'Live original Baron SHA-256 still matches backup.'
$report += 'Static validation only: SPAD.neXt import and simulator/hardware operation have not been tested.'
$report | Set-Content (Join-Path $PSScriptRoot 'validation.txt') -Encoding UTF8
$report
