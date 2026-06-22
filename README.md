# Save-my-song script

> Invisible 16-bit watermark protection for your audio tracks, powered by [Meta's AudioSeal](https://github.com/facebookresearch/audioseal).

Embed an **inaudible watermark** into any WAV file to prove ownership — or verify whether a file already carries one. One script, two modes, zero compromise on audio quality.

---

## ✨ Features

| | |
|---|---|
| 🎵 **Embed mode** | Inject a 16-bit watermark that's imperceptible to human hearing |
| 🔍 **Check mode** | Detect and decode a watermark from any audio file |
| 🎨 **Pretty CLI** | Colored output, progress feedback, timing, and file stats |
| ⚙️ **Flexible** | Custom output paths, adjustable detection thresholds, quiet mode |
| 🛡️ **Robust** | Input validation, graceful error handling, meaningful exit codes |

## 📦 Requirements

- **Python** 3.8+
- **PyTorch** and **torchaudio**
- **AudioSeal**

```bash
pip install torch torchaudio audioseal
```

> [!NOTE]
> Models are downloaded automatically from HuggingFace on first run and cached locally.

## 🚀 Usage

### Embed a watermark

```bash
# Watermark a track → outputs protected_<filename>.wav
python Save_my_song.py my_track.wav

# Specify a custom output path
python Save_my_song.py my_track.wav -o sealed_track.wav
```

### Check for a watermark

```bash
# Detect watermark in a file
python Save_my_song.py --check sealed_track.wav

# Use a stricter detection threshold (0.0–1.0)
python Save_my_song.py --check sealed_track.wav -t 0.7
```

### Example output

**Embed mode:**
```
   ╔═══════════════════════════════════════╗
   ║   🔐  AudioSeal  — Save_my_song.py    ║
   ║   Invisible watermark protection      ║
   ╚═══════════════════════════════════════╝

  ℹ Loading audio: my_track.wav
  ℹ Sample rate 44100 Hz  •  channels 2  •  duration 198.35 s
  ℹ Loading generator model …
  ✔ Generator ready
  ℹ Generating watermark …
  ✔ Watermark generated in 3.21 s
  ℹ Saving → protected_my_track.wav
  ✔ Protected file saved (34.2 MB)

  ✔ Done! Your track is now protected. 🎶
```

**Check mode:**
```
  ℹ Loading audio: protected_my_track.wav
  ℹ Sample rate 44100 Hz  •  channels 2  •  duration 198.35 s
  ℹ Loading detector model …
  ✔ Detector ready
  ℹ Analysing watermark (threshold = 0.5) …

  ┌──────────────────────────────────────
  │  Detection probability : 0.9987
  │  Threshold             : 0.5
  │  Decoded message       : 1010110011001101
  │  Result                : WATERMARK DETECTED ✔
  └──────────────────────────────────────
  ℹ Analysis completed in 1.84 s
```

## ⚙️ CLI Reference

```
usage: Save_my_song.py [-h] [-o OUTPUT] [--check] [-t THRESHOLD] [-q] input
```

| Argument | Description |
|---|---|
| `input` | Path to the input WAV file |
| `-o`, `--output` | Output path for watermarked file (default: `protected_<input>`) |
| `--check` | Detection mode — check for a watermark instead of embedding |
| `-t`, `--threshold` | Detection threshold, 0.0–1.0 (default: `0.5`) |
| `-q`, `--quiet` | Suppress the banner and informational messages |

## 📤 Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success — watermark embedded or detected |
| `1` | Error — missing file, invalid arguments, runtime failure |
| `2` | No watermark found (check mode only) |

> [!TIP]
> Exit code `2` makes it easy to script detection checks:
> ```bash
> if python Save_my_song.py --check track.wav -q; then
>     echo "Watermarked ✔"
> else
>     echo "Not watermarked"
> fi
> ```

## 🧠 How It Works

AudioSeal uses a neural network to generate a **frequency-domain watermark** that sits below the threshold of human perception. The watermark survives common audio transformations (compression, re-encoding, minor edits) while remaining completely inaudible.

```
┌────────────┐     ┌───────────┐      ┌─────────────────┐
│  Original  │ ──▶ │ Generator │ ──▶  │  Watermarked    │
│  audio.wav │     │  (embed)  │      │  protected.wav  │
└────────────┘     └───────────┘      └─────────────────┘
                                              │
                                              ▼
                                      ┌───────────┐
                                      │ Detector  │ ──▶  ✔ / ✖
                                      │  (check)  │      + decoded bits
                                      └───────────┘
```

- **Generator model** — `audioseal_wm_16bits` — embeds 16 bits of hidden information
- **Detector model** — `audioseal_detector_16bits` — recovers the probability + message

2026 [ ivan deus ]
