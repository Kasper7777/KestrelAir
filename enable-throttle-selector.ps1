$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
$root=[System.Windows.Automation.AutomationElement]::RootElement
$comboCondition=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::ComboBox)
foreach($name in @('Button B1','Button B2','Button B3','Button B4','Button B5','Button B6','Mode Rotator')){
 $c=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,$name)
 $label=$root.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$c)
 $panel=[System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($label)
 $combos=$panel.FindAll([System.Windows.Automation.TreeScope]::Descendants,$comboCondition)
 if(!$combos.Count){$c=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Button);$setup=$panel.FindFirst([System.Windows.Automation.TreeScope]::Children,$c);$setup.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke();Start-Sleep -Milliseconds 100}
 $combos=$panel.FindAll([System.Windows.Automation.TreeScope]::Descendants,$comboCondition)
 $expected=1;if($name -eq 'Mode Rotator'){$expected=5};if($combos.Count -ne $expected){throw "Unexpected control layout for $name"}
 foreach($combo in $combos){
  $combo.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Expand()
  $c=New-Object System.Windows.Automation.AndCondition((New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,'Normal')),(New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::ListItem)))
  $option=$root.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$c);$option.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select();$combo.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Collapse()
 }
 Write-Output "$name normal output enabled."
}
$c=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,'Apply Settings & Restart device');$apply=$root.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$c);if(!$apply){throw 'No device Apply control'};$apply.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
