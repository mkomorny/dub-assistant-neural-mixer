# Dub Assistant - Neural Performance Mixer

A real-time neural network mixer assistant for live dub music performance and audio engineering, implemented as a native Max for Live MIDI device with an in-engine JavaScript Multilayer Perceptron (MLP).

## Scientific Foundation

Follows the interaction paradigm and research established by **Joaquín Jiménez-Sauma**, *Creating a Machine Learning Assistant for the Real-Time Performance of Dub Music* (Proceedings of the Sound and Music Computing Conferences, CSMC / MuMe 2020).

## Neural Architecture

Rather than relying on bulky external Python bridges, Dub Assistant embeds a lightweight, high-performance **Multilayer Perceptron neural network in pure JavaScript (`device/dub-assistant.js`)**:
- **Inputs (3 Semantic Dimensions)**: Color, Rhythm, and Space performance macro knobs.
- **Hidden Layers**: 16-neuron dense layer with sigmoid activation.
- **Outputs (24 Audio Parameters)**: Concurrently maps across 8 track sends, 8 feedback probabilities, and 8 dynamic return faders.
- **Training**: Learns your individual mixing style from performance datasets (`device/sample-dataset.csv`) using online backpropagation.

## Repository Contents

- `device/Dub Assistant.amxd`: Packaged, production-ready Max for Live device.
- `device/dub-assistant.js`: The standalone JavaScript neural network engine.
- `device/sample-dataset.csv`: Curated multi-fader dub mixing training corpus.
- `docs/`: Complete PDF user manual, operator reference card, and install guide.

## Requirements

- **Ableton Live 11 or 12 Standard / Suite** with **Max for Live**.
- Cross-platform compatible (Windows 10/11 & macOS Apple Silicon / Intel).

## Instructions

See [INSTRUCTIONS.md](./INSTRUCTIONS.md) for installation and performance instructions.

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0) - see the [LICENSE](./LICENSE) file for details.
