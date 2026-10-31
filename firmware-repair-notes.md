Installed 2026-10-31 into **Baron - GNS 530 + TDS GTNxi 650** only.

- Right WarBRD-D now maps to `3344:03F5:0`, HID path `a&1aa429cf`, identified by its unchanged USB port.
- Added right-stick pitch/roll, CM3 twin throttles, and CP3 twin propeller/mixture axes. Hardware reports 0–60000; directions were recovered from saved MSFS assignments.
- Recovered 24 button assignments onto unused SPAD inputs. All preexisting SPAD actions and unrelated profile XML were verified unchanged.
- Backup: `backups/firmware-repair-20261031-181829/` (profile and local mapping).
- Follow-up: at the user's request, cleared 160 assigned actions from 20 saved MSFS hardware profiles, including VIRPIL and Alpha Flight Controls. Keyboard and Tobii files were verified unchanged. Backup: `backups/msfs-controller-clear-20261031-182055/`. The simulator was closed before editing. SPAD settings were unchanged by this cleanup. Built-in defaults and cloud sync behavior still require a check after launching MSFS.
- Other aircraft SPAD profiles, CP2 assignments, and flaps-axis choice are not repaired by these changes. Cleared native functions without a SPAD replacement will be unavailable until assigned in SPAD.
- Physical input and cockpit response still require live verification. Successful profile loading alone does not prove operation.

`repair-spad-firmware.ps1` records the one-time installation. It deliberately requires the original device mapping and refuses to apply while SPAD is running.
