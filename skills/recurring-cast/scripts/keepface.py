# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["numpy==2.5.3", "opencv-python-headless==5.0.0.93", "mediapipe==1.1.0"]
# ///
"""Keep a person's face after an image edit: the edit model may add glasses or new hands, never new eyes.

Usage:
  keepface.py glasses <base> <edit> <out>   the base's face with only the edit's new glasses frame on it
  keepface.py face <base> <edit> <out>      the edit everywhere (new pose, hands, props) except the base's face oval
  keepface.py check <base> <out>            do the eyes, nose and mouth still line up with the base?

Image edit models redraw what they were not asked to: an edit that adds glasses narrows the eyes and puffs the lids,
and the person reads as someone else. Both commands register the edit onto the base by the face (MediaPipe landmarks,
then ECC), take the face back from the base pixel for pixel, and print their checks:
  PASS  glasses  2.1% of the new frame lost (max 3%)
  PASS  join     0.4% doubled at the seam (max 1.5%)
  PASS  shape    0.012 eye widths from the base (max 0.025)
Exit 1 on a FAIL. The thresholds were measured on one person's edits (black frames, light skin): re-check them on
yours. The glasses mask looks for a dark frame on lighter skin; light or rimless frames over a dark background are
left out, so check those at full size.

Models (local, downloaded once to ~/.cache/ai-film-crew or $AI_FILM_CREW_MODELS): YuNet (OpenCV Zoo, MIT) and the
MediaPipe face landmarker (Apache 2.0).
"""
import hashlib, os, sys, urllib.request
from pathlib import Path

os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
import cv2
import numpy as np

CACHE = Path(os.environ.get("AI_FILM_CREW_MODELS", Path.home() / ".cache" / "ai-film-crew"))
MODELS = {
    "face_detection_yunet_2023mar.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/47534e27c9851bb1128ccc0102f1145e27f23f98/models/face_detection_yunet/"
        "face_detection_yunet_2023mar.onnx", "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"),
    "face_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
        "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"),
}
OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149,
        150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
EYES = ([33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246],
        [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398])
BROWS = ([70, 63, 105, 66, 107], [336, 296, 334, 293, 300])
IRIS = ((468, range(469, 473)), (473, range(474, 478)))
SHAPE = [33, 133, 362, 263, 1, 4, 6, 168, 98, 327, 61, 291]    # eye corners, nose, mouth corners
LOSS_MAX, JOIN_MAX, SHAPE_MAX = 0.03, 0.015, 0.025
_m = {}


def model(name):
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


def mesh(img):
    """478 face landmarks in image px (MediaPipe on an enlarged crop around the biggest YuNet face)."""
    import mediapipe as mp
    if "lm" not in _m:
        _m["lm"] = mp.tasks.vision.FaceLandmarker.create_from_options(mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=model("face_landmarker.task"))))
        _m["det"] = cv2.FaceDetectorYN.create(model("face_detection_yunet_2023mar.onnx"), "", (320, 320), 0.6)
    k = 960 / max(img.shape[:2])
    small = cv2.resize(img, None, fx=k, fy=k)
    _m["det"].setInputSize(small.shape[1::-1])
    r = _m["det"].detect(small)[1]
    if r is None:
        raise ValueError("no face found")
    x, y, w, h = max(r, key=lambda f: f[2] * f[3])[:4] / k
    cx, cy, s = x + w / 2, y + h / 2, max(w, h) * 1.8
    x0, y0 = int(max(cx - s / 2, 0)), int(max(cy - s / 2, 0))
    crop = img[y0:int(cy + s / 2), x0:int(cx + s / 2)]
    z = 768 / crop.shape[1]
    res = _m["lm"].detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                                   data=cv2.cvtColor(cv2.resize(crop, None, fx=z, fy=z), cv2.COLOR_BGR2RGB)))
    if not res.face_landmarks:
        raise ValueError("no face landmarks")
    return np.array([(q.x * crop.shape[1] + x0, q.y * crop.shape[0] + y0) for q in res.face_landmarks[0]], np.float32)


def poly(shape, pts):
    m = np.zeros(shape, np.uint8)
    cv2.fillPoly(m, [np.round(pts).astype(np.int32)], 255)
    return m


def irises(shape, p, grow=1.0):
    """Both iris discs: a glasses rim never crosses an iris, so nothing there may come from the edit."""
    m = np.zeros(shape, np.uint8)
    for c, ring in IRIS:
        r = np.mean([np.linalg.norm(p[i] - p[c]) for i in ring]) * grow
        cv2.circle(m, tuple(np.round(p[c]).astype(int)), int(np.ceil(r)), 255, -1)
    return m


