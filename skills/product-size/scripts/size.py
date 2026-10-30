# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["numpy==2.5.3", "pillow==12.3.0", "opencv-python-headless==5.0.0.93", "mediapipe==1.1.0",
#                 "torch==2.14.1", "transformers==4.57.6"]
# ///
"""Measure a product in millimetres in generated stills or takes, by the eyes of the person holding it.

Usage: size.py <still|clip> [<next> ...] --what "a soda can" --mm 66 [--height-mm 122]
               [--lo 0.8] [--hi 1.2] [--cut-max 0.15] [--fps 2] [--min-score 0.42] [--sheet out.jpg] [--ref product.png]
       size.py <still|clip> [...] --card product.toml
  The card is TOML:  [product]  what = "a soda can"  size_mm = [66, 122]  (width, height; optional lo, hi, cut_max,
  ref = "renders/product.png"). Inputs are one shot each; pass them in cut order.

How it measures: Grounding DINO finds the product by the words in `what` and a hand; SAM outlines the product; the
outline's minimum-area rectangle gives its width (the short side: the same at any tilt for a cylinder) and height.
The holder is the face nearest the product; MediaPipe finds their pupils. Adult pupils sit about 63 mm apart, so
width_px / pupils_px * 63 is the product's width in mm. A clip is sampled at --fps and the median taken.

One line per input, exit 1 on a FAIL:
  PASS  size   shot1.png: a soda can 68 mm wide by the holder's eyes (real 66; allowed 53-79), 1/1 frames
  FAIL  size   shot2.png: a soda can 96 mm wide by the holder's eyes (real 66; allowed 53-79), 1/1 frames: 1.45x
  FAIL  jump   shot3.png -> shot4.png: 67 -> 82 mm (+22%, max 15%)
  FAIL  shape  shot5.png: 2.40 widths tall, the real one is 1.85: stretched
  FLAG  size   shot6.png: not in a hand, 120 mm by the eyes: its distance to the lens is unknown, look yourself
  INFO  size   insert.png: not measured (no face to scale it)
--sheet writes one tile per input scaled so the holder's pupils are 100 px apart, with the real product (--ref, or
its outline) at true size beside it: with that sheet, Claude judged size right 10 times out of 10, from bare frames 5.

Limits: no face in frame (an insert) gives no scale. A product held well in front of the eyes reads up to ~15% big;
the default tolerance (0.8-1.2x) covers that. The width is tilt-proof only for round products; a box turned edge-on
reads narrow. Glass and very thin objects are found less reliably. A face turned past ~60 degrees gives no scale.

Models: Grounding DINO tiny and SAM ViT-B (Apache 2.0, from Hugging Face), YuNet (OpenCV Zoo, MIT) and the MediaPipe
face landmarker (Apache 2.0), all local. Face models download once to ~/.cache/ai-film-crew ($AI_FILM_CREW_MODELS).
"""
import hashlib, math, os, re, sys, tomllib, urllib.request, warnings
from pathlib import Path

os.environ.setdefault("GLOG_minloglevel", "2")          # MediaPipe and TFLite chatter on stderr
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
warnings.filterwarnings("ignore", category=FutureWarning)
import cv2
import numpy as np


IPD_MM = 63.0              # the mean distance between an adult's pupils
SHAPE_SLACK = 1.27         # a product seen from above reads a little taller; more than this is a stretched product
CACHE = Path(os.environ.get("AI_FILM_CREW_MODELS", Path.home() / ".cache" / "ai-film-crew"))
MODELS = {
    "face_detection_yunet_2023mar.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/47534e27c9851bb1128ccc0102f1145e27f23f98/models/face_detection_yunet/"
        "face_detection_yunet_2023mar.onnx", "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"),
    "face_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
        "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"),
}
STOP = {"a", "an", "the", "of", "with", "and", "in"}


# ---- the arithmetic (no models: tests import these) ----------------------------------------------------------------
def to_mm(width_px, pupils_px, ipd_mm=IPD_MM):
    return width_px / pupils_px * ipd_mm


