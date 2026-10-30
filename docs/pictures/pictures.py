"""The README pictures: the crew, and one picture per skill. Ana, Leo, Jo and Mia are the same people in every one."""
import math
from draw import C, T, arrow, curve, stamp, badge, framed, svg
from people import person, ana, leo, jo, serum, grip, ring, eye_points, soda, ANA, LEO, JO, f

MIA = "#4f7fc9"


def room(x, y, w, h, window="left"):
    o = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{C["wall"]}"/>'
    if window is None:
        return o
    ww = w * (0.4 if window == "back" else 0.2)
    wx = {"left": x, "right": x + w - ww, "back": x + w * 0.3}[window]
    wy, wh = y + h * 0.1, h * 0.46
    return (o + f'<rect x="{f(wx)}" y="{f(wy)}" width="{f(ww)}" height="{f(wh)}" fill="{C["window"]}"/>'
            f'<line x1="{f(wx+ww/2)}" y1="{f(wy)}" x2="{f(wx+ww/2)}" y2="{f(wy+wh)}" stroke="#fff" stroke-width="2"/>'
            f'<line x1="{f(wx)}" y1="{f(wy+wh/2)}" x2="{f(wx+ww)}" y2="{f(wy+wh/2)}" stroke="#fff" stroke-width="2"/>')




def couch_back(x, y, w, h):
    return f'<rect x="{x}" y="{f(y+h*0.42)}" width="{w}" height="{f(h*0.3)}" rx="10" fill="#9aa6bd"/>'


def couch_seat(x, y, w, h):
    return (f'<rect x="{x}" y="{f(y+h*0.8)}" width="{w}" height="{f(h*0.2)}" fill="#8592ab"/>'
            f'<rect x="{x}" y="{f(y+h*0.8)}" width="{w}" height="5" fill="#76839c"/>')




