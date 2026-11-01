# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = []
# ///
"""Master a mix to a loudness target with a linear gain and a true-peak limiter, then measure it.

Usage: master.py <mix.wav|video> <out.wav> [target_lufs=-14]

Why not ffmpeg `loudnorm`: it silently switches to dynamic mode when a linear gain would break its peak target, and
pumps. Here the gain is linear; a limiter at 4x oversampling catches inter-sample peaks; the gain is corrected until
the limited result lands on target (the limiter lowers loudness, more the harder it works). Exits 1 if the result
misses the target by more than 0.7 LU or the true peak is above -1 dBTP. Needs ffmpeg on PATH.
"""
import re, subprocess, sys, tempfile
from pathlib import Path

SR = 48000


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


def measure(path):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]), float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])


def master(mix, out, target=-14.0):
    with tempfile.TemporaryDirectory() as d:
        g, tmp = target - measure(mix)[0], Path(d) / "m.wav"
        for _ in range(12):
            ff("-i", mix, "-vn", "-af", f"aresample={4 * SR},volume={g:.2f}dB,"
               f"alimiter=limit=0.75:attack=2:release=60:level=false,aresample={SR}", "-ar", SR, tmp)
            miss = target - measure(tmp)[0]
            if abs(miss) < 0.3:
                break
            g += miss
        tmp.replace(out)
    i, tp = measure(out)
    print(f"{out}: {i:.1f} LUFS (target {target}), true peak {tp:.1f} dBTP")
    if abs(i - target) > 0.7 or tp > -1.0:
        sys.exit("MASTER FAILED")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    master(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else -14.0)