def in_range(mm, real, lo, hi):
    return lo * real <= mm <= hi * real


def jumped(prev_mm, mm, cut_max):
    return abs(mm / prev_mm - 1) > cut_max


def words(what):
    return [w for w in re.findall(r"[a-z]+", what.lower()) if w not in STOP]


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


_m = {}


def detector():
    if "g" not in _m:
        import torch
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor, SamModel, SamProcessor
        dev = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
        _m["dev"] = dev
        _m["gp"] = AutoProcessor.from_pretrained("IDEA-Research/grounding-dino-tiny")
        _m["g"] = AutoModelForZeroShotObjectDetection.from_pretrained("IDEA-Research/grounding-dino-tiny").to(dev)
        _m["sp"] = SamProcessor.from_pretrained("facebook/sam-vit-base")
        _m["s"] = SamModel.from_pretrained("facebook/sam-vit-base").to(dev)
    return _m


def faces_yunet(img):
    if "yunet" not in _m:
        _m["yunet"] = cv2.FaceDetectorYN.create(model("face_detection_yunet_2023mar.onnx"), "", (320, 320), 0.8)
    d = _m["yunet"]
    h0, w0 = img.shape[:2]
    k = min(1.0, 960 / max(h0, w0))
    small = cv2.resize(img, None, fx=k, fy=k) if k < 1 else img
    d.setInputSize((small.shape[1], small.shape[0]))
    _, f = d.detect(small)
    return [tuple(r[:4] / k) for r in ([] if f is None else f) if r[3] / k * 1080 / w0 >= 40]


def pupils(img, box):
    """Distance between the pupils in pixels (MediaPipe on an enlarged crop of the face box), or None."""
    import mediapipe as mp
    if "lm" not in _m:
        _m["lm"] = mp.tasks.vision.FaceLandmarker.create_from_options(mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=model("face_landmarker.task"))))
    x, y, w, h = box
    cx, cy, s = x + w / 2, y + h / 2, max(w, h) * 1.6
    c = img[int(max(cy - s / 2, 0)):int(cy + s / 2), int(max(cx - s / 2, 0)):int(cx + s / 2)]
    if c.size == 0:
        return None
    k = 512 / c.shape[1]
    c = cv2.resize(c, None, fx=k, fy=k)
    r = _m["lm"].detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(c, cv2.COLOR_BGR2RGB)))
    if not r.face_landmarks:
        return None
    a, b = r.face_landmarks[0][468], r.face_landmarks[0][473]
    d = math.hypot((a.x - b.x) * c.shape[1], (a.y - b.y) * c.shape[0]) / k
    return d if d >= 0.28 * w else None          # a face turned past ~60 degrees gives no scale


def find(img_bgr, what, min_score):
    """The product in one frame: {score, w, h, box, held} or None."""
    import torch
    from PIL import Image
    m = detector()
    img = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    x = m["gp"](images=img, text=f"{what}. a hand.", return_tensors="pt").to(m["dev"])
    with torch.no_grad():
        o = m["g"](**x)
    r = m["gp"].post_process_grounded_object_detection(o, x.input_ids, threshold=0.3, text_threshold=0.25,
                                                       target_sizes=[img.size[::-1]])[0]
    labels = r.get("text_labels", r.get("labels"))
    keys = [w for w in words(what) if w != "hand"]
    prod, hands = [], []
    for i, t in enumerate(labels):
        t = str(t).lower()
        box = [float(v) for v in r["boxes"][i]]
        if any(w in t for w in keys):
            prod.append((float(r["scores"][i]), box))
        elif "hand" in t:
            hands.append(box)
    if not prod:
        return None
    score, box = max(prod, key=lambda p: p[0])
    if score < min_score:
        return None
    pad = 0.1 * (box[2] - box[0])
    held = any(hb[0] < box[2] + pad and hb[2] > box[0] - pad and hb[1] < box[3] + pad and hb[3] > box[1] - pad
               for hb in hands)
    s = m["sp"](img, input_boxes=[[box]], return_tensors="pt")
    with torch.no_grad():                           # MPS has no float64: the boxes come as float64
        so = m["s"](pixel_values=s["pixel_values"].to(m["dev"]), input_boxes=s["input_boxes"].float().to(m["dev"]))
    masks = m["sp"].image_processor.post_process_masks(so.pred_masks.cpu(), s["original_sizes"],
                                                       s["reshaped_input_sizes"])[0][0]
    mask = masks[int(torch.argmax(so.iou_scores[0, 0]))].numpy().astype(np.uint8)
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cs:
        return None
    c = max(cs, key=cv2.contourArea)
    _, (rw, rh), _ = cv2.minAreaRect(c)
    bx, by, bw, bh = cv2.boundingRect(c)
    return {"score": score, "w": min(rw, rh), "h": max(rw, rh), "box": (bx, by, bx + bw, by + bh), "held": held}


