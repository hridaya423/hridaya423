import math
import random
from pathlib import Path
from xml.sax.saxutils import escape

W, H = 846, 420
CW, LH = 6.6, 12
COLS, ROWS = 120, 21
PX, PY = (W - COLS * CW) / 2, 30
FRAMES, DT = 72, 0.1
T = FRAMES * DT

BG, EDGE = "#0d1117", "#21262d"
WATER, ORANGE, RED, WHITE = "#2b3a4c", "#f0884a", "#d4512b", "#efe8da"
TEXT, DIM = "#e6edf3", "#7d8590"

RAMP = " .:-=+*#%@"
CX, CY = COLS * CW / 2, ROWS * LH / 2
RX, RY = 250, 80
LENGTH, WIDTH = 200, 25


def path(a):
    return CX + RX * math.cos(a), CY + RY * math.sin(a) * (1 + 0.25 * math.sin(2 * a))


def spine(a0, t):
    trail = [path(a0)]
    a, travelled = a0, 0
    while travelled < LENGTH:
        a -= 0.002
        x, y = path(a)
        travelled += math.hypot(x - trail[-1][0], y - trail[-1][1])
        trail.append((x, y))
    points = []
    for i in range(25):
        u = i / 24
        x, y = trail[min(len(trail) - 1, round(u * (len(trail) - 1)))]
        bx, by = trail[min(len(trail) - 1, round(u * (len(trail) - 1)) + 1)]
        tx, ty = x - bx, y - by
        n = math.hypot(tx, ty) or 1
        wiggle = 12 * u * u * math.sin(6 * u - t * 2 * math.pi * 3)
        points.append((x - ty / n * wiggle, y + tx / n * wiggle, u))
    return points


def radius(u):
    return WIDTH * min(1, 0.45 + u * 5) * (1 - u) ** 0.9


def koi(points, spots):
    cells = {}
    for row in range(ROWS):
        for col in range(COLS):
            x, y = col * CW + CW / 2, row * LH + LH / 2
            best = None
            for (ax, ay, au), (bx, by, bu) in zip(points, points[1:]):
                dx, dy = bx - ax, by - ay
                k = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
                d = math.hypot(x - ax - k * dx, y - ay - k * dy)
                u = au + k * (bu - au)
                if best is None or d < best[0]:
                    best = (d, u, ax + k * dx, ay + k * dy)
            d, u, sx, sy = best
            r = radius(u)
            if u > 0.92:
                tail = (u - 0.92) / 0.08
                if d < 4 + 16 * tail:
                    cells[(row, col)] = ("~", RED)
                continue
            if d < r:
                depth = 1 - d / r
                light = 0.5 + 0.5 * ((sx - x) * 0.4 + (sy - y)) / (r + 1)
                level = 2 + int(min(0.999, depth * 0.7 + light * 0.3) * (len(RAMP) - 2))
                color = WHITE if any(abs(u - s) < w for s, w in spots) else ORANGE
                cells[(row, col)] = (RAMP[level], color)
            elif 0.18 < u < 0.3 and d < r + 11:
                cells[(row, col)] = ("'", RED)
    return cells


def water(t, rng_seed=7):
    rng = random.Random(rng_seed)
    dots = [(rng.randrange(ROWS), rng.randrange(COLS), rng.random()) for _ in range(150)]
    cells = {}
    for row, col, phase in dots:
        v = math.sin(2 * math.pi * (t + phase))
        if v > -0.3:
            cells[(row, col)] = ("~" if v > 0.75 else "-" if v > 0.3 else ".", WATER)
    return cells


def layers(cells):
    out = []
    for color in {c for _, c in cells.values()}:
        for row in range(ROWS):
            cols = [col for (r, col), (_, c) in cells.items() if r == row and c == color]
            if not cols:
                continue
            a, b = min(cols), max(cols)
            text = "".join(cells[(row, col)][0] if (row, col) in cells and cells[(row, col)][1] == color else " " for col in range(a, b + 1))
            x, y = PX + a * CW, PY + row * LH + LH - 3
            length = (b - a + 1) * CW
            out.append(f'<text x="{x:.1f}" y="{y}" fill="{color}" textLength="{length:.1f}" lengthAdjust="spacing">{escape(text)}</text>')
    return "".join(out)


def frame(i):
    t = i / FRAMES
    a = 2 * math.pi * t
    cells = water(t)
    cells.update(koi(spine(a, t), [(0.12, 0.07), (0.45, 0.1)]))
    cells.update(koi(spine(a + math.pi, t + 0.5), [(0.3, 0.12), (0.7, 0.06)]))
    return layers(cells)


def svg():
    frames = "".join(
        f'<g class="f" style="animation-delay:{i * DT - T:.2f}s">{frame(i)}</g>' for i in range(FRAMES)
    )
    step = 100 / FRAMES
    y0 = PY + ROWS * LH + 46
    text = [
        (y0, TEXT, 600, 15, "hridya agrawal", DIM, "  ·  london"),
        (y0 + 30, TEXT, 400, 12.5, "i build tools for problems i run into. a shell that understands english,", None, ""),
        (y0 + 49, TEXT, 400, 12.5, "a gpu video renderer, a mac launcher, games that end up in an arcade.", None, ""),
        (y0 + 78, DIM, 400, 12, "rust · swift · typescript · local models", None, ""),
    ]
    lines = "".join(
        f'<text x="{PX + 4}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}">{escape(s)}'
        + (f'<tspan fill="{tail_fill}" font-weight="400">{escape(tail)}</tspan>' if tail_fill else "")
        + "</text>"
        for y, fill, weight, size, s, tail_fill, tail in text
    )
    label = "Two ASCII koi circling a pond. Hridya Agrawal, London. I build tools for problems I run into: a shell that understands English, a GPU video renderer, a Mac launcher, and games that end up in an arcade."
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(label)}"><title>Hridya Agrawal</title><style>
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-size:11px;white-space:pre}}
.f{{visibility:hidden;animation:k {T:.2f}s steps(1,end) infinite}}
@keyframes k{{0%{{visibility:visible}}{step:.3f}%,100%{{visibility:hidden}}}}
@media (prefers-reduced-motion:reduce){{.f{{animation:none}}.f:first-of-type{{visibility:visible}}}}
</style><rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{BG}" stroke="{EDGE}"/>
<g>{frames}</g>
<line x1="{PX + 4}" x2="{W - PX - 4}" y1="{PY + ROWS * LH + 14}" y2="{PY + ROWS * LH + 14}" stroke="{EDGE}"/>
{lines}</svg>'''


out = Path(__file__).resolve().parent.parent / "assets/koi.svg"
out.write_text(svg())
print(out, out.stat().st_size)
