# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["numpy==2.5.3", "pillow==12.3.0", "opencv-python-headless==5.0.0.93", "mediapipe==1.1.0"]
# ///
"""Check a generated still (or a take) against the set: are the faces where this camera should see them?

Usage: frame_check.py <set.toml> <camera> <image|video> [--fps 4] [--speaker ID] [--min-face PX | --min-face-w FRAC]

From the set (scene.py) pure geometry gives what the camera must see: how many faces, who is on which side of the
frame, who is closer, whose head is higher, which way each person looks, which side the light comes from. On the
still, YuNet finds the faces and MediaPipe their eyes and mouths. One line per check:
  PASS  sides     everyone on their side of the frame
  FAIL  eyelines  ana should look screen-right, looks into the lens (+0.01)
  FLAG  light     too even to tell
A video is sampled at --fps and a check fails when it fails on more than a fifth of the samples. Exit 1 on a FAIL.

Written after stills prompted one by one turned the table, moved people across the room and flipped eyelines between
the wide and the close-ups. On real reels it caught a character looking the wrong way before anyone saw the still.
Known misses: a medium shot can pass as a close-up, and a hand over a face reads as no face.

Models (downloaded once to ~/.cache/ai-film-crew, or $AI_FILM_CREW_MODELS): YuNet face detector (OpenCV Zoo, MIT) and
the MediaPipe face landmarker (Apache 2.0).
"""
import hashlib, os, sys, urllib.request
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scene  # noqa: E402

CACHE = Path(os.environ.get("AI_FILM_CREW_MODELS", Path.home() / ".cache" / "ai-film-crew"))
MODELS = {
    "face_detection_yunet_2023mar.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/47534e27c9851bb1128ccc0102f1145e27f23f98/models/face_detection_yunet/"
        "face_detection_yunet_2023mar.onnx", "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"),
    "face_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
        "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"),
}
_det = _lm = None


def model(name):
    """The model file, downloaded once and checked against its sha256."""
    path = CACHE / name
    url, sha = MODELS[name]
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        CACHE.mkdir(parents=True, exist_ok=True)
        print(f"downloading {name}", file=sys.stderr)
        data = urllib.request.urlopen(url, timeout=120).read()
        if hashlib.sha256(data).hexdigest() != sha:
            sys.exit(f"sha256 mismatch for {url}")
        path.write_bytes(data)
    return str(path)


def det():
    global _det
    if _det is None:
        _det = cv2.FaceDetectorYN.create(model("face_detection_yunet_2023mar.onnx"), "", (320, 320), 0.8)
    return _det


def landmarker():
    global _lm
    if _lm is None:
        import mediapipe as mp
        _lm = mp.tasks.vision.FaceLandmarker.create_from_options(mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=model("face_landmarker.task"))))
    return _lm


def faces(img, min_px=40):
    """YuNet faces as dicts in frame fractions; face_px is the box height on a 1080-wide frame."""
    h0, w0 = img.shape[:2]
    k = min(1.0, 960 / max(h0, w0))                    # YuNet misses faces in 2K frames: detect small, scale back
    small = cv2.resize(img, None, fx=k, fy=k) if k < 1 else img
    d = det()
    d.setInputSize((small.shape[1], small.shape[0]))
    _, f = d.detect(small)
    out = []
    for r in ([] if f is None else f):
        x, y, w, h = r[:4] / k
        if h * 1080 / w0 < min_px:
            continue
        re_, le, nose = r[4:6] / k, r[6:8] / k, r[8:10] / k
        out.append({"u": (x + w / 2) / w0, "v": (y + h / 2) / h0, "face_px": h * 1080 / w0, "face_w": w / w0,
                    "yaw": (nose[0] - (re_[0] + le[0]) / 2) / w, "box": (x, y, w, h)})
    for fc in out:
        fc["iris"], fc["mouth"] = mesh(img, fc["box"])
        fc["lit"] = lit(img, fc["box"])
    return sorted(out, key=lambda fc: fc["u"])


def crop(img, box, scale=1.6, size=512):
    x, y, w, h = box
    cx, cy, s = x + w / 2, y + h / 2, max(w, h) * scale
    x0, y0 = int(max(cx - s / 2, 0)), int(max(cy - s / 2, 0))
    c = img[y0:int(cy + s / 2), x0:int(cx + s / 2)]
    return None if c.size == 0 else cv2.resize(c, (size, int(size * c.shape[0] / c.shape[1])))


