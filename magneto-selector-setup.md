Current selector setup, 2026-10-31, supersedes throttle five-mode instructions.

- Throttle five-position selector drives left `LVAR:BKSQ_IgnitionPosition_1`, buttons 60-64.
- CP3 five-position selector drives right `LVAR:BKSQ_IgnitionPosition_2`, buttons 43-47.
- Positions write 0, 1, 2, 3, 5 respectively. Value 5 holds START; moving back to position 4 writes BOTH (3). The manufacturer's Baron Professional v1.1 changelog documents value 5 as held starter operation.
- Throttle Shifter is None. B1-B6 are ordinary Normal buttons, with no mode banks. Axis calibration was checked unchanged.
- Tobii remains on physical B3/B6, now logical buttons 44/47. Flood and left/right pitot remain physical T5/T6/T7, now buttons 48-53. Retired the former encoder magneto assignments.
- CP2 assignments and both sticks were preserved. CP3's other controls were preserved.
- Before/after SPAD and VIRPIL profiles are saved in the directory recorded in `magneto-selector-backup.txt`.

Saved configuration and input numbers are verified. Full cockpit confirmation of selector position semantics remains required.
