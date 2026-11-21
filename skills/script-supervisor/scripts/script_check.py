# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["numpy==2.5.3"]
# ///
"""The words and the timing of a take or a cut against its script: what was said, what was said after the last line,
dead air, and the pace of the cuts.

Usage:
  uv run script_check.py <video|audio> <script.txt> --words words.json[,primed.json] [--end <s>] [--cuts <t,t,...>]
        [--max-gap 1.0] [--quiet <a-b,a-b>] [--max-asl 3.0] [--max-len 25] [--skip <check>[,<check>]]
  uv run script_check.py pace <reel> [<reel> ...]
        The cuts, average shot length and length of reference reels: set --max-asl and --max-len from them.
  uv run script_check.py edges <take audio> <in s> <out s>
        Is a take's sound cut while someone speaks? Run it on the take's own dialogue, with the in and out points
        the cut uses.

script.txt holds every spoken word in order (an empty file: a wordless video, any word heard fails).
--words takes Whisper JSON with word times (`segments[].words[]`, as openai-whisper and mlx-whisper write it with
word timestamps on) or a flat list of such words. Give two files, one transcribed plain and one with the brand and
character names as Whisper's prompt: a prompt fixes names Whisper doesn't know and can mislead it elsewhere, so both
are printed and the one nearer the script counts. --end is where the words end, before a wordless end card:
Whisper writes words over a card's silence ("Good luck." after one reel's last line). A card with a voice-over is
part of the script: leave --end out.
--quiet names stretches the script leaves without a voice. Needs ffmpeg on PATH.

One line per check, exit 1 on a FAIL:
  FAIL  script    WER 7.1%, last word heard 'go' vs script 'line'
  FAIL  tail      sound from 7.42 s, after the last heard word (-27 dBFS, speech peaks -19): Whisper drops ...
  FAIL  dead_air  no voice for over 1.0 s at: 4.2-5.9
  PASS  pacing    9 shots, ASL 2.4 s (max 3.0), 21.6 s long (max 25)

The checks, and what their thresholds were calibrated on:
  script    word error rate <= 5 % and the last heard word is the script's last word, so a cut-off line fails even
            when the rest is clean. Numbers count as words ("11th" = "eleventh").
  tail      sound after the last heard word, from 0.3 s past it: above -40 dBFS and within 15 dB of the speech's
            loudest 50 ms. Whisper drops a short tail on a whole take: a generated take ad-libbed three words 8 dB
            under its speech after the last line and the transcript read clean. A last word's own decay and a -33 dB
            room tone stay under it. An effect or an end-card voice past the last word fails it too: pass --end.
  dead_air  no gap over --max-gap (1.0 s) between two words inside the body. A voice-over that sits on its shots
            pauses longer on purpose (an approved one: up to 2.5 s between lines): raise --max-gap or name the
            stretch in --quiet.
  pacing    average shot length <= --max-asl and the whole file <= --max-len. The defaults (3.0 s, 25 s) are one
            brand's 9:16 comedy reels (its published ones: 2.3-2.4 s). Yours are whatever `pace` prints for the
            reels you want to sound like. Cuts are found in the picture (a hard cut changes a small grey frame by
            more than 28 levels on average; captions and zooms stay under it) or given in --cuts.
  edges     the take is quiet (< -35 dBFS) in the 80 ms after the in point and before the out point, and stays quiet
            for 0.2 s past the out point: an out point can sit in the silence inside a word ("six" cut in the
            closure of its k was heard as "si-k"). A take whose speech starts on its first frame fails: the
            generator clipped the first word.
Code reads the words and the clock. Whether a line is delivered right is the ear's call.
"""
import json, re, subprocess, sys
from pathlib import Path

import numpy as np

SR = 16000
CHECKS = ("script", "tail", "dead_air", "pacing")
WER_MAX = 0.05
QUIET = -35.0                  # dBFS: a cut point is in silence under this
CUT_THR = 28.0                 # mean absolute change of a 108x192 grey frame at a hard cut


def pcm(path, sr=SR):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True)
    if r.returncode or not r.stdout:
        sys.exit(f"can't decode the sound of {path}: {r.stderr.decode().strip() or 'no audio stream'}")
    return np.frombuffer(r.stdout, np.float32)


def db(x):
    return float(20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-9)) if len(x) else -120.0


