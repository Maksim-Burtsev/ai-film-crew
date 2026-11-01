# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow"]
# ///
"""The set of a multi-shot video as one file: where the walls, window, furniture, people and cameras are. Every shot
is a view of this set; people, furniture and light never move between shots, only the camera does. Written after
stills prompted one by one turned the table, moved a person across the room and stood a seated one up, and after
storyboards where eyelines flipped between the wide and the singles.

Usage (Python 3.11+, numpy, Pillow; run from the project root):
  scene.py plan  <set.toml> <out.png>                 top view: walls, window, furniture, people, cameras, 180 line
  scene.py card  <set.toml> <camera>                  what this camera sees, in words: paste it into the still prompt
  scene.py block <set.toml> <camera> <out.png>        flat-coloured perspective blockout: the still's layout guide
  scene.py sheet <set.toml> <camera> <out.jpg> <still> [<neighbour> ...]
                                                      plan + blockout + candidate + approved neighbours + the card, one
                                                      image for the approver or for comparing a still with its plan
  scene.py ask   <set.toml> <camera> <questions.json> questions about one frame, without answers, for a blind reviewer
  scene.py grade <set.toml> <camera> <answers.json>   the reviewer's answers against the set; exit 1 on a mismatch
  scene.py refs  <set.toml> <camera> [<first>]        the cast images for this camera's still and the sentence that
                                                      names them from Image <first> on (JSON: images, text)
The blind review (the blind-review skill): a fresh subagent sees only the frame and the questions; code compares.
Vision models are poor at "are these two shots consistent?" and fair at "which side is the window on?", so the
reviewer answers facts and the set decides.
`plan` also prints what each camera sees and exits 1 on a camera across the 180 line or a face into the lens; faces
too small for a line are notes (an error only on a camera with talk = true).

The set file (TOML, metres, top view). x runs from the left wall (0) to the right wall (room[0]), y from the front
wall (0) to the back wall (room[1]); "left/right/front/back" are as seen from the front wall. Heights above the floor.
  name = "office"
  room = [5.5, 4.4]
  walls = { left = "warm grey wall, credenza, plant", right = "floor-to-ceiling windows", back = "beige, whiteboard" }
  light = "right"                 # the wall the key light comes from (a window), or [x, y, h] for a lamp
  [[thing]]                       # furniture and props on it
  id = "table"; at = [2.9, 2.4]; size = [2.6, 1.1]; h = 0.75; rot = 0; look = "light oak, two laptops"
  [[person]]
  id = "maya"; at = [2.0, 1.5]; pose = "sits"; height = 1.70; faces = "sam"; look = "blonde bob, navy blazer"
  [[camera]]
  id = "A"; at = [4.8, 2.6]; h = 1.2; aim = "maya"; lens = 50; shots = "s2 s4 s8"; talk = true
`pose` is sits or stands; `height` the person's height in metres (default 1.74): the blockout and the card place the
head, shoulders and hips by it (without it every head sat at one height and the stills drew everyone the same
height). A person whose id is in the project's cast (cast/cast.toml) takes the cast's height unless the set gives one, and
`refs` picks their images from refs/people/<id>/. `faces` a person or thing id, or a heading in degrees (0 = towards
the right wall, 90 = towards the back wall). `aim` a person or thing id, or [x, y, h]. `lens` is the 35 mm-equivalent
focal length on the short side of the 9:16 frame (24 = wide, 35 = medium, 50 = single, 85 = tight). `talk = true`
marks a camera that carries lines: its faces must be big enough to hold a lip-sync. `reverse = true` marks a
deliberate reverse from behind the people (a TV seen from behind the couch, backs only): it is left out of the
180 check. A thing with `h0` (its bottom height) is drawn in the blockout as a solid dark block from h0 to h, e.g. a
wall TV; without it, as a top. `colour = [r, g, b]` gives a thing its blockout colour (a bottle on a table, h0 = the
table top). The numbers need not be exact: they must reproduce what the approved frames show. For a reel that already
exists, build the set from its widest approved frame, then run `frame_check.py` on every approved shot against it: a set
that fails its own footage is wrong.

The cast file (optional, cast/cast.toml in the project root), one table per recurring person, keyed by the id the
set uses; `refs` reads it:
  [maya]
  height = 1.70; age = 34; she = true; name_short = "Maya"; look = "blonde bob, green eyes, light freckles"
  photos = ["photo_1.jpg"]                                  # real photos: they decide the face and the age
  views = { front = "front.png", 34left = "34left.png", 34right = "34right.png", profleft = "profleft.png",
            profright = "profright.png", back = "back.png", fullfront = "full_front.png", fullside = "full_side.png",
            fullback = "full_back.png" }                    # images in refs/people/<id>/
  avoid = { profleft = "reads older" }                      # views with a known flaw, never passed to a still
"""
import json, math, sys, tomllib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920                          # frame the projection works in (9:16)
HEAD = {"sits": 1.22, "stands": 1.62}      # head centre above the floor for a person STATURE tall
STATURE, SEAT = 1.74, 0.47                 # seated, only the body above the seat scales with the height
FACE_M = 0.21                              # face box height (brows to chin) in metres, YuNet-sized
HEAD_R = 0.11                              # a head's half width, m: a back near the lens covers an edge with it
WALL_H = 2.8
MIN_LINE_PX = 250                          # a speaker's face below this morphs in video models (~150 px did)
COLOURS = [(196, 74, 60), (52, 110, 190), (60, 150, 90), (170, 110, 40), (120, 80, 160)]
ROOT = Path.cwd()                          # the calling project's root (run from it), as fal_run.py
CAST = ROOT / "cast/cast.toml"             # the project's cast: heights, looks, images in refs/people/<id>/
# Landmarks as a share of stature (Drillis and Contini, rounded): a height lock names one ("her crown below his
# shoulders"); "1.85 m" alone never held.
MARKS = [("eyes", 0.936), ("nose", 0.913), ("mouth", 0.894), ("chin", 0.87), ("shoulders", 0.818), ("chest", 0.72)]
CHAR_SLOTS = 4                             # character images a still reads: Nano Banana 2 and 2.1 take 4, Pro 5
FALLBACK = {"profleft": "34left", "profright": "34right", "34left": "front", "34right": "front", "back": None,
            "fullside": "fullfront", "fullback": "fullfront"}