# ------------------------------------------------------------------------------------------------- hero B
def hero_crew():
    P, b = "hb", []
    cards = (("The prop master", "product-size", ("Measures the product in", "mm, by the holder's eyes."), "#e9eef5"),
             ("The set designer", "scene-set", ("One set for every shot,", "every still checked on it."), "#efe9f6"),
             ("The casting director", "recurring-cast", ("Keeps every character", "the same person."), "#e6f0ea"),
             ("The test audience", "blind-review", ("Fills in a questionnaire", "about every take; code", "grades it."), "#f4ece4"))
    for k, (role, skill, job, tint) in enumerate(cards):
        x, y, w = 24 + k * 212, 16, 196
        b.append(f'<rect x="{x}" y="{y}" width="{w}" height="348" rx="14" fill="#fff" stroke="{C["line"]}" stroke-width="1.5"/>')
        inner = f'<rect x="{x}" y="{y}" width="{w}" height="216" fill="{tint}"/>'
        stripes = "".join(f'<polygon points="{x+i*28},{y+18} {x+i*28+14},{y} {x+i*28+28},{y} {x+i*28+14},{y+18}" fill="#fff"/>'
                          for i in range(-1, 8))
        inner += f'<rect x="{x}" y="{y}" width="{w}" height="18" fill="{C["ink"]}"/>' + stripes
        cx, top = x + 98, y + 48
        if k == 0:
            inner += ana(P, cx, top, 0.66, turn=0.2, expr="grin", bottom=y + 230)
            inner += (f'<g transform="rotate(-28 {cx-30} {y+180})"><rect x="{cx-72}" y="{y+172}" width="86" height="15" rx="2" '
                      f'fill="#f2c94c" stroke="#c9a12c" stroke-width="1.2"/>'
                      + "".join(f'<line x1="{cx-68+i*8}" y1="{y+172}" x2="{cx-68+i*8}" y2="{y+(180 if i % 2 else 177)}" '
                                f'stroke="#7a6418" stroke-width="1.2"/>' for i in range(11)) + "</g>")
            inner += soda(cx + 18, y + 208, 24) + grip(cx + 18, y + 208, 24, 44, y + 216)
        elif k == 1:
            inner += jo(P, cx, top, 0.66, turn=-0.15, bottom=y + 230)
            px, py = cx - 40, y + 156
            inner += (f'<rect x="{px}" y="{py}" width="80" height="56" rx="3" fill="#fff" stroke="{C["line"]}" stroke-width="1.2" '
                      f'transform="rotate(-5 {cx} {py+28})"/>'
                      f'<g transform="rotate(-5 {cx} {py+28})"><rect x="{px+8}" y="{py+8}" width="64" height="40" fill="none" '
                      f'stroke="{C["ink"]}" stroke-width="1.4"/><rect x="{px+26}" y="{py+20}" width="28" height="14" rx="2" '
                      f'fill="{C["wood"]}" opacity="0.7"/><circle cx="{px+19}" cy="{py+27}" r="4" fill="{ANA}"/>'
                      f'<circle cx="{px+61}" cy="{py+27}" r="4" fill="{LEO}"/><line x1="{px+8}" y1="{py+27}" x2="{px+72}" '
                      f'y2="{py+27}" stroke="{C["amber"]}" stroke-width="1.4" stroke-dasharray="3 2"/>'
                      f'<path d="M{px+36},{py+46} l4,-7 l4,7 z" fill="{C["ink"]}"/></g>')
            inner += (f'<circle cx="{px+2}" cy="{py+40}" r="7" fill="#b97b53"/><circle cx="{px+78}" cy="{py+34}" r="7" fill="#b97b53"/>')
        elif k == 2:
            inner += leo(P, cx, top, 0.66, turn=-0.2, expr="smile", bottom=y + 230)
            px, py = cx - 26, y + 150
            photo = ana("hbp", cx - 2, py + 14, 0.3, bottom=py + 62)
            inner += (f'<rect x="{px}" y="{py}" width="52" height="64" rx="3" fill="#fff" stroke="{C["line"]}" stroke-width="1.2"/>'
                      + framed("hbq", px + 4, py + 4, 44, 46, f'<rect x="{px+4}" y="{py+4}" width="44" height="46" fill="#efe5d9"/>' + photo, r=2, stroke=0.8))
            inner += badge(px + 50, py + 4, True, 10)
            inner += f'<circle cx="{px-2}" cy="{py+46}" r="7" fill="#e9b590"/><circle cx="{px+54}" cy="{py+48}" r="7" fill="#e9b590"/>'
        else:
            inner += person(P, cx, top, 0.66, skin="light", hair="auburn", style="bun", shirt=MIA, turn=0.15, bottom=y + 230)
            px, py = cx - 34, y + 150
            inner += (f'<rect x="{px}" y="{py}" width="68" height="62" rx="4" fill="#c9a476"/>'
                      f'<rect x="{px+6}" y="{py+8}" width="56" height="50" rx="2" fill="#fff"/>'
                      f'<rect x="{px+24}" y="{py-4}" width="20" height="9" rx="2" fill="#8a8f99"/>')
            for i, on in enumerate((True, False, True)):
                yy = py + 18 + i * 14
                inner += (f'<rect x="{px+11}" y="{yy-6}" width="8" height="8" rx="1.5" fill="#fff" stroke="{C["ink"]}" stroke-width="1.2"/>'
                          f'<line x1="{px+24}" y1="{yy-2}" x2="{px+54}" y2="{yy-2}" stroke="{C["soft"]}" stroke-width="2" stroke-linecap="round"/>')
                if on:
                    inner += f'<path d="M{px+12},{yy-2} l2.5,2.5 l4,-5" stroke="{C["green"]}" stroke-width="1.8" fill="none"/>'
                else:
                    inner += f'<path d="M{px+12},{yy-5} l6,6 m0,-6 l-6,6" stroke="{C["red"]}" stroke-width="1.8"/>'
            inner += f'<circle cx="{px-2}" cy="{py+44}" r="7" fill="#f7d9c4"/><circle cx="{px+70}" cy="{py+40}" r="7" fill="#f7d9c4"/>'
        b.append(framed(P, x, y, w, 216, inner, bg=tint, r=14, stroke=0))
        b.append(f'<rect x="{x}" y="{y}" width="{w}" height="348" rx="14" fill="none" stroke="{C["line"]}" stroke-width="1.5"/>')
        b.append(T(x + 16, y + 246, role, 17, C["ink"], "l", weight=700))
        b.append(T(x + 16, y + 268, skill, 13, C["soft"], "m", weight=600))
        for i, ln in enumerate(job):
            b.append(T(x + 16, y + 296 + i * 19, ln, 13.5, C["ink"]))
    return svg(880, 380, "".join(b), "The crew as four cards: the prop master with a ruler and a can, the set designer "
               "with a floor plan, the casting director with a headshot, the test audience with a questionnaire.")


