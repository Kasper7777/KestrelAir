$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
$root=[System.Windows.Automation.AutomationElement]::RootElement
$condition=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,'VIRPIL Controls Configurator - Alpha-0.2.1.0')
$window=$root.FindFirst([System.Windows.Automation.TreeScope]::Children,$condition)
if(!$window){throw 'Configurator window missing'}
function All { $window.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition) }
function Swatches { @(All | Where-Object {$_.Current.ControlType.ProgrammaticName -eq 'ControlType.Button' -and $_.Current.Name -eq 'Avalonia.Controls.Border' -and $_.Current.BoundingRectangle.X -gt 1950 -and $_.Current.BoundingRectangle.Y -ge 240 -and $_.Current.BoundingRectangle.Y -lt 350}) }
# Configurator swatches are in printed-button order; raw HID addresses differ.
# Swatches 0-3 are B1-B4, and 4-9 are B8-B13.
for($index=0;$index -lt 10;$index++){
 $button=(Swatches)[$index]
 if($index -gt 0 -or @(All|Where-Object {$_.Current.ControlType.ProgrammaticName -eq 'ControlType.Edit'}).Count -lt 3){$button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()}
 $edits=@(All | Where-Object {$_.Current.ControlType.ProgrammaticName -eq 'ControlType.Edit'})
 $rgb=@($edits | Select-Object -Last 3)
 if($rgb.Count -ne 3){throw 'RGB editor missing'}
 $color=@(0,255,255)
 if($index -in 0,1){$color=@(64,0,0)}
 if($index -in 2,3){$color=@(64,64,64)}
 for($channel=0;$channel -lt 3;$channel++){$rgb[$channel].GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue([string]$color[$channel])}
 $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
}
$apply=All | Where-Object {$_.Current.Name -eq 'Apply Settings & Restart device' -and $_.Current.ControlType.ProgrammaticName -eq 'ControlType.Button'} | Select-Object -First 1
if($apply){$apply.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()}
Write-Output 'CP3 base colors: B1/B2 dim red, B3/B4 dim white, B8-B13 original cyan.'