def top(x, n=800):
    """The loudest 50 ms window, dBFS."""
    w = x[:len(x) // n * n].reshape(-1, n)
    return float(20 * np.log10(np.sqrt((w ** 2).mean(1)).max() + 1e-9)) if len(w) else -120.0


def load_words(path):
    """Whisper JSON (segments[].words[]) or a flat list of {word, start, end}, in time order."""
    d = json.loads(Path(path).read_text())
    ws = d if isinstance(d, list) else [w for s in d.get("segments", []) for w in s.get("words") or []]
    return sorted((w for w in ws if w["end"] > w["start"]), key=lambda w: w["start"])


# ---- words -----------------------------------------------------------------------------------------------------------
ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
        "seventeen eighteen nineteen").split()
TENS = "- - twenty thirty forty fifty sixty seventy eighty ninety".split()
ORDINAL = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth",
           "twelve": "twelfth"}


def spell(m):
    """0-99 and their ordinals as words: Whisper writes "11th" for "eleventh"."""
    n = int(m.group(1))
    if n > 99:
        return m.group(0)
    w = (ONES[n] if n < 20 else TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])).split()
    if m.group(2):
        w[-1] = ORDINAL.get(w[-1], w[-1][:-1] + "ieth" if w[-1].endswith("y") else w[-1] + "th")
    return " ".join(w)


def norm(s):
    # Whisper splits "o'clock" into "o 'clock": a token starting with an apostrophe belongs to the previous word.
    s = re.sub(r"\b(\d+)(st|nd|rd|th)?\b", spell, s.lower().replace("’", "'"))
    return re.sub(r"\s+'", "'", re.sub(r"[^a-z' ]", " ", s)).split()


def wer(hyp, ref):
    d = np.arange(len(hyp) + 1)
    for i, r in enumerate(ref, 1):
        prev, d[0] = d.copy(), i
        for j, h in enumerate(hyp, 1):
            d[j] = min(prev[j] + 1, d[j - 1] + 1, prev[j - 1] + (r != h))
    return float(d[-1] / max(len(ref), 1))


# ---- the checks: pure functions, (tag, detail) -----------------------------------------------------------------------
def script(words, ref):
    hyp = norm(" ".join(w["word"] for w in words))
    if not ref:
        return ("FAIL" if hyp else "PASS"), "a wordless video: " + (f"heard '{' '.join(hyp)}'" if hyp else "no words heard")
    e = wer(hyp, ref)
    return ("PASS" if e <= WER_MAX and hyp[-1:] == ref[-1:] else "FAIL",
            f"WER {e:.1%}, last word heard '{hyp[-1] if hyp else ''}' vs script '{ref[-1]}'")


def tail(x, words, end=None, sr=SR):
    if not words:
        return "INFO", "no words heard"
    last = max(w["end"] for w in words if end is None or w["start"] < end)
    t0 = last + 0.3
    after, speech = top(x[int(t0 * sr):int(end * sr) if end else None]), top(x[:int(last * sr)])
    loud = after > max(-40.0, speech - 15)
    return ("FAIL" if loud else "PASS",
            (f"sound from {t0:.2f} s, after the last heard word ({after:.0f} dBFS, speech peaks {speech:.0f}): Whisper "
             f"drops a short tail, so transcribe from there before trusting the script check") if loud else
            f"nothing after the last heard word at {last:.2f} s ({after:.0f} dBFS, speech peaks {speech:.0f})")


def dead_air(words, end=None, max_gap=1.0, quiet=()):
    gaps = [(a["end"], b["start"]) for a, b in zip(words, words[1:])
            if b["start"] - a["end"] > max_gap and (end is None or b["start"] < end)
            and not any(q0 <= a["end"] + 0.3 and b["start"] - 0.3 <= q1 for q0, q1 in quiet)]
    return ("FAIL" if gaps else "PASS",
            f"no voice for over {max_gap:g} s at: " + (", ".join(f"{a:.1f}-{b:.1f}" for a, b in gaps) or "nowhere"))


def pacing(cuts, length, max_asl=3.0, max_len=25.0):
    shots = len(cuts) + 1
    asl = length / shots
    return ("PASS" if asl <= max_asl and length <= max_len else "FAIL",
            f"{shots} shots, ASL {asl:.1f} s (max {max_asl:g}), {length:.1f} s long (max {max_len:g})")


