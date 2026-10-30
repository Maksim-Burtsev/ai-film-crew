"""Friendlier flat people and props for the README pictures: dot eyes with a highlight, soft smiles, a few hair
styles, glasses and beards; turn (-1..1) turns the head so the gaze reads from the whole face."""
import math
from draw import C, uid

SKIN = {"light": ("#f7d9c4", "#e2b192"), "tan": ("#e9b590", "#cd936d"), "brown": ("#b97b53", "#985f3e"),
        "deep": ("#83553a", "#683f29")}
HAIR = {"brown": "#5a3826", "black": "#26201c", "blonde": "#e0b55f", "auburn": "#a4472a", "grey": "#b7bac0",
        "chestnut": "#8a5634"}
EYE, LIPC, GLASS = "#2a2321", "#b4544c", "#1f2430"
ANA, LEO, JO, SAM = "#e07a3f", "#3f8f6a", "#8b5cc4", "#3f6fb5"     # shirt colours of the recurring cast


def f(v):
    return f"{v:.1f}"


def brow_colour(hc):
    return {HAIR["blonde"]: "#a37b33", HAIR["grey"]: "#8c9097"}.get(hc, hc)


def eye_points(cx, top, s, turn=0.0, gap=1.0):
    hx, hy = cx + turn * 4 * s, top + 60 * s
    fx = hx + turn * 24 * s
    g = 13.5 * s * gap * (1 - 0.38 * abs(turn))
    return (fx - g, hy + 2 * s), (fx + g, hy + 2 * s)


