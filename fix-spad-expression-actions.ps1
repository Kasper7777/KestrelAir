$ErrorActionPreference = 'Stop'
if (Get-Process -Name 'SPAD.neXt' -ErrorAction SilentlyContinue) { throw 'Exit SPAD.neXt before updating its profile to prevent cached settings overwriting these bindings.' }
# SPAD evaluates an EventActionChangeValue expression only from SourceDataDefinition (as the working
# transponder-digit and ignition bindings do). Expressions placed in Value were ignored and wrote 0,
# slamming the pressurization knobs to their stops and leaving the mixture at cut-off.
$profileName = 'Baron - GNS 530 + TDS GTNxi 650.xml'
$installed = Join-Path $env:USERPROFILE "Documents\SPAD.neXt\profiles\$profileName"
$workspace = Join-Path $PSScriptRoot "profiles\$profileName"
$backup = Join-Path $PSScriptRoot ('backups\spad-expression-fix-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
$ns = 'http://www.fsgs.com/SPAD'
function Step($lvar, $min, $max, $step) { "Min($max, Max($min, [LVAR:$lvar] + ($step)))" }
$fixes = @(
    @{Product='0x025C'; Button='RX_AXIS'; Target='B:BKSQ_TURBOCHARGEDMIXTURECONTROLLER_1'; Exp='Min(1, Max(0, [LOCAL:JOY_0X33440X025C_RX_AXIS] / 100))'},
    @{Product='0x025C'; Button='RY_AXIS'; Target='B:BKSQ_TURBOCHARGEDMIXTURECONTROLLER_2'; Exp='Min(1, Max(0, [LOCAL:JOY_0X33440X025C_RY_AXIS] / 100))'},
    @{Product='0x0194'; Button='BUTTON_55'; Target='LVAR:var_pressurizationClimbRate'; Exp=(Step 'var_pressurizationClimbRate' 150 2000 -50)},
    @{Product='0x0194'; Button='BUTTON_56'; Target='LVAR:var_pressurizationClimbRate'; Exp=(Step 'var_pressurizationClimbRate' 150 2000 50)},
    @{Product='0x0194'; Button='BUTTON_58'; Target='LVAR:var_pressurizationGoal'; Exp=(Step 'var_pressurizationGoal' -1000 15000 -100)},
    @{Product='0x0194'; Button='BUTTON_59'; Target='LVAR:var_pressurizationGoal'; Exp=(Step 'var_pressurizationGoal' -1000 15000 100)}
)
foreach ($entry in @(@{Path=$installed; Label='installed'}, @{Path=$workspace; Label='workspace'})) {
    $doc = New-Object System.Xml.XmlDocument
    $doc.PreserveWhitespace = $true
    $doc.Load($entry.Path)
    $manager = New-Object System.Xml.XmlNamespaceManager($doc.NameTable)
    $manager.AddNamespace('s', $ns)
    Copy-Item -LiteralPath $entry.Path -Destination (Join-Path $backup ($entry.Label + '.xml'))
    $paths = @()
    foreach ($fix in $fixes) {
        $path = '/s:Profile/s:Devices/s:Device[@VendorID="0x3344" and @ProductID="{0}"]/s:DevicePage[@IsDefaultPage="true"]/s:Events/s:Event[@BoundTo="{1}"]' -f $fix.Product, $fix.Button
        $action = $doc.SelectSingleNode($path + ('//s:EventActionChangeValue[@TargetDataDefinition="{0}"]' -f $fix.Target), $manager)
        if (!$action) { throw "$($fix.Product) $($fix.Button) -> $($fix.Target) missing: $($entry.Path)" }
        foreach ($name in 'Value', 'ValueOperation', 'SourceType', 'SourceDataDefinition') { $action.RemoveAttribute($name) }
        $action.SetAttribute('SourceType', 'Exp')
        $action.SetAttribute('SourceDataDefinition', $fix.Exp)
        $paths += $path
    }
    $doc.Save($entry.Path)
    $check = New-Object System.Xml.XmlDocument
    $check.Load($entry.Path)
    $before = New-Object System.Xml.XmlDocument
    $before.Load((Join-Path $backup ($entry.Label + '.xml')))
    for ($i = 0; $i -lt $fixes.Count; $i++) {
        $action = $check.SelectSingleNode($paths[$i] + ('//s:EventActionChangeValue[@TargetDataDefinition="{0}"]' -f $fixes[$i].Target), $manager)
        if ($action.SourceType -ne 'Exp' -or $action.SourceDataDefinition -ne $fixes[$i].Exp -or $action.HasAttribute('Value')) { throw "Verification failed: $($fixes[$i].Button)" }
        foreach ($xml in $check, $before) { $node = $xml.SelectSingleNode($paths[$i], $manager); [void]$node.ParentNode.RemoveChild($node) }
    }
    if ($check.DocumentElement.OuterXml -ne $before.DocumentElement.OuterXml) { throw 'Unrelated profile change detected' }
    Write-Output "Verified $($entry.Label): 2 mixture and 4 pressurization expressions now use SourceDataDefinition; all other XML unchanged."
}