def register(base, edit, p, hide=None, oval_only=False):
    """The edit warped onto the base: a landmark fit, then ECC on the face box (the `hide` rows ignored). An edit
    that changes the room registers on the face oval only, or the new background pulls it off the face."""
    x0, y0 = (p.min(0) - (p.max(0) - p.min(0)) * 0.3).astype(int).clip(0)
    x1, y1 = (p.max(0) + (p.max(0) - p.min(0)) * 0.3).astype(int)
    x1, y1 = min(x1, base.shape[1]), min(y1, base.shape[0])
    def gray(im):
        return cv2.GaussianBlur(cv2.cvtColor(im[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY), (5, 5), 0).astype(np.float32)
    fm = poly(base.shape[:2], p[OVAL])[y0:y1, x0:x1] if oval_only else np.full((y1 - y0, x1 - x0), 255, np.uint8)
    if hide:
        fm[max(hide[0] - y0, 0):max(hide[1] - y0, 0)] = 0
    A = cv2.estimateAffinePartial2D(p, mesh(edit))[0]                    # base px -> edit px
    o = np.array([x0, y0], np.float32)
    W = np.hstack([A[:, :2], (A[:, :2] @ o + A[:, 2] - o)[:, None]]).astype(np.float32)
    _, W = cv2.findTransformECC(gray(base), gray(edit), W, cv2.MOTION_AFFINE,
                                (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), fm, 5)
    W[:, 2] += np.array([x0, y0], np.float32) - W[:, :2] @ np.array([x0, y0], np.float32)
    return cv2.warpAffine(edit, W, base.shape[1::-1], flags=cv2.INTER_LANCZOS4 + cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_REPLICATE)


def band(p):
    """The rows a glasses frame can occupy: from just above the brows to below the eyes."""
    fw = np.ptp(p[:, 0])
    eye_y, brow_y = p[[*EYES[0], *EYES[1]], 1], p[[*BROWS[0], *BROWS[1]], 1]
    return int(brow_y.min() - 0.08 * fw), int(eye_y.max() + 0.30 * fw)


def glasses_mask(src, base, p):
    """Where `src` (aligned to `base`) has a dark glasses frame that `base` lacks, out to the ears, never the eyes."""
    fw = np.ptp(p[:, 0])
    top, bot = band(p)
    ls, lb = (cv2.cvtColor(i, cv2.COLOR_BGR2LAB)[..., 0].astype(np.int16) for i in (src, base))
    near = np.zeros(base.shape[:2], np.uint8)
    near[max(top, 0):bot] = 255
    near &= cv2.dilate(poly(base.shape[:2], p[OVAL]), np.ones((3, int(fw * 1.2) | 1), np.uint8))
    eyes = np.zeros(base.shape[:2], np.uint8)
    for e in EYES:
        eyes |= poly(base.shape[:2], p[e])
    near[cv2.dilate(eyes, np.ones((int(fw * 0.04) | 1,) * 2, np.uint8)) > 0] = 0
    return (((lb - ls) > 35) & (ls < 60)).astype(np.uint8) * 255 & near


def glasses_loss(src, out, base, p):
    """Share of the new frame's pixels that `out` no longer shows (0 = every rim and temple kept)."""
    g = cv2.erode(glasses_mask(src, base, p), np.ones((5, 5), np.uint8)) > 0
    if g.sum() < 50:
        return 1.0
    d = np.abs(out.astype(np.int16) - src.astype(np.int16)).max(2)
    return float((d[g] > 30).mean())


def keep_glasses(base, edit):
    """(out, registered edit, landmarks): the base everywhere except the edit's dark glasses frame."""
    edit = cv2.resize(edit, base.shape[1::-1], interpolation=cv2.INTER_LANCZOS4)
    p = mesh(base)
    sh = base.shape[:2]
    fw = np.ptp(p[:, 0])
    top, bot = band(p)
    edit = register(base, edit, p, (top, bot), oval_only=True)
    rows = np.zeros(sh, np.uint8)
    rows[max(top, 0):bot] = 255
    oval = poly(sh, p[OVAL])
    lb, le = (cv2.cvtColor(i, cv2.COLOR_BGR2LAB)[..., 0].astype(np.int16) for i in (base, edit))
    k = max(3, int(fw * 0.02)) | 1
    rim = (((lb - le) > 35) & (le < 50)).astype(np.uint8) * 255 & rows          # black frame, not the shade it casts
    m = cv2.morphologyEx(rim & cv2.dilate(oval, np.ones((k, k), np.uint8)), cv2.MORPH_CLOSE,
                         cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    m = np.isin(lab, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > (fw * 0.02) ** 2]).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((3, 3), np.uint8))
    eyes = np.zeros(sh, np.uint8)                       # the eyes, lashes and lids always stay the base's
    for e in EYES:
        eyes |= poly(sh, p[e])
    eyes = cv2.dilate(eyes, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(fw * 0.015) | 1, int(fw * 0.03) | 1)))
    full = m.copy()
    m[eyes > 0] = 0
    for kern in ((int(0.35 * fw) | 1, 3), (3, int(0.25 * fw) | 1), (int(0.06 * fw) | 1,) * 2):  # a rim over an eye
        m = np.maximum(m, cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, kern))
                       & full & eyes)
    iris = irises(sh, p, 1.4)
    m[iris > 0] = 0
    a = cv2.GaussianBlur(m, (0, 0), 1.5).astype(np.float32)
    labi = cv2.cvtColor(base, cv2.COLOR_BGR2LAB).astype(np.int16)        # off the face: only true black over skin
    ta, tb = (np.median(labi[..., c][oval > 0]) for c in (1, 2))
    skin = cv2.dilate((np.hypot(labi[..., 1] - ta, labi[..., 2] - tb) < 14).astype(np.uint8) * 255,
                      np.ones((k, k), np.uint8))
    side = rows & ~oval & 255
    black = (((lb - le) > 35) & (le < 50)).astype(np.uint8) * 255 & side
    out = np.where(skin > 0, cv2.morphologyEx(black, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8)), side)
    out = cv2.GaussianBlur(out, (0, 0), 1.5).astype(np.float32)
    out[eyes > 0] = 0
    a = np.maximum(a, out)
    a[cv2.GaussianBlur(iris, (0, 0), 1.5) > 0] = 0
    a = (a / 255)[..., None]
    return (base * (1 - a) + edit * a).astype(np.uint8), edit, p