# ------------------------------------------------------------------------------------------------- prop B
def prop_overlay():
    P, b = "pb", []
    x0, y0, W, H = 24, 44, 252, 448
    s, cx, top = 1.8, x0 + 126, 66
    (lx, ly), (rx_, _) = eye_points(cx, top, s)
    px_mm = (rx_ - lx) / 63
    real, drawn = 48, 65
    wd, wr = drawn * px_mm, real * px_mm
    bx = cx + 20 - wd / 2
    yb = 472
    inner = ana(P, cx, top, s, bottom=y0 + H + 20) + serum(bx, yb, wd) + grip(bx, yb, wd, 2.1 * wd, y0 + H)
    b.append(T(24, 30, "One still, measured", 15, weight=700))
    b.append(framed(P, x0, y0, W, H, inner))
    rxl = bx + wd / 2 - wr / 2
    b.append(f'<rect x="{f(rxl)}" y="{f(yb-2.1*wr)}" width="{f(wr)}" height="{f(2.1*wr)}" rx="6" fill="none" '
             f'stroke="{C["green"]}" stroke-width="2.6" stroke-dasharray="6 4"/>')
    b.append(f'<line x1="{f(lx)}" y1="{f(ly)}" x2="{f(rx_)}" y2="{f(ly)}" stroke="{C["blue"]}" stroke-width="2.4"/>')
    for ex in (lx, rx_):
        b.append(f'<line x1="{f(ex)}" y1="{f(ly-9)}" x2="{f(ex)}" y2="{f(ly+9)}" stroke="{C["blue"]}" stroke-width="2.4"/>')
    b.append(f'<rect x="32" y="{f(ly-34)}" width="58" height="22" rx="11" fill="#fff" stroke="{C["blue"]}" stroke-width="1.5"/>')
    b.append(T(61, ly - 18, "63 mm", 13, C["blue"], "m", "middle", 700))
    b.append(f'<rect x="32" y="{f(yb-26)}" width="146" height="22" rx="11" fill="#fff" stroke="{C["green"]}" stroke-width="1.5"/>')
    b.append(T(105, yb - 10, "dashed: the real one", 12.5, C["green"], "l", "middle", 700))
    b.append(T(316, 60, "How it measures", 15, weight=700))
    steps = (("1", "Find the product", ("Open models find it by the name on your", "card (\"a skincare bottle\") and outline it.")),
             ("2", "Use the face as a ruler", ("Adult pupils sit about 63 mm apart, so the", "holder's eyes give the frame's scale.")),
             ("3", "Compare with the real size", ("65 mm wide in the still, 48 mm in real", "life: 1.35 times too big.")))
    for k, (n, head, lines) in enumerate(steps):
        y = 74 + k * 104
        b.append(f'<rect x="316" y="{y}" width="540" height="92" rx="12" fill="#fff" stroke="{C["line"]}" stroke-width="1.5"/>')
        b.append(f'<circle cx="344" cy="{y+30}" r="14" fill="{C["ink"]}"/>' + T(344, y + 35, n, 14, "#fff", "l", "middle", 800))
        b.append(T(370, y + 35, head, 15, C["ink"], "l", weight=700))
        for i, ln in enumerate(lines):
            b.append(T(370, y + 58 + i * 19, ln, 13.5, C["ink"]))
        ix = 776
        if k == 0:
            b.append(serum(ix, y + 80, 26) + f'<rect x="{ix-8}" y="{y+16}" width="42" height="70" rx="4" fill="none" '
                     f'stroke="{C["amber"]}" stroke-width="2" stroke-dasharray="4 3"/>')
        elif k == 1:
            b.append(f'<circle cx="{ix}" cy="{y+46}" r="5" fill="#2a2321"/><circle cx="{ix+44}" cy="{y+46}" r="5" fill="#2a2321"/>'
                     f'<line x1="{ix}" y1="{y+46}" x2="{ix+44}" y2="{y+46}" stroke="{C["blue"]}" stroke-width="2.2"/>'
                     + T(ix + 22, y + 72, "63 mm", 12, C["blue"], "m", "middle", 700))
        else:
            b.append(stamp(728, y + 46, "FAIL", "1.35×", False, rot=-4))
    b.append(f'<rect x="316" y="400" width="262" height="92" rx="10" fill="#fff" stroke="{C["line"]}" stroke-width="1.5"/>')
    b += [T(332, 422, "YOU GIVE", 11, C["soft"], "l", weight=700, ls=1.2),
          T(332, 446, 'what    = "a skincare bottle"', 12.5, font="m"), T(332, 468, "size_mm = [48, 101]", 12.5, font="m")]
    b.append(f'<rect x="594" y="400" width="262" height="92" rx="10" fill="{C["ink"]}"/>')
    b += [T(610, 422, "YOU GET", 11, "#9aa3b5", "l", weight=700, ls=1.2),
          T(610, 446, "FAIL bottle 65 mm wide", 12.5, "#ff8a84", "m", weight=700),
          T(610, 468, "real 48: 1.35× too big", 12.5, "#e6e9ef", "m")]
    return svg(880, 510, "".join(b), "product-size, explained in three steps on one still: Ana holds a skincare bottle "
               "drawn 65 mm wide; the dashed outline is the real 48 mm bottle at the same scale; her pupils, 63 mm "
               "apart, give the scale.")