def frames(path, fps):
    if Path(path).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        img = cv2.imread(str(path))
        if img is None:
            sys.exit(f"can't read {path}")
        yield img
        return
    cap = cv2.VideoCapture(str(path))
    vf = cap.get(cv2.CAP_PROP_FPS) or 25
    step, i = max(1, round(vf / fps)), 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if i % step == 0:
            yield f
        i += 1


# ---- one run -------------------------------------------------------------------------------------------------------
def measure(inputs, what, real_w, real_h=None, lo=0.8, hi=1.2, cut_max=0.15, fps=2.0, min_score=0.42,
            sheet=None, ref=None):
    """Print one verdict line per input (and per jump between inputs); return the number of FAILs."""
    bad, prev, tiles = 0, None, []
    for path in inputs:
        name = Path(path).name
        got = []                                    # (mm or None, frame, pupils, face box, product)
        n = 0
        for f in frames(path, fps):
            n += 1
            if f.shape[1] != 1080:
                f = cv2.resize(f, (1080, int(f.shape[0] * 1080 / f.shape[1])))
            p = find(f, what, min_score)
            if not p:
                continue
            cx = (p["box"][0] + p["box"][2]) / 2    # the holder: the face nearest the product
            fs = sorted(faces_yunet(f), key=lambda b: abs(b[0] + b[2] / 2 - cx))
            ipd, fbox = next(((q, b) for b in fs[:1] if (q := pupils(f, b))), (None, None))
            mm = to_mm(p["w"], ipd) if ipd else None
            if mm and not 0.4 * real_w < mm < 3 * real_w:
                continue                            # nothing real is 3x the product: something else was found
            got.append((mm, f, ipd, fbox, p))
        if len(got) < 0.25 * n:                     # seen on one frame in ten: a mistaken detection
            got = []
        sized = [g for g in got if g[0] and g[4]["held"]]
        loose = [g for g in got if g[0] and not g[4]["held"]]
        if got and real_h:
            hw = float(np.median([g[4]["h"] / g[4]["w"] for g in got]))
            if hw > real_h / real_w * SHAPE_SLACK:
                bad += 1
                print(f"FAIL  shape  {name}: {hw:.2f} widths tall, the real one is {real_h / real_w:.2f}: stretched")
        pick = None
        if sized:
            mm = float(np.median([g[0] for g in sized]))
            ok = in_range(mm, real_w, lo, hi)
            bad += not ok
            print(f"{'PASS' if ok else 'FAIL'}  size   {name}: {what} {mm:.0f} mm wide by the holder's eyes (real "
                  f"{real_w:.0f}; allowed {lo * real_w:.0f}-{hi * real_w:.0f}), {len(sized)}/{n} frames"
                  + ("" if ok else f": {mm / real_w:.2f}x"))
            if prev and jumped(prev[1], mm, cut_max):
                bad += 1
                print(f"FAIL  jump   {prev[0]} -> {name}: {prev[1]:.0f} -> {mm:.0f} mm ({mm / prev[1] - 1:+.0%}, "
                      f"max {cut_max:.0%})")
            prev = (name, mm)
            pick = min(sized, key=lambda g: abs(g[0] - mm))
        elif loose:
            mm = float(np.median([g[0] for g in loose]))
            print(f"FLAG  size   {name}: not in a hand, {mm:.0f} mm by the eyes ({mm / real_w:.2f}x): its distance to "
                  f"the lens is unknown, look yourself")
            pick = min(loose, key=lambda g: abs(g[0] - mm))
        else:
            print(f"INFO  size   {name}: not measured ({'no face to scale it' if got else f'no {what} found'})")
        if sheet and pick:
            tiles.append(tile(pick, real_w, real_h, ref, len(tiles) + 1))
    if sheet and tiles:
        H = max(t.shape[0] for t in tiles)
        cv2.imwrite(str(sheet), np.hstack([cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, 8, cv2.BORDER_CONSTANT,
                                                              value=(0, 0, 0)) for t in tiles]))
        print(f"sheet: {sheet} (tile n = input n)")
    return bad