def edges(x, t_in, t_out, sr=SR):
    bad, n = [], int(0.02 * sr)
    head, end = x[int(t_in * sr):int((t_in + 0.08) * sr)], x[int((t_out - 0.08) * sr):int(t_out * sr)]
    if db(head) > QUIET:
        bad.append(f"in at {t_in:.2f} s ({db(head):.0f} dBFS)")
    if db(end) > QUIET:
        bad.append(f"out at {t_out:.2f} s ({db(end):.0f} dBFS)")
    after = x[int(t_out * sr):int((t_out + 0.2) * sr)]
    if len(after) > n and max(db(after[i:i + n]) for i in range(0, len(after) - n, n // 2)) > QUIET:
        bad.append(f"out at {t_out:.2f} s: the take sounds again within 0.2 s (a word cut in its closure?)")
    return ("FAIL" if bad else "PASS", "sound cut while someone speaks: " + (", ".join(bad) or "none"))


# ---- the file --------------------------------------------------------------------------------------------------------
def probe(path, entry, stream=None):
    r = subprocess.run(["ffprobe", "-v", "error", *(["-select_streams", stream] if stream else []), "-show_entries",
                        entry, "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return r.stdout.strip().split("\n")[0].strip(",")


def hard_cuts(path):
    """Times of the hard cuts, or None for a file with no picture."""
    rate = probe(path, "stream=r_frame_rate", "v:0")
    if not rate or "/" not in rate:
        return None
    a, b = map(float, rate.split("/"))
    fps, w, h = a / (b or 1), 108, 192
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-an", "-vf", f"scale={w}:{h}:flags=bilinear,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    f = np.frombuffer(raw[:len(raw) // (w * h) * w * h], np.uint8).reshape(-1, w * h).astype(np.int16)
    return [float((i + 1) / fps) for i in np.where(np.abs(np.diff(f, axis=0)).mean(1) > CUT_THR)[0]]


def main(argv):
    a = list(argv)
    def opt(k, d=None):
        if k in a:
            i = a.index(k)
            v = a[i + 1]
            del a[i:i + 2]
            return v
        return d
    if a[:1] == ["pace"] and len(a) > 1:
        for p in a[1:]:
            cuts, length = hard_cuts(p) or [], float(probe(p, "format=duration"))
            print(f"INFO  pace      {Path(p).name}: {len(cuts) + 1} shots, ASL {length / (len(cuts) + 1):.1f} s, {length:.1f} s long")
        return 0
    if a[:1] == ["edges"] and len(a) == 4:
        tag, detail = edges(pcm(a[1]), float(a[2]), float(a[3]))
        print(f"{tag:4s}  edges     {detail}")
        return int(tag == "FAIL")
    wfiles, end, cuts = opt("--words"), opt("--end"), opt("--cuts")
    max_gap, max_asl, max_len = float(opt("--max-gap", 1.0)), float(opt("--max-asl", 3.0)), float(opt("--max-len", 25))
    quiet = [tuple(map(float, q.split("-"))) for q in filter(None, opt("--quiet", "").split(","))]
    skip = set(filter(None, opt("--skip", "").split(",")))
    if len(a) != 2 or not wfiles or skip - set(CHECKS):
        sys.exit(__doc__)
    path, ref, end = a[0], norm(Path(a[1]).read_text()), float(end) if end else None
    cands = [[w for w in load_words(f) if end is None or w["start"] < end + 0.3] for f in wfiles.split(",")]
    if len(cands) > 1:
        for f, ws in zip(wfiles.split(","), cands):
            print(f"      {Path(f).name}: " + " ".join(w["word"].strip() for w in ws))
    words = min(cands, key=lambda ws: wer(norm(" ".join(w["word"] for w in ws)), ref))

    def pace():
        found = [float(t) for t in cuts.split(",")] if cuts else hard_cuts(path)
        if found is None:
            return "INFO", "skipped: no picture"
        return pacing(found, float(probe(path, "format=duration")), max_asl, max_len)
    run = {"script": lambda: script(words, ref), "tail": lambda: tail(pcm(path), words, end),
           "dead_air": lambda: dead_air(words, end, max_gap, quiet), "pacing": pace}
    bad = 0
    for name in CHECKS:
        tag, detail = ("INFO", "skipped (--skip)") if name in skip else run[name]()
        bad += tag == "FAIL"
        print(f"{tag:4s}  {name:9s} {detail}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