SEEN = {"front": "from the front", "34left": "turned three-quarters to the frame's left",
        "34right": "turned three-quarters to the frame's right", "profleft": "in profile, facing the frame's left edge",
        "profright": "in profile, facing the frame's right edge", "back": "from behind"}


def font(size):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def load(path):
    s = tomllib.loads(Path(path).read_text())
    s.setdefault("walls", {}); s.setdefault("thing", []); s.setdefault("person", []); s.setdefault("camera", [])
    s["cast"] = tomllib.loads(CAST.read_text()) if CAST.exists() else {}
    for i, p in enumerate(s["person"]):
        if p["id"] in s["cast"]:
            p.setdefault("height", s["cast"][p["id"]]["height"])   # a set without heights put both heads at 1.74 m
        p["colour"] = COLOURS[i % len(COLOURS)]
        p["head"] = np.array([*p["at"], up(p, HEAD[p["pose"]])], float)
    return s


def up(p, z):
    """A body height drawn for a STATURE-tall person, scaled to the person's `height`."""
    if "height" not in p:
        return z
    base = SEAT if p["pose"] == "sits" else 0.0
    return base + (z - base) * p["height"] / STATURE


def find(s, key):
    for group in ("person", "thing", "camera"):
        for o in s[group]:
            if o["id"] == key:
                return o
    raise SystemExit(f"no person, thing or camera '{key}' in the set")


def point(s, ref):
    """3D point of a person (head), a thing (top centre) or a literal [x, y, h]."""
    if isinstance(ref, list):
        return np.array(ref + [1.2] * (3 - len(ref)), float)
    o = find(s, ref)
    return o["head"] if "pose" in o else np.array([*o["at"], o.get("h", 0.75)], float)


def gaze(s, p):
    """Unit vector a person looks along (to the target's head, or a heading)."""
    f = p["faces"]
    if isinstance(f, (int, float)):
        v = np.array([math.cos(math.radians(f)), math.sin(math.radians(f)), 0.0])
    else:
        v = point(s, f) - p["head"]
    return v / np.linalg.norm(v)


def light_dir(s, at):
    """Unit vector from a point towards the key light."""
    L = s.get("light", "right")
    if isinstance(L, list):
        v = np.array(L, float) - at
    else:
        v = {"left": [-1, 0], "right": [1, 0], "front": [0, -1], "back": [0, 1]}[L] + [0.35]
        v = np.array(v, float)
    return v / np.linalg.norm(v)


class Cam:
    def __init__(self, s, c):
        self.c, self.id = c, c["id"]
        self.pos = np.array([*c["at"], c.get("h", 1.4)], float)
        aim = point(s, c["aim"])
        if isinstance(c["aim"], str) and "pose" in find(s, c["aim"]):
            aim = aim - [0, 0, 0.12]       # frame a person with the head above the centre, as a real single does
        f = aim - self.pos
        self.f = f / np.linalg.norm(f)
        r = np.cross(self.f, [0, 0, 1.0])
        self.r = r / np.linalg.norm(r)
        self.u = np.cross(self.r, self.f)
        self.hfov = 2 * math.degrees(math.atan(12 / c.get("lens", 35)))
        self.fpx = (W / 2) / math.tan(math.radians(self.hfov / 2))

    def cam(self, p):
        d = np.asarray(p, float) - self.pos
        return np.array([d @ self.r, d @ self.u, d @ self.f])

    def px(self, p):
        x, y, z = self.cam(p)
        return (W / 2 + self.fpx * x / z, H / 2 - self.fpx * y / z, z) if z > 0.05 else None


def wall_hit(s, origin, direction):
    """Which wall a horizontal ray from origin meets first."""
    (rw, rd), best = s["room"], (1e9, "")
    for name, axis, val in (("left", 0, 0.0), ("right", 0, rw), ("front", 1, 0.0), ("back", 1, rd)):
        if abs(direction[axis]) > 1e-6:
            t = (val - origin[axis]) / direction[axis]
            if 0 < t < best[0]:
                best = (t, name)
    return best[1]


