Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
$root=[System.Windows.Automation.AutomationElement]::RootElement
$processCondition=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty,2668)
$window=$root.FindFirst([System.Windows.Automation.TreeScope]::Children,$processCondition)
function Elements($type) { $window.FindAll([System.Windows.Automation.TreeScope]::Descendants,(New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,$type))) }
foreach($entry in @(@(526,533,0,0,255),@(582,589,255,255,0),@(638,645,255,0,255),@(694,701,0,255,0))) {
 $button=Elements ([System.Windows.Automation.ControlType]::Button) | Where-Object {$_.Current.BoundingRectangle.X -eq 1887 -and $_.Current.BoundingRectangle.Y -eq $entry[0]} | Select-Object -First 1
 if(!$button) { throw 'Mode colour button not found.' }
 $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
 Start-Sleep -Milliseconds 150
 $edits=@(Elements ([System.Windows.Automation.ControlType]::Edit) | Where-Object {$_.Current.BoundingRectangle.Width -eq 32})
 if($edits.Count -ne 3) { throw 'RGB inputs not found.' }
 for($i=0;$i -lt 3;$i++) { $edits[$i].GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue([string]$entry[$i+2]) }
 $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
 $combo=Elements ([System.Windows.Automation.ControlType]::ComboBox) | Where-Object {$_.Current.BoundingRectangle.X -eq 1925 -and $_.Current.BoundingRectangle.Y -eq $entry[1]} | Select-Object -First 1
 $combo.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Expand()
 Start-Sleep -Milliseconds 100
 $condition=New-Object System.Windows.Automation.AndCondition((New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,'All LEDs on Primary')),(New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::ListItem)))
 $option=$root.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$condition)
 $option.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select()
 $combo.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Collapse()
 Write-Output ('Restored mode colour '+($entry[0]-470)/56)
}
