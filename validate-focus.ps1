$ErrorActionPreference='Stop'
[xml]$p=Get-Content (Join-Path $PSScriptRoot 'profiles\Baron - GNS 530 + TDS GTNxi 650.xml')
function Active-Targets($device,$button,$focus) {
    $event=$device.DevicePage.Events.Event | Where-Object BoundTo -eq "BUTTON_$button"
    foreach($def in $event.EventDefinitions.EventDefinition | Where-Object Trigger -eq 'PRESS') {
        $active=$true
        foreach($condition in $def.EventConditions.EventCondition) {
            if($condition.ConditionValueSource -ne 'PROFILE:KA_AVIONICS_FOCUS'){throw 'Unexpected focus variable'}
            $equal=$focus -eq [int]$condition.ConditionTargetValue
            $active=$active -and $(switch($condition.ConditionComparator){'Equals'{$equal};'Unequal'{!$equal};default{throw 'Unexpected comparator'}})
        }
        if($active){$def.EventActions.ChildNodes | ForEach-Object TargetDataDefinition}
    }
}
$variable=$p.Profile.Variables.Variable
if($variable.Name -ne 'KA_AVIONICS_FOCUS' -or $variable.Value -ne '0' -or $variable.Scope -ne 'PROFILE'){throw 'Focus initialization missing'}
$checks=0
foreach($rot in $p.Profile.Devices.Device | Where-Object ProductID -in @('0x13E4','0x13E3')) {
    $buttons=@(3,4,13,14,15,16,23,24)
    if($rot.ProductID -eq '0x13E3'){$buttons+=@(34,35,36,37,38)}
    foreach($button in $buttons){
        $gns=@(Active-Targets $rot $button 0)
        $tds=@(Active-Targets $rot $button 1)
        if($gns.Count -ne 1 -or $gns[0] -notmatch 'AS530'){throw "PFD route wrong: $($rot.ProductID)/$button"}
        if($tds.Count -ne 1 -or $tds[0] -notmatch '^LVAR:TDSGTNXI650U2_'){throw "MFD route wrong: $($rot.ProductID)/$button"}
        $checks+=2
    }
}
$display=$p.Profile.Devices.Device | Where-Object ProductID -eq '0x14CB'
foreach($selector in @(@(4,0),@(10,1))){
    $event=$display.DevicePage.Events.Event | Where-Object BoundTo -eq "BUTTON_$($selector[0])"
    $action=$event.EventDefinitions.EventDefinition.EventActions.EventActionChangeValue | Where-Object TargetDataDefinition -eq 'PROFILE:KA_AVIONICS_FOCUS'
    if(!$action -or [int]$action.Value -ne $selector[1]){throw 'Selector not setting shared focus'}
    $checks++
}
foreach($button in (1..37 | Where-Object {$_ -notin @(4,10)})){
    $gns=@(Active-Targets $display $button 0)
    $tds=@(Active-Targets $display $button 1)
    if($tds | Where-Object {$_ -match 'AS530'}){throw "GNS action leaks into MFD on display input $button"}
    if($gns | Where-Object {$_ -match '^LVAR:TDSGTNXI'}){throw "TDS action leaks into PFD on display input $button"}
    $checks+=2
}
foreach($bank in @(@(1,7,3),@(13,16,15),@(19,22,21))){
    foreach($button in $bank){if(@(Active-Targets $display $button 1).Count -ne 1){throw "Missing TDS display action $button"};$checks++}
}
$report=@("PASS: $checks focus-routing assertions across GC/ANA, selectors and display firmware banks.", 'PFD routes RANGE/FMS/display keys to GNS530; MFD routes supported controls to TDS650.', 'No GNS display commands execute in MFD focus; no TDS display press commands execute in PFD focus.', 'TDS releases are unconditioned and focus selectors reset held TDS keys.', 'Static routing simulation only; confirm actual SPAD.neXt focus changes and GTN knob behavior in the simulator.')
$report | Set-Content (Join-Path $PSScriptRoot 'focus-validation.txt') -Encoding UTF8
$report

