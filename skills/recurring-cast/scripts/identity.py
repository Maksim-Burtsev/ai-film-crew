# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["numpy==2.5.3", "opencv-python-headless==5.0.0.93"]
# ///
"""Is this the same person? Face similarity of stills and takes to a person's real photos, with a threshold you
calibrate on your own judged stills.

Usage:
  identity.py score <img|video> ... --refs <folder|glob> [--min T]      against a person's real photos
  identity.py score <video> ... --against <still> [--min T]             each take against its own first still
  identity.py calibrate --refs <folder|glob> --same <folder|glob> --other <folder|glob>
Options: --model sface (default) | arcface   --arcface <path to w600k_r50.onnx>  (or $AI_FILM_CREW_ARCFACE)

score prints one line per input; a video is sampled every 0.5 s and the median taken. Each frame scores its face most
like the reference, so a two-shot works. With --min, each line is PASS or FAIL and the exit code is 1 on a FAIL:
  PASS  identity  shot4.png: 0.68 (min 0.52)
  FAIL  identity  shot5.png: 0.39 (min 0.52)
calibrate scores stills you judged "the same person" and "someone else" and prints both ranges and a threshold in the
gap, or says that this model can't separate them on your stills.

A score never picks the winner and never excuses a reject: it screens. The side-by-side look and the blind review
decide. Faces under ~250 px tall, profiles and covered eyes score like strangers.

Models (local): YuNet finds faces (OpenCV Zoo, MIT). SFace, the default, compares them (OpenCV Zoo, Apache 2.0): it
catches a different person, but it can miss a close lookalike. ArcFace (InsightFace w600k_r50) separates lookalikes
better, but its published weights are licensed for non-commercial research only: for client work, license it or use a
commercial face-comparison service. This script never downloads it; point --arcface at a copy you are allowed to use.
YuNet and SFace download once to ~/.cache/ai-film-crew ($AI_FILM_CREW_MODELS).
"""
import glob, hashlib, os, sys, urllib.request
from pathlib import Path

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
import cv2
import numpy as np

CACHE = Path(os.environ.get("AI_FILM_CREW_MODELS", Path.home() / ".cache" / "ai-film-crew"))
ZOO = "https://github.com/opencv/opencv_zoo/raw/47534e27c9851bb1128ccc0102f1145e27f23f98/models/"
MODELS = {
    "face_detection_yunet_2023mar.onnx": (ZOO + "face_detection_yunet/face_detection_yunet_2023mar.onnx",
                                          "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"),
    "face_recognition_sface_2021dec.onnx": (ZOO + "face_recognition_sface/face_recognition_sface_2021dec.onnx",
                                            "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79"),
}
ARCFACE_SHA = "4c06341c33c2ca1f86781dab0e829f88ad5b64be9fba56e56bc9ebdefc619e43"
ARCFACE_POINTS = np.array([[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366], [41.5493, 92.3655],
                           [70.7299, 92.2041]], np.float32)
VIDEO = (".mp4", ".mov", ".webm", ".mkv", ".m4v")


# ---- the arithmetic (no models: tests import these) ----------------------------------------------------------------
def threshold(same, other):
    """(threshold or None, gap): the middle of the gap between the lowest "same" and the highest "other" score."""
    lo_same, hi_other = min(same), max(other)
    gap = lo_same - hi_other
    return ((lo_same + hi_other) / 2 if gap > 0 else None), gap


def unit(v):
    v = np.asarray(v, np.float32).ravel()
    return v / np.linalg.norm(v)


# ---- models --------------------------------------------------------------------------------------------------------
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