def person(pid, cx, top, s, skin="light", hair="brown", style="ponytail", shirt=ANA, turn=0.0, expr="smile",
           glasses=False, beard=None, w=1.0, gap=1.0, nose="soft", brows="soft", eyes="dot", temple_left=True,
           shade=None, earrings=False, bottom=None, blush=True):
    sk, sk2 = SKIN[skin]
    hc = HAIR.get(hair, hair)
    hx, hy = cx + turn * 4 * s, top + 60 * s
    rx, ry = 39 * s * w, 48 * s
    fx = hx + turn * 24 * s
    bot = bottom if bottom is not None else top + 250 * s
    o = []
    if style == "long":
        o.append(f'<path d="M{f(hx-rx-8*s)},{f(hy-10*s)} C{f(hx-rx-12*s)},{f(hy+36*s)} {f(hx-rx-10*s)},{f(hy+70*s)} '
                 f'{f(hx-rx+2*s)},{f(hy+86*s)} Q{f(hx)},{f(hy+96*s)} {f(hx+rx-2*s)},{f(hy+86*s)} C{f(hx+rx+10*s)},'
                 f'{f(hy+70*s)} {f(hx+rx+12*s)},{f(hy+36*s)} {f(hx+rx+8*s)},{f(hy-10*s)} Z" fill="{hc}"/>')
    elif style == "ponytail":
        side = -1 if turn > 0.15 else 1
        tx, ty = hx + side * (rx + 4 * s), hy + 14 * s
        o.append(f'<ellipse cx="{f(tx)}" cy="{f(ty)}" rx="{f(10*s)}" ry="{f(27*s)}" fill="{hc}" '
                 f'transform="rotate({-side*16} {f(tx)} {f(ty)})"/>')
    elif style == "bun":
        o.append(f'<circle cx="{f(hx+3*s)}" cy="{f(hy-ry-4*s)}" r="{f(15*s)}" fill="{hc}"/>')
    o.append(f'<path d="M{f(cx-68*s)},{f(bot)} C{f(cx-68*s)},{f(top+136*s)} {f(cx-46*s)},{f(top+112*s)} {f(cx)},'
             f'{f(top+112*s)} C{f(cx+46*s)},{f(top+112*s)} {f(cx+68*s)},{f(top+136*s)} {f(cx+68*s)},{f(bot)} Z" fill="{shirt}"/>')
    o.append(f'<path d="M{f(cx-15*s)},{f(top+112*s)} Q{f(cx)},{f(top+131*s)} {f(cx+15*s)},{f(top+112*s)} Z" fill="{sk2}"/>')
    o.append(f'<rect x="{f(cx-10*s)}" y="{f(hy+30*s)}" width="{f(20*s)}" height="{f((top+114*s)-(hy+30*s))}" fill="{sk2}"/>')
    for side, show in ((-1, turn > -0.35), (1, turn < 0.35)):
        if show:
            ex_ = hx + side * (rx - 1 * s) - turn * 3 * s
            o.append(f'<ellipse cx="{f(ex_)}" cy="{f(hy+6*s)}" rx="{f(6*s)}" ry="{f(9*s)}" fill="{sk2}"/>')
            if earrings:
                o.append(f'<circle cx="{f(ex_)}" cy="{f(hy+17*s)}" r="{f(2.8*s)}" fill="#e7b443"/>')
    o.append(f'<ellipse cx="{f(hx)}" cy="{f(hy)}" rx="{f(rx)}" ry="{f(ry)}" fill="{sk}"/>')
    if shade:
        cid = uid(pid + "s")
        sx = hx - rx if shade == "left" else hx
        o.append(f'<clipPath id="{cid}"><ellipse cx="{f(hx)}" cy="{f(hy)}" rx="{f(rx)}" ry="{f(ry)}"/></clipPath>'
                 f'<rect x="{f(sx)}" y="{f(hy-ry)}" width="{f(rx)}" height="{f(2*ry)}" fill="#6b3a22" opacity="0.15" '
                 f'clip-path="url(#{cid})"/>')
    ey = hy + 2 * s
    g = 13.5 * s * gap * (1 - 0.38 * abs(turn))
    if blush:
        for sg in (-1, 1):
            o.append(f'<circle cx="{f(fx+sg*(g+6*s))}" cy="{f(ey+12*s)}" r="{f(5.5*s)}" fill="#ef8a80" opacity="0.28"/>')
    if style in ("ponytail", "long", "bun"):
        pt = hx + 12 * s + turn * 8 * s
        o.append(f'<path d="M{f(hx-rx-2*s)},{f(hy+6*s)} C{f(hx-rx-5*s)},{f(hy-42*s)} {f(hx-16*s)},{f(hy-58*s)} '
                 f'{f(hx+6*s)},{f(hy-55*s)} C{f(hx+32*s)},{f(hy-52*s)} {f(hx+rx+5*s)},{f(hy-36*s)} {f(hx+rx+2*s)},'
                 f'{f(hy+6*s)} C{f(hx+rx-3*s)},{f(hy-14*s)} {f(hx+rx-16*s)},{f(hy-24*s)} {f(pt)},{f(hy-27*s)} '
                 f'C{f(hx-4*s)},{f(hy-30*s)} {f(hx-rx+10*s)},{f(hy-24*s)} {f(hx-rx-2*s)},{f(hy+6*s)} Z" fill="{hc}"/>')
    elif style == "short":
        o.append(f'<path d="M{f(hx-rx-1*s)},{f(hy-4*s)} C{f(hx-rx-3*s)},{f(hy-46*s)} {f(hx-12*s)},{f(hy-60*s)} '
                 f'{f(hx+8*s)},{f(hy-57*s)} C{f(hx+34*s)},{f(hy-55*s)} {f(hx+rx+4*s)},{f(hy-40*s)} {f(hx+rx+1*s)},'
                 f'{f(hy-4*s)} C{f(hx+rx-4*s)},{f(hy-22*s)} {f(hx+rx-12*s)},{f(hy-30*s)} {f(hx+16*s)},{f(hy-33*s)} '
                 f'C{f(hx-2*s)},{f(hy-35*s)} {f(hx-rx+9*s)},{f(hy-28*s)} {f(hx-rx-1*s)},{f(hy-4*s)} Z" fill="{hc}"/>')
    elif style == "curly":
        o.append(f'<ellipse cx="{f(hx)}" cy="{f(hy-32*s)}" rx="{f(rx+3*s)}" ry="{f(17*s)}" fill="{hc}"/>')
        for k in range(10):
            a = math.radians(185 + k * 18.9)
            o.append(f'<circle cx="{f(hx+(rx+1*s)*math.cos(a))}" cy="{f(hy-10*s+ry*0.92*math.sin(a))}" '
                     f'r="{f(11.5*s)}" fill="{hc}"/>')
    bc = brow_colour(hc)
    bw = (3.6 if brows == "thick" else 2.3) * s
    for sg in (-1, 1):
        ex = fx + sg * g
        o.append(f'<path d="M{f(ex-6.5*s)},{f(ey-9.5*s)} Q{f(ex)},{f(ey-13.5*s)} {f(ex+6.5*s)},{f(ey-10*s)}" '
                 f'stroke="{bc}" stroke-width="{f(bw)}" fill="none" stroke-linecap="round"/>')
        if eyes == "dot":
            o.append(f'<ellipse cx="{f(ex)}" cy="{f(ey)}" rx="{f(3.3*s)}" ry="{f(4.3*s)}" fill="{EYE}"/>'
                     f'<circle cx="{f(ex+1.1*s)}" cy="{f(ey-1.4*s)}" r="{f(max(0.5, 1.15*s))}" fill="#fff"/>')
        else:
            o.append(f'<ellipse cx="{f(ex)}" cy="{f(ey+0.6*s)}" rx="{f(4.2*s)}" ry="{f(1.5*s)}" fill="{EYE}"/>'
                     f'<path d="M{f(ex-5.8*s)},{f(ey-2*s)} Q{f(ex)},{f(ey-5.2*s)} {f(ex+5.8*s)},{f(ey-2*s)}" '
                     f'stroke="{EYE}" stroke-width="{f(1.7*s)}" fill="none" stroke-linecap="round"/>')
    nx, ny = fx + turn * 5 * s, ey + 14 * s
    nwid = 5.0 if nose == "wide" else 3.3
    if nose == "long":
        o.append(f'<path d="M{f(nx+turn*2*s)},{f(ey+2*s)} L{f(nx+(2.5 if turn >= 0 else -2.5)*s)},{f(ny-1*s)}" '
                 f'stroke="{sk2}" stroke-width="{f(2*s)}" stroke-linecap="round"/>')
    if abs(turn) > 0.25:
        sd = 1 if turn > 0 else -1
        o.append(f'<path d="M{f(nx)},{f(ey+3*s)} L{f(nx+sd*6*s)},{f(ny-0.5*s)} L{f(nx+sd*0.5*s)},{f(ny+1.8*s)}" '
                 f'stroke="{sk2}" stroke-width="{f(2.2*s)}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    else:
        o.append(f'<path d="M{f(nx-nwid*s)},{f(ny)} Q{f(nx)},{f(ny+3.8*s)} {f(nx+nwid*s)},{f(ny)}" stroke="{sk2}" '
                 f'stroke-width="{f(2.2*s)}" fill="none" stroke-linecap="round"/>')
    my = ey + 25 * s
    if beard:
        op = 1 if beard == "full" else 0.22
        o.append(f'<path d="M{f(hx-rx+3*s)},{f(hy+4*s)} C{f(hx-rx+3*s)},{f(hy+44*s)} {f(hx-14*s)},{f(hy+54*s)} '
                 f'{f(hx)},{f(hy+54*s)} C{f(hx+14*s)},{f(hy+54*s)} {f(hx+rx-3*s)},{f(hy+44*s)} {f(hx+rx-3*s)},'
                 f'{f(hy+4*s)} C{f(hx+rx-6*s)},{f(hy+20*s)} {f(fx+13*s)},{f(my-3*s)} {f(fx)},{f(my-4*s)} '
                 f'C{f(fx-13*s)},{f(my-3*s)} {f(hx-rx+6*s)},{f(hy+20*s)} {f(hx-rx+3*s)},{f(hy+4*s)} Z" '
                 f'fill="{hc}" opacity="{op}"/>')
    if expr == "grin":
        o.append(f'<path d="M{f(fx-9*s)},{f(my-1*s)} Q{f(fx)},{f(my+12*s)} {f(fx+9*s)},{f(my-1*s)} '
                 f'Q{f(fx)},{f(my+2*s)} {f(fx-9*s)},{f(my-1*s)} Z" fill="#9f3f39"/>')
    elif expr == "neutral":
        o.append(f'<path d="M{f(fx-6*s)},{f(my+2*s)} Q{f(fx)},{f(my+3.5*s)} {f(fx+6*s)},{f(my+2*s)}" stroke="{LIPC}" '
                 f'stroke-width="{f(2.4*s)}" fill="none" stroke-linecap="round"/>')
    else:
        k = 1.0 if expr == "smile" else 0.75
        o.append(f'<path d="M{f(fx-8*k*s)},{f(my)} Q{f(fx)},{f(my+7.5*k*s)} {f(fx+8*k*s)},{f(my)}" stroke="{LIPC}" '
                 f'stroke-width="{f(2.5*s)}" fill="none" stroke-linecap="round"/>')
    if glasses:
        sw = max(1.2, 2.1 * s)
        el, er = fx - g, fx + g
        for ex in (el, er):
            o.append(f'<circle cx="{f(ex)}" cy="{f(ey)}" r="{f(8.6*s)}" fill="#fff" fill-opacity="0.12" '
                     f'stroke="{GLASS}" stroke-width="{f(sw)}"/>')
        o.append(f'<path d="M{f(el+8.6*s)},{f(ey-1*s)} Q{f(fx)},{f(ey-4*s)} {f(er-8.6*s)},{f(ey-1*s)}" stroke="{GLASS}" '
                 f'stroke-width="{f(sw)}" fill="none"/>')
        if temple_left:
            o.append(f'<line x1="{f(el-8.6*s)}" y1="{f(ey-1*s)}" x2="{f(hx-rx+1*s)}" y2="{f(ey-3*s)}" stroke="{GLASS}" '
                     f'stroke-width="{f(sw)}"/>')
        o.append(f'<line x1="{f(er+8.6*s)}" y1="{f(ey-1*s)}" x2="{f(hx+rx-1*s)}" y2="{f(ey-3*s)}" stroke="{GLASS}" '
                 f'stroke-width="{f(sw)}"/>')
    return "".join(o)


# the recurring cast, so every picture shows the same people
def ana(pid, cx, top, s, **kw):
    a = dict(skin="light", hair="brown", style="ponytail", shirt=ANA, earrings=True)
    a.update(kw)
    return person(pid, cx, top, s, **a)


def leo(pid, cx, top, s, **kw):
    a = dict(skin="tan", hair="black", style="short", shirt=LEO, glasses=True, beard="stubble")
    a.update(kw)
    return person(pid, cx, top, s, **a)


def jo(pid, cx, top, s, **kw):
    a = dict(skin="brown", hair="black", style="curly", shirt=JO)
    a.update(kw)
    return person(pid, cx, top, s, **a)


def soda(x, yb, w):
    h = 1.85 * w
    y = yb - h
    return (f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(w*0.13)}" fill="#d8463a"/>'
            f'<path d="M{f(x)},{f(y+h*0.46)} C{f(x+w*0.35)},{f(y+h*0.37)} {f(x+w*0.65)},{f(y+h*0.57)} {f(x+w)},'
            f'{f(y+h*0.47)} L{f(x+w)},{f(y+h*0.6)} C{f(x+w*0.65)},{f(y+h*0.69)} {f(x+w*0.35)},{f(y+h*0.5)} {f(x)},'
            f'{f(y+h*0.59)} Z" fill="#fff"/>'
            f'<ellipse cx="{f(x+w/2)}" cy="{f(y+w*0.07)}" rx="{f(w/2)}" ry="{f(w*0.1)}" fill="#cfd5de"/>'
            f'<rect x="{f(x+w*0.1)}" y="{f(y+h*0.08)}" width="{f(w*0.1)}" height="{f(h*0.84)}" rx="2" fill="#fff" opacity="0.22"/>')


