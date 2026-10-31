param([switch]$RemoveExtraAnyBank)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
$root=[System.Windows.Automation.AutomationElement]::RootElement
$comboCondition=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::ComboBox)
function Select-Choice($combo,$name) {
 $combo.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Expand()
 Start-Sleep -Milliseconds 70
 $condition=New-Object System.Windows.Automation.AndCondition((New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,$name)),(New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::ListItem)))
 $option=$root.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$condition)
 if(!$option) { throw "Choice not found: $name" }
 $option.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select()
 $combo.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Collapse()
}
foreach($number in 1..6) {
 $condition=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,('Button B'+$number))
 $label=$root.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$condition)
 $panel=[System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($label)
 $combos=$panel.FindAll([System.Windows.Automation.TreeScope]::Descendants,$comboCondition)
 if($combos.Count -eq 0) {
  $setup=$panel.FindFirst([System.Windows.Automation.TreeScope]::Children,(New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Button)))
  $setup.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
  Start-Sleep -Milliseconds 100
 }
 $banks=1..5
 if($RemoveExtraAnyBank) { $banks=@('Any') }
 foreach($bank in $banks) {
  $combos=$panel.FindAll([System.Windows.Automation.TreeScope]::Descendants,$comboCondition)
  Select-Choice $combos[0] ([string]$bank)
  $combos=$panel.FindAll([System.Windows.Automation.TreeScope]::Descendants,$comboCondition)
  $buttonMode='Normal'
  if($RemoveExtraAnyBank) { $buttonMode='Off' }
  Select-Choice $combos[1] $buttonMode
 }
 Write-Output "B$number configured; extra Any bank removal: $RemoveExtraAnyBank"
}
