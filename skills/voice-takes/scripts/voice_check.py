# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["numpy==2.5.3"]
# ///
"""Voice takes in numbers: is this line in the pitch of the take the owner picked, is the read rushed, does a word
start twice.

Usage:
  uv run voice_check.py pitch <picked take> <take>[@<from>-<to>] [...] [--max-st 3]
        The median pitch of each take's speech against the picked take's. `@1.2-3.4` limits a take to those seconds:
        give the words' own window (from Whisper's word times) when the take holds other sound.
  uv run voice_check.py pace <take> [<words.json>] [...]
        Pauses in a read. A words file after a take (Whisper JSON with word times, or a flat list) adds the run-on check.
  uv run voice_check.py stutter <stem> [...]
        Two attacks for one word start. Run it on dialogue stems, before mastering.
Takes are audio or video files. Needs ffmpeg on PATH.

One line per take, exit 1 on a FAIL:
  PASS  pitch     line2.mp4: 222 Hz against 224 Hz in picked.mp4 (-0.2 st, max 3)
  FAIL  pitch     line1.mp4: 161 Hz against 224 Hz in picked.mp4 (-5.7 st, max 3)
  FAIL  pace      take1.wav: 21.4 s, 2 pauses >= 0.3 s (4% of the take): rushed: pauses are 4% of the take (min 12%)
  FAIL  stutter   wait.wav: two attacks for one word start at: 0.01 s

The checks, and what their thresholds were calibrated on:
  pitch     the median pitch of the voiced 40 ms frames (autocorrelation, 70-400 Hz) within --max-st semitones of
            the picked take's. A video model given the picked voice's description word for word spoke the next line
            at 161 Hz against the pick's 224: 5.7 semitones down, a timbre the owner had already turned down. Re-takes
            with the pitch named in the prompt came back at 205 and 222 Hz. One reel, two voices: 3 semitones sits
            between what he heard as the same voice and what he heard as another. Set yours from takes you judged.
  pace      inner pauses of 0.3 s or more make up at least 12 % of the take, there is at least one per 12 words, and
            the pitch moves over at least 3 semitones. Picked TTS takes: pauses 14-19 % of the take, one per 10-11
            words; the takes heard as "rushed, one tone, impossible to listen to": 0-8 %, one per 21-135 words. Words
            per second and pitch range did not separate those two groups: the missing pauses did.
  stutter   a word start whose 10 ms envelope peaks, dips 8 dB or more within 30 ms and comes back higher within
            40 ms. A voice changer fed a take that spoke from its first frame gave "Wait" a burst 20 ms before the
            word ("W-wait"): -24 dB, -34 dB, then the word at -15. The take it was made from rose smoothly.
None of this says a voice sounds like the person or suits the face. The ear decides that, on the moving face.
"""
import json, math, subprocess, sys
from pathlib import Path

import numpy as np

SR = 16000
MAX_ST = 3.0
MIN_PAUSE_SHARE, MAX_WORDS_PER_PAUSE, MIN_RANGE = 0.12, 12, 3.0


def pcm(path, sr=SR):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True)
    if r.returncode or not r.stdout:
        sys.exit(f"can't decode the sound of {path}: {r.stderr.decode().strip() or 'no audio stream'}")
    return np.frombuffer(r.stdout, np.float32)


def db(x):
    return float(20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-9)) if len(x) else -120.0


def runs(mask, min_len):
    """(start, end) index pairs of True runs at least min_len long."""
    edges = np.flatnonzero(np.diff(np.concatenate([[0], np.asarray(mask, np.int8), [0]])))
    return [(int(a), int(b)) for a, b in zip(edges[::2], edges[1::2]) if b - a >= min_len]


def semitones(x, hop=640, win=1024, sr=SR):
    """Pitch of the voiced 40 ms frames by autocorrelation, in semitones above 100 Hz."""
    out, lo, hi = [], sr // 400, sr // 70
    for i in range(0, len(x) - win, hop):
        f = x[i:i + win] * np.hanning(win)
        if db(f) < -35:
            continue
        ac = np.correlate(f, f, "full")[win - 1:]
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.4 * ac[0]:
            out.append(12 * math.log2(sr / k / 100))
    return np.array(out)


def hz(x):
    """Median pitch in Hz, or None when under 10 frames are voiced."""
    st = semitones(x)
    return float(100 * 2 ** (np.median(st) / 12)) if len(st) >= 10 else None


def voiced(x, hop):
    """Per-hop speech mask: within 22 dB of the loud speech, gaps under 0.15 s closed, blips under 0.12 s dropped."""
    n = len(x) // hop
    lv = np.array([db(x[i * hop:(i + 1) * hop]) for i in range(n)])
    m = lv > (max(np.percentile(lv, 95) - 22, -42) if n else -42)
    per_s = SR / hop
    for a, b in runs(~m, 1):
        if 0 < a and b < len(m) and (b - a) < 0.15 * per_s:
            m[a:b] = True
    keep = np.zeros_like(m)
    for a, b in runs(m, max(1, int(0.12 * per_s))):
        keep[a:b] = True
    return keep


