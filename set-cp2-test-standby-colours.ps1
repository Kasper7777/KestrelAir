$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
$root=[System.Windows.Automation.AutomationElement]::RootElement
$c=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,'VIRPIL Controls Configurator - Alpha-0.2.1.0')
$window=$root.FindFirst([System.Windows.Automation.TreeScope]::Children,$c)
function All {$window.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)}
$t=All|Where-Object {$_.Current.Name -eq 'VPC Control Panel #2' -and $_.Current.ControlType.ProgrammaticName -eq 'ControlType.Text'}|Select-Object -First 1
$button=[System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($t)
$button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
Start-Sleep -Milliseconds 200
$led=All|Where-Object {$_.Current.Name -eq 'LED' -and $_.Current.ControlType.ProgrammaticName -eq 'ControlType.Button'}|Select-Object -First 1
if($led){$led.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()}
foreach($index in 13,14){
 $buttons=@(All|Where-Object {$_.Current.Name -eq 'Avalonia.Controls.Border' -and $_.Current.ControlType.ProgrammaticName -eq 'ControlType.Button' -and $_.Current.BoundingRectangle.X -gt 1950 -and $_.Current.BoundingRectangle.Y -ge 240 -and $_.Current.BoundingRectangle.Y -lt 450})
 $buttons[$index].GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
 $rgb=@(All|Where-Object {$_.Current.ControlType.ProgrammaticName -eq 'ControlType.Edit'}|Select-Object -Last 3)
 if($rgb.Count -ne 3){throw 'RGB fields missing'}
 $color=@(64,0,0)
 for($ch=0;$ch -lt 3;$ch++){$rgb[$ch].GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue([string]$color[$ch])}
 $buttons[$index].GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
}
Write-Output 'CP2 B7/B8 momentary pressure test and standby: dim red base colors.'
