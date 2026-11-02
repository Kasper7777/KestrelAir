param([string]$FileName='cp3-corrected')
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
Add-Type @'
using System;using System.Runtime.InteropServices;
public class KestrelVPCSave {
 [DllImport("user32.dll",CharSet=CharSet.Unicode)]public static extern IntPtr SendMessage(IntPtr h,uint m,IntPtr w,string l);
}
'@
$root=[System.Windows.Automation.AutomationElement]::RootElement
$condition=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,'VIRPIL Controls Configurator - Alpha-0.2.1.0')
$window=$root.FindFirst([System.Windows.Automation.TreeScope]::Children,$condition)
function Named($name){$c=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,$name);$window.FindAll([System.Windows.Automation.TreeScope]::Descendants,$c)|Where-Object {$_.Current.ControlType.ProgrammaticName -eq 'ControlType.Button'}|Select-Object -First 1}
$condition=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,'Select full device profile')
$dialog=$window.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$condition)
if(!$dialog){
 (Named "Save Device`nSetup").GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
 Start-Sleep -Milliseconds 250
 (Named 'Save profile').GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
 for($attempt=0;$attempt -lt 20 -and !$dialog;$attempt++){
  Start-Sleep -Milliseconds 250
  $dialog=$window.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$condition)
 }
}
if(!$dialog){throw 'Export dialog missing'}
$elements=$dialog.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
$edit=$elements|Where-Object {$_.Current.ClassName -eq 'Edit' -and $_.Current.AutomationId -eq '1001'}|Select-Object -First 1
$save=$elements|Where-Object {$_.Current.ClassName -eq 'Button' -and $_.Current.AutomationId -eq '1'}|Select-Object -First 1
if(!$edit -or !$save){throw 'Native export controls missing'}
$path=Join-Path $PSScriptRoot $FileName
[void][KestrelVPCSave]::SendMessage([IntPtr]$edit.Current.NativeWindowHandle,0x000C,[IntPtr]::Zero,$path)
[void][KestrelVPCSave]::SendMessage([IntPtr]$save.Current.NativeWindowHandle,0x00F5,[IntPtr]::Zero,$null)
Write-Output ('Exported '+$path+'.device.vpcprofile')
