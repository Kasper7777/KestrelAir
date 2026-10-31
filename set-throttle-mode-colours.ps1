$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
$root=[System.Windows.Automation.AutomationElement]::RootElement
$condition=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty,2668)
$window=$root.FindFirst([System.Windows.Automation.TreeScope]::Children,$condition)
function Elements($type){$window.FindAll([System.Windows.Automation.TreeScope]::Descendants,(New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,$type)))}
$palette=@(@(0,0,255),@(0,255,0),@(255,255,0),@(255,128,0),@(128,0,128))
$condition=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,'LED-switching by Shift:')
$label=$window.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$condition)
$panel=[System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($label)
for($mode=0;$mode -lt 5;$mode++){
 $buttons=@($panel.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition) | Where-Object {$_.Current.ControlType.ProgrammaticName -eq 'ControlType.Button' -and $_.Current.Name -eq 'Avalonia.Controls.Border'})
 $button=$buttons[$mode]
 if(!$button){throw "Mode $mode colour button not found"}
 $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
 Start-Sleep -Milliseconds 150
 $allEdits=@(Elements ([System.Windows.Automation.ControlType]::Edit))
 $edits=@($allEdits | Select-Object -Last 3)
 if($edits.Count -ne 3){throw 'Expected RGB fields'}
 for($channel=0;$channel -lt 3;$channel++){$edits[$channel].GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue([string]$palette[$mode][$channel])}
 $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
 Start-Sleep -Milliseconds 150
}
# Apply every mode colour to the throttle's six illuminated buttons.
$combos=$panel.FindAll([System.Windows.Automation.TreeScope]::Children,(New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::ComboBox)))
$target=$combos[0]
if($target){
 $target.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Expand()
 $condition=New-Object System.Windows.Automation.AndCondition((New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,'All LEDs on Primary')),(New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::ListItem)))
 $option=$root.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$condition)
 $option.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select()
 $target.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Collapse()
}
$condition=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,'Apply Settings & Restart device')
$apply=$window.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$condition)
if(!$apply){throw 'Expected pending settings Apply control'}
$apply.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
Write-Output 'Saved mode colours: blue, green, yellow, orange, purple.'
