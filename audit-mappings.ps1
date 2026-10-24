$ErrorActionPreference = 'Stop'
[xml]$profile = Get-Content (Join-Path $PSScriptRoot 'profiles\Baron - GNS 530 + TDS GTNxi 650.xml')
$sources = @{
    '0x128F'='references\rotAIR-Xplane\SimFlight Services rotAIR type-1 GC.joy'
    '0x1290'='references\rotAIR-Xplane\SimFlight Services rotAIR type-1 ANA.joy'
    '0x13E3'='references\rotAIR-Xplane\SimFlight Services rotAIR type-2 GC.joy'
    '0x13E4'='references\rotAIR-Xplane\SimFlight Services rotAIR type-2 ANA.joy'
    '0x14CA'='references\pulsAIR-Xplane\SimFlight Services pulsAIR type-1 - Windows.joy'
    '0x14CB'='references\pulsAIR-Xplane\SimFlight Services pulsAIR type-2 - Windows.joy'
}
$rows = @()
foreach ($device in $profile.Profile.Devices.Device | Where-Object VendorID -eq '0x16D0') {
    $productId = $device.ProductID
    $reference = Get-Content -LiteralPath (Join-Path $PSScriptRoot $sources[$productId])
    $documented = @($reference | ForEach-Object { if ($_ -match '^Button (\d+): (?:sim|laminar)/') { [int]$matches[1] + 1 } })
    $maximum = switch ($productId) { '0x14CA' {24}; '0x14CB' {37}; default {40} }
    foreach ($button in 1..$maximum) {
        $event = $device.DevicePage.Events.Event | Where-Object BoundTo -eq "BUTTON_$button"
        $reason = ''
        if ($event) {
            $status = 'Mapped'
            $reason = ($event.EventDefinitions.EventDefinition.EventActions.ChildNodes | ForEach-Object { $_.TargetDataDefinition }) -join '; '
        } elseif ($productId -eq '0x14CB' -and $button -in @(4,10)) {
            $status = 'Firmware'; $reason = 'PFD/MFD selector handled by device firmware; no simulator command'
        } elseif ($productId -eq '0x14CB' -and $button -in @(2,8,9)) {
            $status = 'Touchscreen required'; $reason = 'TDS FPL/PROC/ENT have no corresponding exposed bezel action in installed behavior XML'
        } elseif ($productId -eq '0x14CA' -and $button -ge 13) {
            $status = 'Not applicable'; $reason = 'Factory long presses are G1000 PFD softkeys; this aircraft configuration uses GNS530/GTN650'
        } elseif ($button -notin $documented) {
            $status = 'Undocumented input'; $reason = 'Not assigned an emitted function by manufacturer reference for this mode; not filled with an arbitrary command'
        } else { throw "Unexplained missing manufacturer input: $productId BUTTON_$button" }
        $rows += [pscustomobject]@{ProductID=$productId; Button=$button; ManufacturerReference=($button -in $documented); Status=$status; Details=$reason; LiveTest='Not verified'}
    }
}
# Every exposed TDS bezel command (apart from its power circuit) must be assigned.
$tdsSource = Join-Path $env:APPDATA 'Microsoft Flight Simulator 2024\Packages\Community\marcfsx-instruments-tdssim-gtnxi650\simattachments\instruments\marcfsx-tdssim-gtnxi650u2\model\MARCFSX_TDSGTNXI650U2.behavior.xml'
if (!(Test-Path -LiteralPath $tdsSource)) { throw 'Installed TDS behavior reference is missing' }
$tdsNames = [regex]::Matches((Get-Content -LiteralPath $tdsSource -Raw),'L:TDSGTNXI650U2_[A-Za-z0-9_]+') | ForEach-Object Value | Sort-Object -Unique | Where-Object { $_ -notmatch '_ElectricalCircuit$' }
$targets = $profile.SelectNodes('//*[local-name()="Device" and @VendorID="0x16D0"]//*[@TargetDataDefinition]') | ForEach-Object { $_.GetAttribute('TargetDataDefinition') }
foreach ($name in $tdsNames) { if ($name.Replace('L:','LVAR:') -notin $targets) { throw "Missing TDS bezel command $name" } }
$rows | Export-Csv (Join-Path $PSScriptRoot 'mapping-audit.csv') -Encoding UTF8 -NoTypeInformation
$summary = @('# Mapping audit', '', 'Every documented manufacturer input is mapped or has an explicit exception below. All exposed installed TDS bezel commands are assigned. This is static coverage, not proof of simulator operation.', '', '| Device PID | Mapped | Firmware selectors | Touchscreen required | Not applicable | Undocumented inputs |', '| --- | ---: | ---: | ---: | ---: | ---: |')
foreach ($group in $rows | Group-Object ProductID) {
    $counts = foreach ($status in @('Mapped','Firmware','Touchscreen required','Not applicable','Undocumented input')) { @($group.Group | Where-Object Status -eq $status).Count }
    $summary += '| ' + $group.Name + ' | ' + ($counts -join ' | ') + ' |'
}
$summary += @('', 'Touchscreen exceptions: PulsAIR Type-2 MFD-bank FPL (B2), PROC (B8), and ENT (B9). TDS Home, Direct-To, both knobs, volume and both knob pushes are mapped. Its touchscreen page actions still require the screen or mouse.', '', 'AP-module long presses B13â€“B24 are factory G1000 PFD softkeys and have no equivalent in this selected avionics configuration. They remain unassigned. PFD/MFD selectors are internal device functions.', '', 'See mapping-audit.csv for every exposed button slot, including dormant/undocumented slots, and all-SFS-bindings.csv for action values and triggers. Your three original profiles are not edited.', '', 'Live verification still required: NAV/COM tuning and swaps, heading sync, selected altitude, course/baro, transponder digits/state, GNS RANGE/FMS/buttons, GTN Home/Direct-To/knobs/volume and key release, supported AP modes, and display long presses.')
$summary | Set-Content (Join-Path $PSScriptRoot 'mapping-audit.md') -Encoding UTF8
$summary

