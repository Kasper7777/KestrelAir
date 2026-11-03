# SFS Monitor / SPAD handover for RotAIR and PulsAIR

The four SimFlight Services panels (RotAIR Type-1 and Type-2, PulsAIR Type-1 and Type-2) are driven by whichever program you choose:

- **SFS Monitor open** (`SFSmonitor_V5_0.exe`): SimFlight's own monitor drives the panels and SPAD ignores them.
- **SFS Monitor closed:** SPAD drives the panels as before.

Before this, running both at once made every encoder click count twice.

## How it works

1. `.tools/ka-sfs/ka-sfs-watch.exe` runs hidden in the background. Every second it checks whether a process named `SFSmonitor…` is running, and writes the answer into the sim as `L:KA_SFS_MONITOR` (1 = running, 0 = not). It re-sends the value every 2 seconds, because L-variables reset when an aircraft loads, and reconnects by itself after MSFS restarts. It logs each change to `%TEMP%\ka-sfs-watch.log`.
2. Every SPAD binding on those panels has one extra condition: `LVAR:KA_SFS_MONITOR` Unequal 1. That's 260 bindings in each of the four GTN profiles: Baron GTN and Bonanza A36, A36TC and B36TP. The condition covers both the ANA and GC device IDs. SPAD ANDs conditions together, so the existing ones (PFD/MFD focus, hold states and so on) still work. The other four profiles have no SimFlight panels.
3. If the watcher isn't running, the variable reads 0 and SPAD keeps the panels. That means it can never leave the panels dead, though both programs could double up again if SFS Monitor is opened while the watcher is off.

Tested live on 2026-11-03 with the real SFS Monitor. With it closed, SPAD drove the knobs. With it open, each click gave one step with no doubling. After closing it, SPAD took the panels back.

## Starting the watcher automatically

The watcher has to run for the handover to work. Right now it's started by hand; I wasn't permitted to add it to Windows startup without your say-so. To make it start at every logon:

1. Press Win+R, type `shell:startup`, and press Enter.
2. Right-click in that folder and choose New > Shortcut.
3. Set the target to `C:\Users\Aero\Documents\GitHub\KestrelAir\.tools\ka-sfs\ka-sfs-watch.exe` and name it "KestrelAir SFS watch".

It's safe to start it more than once, because only one copy ever runs. `ka-sfs-watch.exe --once` reports whether SFS Monitor is currently detected.

## Files

- `gate-sfs-panels.py <profile.xml>...` adds the condition and is idempotent. `--remove` takes it out again; this was tested to restore the files byte-for-byte. For a new profile that uses the panels, run it with SPAD closed.
- `.tools/ka-sfs/ka-sfs-watch.cs` is the watcher source. It builds with `csc -target:winexe -platform:x64 -out:ka-sfs-watch.exe ka-sfs-watch.cs` and loads `SimConnect_internal.dll` from the running MSFS's folder, so no install path is hard-coded.
- Backup before the change: `backups/sfs-gate-20261103-215325/`.
