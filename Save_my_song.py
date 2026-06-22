#!/usr/bin/env python3
"""
Save_my_song.py — AudioSeal watermark tool 🔐🎵
Developed by [ ivan deus ] 2026

Embed an inaudible 16-bit watermark into any WAV track,
or check whether a file already carries one.

Usage examples:
    python Save_my_song.py track.wav --email owner@example.com
    python Save_my_song.py track.wav -o sealed.wav --email owner@example.com
    python Save_my_song.py --check sealed.wav
    python Save_my_song.py --check sealed.wav --verify-email owner@example.com
    python Save_my_song.py --check sealed.wav -t 0.7
"""

import argparse
import hashlib
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

# ──────────────────────── 16-bit email hashing ───────────────────────
def _email_to_16bit_tensor(email: str, device):
    """Deterministically hash an email to a 16-bit binary tensor [1, 16]."""
    h = hashlib.sha256(email.encode('utf-8')).digest()
    val = int.from_bytes(h[:2], byteorder='big')  # Take first 2 bytes = 16 bits
    bits = [(val >> (15 - i)) & 1 for i in range(16)]
    return torch.tensor([bits], dtype=torch.float32, device=device)

def _decode_msg_to_bits(msg_tensor) -> str:
    """Convert detector message output to a 16-bit string."""
    if msg_tensor is None or msg_tensor.numel() == 0:
        return ""
    # Detector returns probabilities; threshold at 0.5
    bits = (msg_tensor.flatten() > 0.5).int().tolist()
    return "".join(str(b) for b in bits)

def _verify_email_hash(bits_str: str, email: str) -> bool:
    """Check if a decoded 16-bit string matches the hash of an email."""
    if not bits_str or not email:
        return False
    target = _email_to_16bit_tensor(email, 'cpu')
    target_bits = "".join(str(int(b)) for b in target.flatten().tolist())
    return bits_str == target_bits

# ──────────────────────── argument parsing ───────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="Save_my_song.py",
        description="Embed or detect an AudioSeal watermark in a WAV file. Developed by [ ivan deus ].",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("input", help="Path to the input WAV file.")
    p.add_argument("-o", "--output", default=None,
                   help="Output path for the watermarked file (default: protected_<input>). Ignored in --check mode.")
    p.add_argument("--check", action="store_true",
                   help="Detection mode: check if the input file carries a watermark instead of embedding one.")
    p.add_argument("--email", type=str, default=None,
                   help="Owner email to embed as a 16-bit ownership hash (embed mode only).")
    p.add_argument("--verify-email", type=str, default=None,
                   help="Email to verify against the detected watermark hash (check mode only).")
    p.add_argument("-t", "--threshold", type=float, default=0.5,
                   help="Detection probability threshold (0.0–1.0, default: 0.5). Only used in --check mode.")
    p.add_argument("-q", "--quiet", action="store_true",
                   help="Suppress banner and informational messages.")
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

    wav_mono = wav
    if n_channels > 1:
        wav_mono = wav.mean(dim=0, keepdim=True)
        _info("Downmixed to mono for AudioSeal processing")

    return wav_mono.unsqueeze(0), sr, wav   # [1, 1, samples], sr, [ch, samples]


def embed_watermark(input_path: str, output_path: str, email: str = None) -> None:
    """Embed a 16-bit AudioSeal watermark into *input_path* → *output_path*."""
    import torch
    import torchaudio
    from audioseal import AudioSeal

    wav_mono, sr, wav_orig = _load_audio(input_path)

    _info("Loading generator model …")
    model = AudioSeal.load_generator("audioseal_wm_16bits")
    _ok("Generator ready")

    msg_tensor = None
    if email:
        _info(f"Hashing ownership email → 16-bit payload …")
        msg_tensor = _email_to_16bit_tensor(email, wav_mono.device)
        _ok(f"Ownership hash ready for: {_bold(email)}")

    _info("Generating watermark …")
    t0 = time.time()
    with torch.no_grad():
        watermark = model.get_watermark(wav_mono, message=msg_tensor)
    elapsed = time.time() - t0
    _ok(f"Watermark generated in {_cyan(f'{elapsed:.2f}')} s")

    n_channels = wav_orig.shape[0]
    watermarked = wav_orig + watermark.squeeze(0)
    watermarked = watermarked.clamp(-1.0, 1.0)
    if n_channels > 1:
        _info(f"Watermark applied to all {n_channels} channels")

    _info(f"Saving → {_bold(output_path)}")
    torchaudio.save(output_path, watermarked, sr)
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    _ok(f"Protected file saved ({_cyan(f'{size_mb:.1f}')} MB)")


def check_watermark(input_path: str, threshold: float, verify_email: str = None) -> bool:
    """Detect whether *input_path* carries an AudioSeal watermark."""
    import torch
    from audioseal import AudioSeal

    wav_mono, sr, _ = _load_audio(input_path)

    _info("Loading detector model …")
    detector = AudioSeal.load_detector("audioseal_detector_16bits")
    _ok("Detector ready")

    _info(f"Analysing watermark (threshold = {_cyan(str(threshold))}) …")
    t0 = time.time()
    with torch.no_grad():
        prob, msg = detector.detect_watermark(wav_mono)
    elapsed = time.time() - t0

    prob_val = prob.item() if hasattr(prob, "item") else float(prob)
    detected = prob_val >= threshold
    bits_str = _decode_msg_to_bits(msg)

    print()
    print(f"  ┌──────────────────────────────────────")
    print(f"  │  Detection probability : {_bold(f'{prob_val:.4f}')}")
    print(f"  │  Threshold             : {threshold}")

    if bits_str:
        print(f"  │  Decoded 16-bit hash   : {_dim(bits_str)}")
    else:
        print(f"  │  Decoded 16-bit hash   : {_dim('N/A')}")

    if verify_email and bits_str:
        match = _verify_email_hash(bits_str, verify_email)
        status = _green('MATCH ✔') if match else _red('MISMATCH ✖')
        print(f"  │  Email verification    : {status} ({_bold(verify_email)})")
    elif verify_email:
        print(f"  │  Email verification    : {_yellow('Skipped (no watermark)')}")

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

    if not os.path.isfile(args.input):
        _fail(f"File not found: {args.input}")
        return 1

    try:
        if args.check:
            if args.email:
                _warn("--email is ignored in --check mode. Use --verify-email instead.")
            detected = check_watermark(args.input, args.threshold, args.verify_email)
            return 0 if detected else 2

        else:
            if args.verify_email:
                _warn("--verify-email is ignored in embed mode. Use --email instead.")
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

            embed_watermark(args.input, args.output, args.email)
            print()
            _ok(_bold("Done! Your track is now protected. 🎶"))
            return 0

    except Exception as exc:
        _fail(f"Something went wrong: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
