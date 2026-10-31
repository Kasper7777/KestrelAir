Restored in VIRPIL Configurator 2 Alpha-0.2.1.0 on 2026-10-31.

- Source: automatic pre-update throttle backup `2026.10.31_17.40.52.618_VPC MongoosT-50CM3 Throttle.device.vpcprofile`.
- Assigned Primary Mode Rotator as shifter; enabled B1–B6 in numbered states 1–5, Normal button mode. Any and None banks are Off.
- Restored selector USB outputs to Off, matching the original internal shifter behavior. This does not disable mode lighting.
- Verified all six base LED colours and all five `LF_Shifting` lighting rules exactly match the original backup.
- Verified axis setup and calibration match the pre-repair export. No CP3 changes were made.
- Configurator log confirms throttle PID 0194 was written, restarted, rediscovered, and profile applying finished at 18:45:04.
- Before, original, and restored exports are retained in `backups/virpil-throttle-modes/`.

Physical testing of the dial and all SPAD button assignments remains required; firmware button numbering may differ from the old firmware.