def view(s, cam):
    """What a camera sees: per person, screen position, face size, facing, light side. Fractions of the frame."""
    out = []
    for p in s["person"]:
        q = cam.px(p["head"])
        g = gaze(s, p)
        to_cam = cam.pos - p["head"]; to_cam /= np.linalg.norm(to_cam)
        g2, c2 = g[:2] / np.linalg.norm(g[:2]), to_cam[:2] / np.linalg.norm(to_cam[:2])
        yaw = math.degrees(math.acos(np.clip(g2 @ c2, -1, 1)))       # 0 = looks straight into the lens
        side = g @ cam.r                                            # + = looks screen-right
        light = light_dir(s, p["head"])
        lit = "even"
        if abs(light @ cam.r) > 0.45 and light @ -cam.f > -0.3:     # light from a side and not from behind
            lit = "screen-right" if light @ cam.r > 0 else "screen-left"
        e = {"id": p["id"], "pose": p["pose"], "yaw": yaw, "lit": lit, "side": "screen-right" if side > 0 else "screen-left",
             "looks": "into the lens" if yaw < 8 else ("screen-right" if side > 0 else "screen-left"),
             "visible": False, "face": "back" if yaw > 165 else ("profile" if yaw > 70 else "face")}
        if q:
            u, v, z = q
            r = cam.fpx * HEAD_R / z / W                            # the head's radius, in frame widths
            e.update(u=u / W, v=v / H, face_px=cam.fpx * FACE_M / z, dist=z, r=r,
                     visible=-0.05 < u / W < 1.05 and -0.05 < v / H < 1.05)
            if e["face"] == "back" and not e["visible"]:            # a back near the lens is in the frame when any of
                e["visible"] = u / W - r < 0.98 and u / W + r > 0.02 and -0.05 < v / H < 1.05   # its head is: the
                # shoulder of an over-the-shoulder shot fills an edge while the head's centre is off it
        out.append(e)
    # Looking at someone seen from behind in this frame (the over-the-shoulder shot) is looking just past the lens:
    # the eyeline is 3-8 deg off it there, as on a real podcast's reverse shot. Into the lens only under 3 deg.
    for e in out:
        p = find(s, e["id"])
        t = next((x for x in out if x["id"] == p.get("faces")), None)
        if e["looks"] == "into the lens" and e["yaw"] >= 3 and t and t["visible"] and t["face"] == "back":
            e["looks"] = f"just past the lens, {e['side']},"
    return out


def card(s, cid):
    cam = Cam(s, find(s, cid))
    c, pos = cam.c, cam.pos
    tilt = math.degrees(math.asin(np.clip(cam.f[2], -1, 1)))
    height = f"{pos[2]:.2f} m" + (" (seated eye level)" if abs(pos[2] - HEAD["sits"]) < 0.12 else
                                  " (standing eye level)" if abs(pos[2] - HEAD["stands"]) < 0.12 else "")
    lines = [f"Camera {cid}: {c.get('lens', 35)} mm, {height}, tilted {'down' if tilt < 0 else 'up'} {abs(tilt):.0f} deg,"
             f" aimed at {c['aim']}; it looks towards the {wall_hit(s, pos, cam.f)} wall."]
    seen, off, vis = [], [], []
    for e in view(s, cam):
        p = find(s, e["id"])
        if not e["visible"]:
            off.append(f"{e['id']} is off frame {'right' if e.get('u', 0.5) > 0.5 else 'left'}" if "u" in e
                       else f"{e['id']} is behind the camera")
            continue
        vis.append(p)
        where = "left" if e["u"] < 0.4 else "right" if e["u"] > 0.6 else "centre"
        tall = f", {p['height']:.2f} m tall," if "height" in p else ""
        who = (f"{e['id']} ({p.get('look', '')}){tall} {'sits' if e['pose'] == 'sits' else 'stands'}, frame {where}, "
               f"head at {e['v']:.0%} from the top")
        if e["face"] == "back":
            who += ", seen from behind: back of the head and shoulder only"
            if e["r"] > 0.15:                                       # near the lens: a big soft shape at an edge
                who += (f", close to the lens and out of focus, filling the frame's "
                        f"{'right' if e['u'] > 0.5 else 'left'} edge (about "
                        f"{(min(1, e['u'] + e['r']) - max(0, e['u'] - e['r'])) * 100:.0f}% of its width)")
        else:
            tgt = p["faces"] if isinstance(p["faces"], str) else "ahead"
            who += f", face ~{e['face_px']:.0f} px tall, looks {e['looks']} at {tgt}"
            if e["face"] == "profile":
                who += " (near profile)"
            if e["lit"] != "even":
                who += f", lit from {e['lit']}"
            who += f"; behind: the {wall_hit(s, p['head'], p['head'] - pos)} wall"
        seen.append(who)
    rel = heights(vis)                     # on the same line: anchor prompts drop the "In frame:" line
    lines += ["In frame: " + "; ".join(seen) + "." + (f" Heights: {'; '.join(rel)}." if rel else "")
              if seen else "In frame: nobody."]
    if off:
        lines.append("Not in frame: " + "; ".join(off) + ".")
    for t in s["thing"]:
        a, b = axis_px(cam, t)
        if t.get("shape") == "round":
            lines.append(f"The {t['id']} ({t.get('look', '')}) is round.")
        elif squarish(t):
            lines.append(f"The {t['id']} ({t.get('look', '')}) is about as long as it is wide.")
        elif a and b:
            ang = abs(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))) % 180
            run = ("runs left-right across the frame" if ang < 25 or ang > 155 else
                   "recedes into the depth of the frame" if 65 < ang < 115 else
                   f"runs diagonally ({ang:.0f} deg)")
            lines.append(f"The {t['id']} ({t.get('look', '')}) {run}.")
    walls = s["walls"]
    L = s.get("light")
    key = (f"Key light: a lamp at {L[0]:.1f}, {L[1]:.1f} m, {L[2]:.1f} m high" if isinstance(L, list)
           else f"Key light from the {L} wall")
    lines.append("Walls: " + "; ".join(f"{k}: {v}" for k, v in walls.items()) + f". {key}.")
    return "\n".join(lines)


def heights(people):
    """The standing people side by side, tallest first: the difference and the taller one's landmark at the shorter
    one's eyes, e.g. "sam is 10 cm taller than lee: lee's eyes are level with sam's mouth"."""
    st = sorted((p for p in people if p["pose"] == "stands" and "height" in p), key=lambda p: -p["height"])
    out = []
    for a, b in zip(st, st[1:]):
        d = round((a["height"] - b["height"]) * 100)
        mark = min(MARKS, key=lambda m: abs(m[1] * a["height"] - MARKS[0][1] * b["height"]))[0]
        out.append(f"{a['id']} and {b['id']} are about the same height" if d < 3 else
                   f"{a['id']} is {d} cm taller than {b['id']}: {b['id']}'s eyes are level with {a['id']}'s {mark}")
    return out


