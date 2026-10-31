Mixture scaling correction, 2026-10-31.

CURRENT (supersedes everything below): the mixture last worked through MSFS's own CP3 binding ("All Planez" in `recovered-msfs-bindings.json`: RX/RY -> `KEY_MIXTURE1_SET`/`KEY_MIXTURE2_SET`), removed when MSFS controller bindings were cleared. MSFS sends that event the full axis range, -16383..16383. SPAD now sends the same: `MIXTURE1/2_SET` with `Round(local% * 327.66 - 16383, 0)`. Tried and failed: `LEVER_MIXTURE` (sends `AXIS_MIXTURE*_SET`, which the turbo Baron ignores), `MIXTURE_SET` at 0-16383 and at 0-100, and the LVAR writes below. Script: `bind-cp3-mixture-levers.ps1`. Live cockpit response remains to be confirmed.

PREVIOUS: The user reported that both LVAR-based attempts still failed in the cockpit. Those assignments have been replaced by the manufacturer's recommended `SIMCONNECT:MIXTURE1_SET` and `MIXTURE2_SET` events, each with an explicit Exp parameter scaling its CP3 local axis percentage to 0-16383. Midpoint is 8192; no mixture LVAR writes remain. Other bindings were compared and verified unchanged. The historical notes below describe superseded attempts, not verified working behavior. Live intermediate event values and cockpit response remain to be confirmed.

Live logs showed SPAD writing values such as 99 and 100 to `BKSQ_MixtureLeverPosition_1/2`, while the aircraft reported those variables clamped at 1. This explains the full-rich/full-cutoff behavior.

Both CP3 mixture axis VALUE events now write an expression:

`Min(1.0, Max(0.0, [LOCAL:JOY_0X33440X025C_RX_AXIS] / 100.0))`

The right lever uses `RY_AXIS`. Hardware percentages 0,25,50,75,100 now map to 0,0.25,0.5,0.75,1. All ten outputs were evaluated with the installed SPAD NCalc library. This supersedes earlier `SetEventValue_AxisPercent` mixture assignments.

Only the two mixture-action scaling fields changed; comparison verified all other bindings unchanged. Backup: `backups/mixture-proportional-20261031-194809/`. Smooth physical cockpit response still requires confirmation.
