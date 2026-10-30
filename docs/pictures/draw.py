"""Drawing helpers for the README pictures: text, arrows, stamps, badges, framed panels. Every picture has its own
light paper card, so it reads the same on GitHub's light and dark themes."""
import html, math

C = dict(paper="#f2f4f7", panel="#ffffff", ink="#1d2330", soft="#677084", line="#cfd6e0",
         red="#dc3f39", redbg="#fde8e6", green="#13885a", greenbg="#e0f3e8", blue="#2a66d9", bluebg="#e4edff",
         amber="#c47a00", wall="#e8edf4", window="#d3e4fb", wood="#b98a5e", wood2="#a4774f",
         skin="#f1d1b9", skin2="#d9a986", lip="#b25a52",
         dark="#3a2a24", blonde="#d4ab5f", grey="#a7abb3")
FL = "'Golos Text', system-ui, sans-serif"
FM = "'JetBrains Mono', ui-monospace, monospace"
FH = "Caveat, 'Segoe Print', cursive"
MAYA, SAM, LEO = "#d0663a", "#3f6fb5", "#3f8f7a"


def esc(s):
    return html.escape(s, quote=True)


def T(x, y, s, size=14, fill=None, font="l", anchor="start", weight=400, ls=None, rot=None):
    fam = {"l": FL, "m": FM, "h": FH}[font]
    extra = (f' letter-spacing="{ls}"' if ls else "") + (f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot else "")
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill or C["ink"]}" text-anchor="{anchor}"{extra}>{esc(s)}</text>')


def arrow(x1, y1, x2, y2, col, w=2.0, dash=None, head=9, both=False):
    def tip(xa, ya, xb, yb):
        a = math.atan2(yb - ya, xb - xa)
        p1 = (xb - head * math.cos(a - 0.45), yb - head * math.sin(a - 0.45))
        p2 = (xb - head * math.cos(a + 0.45), yb - head * math.sin(a + 0.45))
        return (f'<path d="M{p1[0]:.1f},{p1[1]:.1f} L{xb:.1f},{yb:.1f} L{p2[0]:.1f},{p2[1]:.1f}" stroke="{col}" '
                f'stroke-width="{w}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    d = f' stroke-dasharray="{dash}"' if dash else ""
    s = (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="{w}"{d} '
         f'stroke-linecap="round"/>' + tip(x1, y1, x2, y2))
    return s + (tip(x2, y2, x1, y1) if both else "")


def curve(x1, y1, cx, cy, x2, y2, col, w=2.2, head=9):
    """A curved double-headed arrow (quadratic)."""
    s = f'<path d="M{x1:.1f},{y1:.1f} Q{cx:.1f},{cy:.1f} {x2:.1f},{y2:.1f}" stroke="{col}" stroke-width="{w}" fill="none"/>'
    for (xa, ya, xb, yb) in ((cx, cy, x2, y2), (cx, cy, x1, y1)):
        a = math.atan2(yb - ya, xb - xa)
        p1 = (xb - head * math.cos(a - 0.45), yb - head * math.sin(a - 0.45))
        p2 = (xb - head * math.cos(a + 0.45), yb - head * math.sin(a + 0.45))
        s += (f'<path d="M{p1[0]:.1f},{p1[1]:.1f} L{xb:.1f},{yb:.1f} L{p2[0]:.1f},{p2[1]:.1f}" stroke="{col}" '
              f'stroke-width="{w}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    return s


def stamp(x, y, word, note, ok, rot=-4):
    col, bg = (C["green"], C["greenbg"]) if ok else (C["red"], C["redbg"])
    ww = 12.2 * len(word) + 6
    wn = 7.9 * len(note) if note else 0
    w = 14 + ww + (10 + wn if note else 0) + 8
    s = (f'<g transform="translate({x:.1f} {y:.1f}) rotate({rot})">'
         f'<rect x="0" y="0" width="{w:.0f}" height="32" rx="6" fill="{bg}" stroke="{col}" stroke-width="2.6"/>'
         + T(14, 22.5, word, 17, col, "l", weight=800, ls=1.6))
    if note:
        s += T(14 + ww + 10, 21.5, note, 13, col, "m", weight=700)
    return s + "</g>"


def badge(cx, cy, ok, r=13):
    col = C["green"] if ok else C["red"]
    s = f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{col}" stroke="#fff" stroke-width="2.5"/>'
    k = r / 13
    if ok:
        s += (f'<path d="M{cx-6*k:.1f},{cy+0.5*k:.1f} L{cx-1.5*k:.1f},{cy+5*k:.1f} L{cx+6.5*k:.1f},{cy-5*k:.1f}" '
              f'stroke="#fff" stroke-width="{2.8*k:.1f}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    else:
        s += (f'<path d="M{cx-5*k:.1f},{cy-5*k:.1f} L{cx+5*k:.1f},{cy+5*k:.1f} M{cx+5*k:.1f},{cy-5*k:.1f} '
              f'L{cx-5*k:.1f},{cy+5*k:.1f}" stroke="#fff" stroke-width="{2.8*k:.1f}" stroke-linecap="round"/>')
    return s


_ids = [0]


def uid(p):
    _ids[0] += 1
    return f"{p}{_ids[0]}"


def framed(pid, x, y, w, h, inner, bg=None, r=10, stroke=2):
    cid = uid(pid + "c")
    return (f'<clipPath id="{cid}"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}"/></clipPath>'
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{bg or C["wall"]}"/>'
            f'<g clip-path="url(#{cid})">{inner}</g>'
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="none" stroke="{C["ink"]}" '
            f'stroke-width="{stroke}"/>')




def svg(w, h, body, label):
    return (f'<svg class="pic" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="{esc(label)}"><rect width="{w}" height="{h}" rx="16" fill="{C["paper"]}"/>{body}</svg>')
