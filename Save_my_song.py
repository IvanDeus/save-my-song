#!/usr/bin/env python3
"""
Save_my_song.py — AudioSeal watermark tool 🔐🎵

Embed an inaudible 16-bit watermark into any WAV track,
or check whether a file already carries one.

Usage examples:
    python Save_my_song.py track.wav                        # watermark → protected_track.wav
    python Save_my_song.py track.wav -o sealed.wav          # watermark → sealed.wav
    python Save_my_song.py --check sealed.wav               # verify watermark presence
    python Save_my_song.py --check sealed.wav -t 0.7        # custom detection threshold
"""

import argparse
import os
import sys
import time

# ──────────────────────── tiny colour helpers ────────────────────────
_SUPPORTS_COLOR = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _SUPPORTS_COLOR else text

def _bold(t: str)   -> str: return _c("1", t)
def _green(t: str)  -> str: return _c("32", t)
def _cyan(t: str)   -> str: return _c("36", t)
def _yellow(t: str) -> str: return _c("33", t)
def _red(t: str)    -> str: return _c("31", t)
def _dim(t: str)    -> str: return _c("2", t)

def _ok(msg: str)   -> None: print(f"  {_green('✔')} {msg}")
def _info(msg: str)  -> None: print(f"  {_cyan('ℹ')} {msg}")
def _warn(msg: str)  -> None: print(f"  {_yellow('⚠')} {msg}")
def _fail(msg: str)  -> None: print(f"  {_red('✖')} {msg}", file=sys.stderr)

BANNER = r"""
   ╔═══════════════════════════════════════╗
   ║   🔐  AudioSeal  — Save_my_song.py    ║
   ║   Invisible watermark protection      ║
   ╚═══════════════════════════════════════╝
"""

# ──────────────────────── argument parsing ───────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="Save_my_song.py",
        description="Embed or detect an AudioSeal watermark in a WAV file. Script made by [ ivan deus ].",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "input",
        help="Path to the input WAV file.",
    )
    p.add_argument(
        "-o", "--output",
        default=None,
        help="Output path for the watermarked file "
             "(default: protected_<input>). Ignored in --check mode.",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="Detection mode: check if the input file carries a watermark "
             "instead of embedding one.",
    )
    p.add_argument(
        "-t", "--threshold",
        type=float,
        default=0.5,
        help="Detection probability threshold (0.0–1.0, default: 0.5). "
             "Only used in --check mode.",
    )
    p.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress banner and informational messages.",
    )
    return p


# ──────────────────────── core logic ─────────────────────────────────
def _load_audio(path: str):
    """Load a WAV file and return (mono[batch,1,samples], sample_rate, original_wav)."""
    import torchaudio

    _info(f"Loading audio: {_bold(path)}")
    wav, sr = torchaudio.load(path)
    n_channels = wav.shape[0]
    dur = wav.shape[-1] / sr
    _info(f"Sample rate {_cyan(str(sr))} Hz  •  "
          f"channels {_cyan(str(n_channels))}  •  "
          f"duration {_cyan(f'{dur:.2f}')} s")

    # AudioSeal models expect mono — downmix if needed
    wav_mono = wav
    if n_channels > 1:
        wav_mono = wav.mean(dim=0, keepdim=True)
        _info(f"Downmixed to mono for AudioSeal processing")

    return wav_mono.unsqueeze(0), sr, wav   # [1, 1, samples], sr, [ch, samples]


def embed_watermark(input_path: str, output_path: str) -> None:
    """Embed a 16-bit AudioSeal watermark into *input_path* → *output_path*."""
    import torch
    import torchaudio
    from audioseal import AudioSeal

    wav_mono, sr, wav_orig = _load_audio(input_path)

    _info("Loading generator model …")
    model = AudioSeal.load_generator("audioseal_wm_16bits")
    _ok("Generator ready")

    _info("Generating watermark …")
    t0 = time.time()
    with torch.no_grad():
        watermark = model.get_watermark(wav_mono)  # mono [1,1,samples]
    elapsed = time.time() - t0
    _ok(f"Watermark generated in {_cyan(f'{elapsed:.2f}')} s")

    # Apply the mono watermark to the original audio.
    # The watermark [1, samples] broadcasts across all channels of wav_orig [ch, samples],
    # so the output keeps the original channel layout (mono or stereo).
    n_channels = wav_orig.shape[0]
    watermarked = wav_orig + watermark.squeeze(0)         # broadcast [1, samples] → [ch, samples]
    watermarked = watermarked.clamp(-1.0, 1.0)
    if n_channels > 1:
        _info(f"Watermark applied to all {n_channels} channels")

    _info(f"Saving → {_bold(output_path)}")
    torchaudio.save(output_path, watermarked, sr)
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    _ok(f"Protected file saved ({_cyan(f'{size_mb:.1f}')} MB)")


def check_watermark(input_path: str, threshold: float) -> bool:
    """
    Detect whether *input_path* carries an AudioSeal watermark.

    Returns True if a watermark is detected above *threshold*.
    """
    import torch
    from audioseal import AudioSeal

    wav_mono, sr, _ = _load_audio(input_path)

    _info("Loading detector model …")
    detector = AudioSeal.load_detector("audioseal_detector_16bits")
    _ok("Detector ready")

    _info(f"Analysing watermark (threshold = {_cyan(str(threshold))}) …")
    t0 = time.time()
    with torch.no_grad():
        prob, msg = detector.detect_watermark(
            wav_mono,                 # detector expects [batch, channels, samples]
            detection_threshold=threshold,
        )
    elapsed = time.time() - t0

    prob_val = prob.item() if hasattr(prob, "item") else float(prob)
    detected = prob_val >= threshold

    # ── pretty-print results ──
    print()
    print(f"  ┌──────────────────────────────────────")
    print(f"  │  Detection probability : {_bold(f'{prob_val:.4f}')}")
    print(f"  │  Threshold             : {threshold}")

    if msg is not None and msg.numel() > 0:
        bits = "".join(str(int(b)) for b in msg.flatten().tolist())
        print(f"  │  Decoded message       : {_dim(bits)}")

    if detected:
        print(f"  │  Result                : {_green('WATERMARK DETECTED ✔')}")
    else:
        print(f"  │  Result                : {_yellow('NO WATERMARK FOUND')}")

    print(f"  └──────────────────────────────────────")
    _info(f"Analysis completed in {_cyan(f'{elapsed:.2f}')} s")

    return detected


# ──────────────────────── entry point ────────────────────────────────
def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.quiet:
        print(BANNER)

    # ── validate input ──
    if not os.path.isfile(args.input):
        _fail(f"File not found: {args.input}")
        return 1

    try:
        if args.check:
            # ---------- detection mode ----------
            detected = check_watermark(args.input, args.threshold)
            return 0 if detected else 2     # exit-code 2 = "not detected"

        else:
            # ---------- embed mode ----------
            if args.output is None:
                base = os.path.basename(args.input)
                name, ext = os.path.splitext(base)
                args.output = os.path.join(
                    os.path.dirname(args.input) or ".",
                    f"protected_{name}{ext}",
                )

            if os.path.abspath(args.input) == os.path.abspath(args.output):
                _fail("Input and output paths must differ!")
                return 1

            embed_watermark(args.input, args.output)
            print()
            _ok(_bold("Done! Your track is now protected. 🎶"))
            return 0

    except Exception as exc:
        _fail(f"Something went wrong: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
