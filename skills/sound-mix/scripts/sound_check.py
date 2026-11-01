# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["numpy==2.5.3"]
# ///
"""Measure the sound of a mix: loudness, hum, clicks, a dull generated voice, and noise in the pauses.

Usage: uv run sound_check.py <video|audio> [--words words.json] [--target -14] [--end <s>] [--skip <check>[,<check>]]
Run it on the no-music mix (music masks hum and fills pauses), then the loudness check again on the final master:
  uv run sound_check.py final.mp4 --skip hum,clicks,voice_hf
--words takes Whisper JSON with word times (`segments[].words[]` with word, start, end, as openai-whisper and
mlx-whisper write it with word timestamps on) or a flat list of such words. --end is where the body ends, before an
end card: hum, voice_hf and pauses judge the body only. Pass it whenever there is a card: a silent card pulls the
floor down and hides a hum, and a card's voice-over is the brand's voice, not a generated one. Needs ffmpeg on PATH.

One line per check, exit 1 on a FAIL:
  PASS  loudness  -14.2 LUFS (target -14), true peak -5.4 dBTP
  FAIL  hum       steady floor -33.0 dBFS (max -55: a constant bed reads as a fan or hum)
  FAIL  clicks    abrupt stops at: 13.67s
  FAIL  voice_hf  speech energy above 5 kHz -14.4 dB (min -12: a band-limited voice sounds like a cheap mic, s turns sh)
  PASS  pauses    speech -14 dBFS, pauses -41 dBFS (max -29); bursts within 6 dB of speech: none
  INFO  pauses    skipped: no word times

The checks, and what their thresholds were calibrated on (the approved reel: a dialogue reel a client accepted):
  loudness  integrated within 1 LU of --target, true peak <= -1 dBTP (ffmpeg ebur128). Social video: -14 LUFS.
  hum       the steady floor, the 10th percentile of 50 ms frame levels, <= -55 dBFS. A reel the client rejected
            because the room tone sounded like a fan: -33; the approved reel -84.5; the brand's own studio
            voice-over -84. When over a tenth of the span is digital silence (gaps between clips, a silent card)
            the floor reads -120 and the check can't see a bed under the rest: a FLAG, listen. Ignoring the silence
            instead put the approved reel's floor at -54.9, a false FAIL, so the measure stays as calibrated.
  clicks    sound above -35 dBFS that falls more than 30 dB within 5 ms (2.5 ms frames). A rejected cut had 4
            abrupt stops, all at edits; the client's published reels had none. A linear fade into digital silence
            reads as a stop unless it is long enough for its level: 30 ms clears it from -20 dBFS, 50 ms from -14,
            80 ms from -10 (measured on noise, every frame offset).
  voice_hf  on the frames within 20 dB of the loudest, the share of energy above 5 kHz >= -12 dB. A generated voice
            whose "s" was heard as "sh": -14.4; the approved reel -10.5; the brand's studio voice-over -6.7. It
            judges generated speech: a dark TTS voice-over measured -12.7 to -18.8 and sounded fine, so a mix whose
            only voice is such a VO runs with --skip voice_hf.
  pauses    in every pause over 0.4 s between words (trimmed 0.15 s each side, since Whisper ends words early, and
            past the word's own decay: 20 ms frames within 15 dB of the speech level touching an edge), the mix sits
            >= 15 dB under the speech level and no 20 ms burst comes within 6 dB of it: chatter between lines, a laugh
            under a cut, an ad-lib. Measured at 16 kHz, as calibrated. The approved reel: speech -14, pauses -41.
            A burst cut off from the word by a quiet frame still counts, so a loud breath can fail it: listen first.
An agent can't hear the mix. These numbers catch the gross cases; the owner's ear decides the rest.
"""
import json, subprocess, sys
from pathlib import Path

import numpy as np

SR = 48000
PAUSE_SR = 16000               # the pauses' thresholds were calibrated on 16 kHz audio (Whisper's rate)
CHECKS = ("loudness", "hum", "clicks", "voice_hf", "pauses")
HUM_MAX = -55.0                # dBFS: the steady floor of a clean mix
CLICK_FROM, CLICK_DROP = -35.0, 30.0
HF_MIN = -12.0                 # dB of the speech's energy above 5 kHz
PAUSE_UNDER, BURST_UNDER = 15.0, 6.0


def pcm(path, sr=SR):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True)
    if r.returncode or not r.stdout:
        sys.exit(f"can't decode the sound of {path}: {r.stderr.decode().strip() or 'no audio stream'}")
    return np.frombuffer(r.stdout, np.float32)


def db(x):
    return float(20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-9))