def refs(s, cid, first=1):
    """The cast images for a still of this camera, and the sentence that names them from Image `first` on. Per person,
    in this order: the cast view nearest the camera's angle; the full-length view if they stand and the frame shows
    0.8 m of them below the head; the real photo, which decides the face and the age (some generated views read older); the front view. The CHAR_SLOTS are shared: one person gets four images, two get two each, three or
    more one each. A view in the person's `avoid` (a known flaw) is never passed; the next in FALLBACK goes instead."""
    cam = Cam(s, find(s, cid)); cast = s["cast"]
    people = [e for e in view(s, cam) if e["visible"] and e["id"] in cast]
    k, images, text = max(1, CHAR_SLOTS // max(1, len(people))), [], []
    for e in people:
        c, p = cast[e["id"]], find(s, e["id"])
        side = "left" if e["looks"] == "screen-left" else "right"
        ang = min([(0, "front"), (45, f"34{side}"), (90, f"prof{side}"), (180, "back")],
                  key=lambda a: abs(a[0] - e["yaw"]))[1]
        body = p["pose"] == "stands" and (1 - e["v"]) * H * FACE_M / e["face_px"] >= 0.8
        full = "fullback" if ang == "back" else "fullside" if ang == "profleft" else "fullfront"
        picked = []
        for v in [ang] + ([full] if body else []) + ["photo", "front"]:
            while v in c.get("avoid", {}):
                v = FALLBACK[v]
            if v and v not in picked:
                picked.append(v)
        picked = picked[:k]
        his, him = ("her", "her") if c.get("she") else ("his", "him")
        role = {"photo": f"is a photo of {him} that decides {his} face, eyes and age wherever the images differ",
                "fullfront": f"is {his} full figure, for {his} build and height",
                "fullside": f"is {his} full figure from the side, for {his} build and height",
                "fullback": f"is {his} full figure from behind, for {his} build and height"}
        nums = range(first + len(images), first + len(images) + len(picked))
        images += [f"refs/people/{e['id']}/{c['photos'][0] if v == 'photo' else c['views'][v]}" for v in picked]
        text.append(f"{c.get('name_short', e['id'].capitalize())} ({c['age']}, {round(p['height'] * 100)} cm) is the "
                    f"{'woman' if c.get('she') else 'man'} in Image{'s' if len(nums) > 1 else ''} "
                    f"{nums[0]}{f'-{nums[-1]}' if len(nums) > 1 else ''}: "
                    + "; ".join(f"Image {i} {role.get(v, f'shows {him} {SEEN.get(v)}')}" for i, v in zip(nums, picked))
                    + f". Take only {his} face, hair, skin, build and height from {'them' if len(nums) > 1 else 'it'} "
                    f"(not clothes, pose, expression, backdrop or light, nor any logo, patch or lettering): "
                    f"{c['look']}. {his.capitalize()} expression is the one this shot asks for.")
    for q in images:
        if not (ROOT / q).exists():
            sys.exit(f"{q} is missing: refs/people/ holds the cast images (keep them out of git)")
    if text:
        text.append("Each of them appears exactly once: the reference images give identity, not the layout.")
    return {"images": images, "text": " ".join(text)}


def squarish(t):
    """No long side to ask about: a 1.1 x 1.3 m console seen from one end was "across" for the projection and "into the
    depth" for the reviewer, and neither is wrong."""
    return max(t["size"]) < 1.3 * min(t["size"])


def axis_px(cam, t):
    """Screen points of a thing's long axis ends at its top height."""
    sx, sy = t["size"]; a = math.radians(t.get("rot", 0))
    d = np.array([math.cos(a), math.sin(a)]) * sx / 2 if sx >= sy else np.array([-math.sin(a), math.cos(a)]) * sy / 2
    c = np.array(t["at"], float); h = t.get("h", 0.75)
    return [cam.px([*(c + k * d), h]) for k in (-1, 1)]


def warnings(s):
    """(warnings, notes): a camera across the 180 line or a face into the lens is wrong; a face too small for a line
    is fine for a silent shot, so it is only a note unless the camera has talk = true."""
    out, notes, people = [], [], s["person"]
    if len(people) >= 2:
        a, b = people[0]["head"][:2], people[1]["head"][:2]
        line = b - a; sides = {}
        for c in s["camera"]:
            if c.get("reverse"):
                continue
            v = np.array(c["at"], float) - a
            cr = line[0] * v[1] - line[1] * v[0]
            if abs(cr) > 0.05:
                sides[c["id"]] = cr > 0
        if len(set(sides.values())) > 1:
            maj = max((True, False), key=lambda k: list(sides.values()).count(k))
            bad = [k for k, v in sides.items() if v != maj]
            out.append(f"180 line ({people[0]['id']}-{people[1]['id']}): camera(s) {', '.join(bad)} on the other side; "
                       f"eyelines flip on the cut")
    for c in s["camera"]:
        cam = Cam(s, c)
        for e in view(s, cam):
            if e["visible"] and e["face"] != "back" and e["face_px"] < MIN_LINE_PX:
                (out if c.get("talk") else notes).append(
                    f"camera {c['id']}: {e['id']}'s face ~{e['face_px']:.0f} px, too small for a line (min {MIN_LINE_PX})")
            if e["visible"] and e["looks"] == "into the lens":
                out.append(f"camera {c['id']}: {e['id']} looks into the lens")
    return out, notes


def plan(s, out):
    """Top view for people: walls, window, furniture, who sits where and looks where, every camera and what it covers."""
    rw, rd = s["room"]
    k = 600 / max(rw, rd, 4.0)                        # px per metre: the room fills ~600 px
    L, T, R = 70, 110, 430                            # margins: left, top, right (camera labels and the legend)
    warn, notes = warnings(s)
    Wd, Hd = int(L + rw * k + R), int(T + rd * k + 90 + 30 * len(warn + notes))
    img = Image.new("RGB", (Wd, Hd), "white")
    over = Image.new("RGBA", img.size, (0, 0, 0, 0)); od = ImageDraw.Draw(over)
    d = ImageDraw.Draw(img)
    P = lambda x, y: (L + x * k, T + (rd - y) * k)    # the back wall on top, the front wall at the bottom
    f, fs, fb = font(20), font(17), font(26)
    d.text((L, 18), s.get("name", "set"), fill="black", font=fb)
    d.text((L, 54), "top view; the front wall is at the bottom", fill=(90, 90, 90), font=fs)
    for c in s["camera"]:                              # field of view, translucent, under everything else
        cam = Cam(s, c); o = np.array(c["at"], float)
        h = math.atan2(cam.f[1], cam.f[0]); half = math.radians(cam.hfov / 2)
        reach = max(1.0, min(2.2, np.linalg.norm(point(s, c["aim"])[:2] - o) + 0.4))
        od.polygon([P(*o)] + [P(*(o + reach * np.array([math.cos(h + q), math.sin(h + q)]))) for q in (-half, half)],
                   fill=(120, 120, 120, 38), outline=(120, 120, 120, 110))
    img.paste(over, (0, 0), over); d = ImageDraw.Draw(img)
    for name, (a, b) in {"front": ((0, 0), (rw, 0)), "back": ((0, rd), (rw, rd)),
                         "left": ((0, 0), (0, rd)), "right": ((rw, 0), (rw, rd))}.items():
        window = "window" in s["walls"].get(name, "").lower()
        d.line([P(*a), P(*b)], fill=(60, 130, 220) if window else (40, 40, 40), width=9 if window else 5)
        label = s["walls"].get(name, "")
        if not label:
            continue
        label = f"{name.upper()}: {label}"
        if name in ("left", "right"):
            tl = Image.new("RGBA", (int(rd * k), 24), (255, 255, 255, 0))
            ImageDraw.Draw(tl).text((int(rd * k) // 2, 12), label[:int(rd * k / 9)], fill=(60, 60, 60), font=fs,
                                    anchor="mm")
            tl = tl.rotate(90 if name == "left" else -90, expand=True)
            x0 = int(P(0, 0)[0] - 34) if name == "left" else int(P(rw, 0)[0] + 10)
            img.paste(tl, (x0, int(T)), tl)
        else:
            y = P(0, rd if name == "back" else 0)[1]
            d.text((L, y - 26 if name == "back" else y + 8), label[:int((rw * k + R - 20) / 8.5)], fill=(60, 60, 60),
                   font=fs)
    for t in s["thing"]:
        pts = [P(*p) for p in outline(t["at"], t["size"], t.get("rot", 0), t.get("shape") == "round")]
        d.polygon(pts, fill=(226, 196, 150), outline=(120, 90, 50), width=2)
        d.text(P(*t["at"]), t["id"], fill=(80, 60, 30), font=f, anchor="mm")
    people = s["person"]
    if len(people) >= 2:                               # the 180 line, inside the room only
        a, b = people[0]["head"][:2], people[1]["head"][:2]; v = (b - a) / np.linalg.norm(b - a)
        ts = [t for t in np.linspace(-12, 12, 2401) if 0 <= (a + v * t)[0] <= rw and 0 <= (a + v * t)[1] <= rd]
        if ts:
            d.line([P(*(a + v * ts[0])), P(*(a + v * ts[-1]))], fill=(220, 60, 60), width=2)
    for p in people:
        x, y = P(*p["at"]); g = gaze(s, p)[:2]; g /= np.linalg.norm(g)
        d.line([(x, y), (x + g[0] * 70, y - g[1] * 70)], fill=p["colour"], width=7)
        d.ellipse([x - 24, y - 24, x + 24, y + 24], fill=p["colour"], outline="black", width=2)
        d.text((x, y + 38), f"{p['id']} ({p['pose']})", fill="black", font=f, anchor="mm")
    taken, icons = [], []
    for c in s["camera"]:                              # labels first, then the camera icons on top of them
        cam = Cam(s, c); o = np.array(c["at"], float); fv = cam.f[:2] / np.linalg.norm(cam.f[:2])
        pr = np.array([-fv[1], fv[0]])
        icons.append([P(*(o + fv * 0.22)), P(*(o - fv * 0.1 + pr * 0.12)), P(*(o - fv * 0.1 - pr * 0.12))])
        x, y = P(*o)
        label = f"{c['id']}  {c.get('lens', 35)} mm, h {c.get('h', 1.4):.2f} m" + (f"  [{c['shots']}]" if c.get("shots") else "")
        lx, ly = (x + 24, y + 6)
        while any(abs(ly - ty) < 24 and abs(lx - tx) < 220 for tx, ty in taken): ly += 24
        taken.append((lx, ly))
        tw = d.textlength(label, font=fs)
        if lx + tw > Wd - 8: lx = Wd - 8 - tw
        d.rectangle([lx - 3, ly - 2, lx + tw + 3, ly + 20], fill=(255, 255, 255))
        d.text((lx, ly), label, fill="black", font=fs)
    for tri in icons:
        d.polygon(tri, fill="black")
    y = T + rd * k + 34
    d.text((L, y), "black triangle: camera (lens, height, the shots it covers); grey wedge: what it sees; "
                   "coloured arrow: where a person looks;", fill=(90, 90, 90), font=fs)
    d.text((L, y + 22), "red line: the 180 line, every camera stays on one side of it", fill=(200, 50, 50), font=fs)
    for i, w in enumerate(warn + notes):
        d.text((L, y + 50 + 28 * i), ("WARNING " if w in warn else "note: ") + w, fill=(200, 50, 50) if w in warn
               else (90, 90, 90), font=fs)
    img.save(out)
    return warn


def clip_near(poly, z0=0.06):
    """Sutherland-Hodgman against the camera's near plane, on camera-space points."""
    out = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        if a[2] >= z0: out.append(a)
        if (a[2] >= z0) != (b[2] >= z0):
            t = (z0 - a[2]) / (b[2] - a[2]); out.append(a + t * (b - a))
    return out


def outline(c, size, rot=0, round_=False):
    """Corner points of a thing's footprint: a rotated rectangle, or a 24-gon for shape = "round"."""
    sx, sy = size; a = math.radians(rot)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    vs = ([[sx / 2 * math.cos(t), sy / 2 * math.sin(t)] for t in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
          if round_ else [[-sx / 2, -sy / 2], [sx / 2, -sy / 2], [sx / 2, sy / 2], [-sx / 2, sy / 2]])
    return [np.array(c) + R @ v for v in vs]


def box(c, size, h0, h1, rot=0, round_=False):
    """Faces of a prism: footprint centre c (x, y), size (sx, sy), from height h0 to h1."""
    q = outline(c, size, rot, round_)
    lo, hi = [[*p, h0] for p in q], [[*p, h1] for p in q]
    n = len(q)
    return [hi, lo] + [[lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]] for i in range(n)]


def block(s, cid, out, size=(540, 960)):
    cam = Cam(s, find(s, cid)); rw, rd = s["room"]
    polys = []                                                     # (camera-space points, fill, label)
    def add(pts, fill, label=None):
        cp = clip_near([cam.cam(p) for p in pts])
        if len(cp) >= 3:
            polys.append((cp, fill, label))
    add([[0, 0, 0], [rw, 0, 0], [rw, rd, 0], [0, rd, 0]], (205, 196, 182))
    for name, quad in {"back": [[0, rd], [rw, rd]], "left": [[0, 0], [0, rd]], "right": [[rw, 0], [rw, rd]],
                       "front": [[0, 0], [rw, 0]]}.items():
        (x0, y0), (x1, y1) = quad
        window = "window" in s["walls"].get(name, "").lower()
        add([[x0, y0, 0], [x1, y1, 0], [x1, y1, WALL_H], [x0, y0, WALL_H]],
            (176, 212, 240) if window else (232, 228, 220), f"{name.upper()} WALL: {s['walls'].get(name, '')}")
    shell = len(polys)                     # floor and walls: drawn first, nothing in the room is behind them (a
                                           # wall seen at an angle sorted nearer than the TV on it and hid it)
    for t in s["thing"]:
        h, rnd = t.get("h", 0.75), t.get("shape") == "round"
        solid = "h0" in t                                          # a TV or a cabinet: a dark block, not a top
        for face in box(t["at"], t["size"], t["h0"] if solid else h - 0.05, h, t.get("rot", 0), rnd):
            add(face, tuple(t["colour"]) if "colour" in t else (55, 58, 66) if solid else (210, 170, 110), None)
        add(box(t["at"], t["size"], 0.0, 0.01, t.get("rot", 0), rnd)[0], (170, 160, 145), None)  # its shadow
    heads = []
    for p in s["person"]:
        sits = p["pose"] == "sits"
        hip, sh = up(p, 0.47 if sits else 0.92), up(p, 1.02 if sits else 1.42)
        g = gaze(s, p); yaw = math.degrees(math.atan2(g[1], g[0])); g2 = g[:2] / np.linalg.norm(g[:2])
        body = np.array(p["at"]) - g2 * 0.04
        for face in box(body, (0.22, 0.40), hip, sh - 0.06, yaw):          # torso
            add(face, p["colour"], None)
        for face in box(body, (0.18, 0.46), sh - 0.08, sh, yaw):           # shoulders
            add(face, p["colour"], None)
        if sits:
            seat = np.array(p["at"]) - g2 * 0.05
            for face in box(seat, (0.46, 0.46), 0.42, 0.47, yaw):          # seat
                add(face, (95, 95, 100), None)
            for face in box(seat - g2 * 0.24, (0.06, 0.46), 0.47, 0.95, yaw):  # backrest
                add(face, (95, 95, 100), None)
            for face in box(np.array(p["at"]) + g2 * 0.22, (0.36, 0.30), 0.40, 0.47, yaw):  # thighs
                add(face, p["colour"], None)
        else:
            for face in box(body, (0.18, 0.34), 0.0, hip, yaw):            # legs
                add(face, (70, 70, 80), None)
        q = cam.cam(p["head"])
        if q[2] > 0.06:
            heads.append((q, p))
    for q, p in heads:
        polys.append(([q], "head", p))
    depth = lambda q: -np.mean([p[2] for p in q[0]])
    polys = sorted(polys[:shell], key=depth) + sorted(polys[shell:], key=depth)
    img = Image.new("RGB", (W, H), (250, 250, 250)); d = ImageDraw.Draw(img); f = font(30)
    to2 = lambda p: (W / 2 + cam.fpx * p[0] / p[2], H / 2 - cam.fpx * p[1] / p[2])
    labels = []
    for pts, fill, label in polys:
        if fill == "head":
            draw_head(d, s, cam, label, to2(pts[0]), cam.fpx * 0.115 / pts[0][2])
            continue
        d.polygon([to2(p) for p in pts], fill=fill, outline=(90, 90, 90))
        if label:
            labels.append((np.mean([to2(p) for p in pts], 0), label))
    for (x, y), label in labels:
        if 0 < x < W and 0 < y < H:
            d.text((x, y), label[:48], fill=(60, 60, 60), font=f, anchor="mm")
    d.text((24, 24), f"BLOCKOUT camera {cid}: {cam.c.get('lens', 35)} mm, h {cam.pos[2]:.2f} m", fill="black",
           font=font(36))
    img.resize(size).save(out)


def questions(s, cid):
    """Camera-relative questions about one frame, each with the answers the set accepts."""
    cam = Cam(s, find(s, cid)); v = {e["id"]: e for e in view(s, cam)}
    who = lambda p: f"the person with {p.get('look') or p['id']}"
    band = lambda u: ({"left third"} if u < 0.3 else {"left third", "centre"} if u < 0.45 else {"centre"} if u <= 0.55
                      else {"centre", "right third"} if u <= 0.7 else {"right third"})
    Q = []
    def q(qid, text, options, accept):
        Q.append({"id": qid, "q": text, "options": options + ["can't tell"], "accept": sorted(accept)})
    for p in s["person"]:
        e = v[p["id"]]
        if not e["visible"]:
            accept = {"not in the frame"}
        elif e["face"] == "back":
            accept = {"seen from behind"} | band(e["u"])
        else:
            accept = band(e["u"]) | ({"seen from behind"} if e["face"] == "profile" and e["yaw"] > 120 else set())
        q(f"where_{p['id']}", f"Where is {who(p)}?", ["left third", "centre", "right third", "seen from behind",
                                                      "not in the frame"], accept)
        if e["visible"]:
            q(f"pose_{p['id']}", f"Is {who(p)} sitting or standing?", ["sitting", "standing"],
              {"sitting" if p["pose"] == "sits" else "standing"})
        if e["visible"] and e["face"] != "back" and e["looks"] != "into the lens" and e["yaw"] >= 15:
            q(f"looks_{p['id']}", f"Which way does {who(p)} look?", ["towards the frame's left edge",
              "towards the frame's right edge", "into the camera", "down at something"],
              {"towards the frame's left edge" if e["looks"] == "screen-left" else "towards the frame's right edge"})
            q(f"behind_{p['id']}", f"What is directly behind {who(p)}?", [f"{k} wall: {d}" for k, d in s["walls"].items()]
              + ["something else"], {f"{wall_hit(s, p['head'], p['head'] - cam.pos)} wall: "
                                     f"{s['walls'].get(wall_hit(s, p['head'], p['head'] - cam.pos), '')}"})
    vis = [p for p in s["person"] if v[p["id"]]["visible"]]
    for i, a in enumerate(vis):
        for b in vis[i + 1:]:
            d = float(np.linalg.norm(a["head"][:2] - b["head"][:2]))
            opts = ["within arm's reach (under 1 m)", "1 to 2 m", "more than 2 m"]
            acc = {opts[0] if d < 1 else opts[1] if d <= 2 else opts[2]}
            if 0.75 < d < 1.25: acc |= {opts[0], opts[1]}
            if 1.75 < d < 2.25: acc |= {opts[1], opts[2]}
            q(f"apart_{a['id']}_{b['id']}", f"How far apart in the room are {who(a)} and {who(b)}?", opts, acc)
            dv = v[a["id"]]["v"] - v[b["id"]]["v"]
            acc = {"about level"} if abs(dv) < 0.06 else {who(a) if dv < 0 else who(b)}
            if 0.04 < abs(dv) < 0.1: acc |= {"about level"}
            q(f"higher_{a['id']}_{b['id']}", "Whose head is higher in the frame?", [who(a), who(b), "about level"], acc)
    win = next((k for k, d in s["walls"].items() if "window" in d.lower()), None)  # no question on a set without one
    if win:
        rw, rd = s["room"]
        line = {"left": ((0, 0), (0, rd)), "right": ((rw, 0), (rw, rd)), "front": ((0, 0), (rw, 0)),
                "back": ((0, rd), (rw, rd))}[win]
        us = []
        for t in np.linspace(0.02, 0.98, 25):
            for h in (0.8, 1.5, 2.2):
                pt = [line[0][0] + t * (line[1][0] - line[0][0]), line[0][1] + t * (line[1][1] - line[0][1]), h]
                pr = cam.px(pt)
                if pr and 0 <= pr[0] <= W and 0 <= pr[1] <= H: us.append(pr[0] / W)
        if not us: acc = {"not visible"}
        elif min(us) < 0.35 and max(us) > 0.65: acc = {"behind the people, on the far wall"}
        else: acc = {"left side of the frame" if np.mean(us) < 0.5 else "right side of the frame"}
        q("window", "Where are the windows in this frame?", ["left side of the frame", "right side of the frame",
                                                             "behind the people, on the far wall", "not visible"], acc)
    for t in s["thing"]:
        if t.get("shape") == "round" or squarish(t):
            continue
        a, b = axis_px(cam, t)
        inside = [p for p in (a, b) if p and -0.2 * W < p[0] < 1.2 * W and -0.2 * H < p[1] < 1.2 * H]
        opts = ["across the frame, left to right", "away from the camera, into the depth", "diagonally", "not visible"]
        if not inside: acc = {opts[3]}
        else:
            ang = abs(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))) % 180 if a and b else 90
            acc = {opts[0]} if ang < 25 or ang > 155 else {opts[1]} if 65 < ang < 115 else {opts[2]}
            if 18 < ang < 32 or 148 < ang < 162: acc |= {opts[0], opts[2]}
            if 58 < ang < 72 or 108 < ang < 122: acc |= {opts[1], opts[2]}
        q(f"axis_{t['id']}", f"How does the long side of the {t['id']} ({t.get('look', '')}) run?", opts, acc)
    h = cam.pos[2]
    opts = ["below a seated person's eyes", "at a seated person's eye level", "at a standing person's eye level",
            "above everyone, looking down"]
    acc = {opts[0]} if h < 1.05 else {opts[1]} if h < 1.4 else {opts[2]} if h < 1.8 else {opts[3]}
    if 1.3 < h < 1.5: acc |= {opts[1], opts[2]}
    q("camera_height", "Where is the camera relative to the people's eyes?", opts, acc)
    q("others", "Is anyone or any body part visible that none of the questions above describe (a stranger, an extra "
                "hand, a reflection of a person)?", ["no", "yes"], {"no"})
    return Q