# ---- the checks: pure functions on mono 16 kHz float arrays ----------------------------------------------------------
def pitch(ref, x, max_st=MAX_ST):
    """(tag, semitones from the picked take, Hz, the pick's Hz)."""
    f0, f = hz(ref), hz(x)
    if f0 is None or f is None:
        return "FAIL", None, f, f0
    st = 12 * math.log2(f / f0)
    return ("PASS" if abs(st) <= max_st else "FAIL"), st, f, f0


def pace(x, n_words=None):
    """(tag, detail) for one read."""
    dur, sp = len(x) / SR, voiced(x, SR // 100)
    pauses = [(b - a) / 100 for a, b in runs(~sp, 30) if a > 0 and b < len(sp)]       # inner pauses >= 0.3 s
    st = semitones(x)
    rng = float(np.percentile(st, 90) - np.percentile(st, 10)) if len(st) > 20 else 0.0
    fails = []
    if sum(pauses) < MIN_PAUSE_SHARE * dur:
        fails.append(f"rushed: pauses are {sum(pauses) / dur:.0%} of the take (min {MIN_PAUSE_SHARE:.0%})")
    if n_words and len(pauses) < n_words / MAX_WORDS_PER_PAUSE:
        fails.append(f"run-on: {len(pauses)} pauses for {n_words} words (one per {MAX_WORDS_PER_PAUSE} at least)")
    if rng < MIN_RANGE:
        fails.append(f"flat: the pitch moves over {rng:.1f} semitones (min {MIN_RANGE:g})")
    return ("FAIL" if fails else "PASS",
            f"{dur:.1f} s, {len(pauses)} pauses >= 0.3 s ({sum(pauses) / dur:.0%} of the take), pitch range {rng:.1f} st"
            + (f": {'; '.join(fails)}" if fails else ""))


def stutter(x):
    """Times of word starts with two attacks."""
    x = np.concatenate([np.zeros(int(0.2 * SR), np.float32), x])        # a word on the first sample is a start too
    hop, win, out = SR // 500, SR // 100, []
    e = np.array([db(x[i:i + win]) for i in range(0, len(x) - win, hop)])
    for i in range(40, len(e) - 40):
        if e[i] > -35 and e[i - 40:i - 1].max() < -45:
            seg = e[i:i + 40]
            p1i = int(np.argmax(seg[:10]))
            m = p1i + 1 + int(np.argmin(seg[p1i + 1:p1i + 16]))
            if seg[p1i] - seg[m] >= 8 and seg[m + 1:m + 21].max() > seg[p1i] and (not out or i * hop / SR - out[-1] > 0.05):
                out.append(i * hop / SR)
    return [t - 0.2 for t in out]


# ---- the files -------------------------------------------------------------------------------------------------------
def span(arg):
    """'take.mp4@1.2-3.4' -> (name, samples of that window); without '@', the whole take."""
    path, _, w = arg.partition("@")
    x = pcm(path)
    if w:
        a, b = map(float, w.split("-"))
        x = x[int(a * SR):int(b * SR)]
    return "/".join(Path(path).parts[-2:]), x


def main(argv):
    a = list(argv)
    max_st = MAX_ST
    if "--max-st" in a:
        i = a.index("--max-st")
        max_st = float(a[i + 1])
        del a[i:i + 2]
    cmd, rest, bad = (a[0] if a else ""), a[1:], 0
    if cmd == "pitch" and len(rest) >= 2:
        ref_name, ref = span(rest[0])
        for arg in rest[1:]:
            name, x = span(arg)
            tag, st, f, f0 = pitch(ref, x, max_st)
            bad += tag == "FAIL"
            print(f"{tag}  pitch     {name}: " + ("too little voiced sound to read a pitch" if st is None else
                  f"{f:.0f} Hz against {f0:.0f} Hz in {ref_name} ({st:+.1f} st, max {max_st:g})"))
    elif cmd == "pace" and rest:
        takes = [(t, rest[i + 1] if i + 1 < len(rest) and rest[i + 1].endswith(".json") else None)
                 for i, t in enumerate(rest) if not t.endswith(".json")]
        for take, wfile in takes:
            n = None
            if wfile:
                d = json.loads(Path(wfile).read_text())
                n = len(d if isinstance(d, list) else [w for s in d.get("segments", []) for w in s.get("words") or []])
            tag, detail = pace(pcm(take), n)
            bad += tag == "FAIL"
            print(f"{tag}  pace      {'/'.join(Path(take).parts[-2:])}: {detail}")
    elif cmd == "stutter" and rest:
        for p in rest:
            at = stutter(pcm(p))
            bad += bool(at)
            print(f"{'FAIL' if at else 'PASS'}  stutter   {'/'.join(Path(p).parts[-2:])}: two attacks for one word start at: "
                  + (", ".join(f"{t:.2f} s" for t in at) or "none"))
    else:
        sys.exit(__doc__)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
