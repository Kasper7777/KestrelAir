param([switch]$DryRun)
# CP3 B3 avionics toggle: SPAD cannot create the indexed variable SIMCONNECT:AVIONICS MASTER SWITCH:1 (its catalogue entry has
# WriteMode Indirect:AVIONICS_MASTER_SET; spad.log "unsupported writeMode ... not found, assuming delayed init"), so the
# expression read 0 and every press sent ON. The unindexed SIMCONNECT:AVIONICS MASTER SWITCH reads the same value as index 1
# (SimConnect check 2026-11-03: both 1) and is readable by SPAD, so the toggle reads that instead.
$ErrorActionPreference='Stop'
$name='Baron - GNS 530 + TDS GTNxi 650.xml'
$files=@((Join-Path $env:USERPROFILE ('Documents\SPAD.neXt\profiles\'+$name)),(Join-Path $PSScriptRoot ('profiles\'+$name)))
if(!$DryRun -and (Get-Process SPAD.neXt -ErrorAction SilentlyContinue)){throw 'Exit SPAD.neXt first; it rewrites the profile when it closes.'}
$ns='http://www.fsgs.com/SPAD'
$old='1 - [SIMCONNECT:AVIONICS MASTER SWITCH:1]';$new='1 - [SIMCONNECT:AVIONICS MASTER SWITCH]'
$backup=Join-Path $PSScriptRoot ('backups\avionics-toggle-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
foreach($file in $files){
 $doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($file)
 $m=New-Object Xml.XmlNamespaceManager($doc.NameTable);$m.AddNamespace('s',$ns)
 $before=$doc.OuterXml
 $actions=@($doc.SelectNodes('//s:Device[@ProductID="0x025C"]//s:Event[@BoundTo="BUTTON_3"]//s:EventActionChangeValue[@TargetDataDefinition="B:ELECTRICAL_AVIONICS_BUS_1"]',$m))
 if($actions.Count -ne 1){throw "Expected one CP3 BUTTON_3 avionics action in $file, found $($actions.Count)"}
 $a=$actions[0]
 if($a.SourceDataDefinition -eq $new){Write-Output "Already fixed: $file";continue}
 if($a.SourceDataDefinition -ne $old){throw "Unexpected CP3 B3 expression in ${file}: $($a.SourceDataDefinition)"}
 $a.SetAttribute('SourceDataDefinition',$new)
 if($doc.OuterXml -ne $before.Replace([Security.SecurityElement]::Escape($old),[Security.SecurityElement]::Escape($new))){throw "Unrelated change detected in $file"}
 if($DryRun){Write-Output "Dry run OK: $file";continue}
 if(!(Test-Path $backup)){[void](New-Item -ItemType Directory $backup)}
 Copy-Item -LiteralPath $file -Destination (Join-Path $backup ((Split-Path (Split-Path $file) -Leaf)+'-'+[IO.Path]::GetFileName($file)))
 $doc.Save($file)
 Write-Output "Fixed CP3 B3 avionics toggle: $file"
}
if(Test-Path $backup){Write-Output "Backup=$backup"}
