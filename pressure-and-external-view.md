Installed 2026-10-31 in Baron - GNS 530 + TDS GTNxi 650.

- CP3 B13 sends Backspace to the active simulator window, matching the preserved keyboard `KEY_VIEW_MODE` shortcut. B8-B12 are byte-for-byte unchanged in the XML comparison.
- Throttle E1: CCW55 decreases pressurization rate by 50 ft/min; CW56 increases it. Range is clamped to 150-2000 ft/min using `LVAR:var_pressurizationClimbRate`.
- Throttle E2: CCW58 decreases cabin-altitude goal by 100 ft; CW59 increases it. Range is clamped to -1000-15000 ft using `LVAR:var_pressurizationGoal`.
- Expressions use SPAD's `SourceDataDefinition` field, matching the user's working expression configuration. The variables/ranges were verified in the Baron Professional manual, Environmental Control Variables.
- The user confirmed the mixtures work. Their current configuration and all other bindings were preserved by a complete-profile comparison allowing only B13 and these four encoder directions to change.
- Boundary/midrange expressions were evaluated using the installed NCalc library. Backup: `backups/pressure-external-view-20261031-230228/`.

Live cockpit confirmation of the new pressure controls and B13 remains required.