def draw_head(d, s, cam, p, uv, r):
    """A head as hair with the face turned the way the person looks: frontal, three-quarter, profile or the back."""
    u, v = uv
    gc = cam.cam(p["head"] + gaze(s, p)) - cam.cam(p["head"]); gc /= np.linalg.norm(gc)
    front, side = -gc[2], gc[0]                       # 1 = into the lens, 0 = profile, -1 = the back of the head
    d.ellipse([u - r, v - r * 1.15, u + r, v + r * 1.15], fill=(75, 55, 45), outline="black", width=2)
    if front > -0.45:
        w = r * (0.45 + 0.5 * max(front, 0))
        cu = u + (r - w) * side
        d.ellipse([cu - w, v - r * 0.85, cu + w, v + r * 1.1], fill=(236, 200, 170))
        for k in (-0.4, 0.4):
            ex = cu + w * (k * max(front, 0.25) + 0.35 * side)
            d.ellipse([ex - r * 0.07, v - r * 0.2, ex + r * 0.07, v - r * 0.06], fill="black")
        nx = cu + w * 0.55 * side
        d.polygon([(nx + r * 0.45 * side, v + r * 0.15), (nx, v - r * 0.05), (nx, v + r * 0.3)], fill=(190, 140, 110))
    d.text((u, v - r * 1.45), p["id"], fill="black", font=font(40), anchor="mm")