# ------------------------------------------------------------------------------------------------- set helpers
def plan_box(b, title):
    def p(u, v):
        return 30 + u * 0.9667, 52 + v * 0.9667
    b.append(T(24, 30, title, 15, weight=700))
    x0, y0 = p(0, 0)
    x1, y1 = p(300, 300)
    b.append(f'<rect x="{x0}" y="{y0}" width="{x1-x0:.1f}" height="{y1-y0:.1f}" fill="#fff" stroke="{C["ink"]}" stroke-width="2"/>')
    return p


def cam_marks(b, p, cams, offsets):
    for name, ((cu, cv), (au, av), half) in cams.items():
        a = math.atan2(av - cv, au - cu)
        pts = [p(cu, cv)] + [p(cu + 185 * math.cos(a + d), cv + 185 * math.sin(a + d))
                             for d in (math.radians(half), math.radians(-half))]
        b.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="{C["amber"]}" opacity="0.10"/>')
    return lambda: [b.append(_cam(p, n, c, offsets[n])) for n, c in cams.items()]


def _cam(p, name, c, off):
    (cu, cv), (au, av), _ = c
    cx_, cy_ = p(cu, cv)
    a = math.atan2(av - cv, au - cu)
    tip = (cx_ + 12 * math.cos(a), cy_ + 12 * math.sin(a))
    bl = (cx_ - 8 * math.cos(a) + 8 * math.cos(a + math.pi / 2), cy_ - 8 * math.sin(a) + 8 * math.sin(a + math.pi / 2))
    br = (cx_ - 8 * math.cos(a) - 8 * math.cos(a + math.pi / 2), cy_ - 8 * math.sin(a) - 8 * math.sin(a + math.pi / 2))
    return (f'<path d="M{tip[0]:.1f},{tip[1]:.1f} L{bl[0]:.1f},{bl[1]:.1f} L{br[0]:.1f},{br[1]:.1f} Z" fill="{C["ink"]}"/>'
            + T(cx_ + off[0], cy_ + off[1], name, 14, C["ink"], "m", "middle", 700))


def dot(b, p, name, u, v, facing, col, label_dy):
    cx_, cy_ = p(u, v)
    a = math.radians(facing)
    nxp, nyp = cx_ + 18 * math.cos(a), cy_ + 18 * math.sin(a)
    l1 = (cx_ + 10 * math.cos(a + 0.6), cy_ + 10 * math.sin(a + 0.6))
    l2 = (cx_ + 10 * math.cos(a - 0.6), cy_ + 10 * math.sin(a - 0.6))
    b.append(f'<path d="M{l1[0]:.1f},{l1[1]:.1f} L{nxp:.1f},{nyp:.1f} L{l2[0]:.1f},{l2[1]:.1f} Z" fill="{C["ink"]}"/>')
    b.append(f'<circle cx="{cx_:.1f}" cy="{cy_:.1f}" r="12" fill="{col}" stroke="#fff" stroke-width="2"/>')
    b.append(T(cx_, cy_ + label_dy, name, 13, col, "l", "middle", 700))