def serum(x, yb, w):
    h = 2.1 * w
    y = yb - h
    body = "#7fbfaa"
    return (f'<rect x="{f(x)}" y="{f(y+h*0.2)}" width="{f(w)}" height="{f(h*0.8)}" rx="{f(w*0.2)}" fill="{body}"/>'
            f'<rect x="{f(x)}" y="{f(y+h*0.45)}" width="{f(w)}" height="{f(h*0.3)}" fill="#fff" opacity="0.92"/>'
            f'<rect x="{f(x+w*0.18)}" y="{f(y+h*0.52)}" width="{f(w*0.64)}" height="{f(h*0.05)}" rx="1.5" fill="{body}"/>'
            f'<rect x="{f(x+w*0.28)}" y="{f(y+h*0.61)}" width="{f(w*0.44)}" height="{f(h*0.035)}" rx="1.5" fill="{body}" opacity="0.6"/>'
            f'<rect x="{f(x+w*0.33)}" y="{f(y+h*0.1)}" width="{f(w*0.34)}" height="{f(h*0.11)}" fill="#e6ebef"/>'
            f'<rect x="{f(x+w*0.2)}" y="{f(y)}" width="{f(w*0.6)}" height="{f(h*0.1)}" rx="{f(w*0.08)}" fill="#2a2f38"/>'
            f'<rect x="{f(x+w*0.74)}" y="{f(y+h*0.02)}" width="{f(w*0.3)}" height="{f(h*0.035)}" rx="1" fill="#2a2f38"/>'
            f'<rect x="{f(x+w*0.1)}" y="{f(y+h*0.25)}" width="{f(w*0.1)}" height="{f(h*0.68)}" rx="2" fill="#fff" opacity="0.25"/>')


