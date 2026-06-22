# Save-my-song script

> Invisible 16-bit watermark protection for your audio tracks, powered by [Meta's AudioSeal](https://github.com/facebookresearch/audioseal).

Embed an **inaudible watermark** into any WAV file to prove ownership — or verify whether a file already carries one. One script, two modes, zero compromise on audio quality.

---

## ✨ Features

| | |
|---|---|
| 🎵 **Embed mode** | Inject a 16-bit watermark that's imperceptible to human hearing |
| 🔍 **Check mode** | Detect and decode a watermark from any audio file |
| 📧 **Ownership Proof** | Hash your email into the 16-bit payload to cryptographically tie the file to you |
| 🎨 **Pretty CLI** | Colored output, progress feedback, timing, and file stats |
| ⚙️ **Flexible** | Custom output paths, adjustable detection thresholds, quiet mode |
| 🛡️ **Robust** | Input validation, graceful error handling, meaningful exit codes |

## 📦 Requirements

- **Python** 3.12+
- **PyTorch** and **torchaudio**
- **AudioSeal**

```bash
pip install torch torchaudio audioseal
```

> [!NOTE]
> Models are downloaded automatically from HuggingFace on first run and cached locally.

## 🚀 Usage

### Embed a watermark with ownership proof

```bash
# Watermark a track and bind it to your email
python Save_my_song.py my_track.wav --email owner@example.com

# Specify a custom output path
python Save_my_song.py my_track.wav -o sealed_track.wav --email owner@example.com
```

### Check for a watermark & verify ownership

```bash
# Detect watermark in a file
python Save_my_song.py --check sealed_track.wav

# Verify if a specific email matches the embedded ownership hash
python Save_my_song.py --check sealed_track.wav --verify-email owner@example.com

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
  ℹ Hashing ownership email → 16-bit payload …
  ✔ Ownership hash ready for: owner@example.com
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
  │  Decoded 16-bit hash   : 1010110011001101
  │  Email verification    : MATCH ✔ (owner@example.com)
  │  Result                : WATERMARK DETECTED ✔
  └──────────────────────────────────────
  ℹ Analysis completed in 1.84 s
```

## ⚙️ CLI Reference

```
usage: Save_my_song.py [-h] [-o OUTPUT] [--check] [--email EMAIL] [--verify-email EMAIL] [-t THRESHOLD] [-q] input
```

| Argument | Description |
|---|---|
| `input` | Path to the input WAV file |
| `-o`, `--output` | Output path for watermarked file (default: `protected_<input>`) |
| `--check` | Detection mode — check for a watermark instead of embedding |
| `--email` | Owner email to embed as a 16-bit ownership hash (embed mode) |
| `--verify-email` | Email to verify against the detected watermark hash (check mode) |
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

### 🔐 About the 16-bit Email Hash
AudioSeal's payload capacity is strictly **16 bits** (65,536 combinations). An email address cannot fit directly. This script solves it by:
1. Hashing your email with `SHA-256`
2. Taking the first 16 bits as a deterministic fingerprint
3. Embedding that fingerprint into the audio
4. During verification, re-hashing the claimed email and comparing it to the decoded bits

This provides a lightweight, reproducible proof-of-ownership mechanism suitable for creator tracking and attribution. For enterprise-grade cryptographic guarantees, consider pairing this with external metadata registries.

2026 [ ivan deus ]