def card_and_terminal(b, card_title, card_lines, cmd, out1, out2):
    b.append(f'<rect x="20" y="372" width="312" height="116" rx="10" fill="#fff" stroke="{C["line"]}" stroke-width="1.5"/>')
    b.append(T(34, 394, card_title, 11, C["soft"], "l", weight=700, ls=1.2))
    for k, ln in enumerate(card_lines):
        b.append(T(34, 418 + k * 19, ln, 13, font="m"))
    b.append(f'<rect x="376" y="404" width="440" height="84" rx="10" fill="{C["ink"]}"/>')
    b.append(T(392, 428, cmd, 12.5, "#9aa3b5", "m"))
    b.append(T(392, 450, out1, 12.5, "#ff8a84", "m", weight=700))
    b.append(T(392, 470, out2, 12.5, "#e6e9ef", "m"))


def verdicts(b, xs, rows):
    for x, (ok, l1, l2) in zip(xs, rows):
        b.append(stamp(x + 4, 302, "PASS" if ok else "FAIL", "", ok))
        b.append(T(x + 2, 362, l1, 13.5, C["ink"], "l", weight=600))
        if l2:
            b.append(T(x + 2, 380, l2, 13.5, C["ink"], "l", weight=600))


# ------------------------------------------------------------------------------------------------- set B
def set_couch():
    P, b = "sb", []
    p = plan_box(b, "One set file, seen from the top")
    x0, y0 = p(0, 0)
    tv0, tv1 = p(0, 112)[1], p(0, 188)[1]
    b.append(f'<line x1="{x0+4}" y1="{tv0:.1f}" x2="{x0+4}" y2="{tv1:.1f}" stroke="#2a2f38" stroke-width="9"/>')
    b.append(T(x0 + 14, tv1 + 18, "TV", 13, C["ink"], "l", weight=700))
    wx0, wx1 = p(150, 0)[0], p(270, 0)[0]
    b.append(f'<line x1="{wx0:.1f}" y1="{y0}" x2="{wx1:.1f}" y2="{y0}" stroke="{C["blue"]}" stroke-width="7"/>')
    b.append(T(wx0, y0 + 18, "window", 12, C["blue"], "l", weight=600))
    cams = {"W": ((70, 272), (234, 150), 26), "C": ((140, 236), (234, 150), 12)}
    draw_cams = cam_marks(b, p, cams, {"W": (-16, 6), "C": (0, 26)})
    c0, c1 = p(210, 70), p(262, 230)
    b.append(f'<rect x="{c0[0]:.1f}" y="{c0[1]:.1f}" width="{c1[0]-c0[0]:.1f}" height="{c1[1]-c0[1]:.1f}" rx="12" fill="#c7cfdc" stroke="#9aa6bd" stroke-width="1.5"/>')
    t0, t1 = p(112, 122), p(164, 178)
    b.append(f'<rect x="{t0[0]:.1f}" y="{t0[1]:.1f}" width="{t1[0]-t0[0]:.1f}" height="{t1[1]-t0[1]:.1f}" rx="8" fill="{C["wood"]}" opacity="0.55" stroke="{C["wood2"]}" stroke-width="1.5"/>')
    for cu, cv in ((128, 140), (148, 160)):
        cx_, cy_ = p(cu, cv)
        b.append(f'<circle cx="{cx_:.1f}" cy="{cy_:.1f}" r="5" fill="#d8463a" stroke="#fff" stroke-width="1.5"/>')
    tvc = p(6, 150)
    for v in (100, 150, 200):
        a = p(220, v)
        b.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{tvc[0]:.1f}" y2="{tvc[1]:.1f}" stroke="{C["green"]}" stroke-width="1.8" stroke-dasharray="5 4"/>')
    b.append(T(x0 + 12, p(0, 98)[1], "everyone watches the TV", 17, C["green"], "h", "start", 700))
    dot(b, p, "Jo", 236, 100, 180, JO, 4 - 26)
    dot(b, p, "Ana", 236, 150, 180, ANA, 30)
    dot(b, p, "Leo", 236, 200, 180, LEO, 30)
    draw_cams()
    b.append(T(376, 22, "green: what the set expects · red: what the model drew", 12.5, C["soft"]))
    W, H, y = 136, 242, 48
    xs = (376, 528, 680)
    for x, cap in zip(xs, ("camera W", "camera W, next shot", "camera W, later")):
        b.append(T(x, 40, cap, 13, C["soft"], "l", weight=600))
    def couch_shot(x, order, ana_turn=-0.65):
        inner = room(x, y, W, H, "back") + couch_back(x, y, W, H)
        spots = ((x + 30, y + 104, 0.34), (x + 70, y + 104, 0.38), (x + 108, y + 98, 0.43))
        for who, (cx, top, s) in zip(order, spots):
            fn = {"Jo": jo, "Ana": ana, "Leo": leo}[who]
            inner += fn(P, cx, top, s, turn=(ana_turn if who == "Ana" else -0.65), bottom=y + H)
        return inner + couch_seat(x, y, W, H)
    b.append(framed(P, xs[0], y, W, H, couch_shot(xs[0], ("Jo", "Ana", "Leo"))))
    for k, (cx, cy) in enumerate(((xs[0] + 22, y + 124), (xs[0] + 62, y + 126), (xs[0] + 98, y + 122))):
        b.append(arrow(cx, cy, cx - 13, cy, C["green"], 2.2, head=6))
    b.append(framed(P, xs[1], y, W, H, couch_shot(xs[1], ("Jo", "Ana", "Leo"), ana_turn=0.0)))
    b.append(ring(xs[1] + 70, y + 132, 22, 26, 0))
    b.append(framed(P, xs[2], y, W, H, couch_shot(xs[2], ("Leo", "Ana", "Jo"))))
    b.append(curve(xs[2] + 28, y + 84, xs[2] + 68, y + 50, xs[2] + 108, y + 80, C["red"], 2.6))
    b.append(T(xs[2] + 68, y + 46, "swapped", 18, C["red"], "h", "middle", 700))
    verdicts(b, xs, ((True, "all eyes on the TV,", "off screen left"), (False, "Ana looks into", "the lens"),
                     (False, "Jo and Leo", "swapped seats")))
    card_and_terminal(b, "PROMPT CARD · CAMERA W", ("35 mm, from the corner.", "Jo, Ana, Leo on the couch, all",
                                                    "look screen-left at the TV.", "Window behind them."),
                      "$ frame_check.py set.toml W still_W2.png", "FAIL eyelines  ana should look screen-left,",
                      "               looks into the lens")
    return svg(880, 500, "".join(b), "scene-set: a top plan where Jo, Ana and Leo sit on a couch and all watch a TV on "
               "the left wall; the wide where everyone looks at the TV passes, a still where Ana looks into the lens "
               "fails, a still where Jo and Leo swapped seats fails.")