def tile(pick, real_w, real_h, ref, n):
    """The frame scaled so the pupils are 100 px apart, with the real product at true size beside the found one."""
    _, f, ipd, fbox, p = pick
    k = 100 / ipd
    g = cv2.copyMakeBorder(cv2.resize(f, None, fx=k, fy=k), 400, 400, 400, 400, cv2.BORDER_CONSTANT,
                           value=(255, 255, 255))
    rw = round(100 * real_w / IPD_MM)
    rh = round(100 * (real_h or real_w * 1.85) / IPD_MM)
    x0, y0 = int(p["box"][2] * k) + 415, int(p["box"][3] * k) + 400 - rh
    if ref:
        r = cv2.imread(str(ref), cv2.IMREAD_UNCHANGED)
        if r.shape[2] == 4:
            ys, xs = np.where(r[..., 3] > 20)
            r = r[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        r = cv2.resize(r, (rw, round(rw * r.shape[0] / r.shape[1])))
        y0 = int(p["box"][3] * k) + 400 - r.shape[0]
        roi = g[y0:y0 + r.shape[0], x0:x0 + rw]
        a = r[..., 3:] / 255.0 if r.shape[2] == 4 else 1.0
        roi[:] = (r[..., :3] * a + roi * (1 - a)).astype(np.uint8)
    else:
        cv2.rectangle(g, (x0, y0), (x0 + rw, y0 + rh), (60, 140, 40), 2)
    cv2.putText(g, "real", (x0, y0 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (60, 140, 40), 2)
    fx, fy = int((fbox[0] + fbox[2] / 2) * k) + 400, int((fbox[1] + fbox[3] * 0.4) * k) + 400
    t = g[max(fy - 160, 0):int(p["box"][3] * k) + 460, max(min(fx - 360, int(p["box"][0] * k) + 360), 0):x0 + rw + 40]
    t = t.copy()
    cv2.putText(t, str(n), (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    return t


def main(argv):
    a = list(argv)
    def opt(k, d=None):
        if k in a:
            i = a.index(k)
            v = a[i + 1]
            del a[i:i + 2]
            return v
        return d
    card = opt("--card")
    c = tomllib.loads(Path(card).read_text())["product"] if card else {}
    size = c.get("size_mm", [None, None])
    what = opt("--what", c.get("what"))
    real_w = float(opt("--mm", size[0] or 0))
    real_h = opt("--height-mm", size[1] if len(size) > 1 else None)
    if not a or not what or not real_w:
        sys.exit(__doc__)
    return 1 if measure(a, what, real_w, float(real_h) if real_h else None, float(opt("--lo", c.get("lo", 0.8))),
                        float(opt("--hi", c.get("hi", 1.2))), float(opt("--cut-max", c.get("cut_max", 0.15))),
                        float(opt("--fps", 2)), float(opt("--min-score", c.get("min_score", 0.42))),
                        opt("--sheet"), opt("--ref", c.get("ref"))) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