class Faces:
    """Unit embeddings of every face in an image, with the chosen recognition model."""

    def __init__(self, kind="sface", arcface=None):
        self.det = cv2.FaceDetectorYN.create(model("face_detection_yunet_2023mar.onnx"), "", (320, 320), 0.6)
        self.kind = kind
        if kind == "arcface":
            path = arcface or os.environ.get("AI_FILM_CREW_ARCFACE")
            if not path or not Path(path).exists():
                sys.exit("--model arcface needs --arcface <path to w600k_r50.onnx> (or $AI_FILM_CREW_ARCFACE). Its "
                         "weights are licensed for non-commercial research only: check you may use them.")
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != ARCFACE_SHA:
                print("note: this is not the w600k_r50 file the thresholds were measured with", file=sys.stderr)
            self.net = cv2.dnn.readNetFromONNX(str(path))
        elif kind == "sface":
            self.rec = cv2.FaceRecognizerSF.create(model("face_recognition_sface_2021dec.onnx"), "")
        else:
            sys.exit(f"unknown model {kind}: sface or arcface")

    def __call__(self, img):
        """[(face area, unit embedding)] for every face in the image."""
        h, w = img.shape[:2]
        if max(h, w) > 1920:
            k = 1920 / max(h, w)
            img = cv2.resize(img, None, fx=k, fy=k)
            h, w = img.shape[:2]
        self.det.setInputSize((w, h))
        rows = self.det.detect(img)[1]
        out = []
        for f in ([] if rows is None else rows):
            if self.kind == "sface":
                e = self.rec.feature(self.rec.alignCrop(img, f))
            else:
                A, _ = cv2.estimateAffinePartial2D(f[4:14].reshape(5, 2).astype(np.float32), ARCFACE_POINTS,
                                                   method=cv2.LMEDS)
                crop = cv2.warpAffine(img, A, (112, 112), borderValue=0)
                self.net.setInput(cv2.dnn.blobFromImage(crop, 1 / 127.5, (112, 112), (127.5, 127.5, 127.5), swapRB=True))
                e = self.net.forward()[0]
            out.append((float(f[2] * f[3]), unit(e)))
        return out


def frames(path):
    if Path(path).suffix.lower() in VIDEO:
        cap = cv2.VideoCapture(str(path))
        step, i = max(1, int((cap.get(cv2.CAP_PROP_FPS) or 25) / 2)), 0
        while True:
            ok, img = cap.read()
            if not ok:
                break
            if i % step == 0:
                yield img
            i += 1
    else:
        img = cv2.imread(str(path))
        if img is None:
            sys.exit(f"can't read {path}")
        yield img


def paths(pattern):
    p = Path(pattern)
    if p.is_dir():
        return sorted(str(q) for q in p.iterdir() if q.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
    return sorted(glob.glob(pattern))


def mean_face(emb, files):
    """The mean unit embedding of the biggest face in each file."""
    es = []
    for f in files:
        for img in frames(f):
            faces = emb(img)
            if faces:
                es.append(max(faces, key=lambda x: x[0])[1])
            break
    if not es:
        sys.exit("no face found in the reference images")
    return unit(np.mean(es, axis=0))


def score(emb, path, ref):
    """Per-frame best match against the reference; [] when no face was found."""
    return [max(float(e @ ref) for _, e in faces) for faces in (emb(img) for img in frames(path)) if faces]


def main(argv):
    a = list(argv)
    def opt(k, d=None):
        if k in a:
            i = a.index(k)
            v = a[i + 1]
            del a[i:i + 2]
            return v
        return d
    kind, arcface = opt("--model", "sface"), opt("--arcface")
    refs, against, mn = opt("--refs"), opt("--against"), opt("--min")
    same, other = opt("--same"), opt("--other")
    if not a or a[0] not in ("score", "calibrate"):
        sys.exit(__doc__)
    cmd, inputs = a[0], a[1:]
    emb = Faces(kind, arcface)
    if cmd == "calibrate":
        if not (refs and same and other):
            sys.exit(__doc__)
        ref = mean_face(emb, paths(refs))
        groups = {}
        for name, pattern in (("same person", same), ("someone else", other)):
            sc = [s for f in paths(pattern) if (s := score(emb, f, ref))]
            groups[name] = [float(np.median(s)) for s in sc]
            if not groups[name]:
                sys.exit(f"no face found in the {name} stills")
            print(f"{name:13s} {min(groups[name]):.2f}-{max(groups[name]):.2f} ({len(groups[name])} stills)")
        t, gap = threshold(groups["same person"], groups["someone else"])
        if t is None:
            print(f"overlap {-gap:.2f}: {kind} can't tell them apart on these stills. Don't gate on it; look yourself.")
            return 1
        print(f"gap {gap:.2f}: use --min {t:.2f}")
        return 0
    if not inputs or not (refs or against):
        sys.exit(__doc__)
    bad = 0
    for path in inputs:
        ref = mean_face(emb, [against] if against else paths(refs))
        sc = score(emb, path, ref)
        if not sc:
            print(f"FAIL  identity  {path}: no face")
            bad += 1
            continue
        med = float(np.median(sc))
        tag = "" if mn is None else ("PASS  " if med >= float(mn) else "FAIL  ")
        bad += tag.startswith("FAIL")
        extra = f" (min {mn})" if mn is not None else ""
        many = f", lowest {min(sc):.2f} over {len(sc)} samples" if len(sc) > 1 else ""
        print(f"{tag or '      '}identity  {path}: {med:.2f}{extra}{many}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