# ------------------------------------------------------------------------------------------------- cast A
def cast_rank():
    P, b = "ca", []
    def portrait(x, y, pw, ph, bg, fn, s, **kw):
        inner = f'<rect x="{x}" y="{y}" width="{pw}" height="{ph}" fill="{bg}"/>' + fn(P, x + pw / 2, y + 22, s, bottom=y + ph + 10, **kw)
        return framed(P, x, y, pw, ph, inner, bg=bg, r=10, stroke=1.6)
    for rot, dx, bg, kw in ((-11, -34, "#dfe8f3", dict(turn=-0.4)), (11, 36, "#e4efe6", dict(turn=0.4, expr="grin")),
                            (0, 0, "#efe5d9", dict())):
        cx_, cy_ = 120 + dx, 150
        b.append(f'<g transform="rotate({rot} {cx_} {cy_})"><rect x="{cx_-52}" y="{cy_-68}" width="104" height="132" rx="6" '
                 f'fill="#fff" stroke="{C["line"]}" stroke-width="1.5"/>' + portrait(cx_ - 46, cy_ - 62, 92, 100, bg, ana, 0.5, **kw) + "</g>")
    b.append(T(120, 252, "Real photos of Ana", 14, C["ink"], "l", "middle", 700))
    b.append(T(120, 270, "5–20 per person", 13, C["soft"], "l", "middle"))
    for i in range(10):
        for j in range(3):
            shade = ("#2a66d9", "#5d8ae3", "#9db7ef", "#c9d8f6")[(i * 7 + j * 3) % 4]
            b.append(f'<rect x="{232+i*8}" y="{106+j*8}" width="6" height="6" rx="1" fill="{shade}"/>')
    b += [T(271, 148, "face model", 13, C["ink"], "l", "middle", 700), arrow(226, 160, 318, 160, C["blue"], 2.2),
          T(271, 180, "512 numbers", 12, C["soft"], "l", "middle"), T(271, 195, "per face", 12, C["soft"], "l", "middle")]
    b.append(T(340, 34, "New stills from the image model", 15, weight=700))
    items = ((ana, dict(turn=0.45), "0.71", "same person", True),
             (ana, dict(turn=-0.4, expr="grin"), "0.66", "same person", True),
             (ana, dict(w=1.16, gap=0.8, nose="long", brows="thick", expr="neutral", blush=False), "0.41", "a lookalike", False),
             (person, dict(skin="tan", hair="blonde", style="long", shirt=ANA, w=1.04), "0.22", "someone else", False))
    for k, (fn, kw, score, verdict, ok) in enumerate(items):
        x = 340 + k * 130
        b.append(portrait(x, 50, 116, 146, ("#e6edf6", "#ece6f3", "#e6eef0", "#efe9e2")[k], fn, 0.6, **kw))
        b.append(badge(x + 104, 58, ok, 12))
        b.append(T(x + 58, 226, score, 24, C["green"] if ok else C["red"], "m", "middle", 800))
        b.append(T(x + 58, 246, verdict, 13.5, C["ink"], "l", "middle", 600))
    b.append(f'<line x1="593" y1="44" x2="593" y2="256" stroke="{C["blue"]}" stroke-width="2" stroke-dasharray="6 5"/>')
    b.append(f'<rect x="513" y="266" width="160" height="26" rx="13" fill="{C["bluebg"]}"/>')
    b += [T(593, 284, "threshold 0.52", 13, C["blue"], "m", "middle", 700),
          T(593, 310, "set on stills you approved and rejected", 13, C["soft"], "l", "middle")]
    b.append(f'<line x1="24" y1="336" x2="856" y2="336" stroke="{C["line"]}" stroke-width="1.5"/>')
    b += [T(24, 366, "keepface", 15, weight=700), T(24, 386, "An edit may add glasses.", 13, C["soft"]),
          T(24, 404, "It must not touch the eyes.", 13, C["soft"])]
    for k, (kw, label, ok) in enumerate(((dict(), "Base still", None), (dict(glasses=True, eyes="narrow", brows="thick"), "Edit: add glasses", False),
                                         (dict(glasses=True), "keepface", True))):
        x = 250 + k * 210
        b.append(portrait(x, 356, 128, 134, "#e8edf4", ana, 0.72, **kw))
        b.append(T(x + 64, 510, label, 13.5, C["ink"], "l", "middle", 700))
        if ok is not None:
            b.append(badge(x + 116, 364, ok, 12))
        if k < 2:
            b.append(arrow(x + 138, 423, x + 200, 423, C["ink"], 2))
    (l1, l2) = eye_points(460 + 64, 356 + 22, 0.72)
    b.append(ring((l1[0] + l2[0]) / 2, l1[1], 32, 13, 0))
    b += [T(460 + 64, 346, "eyes redrawn", 19, C["red"], "h", "middle", 700),
          T(670 + 64, 346, "her eyes back", 19, C["green"], "h", "middle", 700)]
    return svg(880, 528, "".join(b), "recurring-cast: real photos of Ana go through a face model; two new stills of Ana "
               "score 0.71 and 0.66, a lookalike scores 0.41 and a different woman 0.22, split by a threshold of 0.52; "
               "below, keepface puts Ana's eyes back after an edit that added glasses redrew them.")