def levels(x, n):
    """dBFS of consecutive n-sample frames."""
    return 10 * np.log10(np.mean(np.square(x[:len(x) // n * n]).reshape(-1, n), 1) + 1e-12)


# ---- the checks: pure functions on a mono float array, (tag, detail) ------------------------------------------------
def hum(x, sr=SR):
    floor = float(np.percentile(levels(x, int(0.05 * sr)), 10))
    if floor < -100:                   # a tenth of it is digital silence: a bed under the rest doesn't reach the 10th
        return "FLAG", (f"steady floor {floor:.1f} dBFS: over a tenth of it is digital silence, so a bed under the "
                        f"rest would not show; listen to the pauses")
    return ("PASS" if floor <= HUM_MAX else "FAIL",
            f"steady floor {floor:.1f} dBFS (max {HUM_MAX:.0f}: a constant bed reads as a fan or hum)")


def clicks(x, sr=SR):
    n = int(0.0025 * sr)
    lv = levels(x, n)
    stops = np.where((lv[:-2] > CLICK_FROM) & (lv[:-2] - lv[2:] > CLICK_DROP))[0]
    at = sorted({round(k * n / sr, 2) for k in stops})
    return ("FAIL" if at else "PASS", "abrupt stops at: " + (", ".join(f"{t:.2f}s" for t in at) or "none"))


def voice_hf(x, sr=SR):
    n = int(0.05 * sr)
    fr = x[:len(x) // n * n].reshape(-1, n)
    lv = levels(x, n)
    loud = lv > lv.max() - 20
    if not len(fr) or lv.max() < -60:
        return "INFO", "no sound to judge"
    S = np.abs(np.fft.rfft(fr[loud] * np.hanning(n), axis=1)) ** 2
    hf = float(10 * np.log10(S[:, np.fft.rfftfreq(n, 1 / sr) > 5000].sum() / S.sum() + 1e-12))
    return ("PASS" if hf >= HF_MIN else "FAIL",
            f"speech energy above 5 kHz {hf:.1f} dB (min {HF_MIN:.0f}: a band-limited voice sounds like a cheap mic, "
            f"s turns sh)")


def pauses(x, words, sr=PAUSE_SR, end=None):
    speech = np.zeros(len(x), bool)
    for w in words:
        speech[int(w["start"] * sr):int(w["end"] * sr)] = True
    if not speech.any():
        return "FAIL", "no speech at the word times"
    sp, n = db(x[speech]), int(0.02 * sr)

    def trim(p, q):                    # past a word's own contiguous decay and the next word's onset
        while q - p > n and db(x[p:p + n]) > sp - PAUSE_UNDER:
            p += n
        while q - p > n and db(x[q - n:q]) > sp - PAUSE_UNDER:
            q -= n
        return p, q

    spans = [trim(int((a["end"] + 0.15) * sr), int((b["start"] - 0.15) * sr))
             for a, b in zip(words, words[1:]) if b["start"] - a["end"] > 0.4 and (end is None or a["end"] < end)]
    if not spans:
        return "PASS", f"speech {sp:.0f} dBFS; no pause over 0.4 s between words"
    level = db(np.concatenate([x[p:q] for p, q in spans]))
    loud = [p / sr + k * 0.02 for p, q in spans for k in range((q - p) // n)
            if db(x[p + k * n:p + (k + 1) * n]) > sp - BURST_UNDER]
    ok = level <= sp - PAUSE_UNDER and not loud
    return ("PASS" if ok else "FAIL",
            f"speech {sp:.0f} dBFS, pauses {level:.0f} dBFS (max {sp - PAUSE_UNDER:.0f}); bursts within "
            f"{BURST_UNDER:.0f} dB of speech: " + (", ".join(f"{t:.2f}s" for t in loud[:8]) or "none"))


def load_words(path):
    """Whisper JSON (segments[].words[]) or a flat list of {word, start, end}, in time order."""
    d = json.loads(Path(path).read_text())
    ws = d if isinstance(d, list) else [w for s in d.get("segments", []) for w in s.get("words") or []]
    return sorted((w for w in ws if w["end"] > w["start"]), key=lambda w: w["start"])


# ---- the file --------------------------------------------------------------------------------------------------------
def loudness(path, target):
    from master import measure         # ffmpeg's ebur128, as the master was measured
    i, tp = measure(path)
    return ("PASS" if abs(i - target) <= 1.0 and tp <= -1.0 else "FAIL",
            f"{i:.1f} LUFS (target {target:g}), true peak {tp:.1f} dBTP")


def main(argv):
    a = list(argv)
    def opt(k, d=None):
        if k in a:
            i = a.index(k)
            v = a[i + 1]
            del a[i:i + 2]
            return v
        return d
    words, target, end = opt("--words"), float(opt("--target", -14)), opt("--end")
    skip = set(filter(None, opt("--skip", "").split(",")))
    if len(a) != 1 or skip - set(CHECKS):
        sys.exit(__doc__)
    path, x = a[0], pcm(a[0])
    body = x[:int(float(end) * SR)] if end else x
    run = {"loudness": lambda: loudness(path, target), "hum": lambda: hum(body), "clicks": lambda: clicks(x),
           "voice_hf": lambda: voice_hf(body),
           "pauses": lambda: pauses(pcm(path, PAUSE_SR), load_words(words), PAUSE_SR, float(end) if end else None)
           if words else ("INFO", "skipped: no word times")}
    bad = 0
    for name in CHECKS:
        tag, detail = ("INFO", "skipped (--skip)") if name in skip else run[name]()
        bad += tag == "FAIL"
        print(f"{tag:4s}  {name:9s} {detail}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