def sheet(s, cid, out, still, *refs):
    """One image to compare a still with its plan: top view, blockout, the candidate, approved neighbours, the card."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        plan(s, f"{tmp}/plan.png"); block(s, cid, f"{tmp}/block.png")
        h = 960
        tiles = [("TOP VIEW", Image.open(f"{tmp}/plan.png")), (f"BLOCKOUT {cid}", Image.open(f"{tmp}/block.png")),
                 ("CANDIDATE", Image.open(still))] + [(f"APPROVED {Path(r).stem}", Image.open(r)) for r in refs]
        tiles = [(t, im.convert("RGB").resize((int(im.width * h / im.height), h))) for t, im in tiles]
        text = card(s, cid)
        sheet_w = sum(im.width for _, im in tiles) + 20 * len(tiles)
        img = Image.new("RGB", (sheet_w, h + 60 + 34 * (text.count("\n") + 3)), "white"); d = ImageDraw.Draw(img)
        x = 10
        for t, im in tiles:
            d.text((x, 10), t, fill="black", font=font(30)); img.paste(im, (x, 50)); x += im.width + 20
        d.multiline_text((10, h + 70), text, fill="black", font=font(26), spacing=8)
        img.save(out, quality=88)


if __name__ == "__main__":
    cmd, sp = sys.argv[1], load(sys.argv[2])
    if cmd == "plan":
        w = plan(sp, sys.argv[3])
        for c in sp["camera"]:
            seen = [f"{e['id']} at u={e['u']:.2f} ({'left' if e['u'] < 0.4 else 'right' if e['u'] > 0.6 else 'centre'} of frame), "
                    f"{e['face']} {e['face_px']:.0f}px, looks {e['looks']}" for e in view(sp, Cam(sp, c)) if e["visible"]]
            print(f"camera {c['id']:4s} {c.get('lens', 35)}mm h{c.get('h', 1.4):.2f}: " + ("; ".join(seen) or "nobody in frame"))
        print("\n".join(f"WARNING {x}" for x in w) or "plan OK: no warnings")
        sys.exit(1 if w else 0)
    elif cmd == "card":
        print(card(sp, sys.argv[3]))
    elif cmd == "block":
        block(sp, sys.argv[3], sys.argv[4])
    elif cmd == "sheet":
        sheet(sp, sys.argv[3], sys.argv[4], *sys.argv[5:])
    elif cmd == "refs":
        print(json.dumps(refs(sp, sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 1), indent=1))
    elif cmd == "ask":
        Path(sys.argv[4]).write_text(json.dumps([{k: q[k] for k in ("id", "q", "options")} for q in questions(sp, sys.argv[3])],
                                                indent=1))
        print(f"{sys.argv[4]}: {len(questions(sp, sys.argv[3]))} questions")
    elif cmd == "grade":
        got = json.loads(Path(sys.argv[4]).read_text())
        bad = 0
        for q in questions(sp, sys.argv[3]):
            a = got.get(q["id"])
            tag = "FLAG" if a in (None, "can't tell") else "PASS" if a in q["accept"] else "FAIL"
            bad += tag == "FAIL"
            print(f"{tag}  {q['id']:16s} answer '{a}'" + ("" if tag == "PASS" else f", the set gives {' or '.join(q['accept'])}"))
        sys.exit(1 if bad else 0)
    else:
        sys.exit(__doc__)