# ------------------------------------------------------------------------------------------------- test B
def test_why():
    P, b = "tb", []
    def still(x, y):
        inner = room(x, y, 120, 168, None) + soda(x + 36, y + 156, 40) + grip(x + 36, y + 156, 40, 74, y + 168, fingers=5)
        return framed(P, x, y, 120, 168, inner)
    for col, x0, head in ((C["red"], 24, "Ask \"does this look right?\""), (C["green"], 456, "Ask a question with fixed answers")):
        b.append(f'<rect x="{x0}" y="20" width="400" height="390" rx="14" fill="#fff" stroke="{C["line"]}" stroke-width="1.5"/>')
        b.append(T(x0 + 20, 50, head, 16, C["ink"], "l", weight=700))
        b.append(still(x0 + 20, 70))
    # left: the open question misses it
    b.append(f'<rect x="164" y="84" width="240" height="88" rx="12" fill="{C["paper"]}"/>')
    b += [T(180, 108, "Reviewer:", 12, C["soft"], "l", weight=700), T(180, 132, "\"Looks great! The can and", 13.5, C["ink"]),
          T(180, 152, "the hand look natural.\"", 13.5, C["ink"])]
    b.append(ring(84, 196, 40, 34))
    b.append(T(164, 214, "six fingers, missed", 21, C["red"], "h", weight=700))
    b += [T(44, 284, "The model judges the whole picture at once,", 13.5, C["ink"]),
          T(44, 304, "and a still that looks fine at a glance passes.", 13.5, C["ink"])]
    b.append(stamp(44, 334, "MISSED", "", False))
    # right: the fixed question catches it
    b.append(T(612, 96, "How many fingers on the hand", 13.5, C["ink"], "l", weight=600))
    b.append(T(612, 115, "around the can?", 13.5, C["ink"], "l", weight=600))
    ox = 612
    for o in ("4", "5", "6", "can't tell"):
        on = o == "6"
        colr = C["red"] if on else C["soft"]
        b.append(f'<circle cx="{ox+7}" cy="{142}" r="7" fill="#fff" stroke="{colr}" stroke-width="1.7"/>')
        if on:
            b.append(f'<circle cx="{ox+7}" cy="142" r="3.8" fill="{colr}"/>')
        b.append(T(ox + 19, 147, o, 13, colr, "l", weight=700 if on else 400))
        ox += 19 + 7.2 * len(o) + 14
    b += [T(612, 186, "accepted: 5", 13, C["soft"], "m"), T(612, 206, "answer:   6", 13, C["red"], "m", weight=700)]
    b.append(ring(516, 196, 40, 34, col=C["red"]))
    b += [T(476, 284, "A narrow question about one thing, with fixed", 13.5, C["ink"]),
          T(476, 304, "answers. Code compares, no one argues.", 13.5, C["ink"])]
    b.append(stamp(476, 334, "CAUGHT", "", True))
    b.append(T(440, 448, "46 questions like this one: faces · the set · hands · the product · logos · acting · sound · story", 14.5, C["ink"], "l", "middle", 700))
    return svg(880, 470, "".join(b), "blind-review: the same still of a hand with six fingers on a can; asked whether it "
               "looks right, the reviewer says it looks great and misses it; asked how many fingers there are with "
               "fixed answers, it answers six and code catches it.")


