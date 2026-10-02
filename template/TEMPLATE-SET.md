# Dub Assistant template Set

This is the Live Set the device expects. Build it once, then **Collect
All and Save** as your starting template (Live manual chapter 5).

Producer Pal can create the tracks, returns, and native Delay / Reverb.
It cannot add this Max device, trigger Stem Separation, or write the
real-time fader motion.

## Track list

Create the following, in this order if you are starting empty:

| Kind | Name | Notes |
| --- | --- | --- |
| Audio | Drums | Heart track |
| Audio | Bass | Heart track |
| Audio | Vox | |
| Audio | Keys | |
| Audio | Guitar | |
| Audio | FX | |
| Audio | Perc | |
| Audio | Other | Spare / others stem |
| Return | Dub Delay | Native **Delay**. Send A |
| Return | Dub Verb | Native **Reverb**. Send B |
| MIDI | Dub Assistant | This device only. No clips required |

Turn send A and send B on for every audio track. Leave the MIDI track
unrouted to audio.

## Load the device

1. In the Browser, open **User Library → Presets → MIDI Effects → Max
   MIDI Effect → Dub Assistant**.
2. Drop **Dub Assistant** onto the MIDI track of the same name.
3. Click **Bind** on the device.

## Optional: stems

If you have Live 12 Suite:

1. Select a stereo clip.
2. Run **Stem Separation** (chapter 22). Pal cannot start this.
3. Drag Vocals, Drums, Bass, and Other onto `Vox`, `Drums`, `Bass`,
   and `Other`.
4. Fill Keys / Guitar / FX / Perc from the rest of the arrangement or
   leave them empty.

## Pal-only half

If Pal is connected, ask it to:

1. Create the eight audio tracks and two returns with the names above.
2. Put Delay on `Dub Delay` and Reverb on `Dub Verb`.
3. Create the MIDI track `Dub Assistant`.

You still drop the `.amxd` yourself. Pal cannot add a User Library Max
device in v1 of this project.

## Colors (optional)

These colors are only a visual aid. The device does not read them.

| Track | Hex |
| --- | --- |
| Drums | `#FF5A36` |
| Bass | `#3D8BFF` |
| Vox | `#F2F2F2` |
| Keys | `#C9A227` |
| Guitar | `#7A5C3C` |
| FX | `#9B59B6` |
| Perc | `#E67E22` |
| Other | `#7F8C8D` |
| Dub Delay | `#1ABC9C` |
| Dub Verb | `#3498DB` |
| Dub Assistant | `#2C3E50` |
