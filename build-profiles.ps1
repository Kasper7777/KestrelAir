$ErrorActionPreference = 'Stop'
$ns = 'http://www.fsgs.com/SPAD'
$source = Join-Path $PSScriptRoot 'backups\SPAD.neXt-20261024-170138\profiles\Baron.xml'
$reference = Get-ChildItem (Join-Path $PSScriptRoot 'references\rotAIR_SpadNext') -Filter '*.xml' | Select-Object -First 1
[xml]$stock = Get-Content -LiteralPath $reference.FullName
[xml]$panels = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'backups\SPAD.neXt-20261024-170138\conf\PanelNames.xml')
$out = Join-Path $PSScriptRoot 'profiles'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$script:rows = [System.Collections.Generic.List[object]]::new()

function Element($parent, $name, $attrs = @{}) {
    $e = $parent.OwnerDocument.CreateElement($name, $ns)
    foreach ($key in $attrs.Keys) { $e.SetAttribute($key, [string]$attrs[$key]) }
    [void]$parent.AppendChild($e)
    return ,$e
}
function Bind($device, [int]$button, [string]$target, [string]$label, [string]$trigger = 'PRESS', $value = $null) {
    $events = $device.SelectSingleNode('./*[local-name()="DevicePage"]/*[local-name()="Events"]')
    $event = @($events.Event) | Where-Object BoundTo -eq "BUTTON_$button" | Select-Object -First 1
    if (!$event) { $event = Element $events 'Event' @{BoundTo="BUTTON_$button"}; $defs = Element $event 'EventDefinitions' }
    else { $defs = $event.EventDefinitions }
    $def = Element $defs 'EventDefinition' @{Trigger=$trigger}
    $actions = Element $def 'EventActions'
    if ($null -ne $value) { $null = Element $actions 'EventActionChangeValue' @{TargetDataDefinition=$target; Value=$value} }
    else { $null = Element $actions 'EventActionControl' @{TargetDataDefinition=$target} }
    $script:rows.Add([pscustomobject]@{Profile=$script:profileName; PID=$device.ProductID; Button=$button; Trigger=$trigger; Function=$label; Target=$target; Value=$value})
}
function Remove-Bind($device, $button) {
    foreach ($e in @($device.DevicePage.Events.Event | Where-Object BoundTo -eq "BUTTON_$button")) { [void]$e.ParentNode.RemoveChild($e) }
}
function Heading-Sync($device, $button) {
    Bind $device $button 'SIMCONNECT:AUTOPILOT HEADING LOCK DIR' 'Sync heading bug to magnetic heading' 'PRESS' '0'
    $event = $device.DevicePage.Events.Event | Where-Object BoundTo -eq "BUTTON_$button"
    $action = $event.EventDefinitions.EventDefinition.EventActions.EventActionChangeValue
    $action.RemoveAttribute('Value')
    $action.SetAttribute('SourceType','Exp')
    $action.SetAttribute('SourceDataDefinition','[SIMCONNECT:PLANE HEADING DEGREES MAGNETIC]')
}
function New-Device($profile, $productId, [bool]$fromTemplate = $false) {
    if ($fromTemplate) {
        $template = $stock.Profile.Devices.Device | Where-Object ProductID -eq $productId
        $d = $profile.ImportNode($template, $true)
    } else {
        $d = $profile.CreateElement('Device', $ns)
        foreach ($kv in @{VendorID='0x16D0'; ProductID=$productId; Serial=''; DeviceIndex='0'; Version='3'}.GetEnumerator()) { $d.SetAttribute($kv.Key,$kv.Value) }
        $page = Element $d 'DevicePage' @{ID=[guid]::NewGuid(); IsDefaultPage='true'; Name='Default'}
        $null = Element $page 'Events'
    }
    $panel = $panels.PanelNames.Panel | Where-Object { $_.ProductIndex -eq ('16D0:' + $productId.Substring(2)) } | Select-Object -First 1
    if (!$panel) { $panel = $panels.DocumentElement.ChildNodes | Where-Object { $_.ProductIndex -eq ('16D0:' + $productId.Substring(2)) } | Select-Object -First 1 }
    if (!$panel) { throw "No local device identity for $productId" }
    $d.SetAttribute('DevicePath', $panel.Key)
    [void]$profile.Profile.Devices.AppendChild($d)
    return ,$d
}
function Get-HEvent($unit, $suffix) { return "H:$($unit.Prefix)_$suffix" }
function Bezel($device, $button, $unit, $suffix, $label) {
    if ($unit.Kind -eq 'TDS') {
        $target = "LVAR:TDSGTNXI$($unit.Prefix)_$suffix"
        Bind $device $button $target $label 'PRESS' '1'
        # Rotation requests are consumed/reset by TDS, just like its cockpit wheel events.
        # Keys and knob pushes are held signals and require release.
        if ($suffix -match 'Key$|CRSR$') { Bind $device $button $target "$label release" 'RELEASE' '0' }
    } else { Bind $device $button (Get-HEvent $unit $suffix) $label }
}
function Fms($device, $unit, $innerUp, $innerDown, $outerUp, $outerDown, $push) {
    if ($unit.Kind -eq 'GNS') { $names = @('RightSmallKnob_Right','RightSmallKnob_Left','RightLargeKnob_Right','RightLargeKnob_Left','RightSmallKnob_Push') }
    elseif ($unit.Kind -eq 'G1000') { $names = @('FMS_Upper_INC','FMS_Upper_DEC','FMS_Lower_INC','FMS_Lower_DEC','FMS_Upper_PUSH') }
    elseif ($unit.Kind -eq 'TDS') { $names = @('RKnobInnerInc','RKnobInnerDec','RKnobOuterInc','RKnobOuterDec','RKnobCRSR') }
    else { $names = @('KnobSmallInc','KnobSmallDec','KnobLargeInc','KnobLargeDec','KnobPush') }
    $buttons = @($innerUp,$innerDown,$outerUp,$outerDown,$push)
    for ($i=0; $i -lt 5; $i++) {
        if ($unit.Kind -eq 'GNS') {
            # Use the manufacturer's SPAD control definitions verbatim for FMS.
            # These resolve through MSFS rather than assuming an indexed H-event.
            $fmsPrefix = $unit.Prefix -replace '_1$',''
            Bind $device $buttons[$i] "MSFS:$($fmsPrefix)_$($names[$i])" "$($unit.Name) $($names[$i])"
        } else { Bezel $device $buttons[$i] $unit $names[$i] "$($unit.Name) $($names[$i])" }
    }
}
function Display-Keys($device, $unit, $buttons) {
    # Order: Direct-To, FPL, CLR, MENU, PROC, ENT.
    if ($unit.Kind -eq 'GNS') { $names = @('DRCT_Push','FPL_Push','CLR_Push','MENU_Push','PROC_Push','ENT_Push') }
    elseif ($unit.Kind -eq 'G1000') { $names = @('DIRECTTO','FPL_Push','CLR','MENU_Push','PROC_Push','ENT_Push') }
    elseif ($unit.Kind -eq 'PMS') { $names = @('DirectToPush','GoToPage-HOME-PageFlighPlan','BACK','MENU','GoToPage-HOME-PageProcs','ENTER') }
    else { $names = @('DTOKey',$null,'RKnobCRSR','HomeKey',$null,$null) }
    for ($i=0; $i -lt 6; $i++) {
        if ($names[$i]) { Bezel $device $buttons[$i] $unit $names[$i] "$($unit.Name) $($names[$i])" }
    }
}
function Unit($name,$kind,$prefix) { return @{Name=$name; Kind=$kind; Prefix=$prefix} }
$gns530 = Unit 'GNS 530' 'GNS' 'AS530_1'
$gns430 = Unit 'GNS 430' 'GNS' 'AS430_1'
$pms750 = Unit 'PMS50 GTN 750' 'PMS' 'GTN750'
$pms650 = Unit 'PMS50 GTN 650' 'PMS' 'GTN650'
$pms650second = Unit 'PMS50 GTN 650 COM2' 'PMS' 'GTN650_2'
$tds750 = Unit 'TDS GTNxi 750' 'TDS' '750U1'
$tds650 = Unit 'TDS GTNxi 650' 'TDS' '650U1'
$tds650second = Unit 'TDS GTNxi 650 unit 2' 'TDS' '650U2'
$setups = @(
    @{Name='GNS 530'; Primary=$gns530},
    @{Name='GNS 430'; Primary=$gns430},
    @{Name='GNS 530 + GNS 430'; Primary=$gns530; Secondary=$gns430},
    @{Name='G1000 PFD'; Primary=(Unit 'G1000 PFD' 'G1000' 'AS1000_PFD')},
    @{Name='G1000 MFD'; Primary=(Unit 'G1000 MFD' 'G1000' 'AS1000_MFD')},
    @{Name='PMS50 GTN 750'; Primary=$pms750},
    @{Name='PMS50 GTN 650'; Primary=$pms650},
    @{Name='PMS50 GTN 750 + 650'; Primary=$pms750; Secondary=$pms650second},
    @{Name='GNS 530 + PMS50 GTN 650'; Primary=$gns530; Secondary=$pms650second},
    @{Name='TDS GTNxi 750'; Primary=$tds750},
    @{Name='TDS GTNxi 650'; Primary=$tds650},
    @{Name='TDS GTNxi 750 + 650'; Primary=$tds750; Secondary=$tds650second},
    @{Name='GNS 530 + TDS GTNxi 650'; Primary=$gns530; Secondary=$tds650second}
)
foreach ($setup in $setups) {
    if ($setup.Name -ne 'GNS 530 + TDS GTNxi 650') { continue }
    $script:profileName = 'Baron - ' + $setup.Name
    [xml]$p = Get-Content -LiteralPath $source
    # Preserve all existing hardware sections; new SFS sections have independent assignments.
    $r1 = New-Device $p '0x1290' $true
    $r2 = New-Device $p '0x13E4' $true
    # Remove known problems from the old manufacturer profile: heading push sets north;
    # altitude-up emits two unrelated actions; obsolete transponder shortcuts.
    foreach ($b in @(2,3,4,8,15,16,23,24)) { Remove-Bind $r1 $b }
    foreach ($pair in @(@(3,4),@(4,3),@(8,1))) { Bind $r1 $pair[0] 'SIMCONNECT:TRANSPONDER STATE:1' 'Transponder state' 'PRESS' ([string]$pair[1]) }
    foreach ($spec in @(@(15,'100','Increment'),@(16,'100','Decrement'),@(23,'1000','Increment'),@(24,'1000','Decrement'))) {
        Bind $r1 $spec[0] 'SIMCONNECT:AUTOPILOT ALTITUDE LOCK VAR' "Selected altitude $($spec[2]) $($spec[1]) ft" 'PRESS' $spec[1]
        $event = $r1.DevicePage.Events.Event | Where-Object BoundTo -eq "BUTTON_$($spec[0])"
        $event.EventDefinitions.EventDefinition.EventActions.EventActionChangeValue.SetAttribute('ValueOperation',$spec[2])
    }
    # Normalize rotary pulses to PRESS (firmware already emits dedicated long-press inputs).
    foreach ($def in $r1.SelectNodes('.//*[local-name()="EventDefinition"]')) { $def.SetAttribute('Trigger','PRESS') }
    foreach ($def in $r2.SelectNodes('.//*[local-name()="EventDefinition"]')) { $def.SetAttribute('Trigger','PRESS') }
    foreach ($b in @(3,4,8,13,14,15,16,23,24)) { Remove-Bind $r2 $b }
    Fms $r2 $setup.Primary 15 16 23 24 4
    if ($setup.Secondary) {
        # Keep RANGE as range. Use the ADF encoder for the second GPS instead.
        foreach ($b in @(3,13,14,21,22)) { Remove-Bind $r1 $b }
        Fms $r1 $setup.Secondary 13 14 21 22 3
        Bind $r2 13 'B:AS530_RANGE_ZOOM_Inc' 'GNS 530 range increase (zoom out)'
        Bind $r2 14 'B:AS530_RANGE_ZOOM_Dec' 'GNS 530 range decrease (zoom in)'
        Bind $r2 3 (Get-HEvent $setup.Primary 'FPL_Push') 'GNS 530 flight plan'
    } elseif ($setup.Primary.Kind -eq 'GNS') {
        Bind $r2 13 (Get-HEvent $setup.Primary 'RNG_Dezoom') 'Map range increase'
        Bind $r2 14 (Get-HEvent $setup.Primary 'RNG_Zoom') 'Map range decrease'
        Bind $r2 3 (Get-HEvent $setup.Primary 'FPL_Push') 'Flight plan'
    } elseif ($setup.Primary.Kind -eq 'G1000') {
        Bind $r2 13 (Get-HEvent $setup.Primary 'RANGE_INC') 'Map range increase'
        Bind $r2 14 (Get-HEvent $setup.Primary 'RANGE_DEC') 'Map range decrease'
        Bind $r2 3 (Get-HEvent $setup.Primary 'JOYSTICK_PUSH') 'Map joystick push'
    } elseif ($setup.Primary.Kind -eq 'PMS') {
        Bezel $r2 13 $setup.Primary 'ZOOM_OUT' 'Contextual zoom out'
        Bezel $r2 14 $setup.Primary 'ZOOM_IN' 'Contextual zoom in'
        Bezel $r2 3 $setup.Primary 'HomePush' 'Home'
        foreach ($b in @(21,22)) { Remove-Bind $r2 $b }
        Bezel $r2 21 $setup.Primary 'VolInc' 'Volume increase'
        Bezel $r2 22 $setup.Primary 'VolDec' 'Volume decrease'
    } else {
        Bezel $r2 13 $setup.Primary 'LKnobInc' 'Volume increase'
        Bezel $r2 14 $setup.Primary 'LKnobDec' 'Volume decrease'
        Bezel $r2 3 $setup.Primary 'HomeKey' 'Home'
    }
    if ($setup.Primary.Kind -eq 'GNS') { Bind $r2 8 (Get-HEvent $setup.Primary 'CDI_Push') 'Primary CDI' }
    elseif ($setup.Primary.Kind -eq 'G1000') { Bind $r2 8 (Get-HEvent $setup.Primary 'SOFTKEYS_6') 'CDI softkey' }

    # Fill physical knob pushes and directions absent from the old sample profile.
    Bind $r1 1 'SIMCONNECT:RADIO_VOR1_IDENT_TOGGLE' 'NAV1 audio ident toggle'
    Heading-Sync $r1 2
    Remove-Bind $r1 7
    Bezel $r1 7 $setup.Secondary 'DTOKey' 'GTN 650 Direct-To (ADF hold)'
    Bind $r2 1 'SIMCONNECT:COM1_RECEIVE_SELECT' 'COM1 receiver toggle'
    Bind $r2 2 (Get-HEvent $setup.Primary 'OBS_Push') 'GNS 530 OBS toggle (course push)'
    Bezel $r2 6 $setup.Secondary 'LKnobCRSR' 'GTN 650 volume knob push (course hold)'
    Bezel $r2 7 $setup.Secondary 'HomeKey' 'GTN 650 Home (RANGE hold)'
    foreach ($b in @(21,22)) { Remove-Bind $r2 $b }
    Bezel $r2 21 $setup.Secondary 'LKnobInc' 'GTN 650 volume increase (RANGE outer)'
    Bezel $r2 22 $setup.Secondary 'LKnobDec' 'GTN 650 volume decrease (RANGE outer)'
    foreach ($spec in @(@(29,'B:AS530_RANGE_ZOOM_Inc'),@(30,'B:AS530_RANGE_ZOOM_Dec'))) {
        Remove-Bind $r2 $spec[0]
        Bind $r2 $spec[0] $spec[1] 'GNS range (pressed RANGE rotation)'
    }
    foreach ($spec in @(@(31,'XPNDR_1_INC'),@(32,'XPNDR_1_DEC'))) {
        Remove-Bind $r2 $spec[0]
        Bind $r2 $spec[0] ('SIMCONNECT:'+$spec[1]) 'Transponder ones (ANA extra inputs)'
    }

    $ap = New-Device $p '0x14CA'
    $apEvents = @('AP_MASTER','AP_PANEL_HEADING_HOLD','AP_NAV1_HOLD','AP_APR_HOLD','AP_PANEL_VS_HOLD','FLIGHT_LEVEL_CHANGE','TOGGLE_FLIGHT_DIRECTOR','AP_ALT_HOLD',$null,'AP_BC_HOLD','AP_VS_VAR_INC','AP_VS_VAR_DEC')
    for ($i=0; $i -lt 12; $i++) { if ($apEvents[$i]) { Bind $ap ($i+1) ('SIMCONNECT:'+$apEvents[$i]) $apEvents[$i] } }
    Bind $ap 9 (Get-HEvent $setup.Primary 'VNAV_Push') 'GNS VNAV page (not AP VNAV arming)'
    if ($setup.Primary.Kind -eq 'G1000') {
        for ($i=1; $i -le 12; $i++) { Bind $ap ($i+12) "H:AS1000_PFD_SOFTKEYS_$i" "PFD softkey $i (hold)" }
    }
    $display = New-Device $p '0x14CB'
    # PulsAIR firmware changes six key IDs with PFD/MFD mode, as documented in its manual.
    Display-Keys $display $setup.Primary @(13,14,15,16,17,18)
    if ($setup.Secondary) { Display-Keys $display $setup.Secondary @(1,2,3,7,8,9) }
    elseif ($setup.Primary.Kind -eq 'G1000') { Display-Keys $display (Unit 'G1000 MFD' 'G1000' 'AS1000_MFD') @(1,2,3,7,8,9) }
    else { Display-Keys $display $setup.Primary @(1,2,3,7,8,9) }
    Display-Keys $display $setup.Primary @(19,20,21,22,23,24)
    if ($setup.Primary.Kind -eq 'GNS') {
        foreach ($spec in @(@(5,'CDI_Push'),@(25,'CDI_Push'),@(6,'OBS_Push'),@(11,'VNAV_Push'),@(12,'MSG_Push'))) { Bind $display $spec[0] (Get-HEvent $setup.Primary $spec[1]) "Primary $($spec[1])" }
        # Dedicated firmware long-press IDs: useful GNS shortcuts in either bank.
        foreach ($spec in @(@(26,'DRCT_Push'),@(27,'FPL_Push'),@(28,'CLR_Push_Long'),@(29,'RightSmallKnob_Push'),@(30,'CDI_Push'),@(31,'OBS_Push'),@(32,'MENU_Push'),@(33,'PROC_Push'),@(34,'ENT_Push'),@(36,'VNAV_Push'),@(37,'MSG_Push'))) {
            Bind $display $spec[0] (Get-HEvent $setup.Primary $spec[1]) "GNS hold shortcut $($spec[1])"
        }
        Bezel $display 35 $setup.Secondary 'HomeKey' 'GTN Home (MFD hold)'
    } elseif ($setup.Primary.Kind -eq 'G1000') {
        Bind $display 5 'H:AS1000_PFD_SOFTKEYS_6' 'PFD CDI softkey'
        for ($i=1; $i -le 12; $i++) { Bind $display ($i+25) "H:AS1000_MFD_SOFTKEYS_$i" "MFD softkey $i (hold)" }
    } elseif ($setup.Primary.Kind -eq 'PMS') {
        foreach ($spec in @(@(5,'CDI'),@(25,'CDI'),@(6,'OBS'),@(12,'MSG'))) { Bezel $display $spec[0] $setup.Primary $spec[1] "Primary contextual $($spec[1])" }
    }
    # GC and ANA enumerate as different HID devices. Bind both identities so the
    # connected mode receives events; latest session connects 128F/13E3 (GC).
    foreach ($mode in @(@($r1,'0x128F'),@($r2,'0x13E3'))) {
        $gc = $p.ImportNode($mode[0], $true)
        $gc.SetAttribute('ProductID',$mode[1])
        $identity = $panels.DocumentElement.ChildNodes | Where-Object ProductIndex -eq ('16D0:' + $mode[1].Substring(2)) | Select-Object -First 1
        if (!$identity) { throw 'Missing GC hardware identity' }
        $gc.SetAttribute('DevicePath',$identity.Key)
        [void]$p.Profile.Devices.AppendChild($gc)
        if ($mode[1] -eq '0x13E3') {
            # GC firmware may select its alternate PFD FMS bank.
            foreach ($b in @(34,35,36,37,38)) { Remove-Bind $gc $b }
            Fms $gc $setup.Primary 34 35 36 37 38
        }
    }
    $p.Profile.ProfileInformation.ProfileID = [guid]::NewGuid().ToString()
    $p.Profile.ProfileInformation.LastChanged = [DateTimeOffset]::Now.ToString('o')
    $p.Profile.ProfileInformation.Description = "<HTML><BODY><P>$script:profileName; RotAIR GC and ANA; RANGE=GNS530; ADF=GTN650 knobs; see README. Built from original Baron. Requires in-simulator validation.</P></BODY></HTML>"
    $destination = Join-Path $out ($script:profileName + '.xml')
    if (Test-Path -LiteralPath $destination) {
        [xml]$previous = Get-Content -LiteralPath $destination
        $p.Profile.ProfileInformation.ProfileID = $previous.Profile.ProfileInformation.ProfileID
    }
    $p.Save($destination)
}
$script:rows | Export-Csv (Join-Path $PSScriptRoot 'added-bindings.csv') -NoTypeInformation -Encoding UTF8
$inventory = foreach ($file in Get-ChildItem $out -Filter '*.xml') {
    [xml]$profile = Get-Content -LiteralPath $file.FullName
    foreach ($device in $profile.Profile.Devices.Device | Where-Object VendorID -eq '0x16D0') {
        foreach ($event in $device.DevicePage.Events.Event) {
            foreach ($def in $event.EventDefinitions.EventDefinition) {
                foreach ($action in $def.EventActions.ChildNodes) {
                    [pscustomobject]@{Profile=$file.BaseName; ProductID=$device.ProductID; Input=$event.BoundTo; Trigger=$def.Trigger; Action=$action.LocalName; Target=$action.TargetDataDefinition; Value=$action.Value; Operation=$action.ValueOperation; SourceType=$action.SourceType; Source=$action.SourceDataDefinition; Parameter=($action.Parameter.Value -join ',')}
                }
            }
        }
    }
}
$inventory | Export-Csv (Join-Path $PSScriptRoot 'all-SFS-bindings.csv') -NoTypeInformation -Encoding UTF8
Write-Output "Created GNS 530 + TDS GTNxi 650 profile in $out"



