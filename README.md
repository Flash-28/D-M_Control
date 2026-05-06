# D+M Master Manager

Interactive Python control script for compatible Denon and Marantz receivers
that expose the same HTTPS AJAX API on port 10443.

It audits the receiver's current state, lets you back up / restore a full
configuration snapshot as JSON, toggles power, sets volume, and runs two
pre-baked "calibration environment" macros used before running external room
measurement / tuning sessions.

## What it controls

- Power (Main Zone)
- Master Volume (dB or absolute scale, 0.5 dB steps)
- Audyssey mode (Reference / L-C-R Bypass / Flat / Off)
- Surround mode (Stereo / Direct / Movie / Game / Music / Auro3D)
- ECO mode (On / Auto / Off)
- Subwoofer LPF for LFE (250 Hz)
- Per-speaker Size, Level, Distance, Crossover (all 13.2 channels)
- 2-Channel Playback: Setting (Auto/Manual), Front size, Subwoofer Mode
  (LFE / LFE+Main), Front L/R Distance, Front L/R Level

## Requirements

- Python 3.8+ (stdlib only — no pip install needed)
- The AVR and the machine running the script must be on the same LAN
- The AVR's web UI must be reachable at `https://<avr-ip>:10443/`

## Running

```bash
python3 D+M_MasterManager.py
```

On launch the script SSDP-discovers the AVR on the local network. If discovery
fails it prompts for an IP manually.

## Menu

```
 b: Backup               r: Restore           
 f: Full Calibration     s: Sub Calibration
 v: Set Volume           p: Toggle Power
 d: Refresh Display      q: Quit
```

| Key | Action                                                              |
|-----|---------------------------------------------------------------------|
| b   | Snapshot current state to `avr_backup.json` (same directory)        |
| r   | Differential restore from `avr_backup.json` (only pushes changed values) |
| s   | Sub-only calibration environment (Front L/R + Sub1)                 |
| f   | Full calibration environment (every configured speaker)             |
| v   | Prompt for a new master volume (dB or absolute)                     |
| p   | Toggle Main Zone power (waits 10 s on power-on for network services)|
| d   | Re-fetch and redraw the audit                                       |
| q   | Quit                                                                |

Volume input rules: values `<= 20` are treated as dB (e.g. `-40`, `-12.5`);
values `> 20` are treated as absolute 0–98 scale (e.g. `38`, `67.5`).

## Backup / Restore

`b` writes the full fetched state to `avr_backup.json` in the current working
directory. The file is human-readable; committing it alongside the script is a
reasonable way to version your configuration.

`r` reads that file, fetches the live state, and applies **only the fields
that differ** — the console prints each change as `field: old -> new`. Because
the 2-channel Front / SubwooferMode / L-R distance / L-R level are read-only
when 2CH Setting is Auto, the restore automatically switches to Manual,
writes the individual fields, then re-applies the target Setting last (so an
Auto backup ends up back in Auto).

## Calibration macros

Both macros force:

- Audyssey: **Off**
- Master Volume: **-10 dB** (70 absolute)
- 2-Channel Mode: **Manual, Large front, LFE (not LFE+Main), L/R at 0 dB / 0 ft**
- All targeted speakers: **Level 0 dB, Distance 0 ft, Size Large**
- Surround mode: **Stereo**
- ECO mode: **Off**
- Subwoofer LPF for LFE: **250 Hz**

| Mode | Targets                                         |
|------|-------------------------------------------------|
| `s`  | Front L, Front R, Subwoofer 1                   |
| `f`  | Every speaker that the AVR reports as configured|

Use the matching `r` (Restore) afterward to return to your saved configuration.

## Audit display

Each menu cycle redraws the screen with four sections:

1. **Header**: model, IP, power state (green/red)
2. **Status**: Audyssey, Volume, Source, Eco, Surround
3. **Speakers table**: Size / Level / Distance / Crossover for every configured channel
4. **2-Channel Mode table**: Front L and Front R with Size / Level / Distance / Crossover,
   plus the current Setting and SW Mode on the header line

## Notes and caveats

- The script uses `ssl._create_unverified_context()` because the AVR serves a
  self-signed certificate. Traffic is still encrypted; hostname verification
  is simply skipped.
- `fetch_full_state` filters speakers to those actually reported by the AVR
  in the live Level block (type 5). Channels absent from your speaker layout
  are never written, even if you have a large backup file.
- 2-channel writes are deliberately per-speaker (one HTTP request each) to
  match the web UI's write pattern. The AVR silently ignores batched 2-ch
  payloads on some firmware revisions.
- This script is provided as-is and I make no guarantees or warranties that it
  will work for your reciever.  I have tested this on exactly ONE reciever, the
  Denon X8500HA, so use at your own risk.
- I recommend starting with a backup before making any changes.