def grip(x, yb, w, h, fb, skin="light", fingers=3):
    sk, sk2 = SKIN[skin]
    hy = yb - h * 0.36
    fh = max(5.0, h * 0.1)
    o = [f'<line x1="{f(x+w*0.95)}" y1="{f(hy+fh)}" x2="{f(x+w+55)}" y2="{f(fb+40)}" stroke="{sk}" '
         f'stroke-width="{f(max(14, w*0.62))}" stroke-linecap="round"/>',
         f'<ellipse cx="{f(x+w*0.98)}" cy="{f(hy)}" rx="{f(w*0.3)}" ry="{f(fh*2.1)}" fill="{sk}"/>']
    for i in range(fingers):
        fy = hy - 1.55 * fh + i * 1.06 * fh
        o.append(f'<rect x="{f(x-w*0.05)}" y="{f(fy)}" width="{f(w*1.0)}" height="{f(fh*0.98)}" rx="{f(fh/2)}" '
                 f'fill="{sk}" stroke="{sk2}" stroke-width="1.2"/>')
    o.append(f'<rect x="{f(x-w*0.12)}" y="{f(hy-2.75*fh)}" width="{f(w*0.42)}" height="{f(fh*0.95)}" rx="{f(fh/2)}" '
             f'fill="{sk}" stroke="{sk2}" stroke-width="1.2" transform="rotate(-24 {f(x+w*0.08)} {f(hy-2.3*fh)})"/>')
    return "".join(o)


def ring(cx, cy, rx, ry, rot=-8, col=None, w=3.0):
    """A grease-pencil ellipse: a little more than one turn, so the ends overlap like a hand-drawn mark."""
    pts = []
    for i in range(0, 385, 8):
        a = math.radians(i)
        j = 1 + 0.045 * math.sin(i * 0.05) + (0.06 if i > 360 else 0)
        pts.append((cx + rx * j * math.cos(a), cy + ry * j * math.sin(a)))
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return (f'<path d="{d}" fill="none" stroke="{col or C["red"]}" stroke-width="{w}" stroke-linecap="round" '
            f'stroke-linejoin="round" opacity="0.92" transform="rotate({rot} {cx:.1f} {cy:.1f})"/>')