def mesh(img, box):
    """(horizontal iris offset, + = screen-right; mouth opening / face height) from MediaPipe on an enlarged crop."""
    import mediapipe as mp
    c = crop(img, box)
    if c is None:
        return None, None
    r = landmarker().detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(c, cv2.COLOR_BGR2RGB)))
    if not r.face_landmarks:
        return None, None
    lm = r.face_landmarks[0]
    offs = []
    for iris, a, b in ((468, 33, 133), (473, 362, 263)):
        lo, hi = sorted((lm[a].x, lm[b].x))
        if hi - lo > 1e-3:
            offs.append((lm[iris].x - (lo + hi) / 2) / (hi - lo))
    mouth = abs(lm[14].y - lm[13].y) / max(abs(lm[152].y - lm[10].y), 1e-3)
    return (float(np.mean(offs)) if offs else None), mouth


def lit(img, box):
    """(right half - left half) / sum of the inner face's lightness: + = lit from screen-right."""
    x, y, w, h = box
    a = img[int(y + 0.25 * h):int(y + 0.85 * h), int(x + 0.15 * w):int(x + 0.85 * w)]
    if a.size == 0:
        return 0.0
    L = cv2.cvtColor(a, cv2.COLOR_BGR2LAB)[:, :, 0].astype(float)
    left, right = L[:, :L.shape[1] // 2].mean(), L[:, L.shape[1] // 2:].mean()
    return (right - left) / max(right + left, 1)


def gaze(fc):
    """Head yaw plus half the eye turn: + = looks screen-right. |g| < 0.04 reads as into the lens."""
    return fc["yaw"] + 0.5 * (fc["iris"] or 0.0)


def frames(path, fps):
    if Path(path).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        img = cv2.imread(str(path))
        if img is None:
            sys.exit(f"can't read {path}")
        yield 0.0, img
        return
    cap = cv2.VideoCapture(str(path))
    vf = cap.get(cv2.CAP_PROP_FPS) or 25
    step, i = max(1, round(vf / fps)), 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if i % step == 0:
            yield i / vf, f
        i += 1


def judge(exp, got, speaker=None, min_face=0.0, min_face_w=0.0):
    """One frame against the camera's expected view: {check: (ok, detail)}; ok None = can't judge (FLAG)."""
    r = {}
    # A face 70-165 degrees from the lens (profile to three-quarter back) may or may not be detected: it counts either
    # way. Generated frames turn heads more towards the lens than the geometry says.
    sure = sorted((e for e in exp if e["visible"] and e["face"] == "face"), key=lambda e: e["u"])
    maybe = sorted((e for e in exp if e["visible"] and e["face"] != "back"), key=lambda e: e["u"])
    want = maybe if len(got) == len(maybe) else sure
    out = [e["id"] for e in exp if not e["visible"]]
    r["faces"] = (len(got) == len(want), f"{len(sure)}-{len(maybe)} expected ({', '.join(e['id'] for e in maybe) or 'none'}),"
                                         f" {len(got)} found" + (f"; out of this camera's frame in the set: {', '.join(out)}"
                                                                 if len(got) > len(maybe) and out else ""))
    if len(got) != len(want):
        return r
    pairs = list(zip(want, got))
    side = [f"{e['id']} expected at {e['u']:.2f}, found at {g['u']:.2f}" for e, g in pairs
            if abs(e["u"] - 0.5) > 0.12 and (g["u"] - 0.5) * (e["u"] - 0.5) < 0 and abs(g["u"] - e["u"]) > 0.2]
    r["sides"] = (not side, "; ".join(side) or "everyone on their side of the frame")
    look = []
    for e, g in pairs:
        if e["looks"] == "into the lens" or e["yaw"] < 15:
            continue
        s = gaze(g)
        want_sign = 1 if e["looks"] == "screen-right" else -1
        if abs(s) < 0.04:
            look.append((None, f"{e['id']} should look {e['looks']}, looks into the lens ({s:+.2f})"))
        elif s * want_sign < 0:
            look.append((False, f"{e['id']} should look {e['looks']}, looks the other way ({s:+.2f})"))
    r["eyelines"] = (all(ok is not False for ok, _ in look) if look else True,
                     "; ".join(t for _, t in look) or "every face looks where the set says")
    if any(ok is None for ok, _ in look) and r["eyelines"][0]:
        r["eyelines"] = (None, r["eyelines"][1])
    if len(pairs) >= 2:
        (ea, ga), (eb, gb) = sorted(pairs, key=lambda p: -p[0]["face_px"])[:2]
        q_exp, q_got = ea["face_px"] / eb["face_px"], ga["face_px"] / gb["face_px"]
        ok = max(q_exp, q_got) / min(q_exp, q_got) < 1.6
        r["depth"] = (ok, f"{ea['id']}/{eb['id']} face size ratio {q_got:.2f}, the set gives {q_exp:.2f}"
                          + ("" if ok else ": someone moved closer or farther than the room allows"))
        (e1, g1), (e2, g2) = pairs[0], pairs[1]
        dv_e, dv_g = e1["v"] - e2["v"], g1["v"] - g2["v"]
        if abs(dv_e) > 0.06:
            ok = dv_g * dv_e > 0 and abs(dv_g) > abs(dv_e) / 3
            r["heights"] = (ok, f"{e1['id']} head {'above' if dv_e < 0 else 'below'} {e2['id']}'s by {abs(dv_e):.2f} "
                                f"of the frame in the set, {dv_g:+.2f} found" + ("" if ok else ": who sits, who stands?"))
    light = []
    for e, g in pairs:
        if e["lit"] == "even" or abs(g["lit"]) < 0.08:
            continue
        if (g["lit"] > 0) != (e["lit"] == "screen-right"):
            light.append((abs(g["lit"]) < 0.15, f"{e['id']} should be lit from {e['lit']}, lit from the other side "
                                                f"({g['lit']:+.2f})"))
    r["light"] = (None if light and all(soft for soft, _ in light) else not light,
                  "; ".join(t for _, t in light) or "light side as the set gives (or too even to tell)")
    size = [f"{e['id']} face {g['face_px']:.0f} px, the set gives {e['face_px']:.0f}" for e, g in pairs
            if g["face_px"] / e["face_px"] > 1.8 or g["face_px"] / e["face_px"] < 0.55]
    r["framing"] = (None if size else True, "; ".join(size) + (": change the lens or distance in the set if this "
                                                               "framing is wanted" if size else "") or "as the set's lens")
    if speaker:
        g = next((g for e, g in pairs if e["id"] == speaker), None)
        if g is None:
            r["speaker"] = (False, f"{speaker} speaks in this shot but is not in frame")
        else:
            ok = g["face_px"] >= min_face and g["face_w"] >= min_face_w
            floor = ", ".join(x for x in (f"{min_face:.0f} px tall" if min_face else "",
                                          f"{min_face_w:.0%} of the width" if min_face_w else "") if x)
            r["speaker"] = (ok, f"{speaker} face {g['face_px']:.0f} px tall, {g['face_w']:.0%} of the frame width"
                                + (f" (min {floor})" if floor else ""))
    return r


def check(set_path, cid, media, fps=4, speaker=None, min_face=0.0, min_face_w=0.0):
    """Print one verdict line per check; return the number of FAILs."""
    s = scene.load(set_path)
    exp = scene.view(s, scene.Cam(s, scene.find(s, cid)))
    per = [(t, judge(exp, faces(img), speaker, min_face, min_face_w)) for t, img in frames(media, float(fps))]
    names = list(dict.fromkeys(k for _, r in per for k in r))
    bad = 0
    for k in names:
        rows = [(t, r[k]) for t, r in per if k in r]
        fails = [t for t, (ok, _) in rows if ok is False]
        flags = [t for t, (ok, _) in rows if ok is None]
        if len(per) == 1:
            ok, detail = rows[0][1]
            tag = "PASS" if ok else ("FLAG" if ok is None else "FAIL")
        else:
            worst = next((d for _, (ok, d) in rows if ok is False), None) or next((d for _, (ok, d) in rows if ok is None),
                                                                                 rows[0][1][1])
            tag = "FAIL" if len(fails) > len(per) / 5 else ("FLAG" if fails or flags else "PASS")
            detail = (f"{len(fails)}/{len(per)} samples fail"
                      + (f" at {', '.join(f'{t:.2f}' for t in fails[:8])} s" if fails else "")
                      + (f", {len(flags)} to look at" if flags else "") + f"; e.g. {worst}")
        bad += tag == "FAIL"
        print(f"{tag}  {k:9s} {detail}")
    print(f"set {Path(set_path).name}, camera {cid}: " + scene.card(s, cid).splitlines()[0])
    return bad


def main(argv):
    args = list(argv)
    def opt(name, default=None):
        if name in args:
            i = args.index(name)
            value = args[i + 1]
            del args[i:i + 2]
            return value
        return default
    fps, speaker = float(opt("--fps", 4)), opt("--speaker")
    min_face, min_face_w = float(opt("--min-face", 0)), float(opt("--min-face-w", 0))
    if len(args) != 3:
        sys.exit(__doc__)
    return 1 if check(args[0], args[1], args[2], fps, speaker, min_face, min_face_w) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
