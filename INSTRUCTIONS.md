# Dub Assistant - Setup & Performance Guide

## Prerequisites
- **Ableton Live 11 / 12** with Max for Live enabled.

---

## 1. Installation

1. Copy `device/Dub Assistant.amxd` into your Ableton User Library:
   - Windows: `Documents/Ableton/User Library/Presets/MIDI Effects/Max MIDI Effect/`
   - macOS: `Music/Ableton/User Library/Presets/MIDI Effects/Max MIDI Effect/`
2. In Live, drag `Dub Assistant` onto a MIDI track or master return bus.

---

## 2. Training the Neural Network

1. Click **Train** on the device interface to ingest `sample-dataset.csv`.
2. The internal JavaScript MLP trains over 50 epochs directly in Max without freezing the audio thread.
3. Map your MIDI hardware controller knobs to **Color**, **Rhythm**, and **Space**.
4. Perform live: moving a single macro knob now coordinates multi-send delay/reverb dub throws across all 8 tracks simultaneously.