# ------------------------------------------------------------------------------------------------- icon and social card
def icon():
    """The plugin icon: a clapper over a checked frame."""
    b = [f'<rect width="512" height="512" rx="104" fill="{C["ink"]}"/>']
    stripes = "".join(f'<polygon points="{60+i*56},126 {88+i*56},70 {116+i*56},70 {88+i*56},126" fill="#fff"/>'
                      for i in range(7))
    b.append(f'<g transform="rotate(-9 70 126)"><rect x="60" y="70" width="392" height="56" rx="10" fill="#2c3443"/>'
             f'{stripes}</g>')
    inner = f'<rect x="156" y="170" width="200" height="290" fill="#e8edf4"/>' + ana("ic", 256, 222, 1.45, bottom=500)
    b.append(framed("ic", 156, 170, 200, 290, inner, r=22, stroke=0))
    b.append(badge(352, 180, True, 40))
    return ('<svg viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="ai-film-crew">'
            + "".join(b) + "</svg>")


def social():
    """The 1280x640 card GitHub shows when the repo link is shared."""
    crew = hero_crew().replace('<svg class="pic" viewBox="0 0 880 380"',
                               '<svg x="258" y="276" width="764" height="330" viewBox="0 0 880 380"', 1)
    return (f'<svg viewBox="0 0 1280 640" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="ai-film-crew">'
            f'<rect width="1280" height="640" fill="{C["paper"]}"/>'
            + T(640, 118, "ai-film-crew", 76, C["ink"], "l", "middle", 800)
            + T(640, 182, "Agent skills that catch what AI video gets wrong,", 30, C["soft"], "l", "middle", 500)
            + T(640, 224, "on the stills, before you pay for the video.", 30, C["soft"], "l", "middle", 500)
            + crew + "</svg>")