def keep_face(base, edit, grow=0.04):
    """(out, doubled share at the seam): the edit everywhere except the base's face oval, with a soft join. Where the
    two layers disagree inside the join, two of a thing show (two mics, a smeared collar)."""
    edit = cv2.resize(edit, base.shape[1::-1], interpolation=cv2.INTER_LANCZOS4)
    p = mesh(base)
    fw = np.ptp(p[:, 0])
    edit = register(base, edit, p)
    m = cv2.dilate(poly(base.shape[:2], p[OVAL]), np.ones((int(fw * grow) | 1,) * 2, np.uint8))
    a = cv2.GaussianBlur(m, (0, 0), fw * 0.02).astype(np.float32)[..., None] / 255
    ring = (a[..., 0] > 0.1) & (a[..., 0] < 0.9)
    d = np.abs(base.astype(np.int16) - edit.astype(np.int16)).max(2) > 40
    doubled = float((d * a[..., 0] * (1 - a[..., 0]) * 4)[ring].sum() / max(ring.sum(), 1))
    return (edit * (1 - a) + base * a).astype(np.uint8), doubled


def shape_diff(a, b):
    """Mean distance between the faces' eye, nose and mouth-corner points after a similarity fit, in eye widths
    (outer corner to outer corner; 0 = the same features)."""
    p, q = (mesh(i)[SHAPE].astype(np.float64) for i in (a, b))
    m, _ = cv2.estimateAffinePartial2D(q, p, method=cv2.LMEDS)
    return float(np.linalg.norm(p - (q @ m[:, :2].T + m[:, 2]), axis=1).mean() / np.linalg.norm(p[0] - p[3]))


def line(ok, name, text):
    print(f"{'PASS' if ok else 'FAIL'}  {name:7s}  {text}")
    return 0 if ok else 1


def main(argv):
    if len(argv) < 3 or argv[0] not in ("glasses", "face", "check"):
        sys.exit(__doc__)
    cmd = argv[0]
    imgs = [cv2.imread(str(x)) for x in argv[1:3]]
    if any(i is None for i in imgs):
        sys.exit("can't read an input image")
    base, other = imgs
    bad = 0
    if cmd == "check":
        sd = shape_diff(base, other)
        return line(sd <= SHAPE_MAX, "shape", f"{sd:.3f} eye widths from the base (max {SHAPE_MAX})")
    if len(argv) < 4:
        sys.exit(__doc__)
    if cmd == "glasses":
        out, edit, p = keep_glasses(base, other)
        loss = glasses_loss(edit, out, base, p)
        bad += line(loss <= LOSS_MAX, "glasses", f"{loss:.1%} of the new frame lost (max {LOSS_MAX:.0%})")
    else:
        out, doubled = keep_face(base, other)
        bad += line(doubled <= JOIN_MAX, "join", f"{doubled:.1%} doubled at the seam (max {JOIN_MAX:.1%})")
    cv2.imwrite(str(argv[3]), out)
    sd = shape_diff(base, out)
    bad += line(sd <= SHAPE_MAX, "shape", f"{sd:.3f} eye widths from the base (max {SHAPE_MAX})")
    print(f"wrote {argv[3]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
