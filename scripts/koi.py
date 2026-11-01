import math
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

W = 846
CW, LH, FONT = 5.4, 10, 9
COLS, ROWS = 148, 28
PX, PY = (W - COLS * CW) / 2, 22
POND_W, POND_H = COLS * CW, ROWS * LH
H = int(PY + POND_H + 118)
FRAMES, DT = 72, 0.12
T = FRAMES * DT
SUB_X, SUB_Y = 3, 4

BG, EDGE = "#0d1117", "#21262d"
TEXT, DIM = "#e6edf3", "#7d8590"
PALETTE = {
    "white": ["#6f6a63", "#a59e93", "#d8d1c4", "#fbf7ef"],
    "red": ["#7a2618", "#b83a22", "#e8582f", "#ff8a5c"],
    "gold": ["#7a4a14", "#b8741f", "#e8a33a", "#ffd27a"],
    "fin": ["#3a2c2a", "#6a4c44", "#a37a6c", "#dcb3a2"],
    "water": ["#16232d", "#1f3442", "#2c4a5c", "#41687e"],
    "eye": ["#14110f"],
}
COLORS = [c for tones in PALETTE.values() for c in tones]
CLASS = {c: f"c{i}" for i, c in enumerate(COLORS)}

BODY_RAMP = ":-=+*#%@"
FIN_RAMP = ".,:;"
LENGTH, RADIUS = 250, 29
PROFILE_U = [0, 0.03, 0.1, 0.24, 0.4, 0.6, 0.8, 0.93, 1.0]
PROFILE_R = [0.5, 0.7, 0.9, 1.0, 0.95, 0.72, 0.42, 0.24, 0.2]
LIGHT = np.array([-0.45, -0.55, 0.7]) / np.linalg.norm([-0.45, -0.55, 0.7])
BEATS = 14

KOI = [
    {
        "phase": 0.0,
        "base": "white",
        "blobs": [
            ("red", 0.11, 0.0, 0.07, 0.95),
            ("red", 0.33, -0.3, 0.12, 1.0),
            ("red", 0.37, 0.5, 0.06, 0.55),
            ("red", 0.6, 0.12, 0.1, 0.9),
            ("red", 0.8, -0.15, 0.05, 0.7),
        ],
        "scales": 0.04,
    },
    {
        "phase": 0.25,
        "base": "gold",
        "blobs": [
            ("white", 0.07, 0.0, 0.07, 1.4),
            ("white", 0.48, 0.35, 0.13, 0.65),
            ("white", 0.72, -0.4, 0.07, 0.6),
        ],
        "scales": 0.16,
    },
]

CX, CY = POND_W / 2, POND_H / 2
ANGLES = np.linspace(0, 2 * np.pi, 6000)
TRACK = np.stack([CX + 318 * np.sin(ANGLES), CY + 86 * np.sin(2 * ANGLES)], axis=1)
TRACK_S = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(TRACK, axis=0), axis=1))])
TRACK_LEN = TRACK_S[-1]


def on_track(s):
    s = np.mod(s, TRACK_LEN)
    x = np.interp(s, TRACK_S, TRACK[:, 0])
    y = np.interp(s, TRACK_S, TRACK[:, 1])
    return np.stack([x, y], axis=-1)


def spine(fish, t):
    u = np.linspace(0, 1.24, 48)
    head = (fish["phase"] + t) * TRACK_LEN
    s = head - u * LENGTH
    p = on_track(s)
    ahead = on_track(s + 1)
    forward = ahead - p
    forward /= np.linalg.norm(forward, axis=1, keepdims=True)
    lateral = np.stack([-forward[:, 1], forward[:, 0]], axis=1)
    wiggle = 7.5 * (0.12 + u) ** 2 * np.sin(2 * np.pi * (BEATS * t - 1.1 * u))
    return u, p + lateral * wiggle[:, None]


def project(points, u, q):
    a, b = q[:-1], q[1:]
    d = b - a
    rel = points[:, None, :] - a[None]
    k = np.clip((rel * d[None]).sum(-1) / (d * d).sum(-1)[None], 0, 1)
    closest = a[None] + k[..., None] * d[None]
    dist = np.linalg.norm(points[:, None, :] - closest, axis=-1)
    i = dist.argmin(1)
    n = np.arange(len(points))
    seg = d[i] / np.linalg.norm(d[i], axis=1, keepdims=True)
    normal = np.stack([seg[:, 1], -seg[:, 0]], axis=1)
    offset = points - closest[n, i]
    v = (offset * normal).sum(1)
    uu = u[i] + k[n, i] * (u[i + 1] - u[i])
    return uu, v, dist[n, i], normal


def shade_koi(fish, t, points):
    u, q = spine(fish, t)
    uu, v, d, normal = project(points, u, q)
    r = RADIUS * np.interp(uu, PROFILE_U, PROFILE_R)
    body = (uu <= 1.0) & (d < r)
    flap = 0.78 + 0.22 * np.sin(2 * np.pi * (BEATS / 2 * t) + np.sign(v))
    a = (uu - 0.15) / 0.21
    pect = (a > 0) & (a < 1) & (np.abs(v) > r * 0.6)
    pect &= np.abs(v) < r + RADIUS * 0.85 * np.sin(np.pi * np.clip(a, 0, 1)) ** 0.8 * flap * (1 - 0.35 * a)
    b = (uu - 0.5) / 0.12
    pelvic = (b > 0) & (b < 1) & (np.abs(v) < r + RADIUS * 0.35 * np.sin(np.pi * np.clip(b, 0, 1)))
    c = np.clip((uu - 0.95) / 0.29, 0, 1)
    tail = (uu > 0.93) & (uu < 1.235) & (np.abs(v) < RADIUS * (0.22 + 1.05 * c ** 0.9))
    tail &= ~((uu > 1.12) & (np.abs(v) < RADIUS * 0.9 * (uu - 1.12) / 0.12))
    fin = (pect | pelvic | tail) & ~body
    rays = np.where(tail, np.sin(np.arctan2(v, (uu - 0.93) * LENGTH + 1) * 18), np.sin(uu * LENGTH * 0.55))
    eye = ((uu - 0.075) * LENGTH) ** 2 + (np.abs(v) - 0.58 * r) ** 2 < 2.4 ** 2

    vn = np.clip(v / np.maximum(r, 1e-3), -1, 1)
    height = np.sqrt(1 - vn ** 2)
    nx = normal[:, 0] * vn
    ny = normal[:, 1] * vn
    light = np.clip(nx * LIGHT[0] + ny * LIGHT[1] + height * LIGHT[2], 0, 1)
    light = 0.18 + 0.82 * light
    light *= 1 - fish["scales"] * (0.5 + 0.5 * np.cos(uu * LENGTH * 0.62) * np.cos(vn * 9))

    color = np.full(len(points), fish["base"], dtype=object)
    for name, cu, cv, ru, rv in fish["blobs"]:
        wobble = 0.18 * np.sin(uu * 47 + vn * 5 + cu * 13)
        inside = ((uu - cu) / ru) ** 2 + ((vn - cv) / rv) ** 2 < 1 + wobble
        color[inside] = name
    return body, fin, eye, light, color, rays


def cell_points():
    cols, rows = np.meshgrid(np.arange(COLS * SUB_X), np.arange(ROWS * SUB_Y))
    x = (cols + 0.5) * CW / SUB_X
    y = (rows + 0.5) * LH / SUB_Y
    return np.stack([x.ravel(), y.ravel()], axis=1)


POINTS = cell_points()


def per_cell(values):
    return values.reshape(ROWS, SUB_Y, COLS, SUB_X).mean(axis=(1, 3))


def edge_char(gx, gy):
    angle = (math.degrees(math.atan2(gy, gx)) + 90) % 180
    if angle < 22.5 or angle >= 157.5:
        return "-"
    if angle < 67.5:
        return "\\"
    if angle < 112.5:
        return "|"
    return "/"


def water_texture():
    x, y = np.meshgrid(np.arange(COLS) * CW, np.arange(ROWS) * LH)
    field = np.sin(x * 0.021 + y * 0.013) + np.sin(y * 0.045 - x * 0.008 + 1.7) + np.sin((x + 2 * y) * 0.011 + 0.6)
    rng = np.random.default_rng(3)
    grain = rng.random((ROWS, COLS))
    cells = {}
    for row in range(ROWS):
        for col in range(COLS):
            f = field[row, col]
            if f > 2.2 and grain[row, col] < 0.3:
                cells[(row, col)] = ("~" if f > 2.25 else "-", PALETTE["water"][1 if f > 2.25 else 0])
            elif grain[row, col] < 0.008:
                cells[(row, col)] = (".", PALETTE["water"][0])
    return cells


TEXTURE = water_texture()


def frame(t):
    cells = {}
    for fish in KOI:
        body, fin, eye, light, color, rays = shade_koi(fish, t, POINTS)
        body_cov = per_cell(body.astype(float))
        fin_cov = per_cell(fin.astype(float))
        eye_cov = per_cell(eye & body)
        lit = per_cell(np.where(body, light, 0)) / np.maximum(body_cov, 1e-6)
        ray = per_cell(np.where(fin, rays, 0)) / np.maximum(fin_cov, 1e-6)
        names = color.reshape(ROWS, SUB_Y, COLS, SUB_X)
        mask = body.reshape(ROWS, SUB_Y, COLS, SUB_X)
        total = body_cov + fin_cov
        for row, col in zip(*np.nonzero(total > 0.12)):
            if body_cov[row, col] >= 0.3:
                picked = names[row, :, col, :][mask[row, :, col, :]]
                values, counts = np.unique(picked.astype(str), return_counts=True)
                tones = PALETTE[values[counts.argmax()]]
                level = lit[row, col]
                cover = body_cov[row, col]
                if eye_cov[row, col] > 0.15:
                    cells[(row, col)] = ("o", PALETTE["eye"][0])
                elif cover < 0.75:
                    cells[(row, col)] = (".:-=+"[min(4, int((cover - 0.3) / 0.45 * 5))], tones[max(1, min(3, int(level * 4)))])
                else:
                    char = "+*#%@"[min(4, int(level * 5))]
                    cells[(row, col)] = (char, tones[min(3, int(level * 4.2))])
            elif fin_cov[row, col] > 0.2:
                strength = fin_cov[row, col] * (0.7 + 0.3 * ray[row, col])
                char = FIN_RAMP[min(3, int(strength * 4))]
                cells[(row, col)] = (char, PALETTE["fin"][min(3, 1 + int(fin_cov[row, col] * 3))])
    return cells


def runs(cells, gap=9):
    out = []
    by_row = {}
    for (row, col), (char, color) in cells.items():
        by_row.setdefault((row, color), []).append((col, char))
    for (row, color), items in sorted(by_row.items()):
        items.sort()
        group = [items[0]]
        for item in items[1:]:
            if item[0] - group[-1][0] <= gap:
                group.append(item)
            else:
                out.append(text_run(row, color, group))
                group = [item]
        out.append(text_run(row, color, group))
    return "".join(out)


def text_run(row, color, group):
    start, end = group[0][0], group[-1][0]
    line = [" "] * (end - start + 1)
    for col, char in group:
        line[col - start] = char
    x, y = PX + start * CW, PY + row * LH + LH - 2
    fit = f' textLength="{len(line) * CW:.1f}"' if len(line) > 5 else ""
    return f'<text x="{x:.1f}" y="{y}" class="{CLASS[color]}"{fit}>{escape("".join(line))}</text>'


def svg():
    frames = "".join(
        f'<g class="f" style="animation-delay:{i * DT - T:.1f}s">{runs(frame(i / FRAMES))}</g>' for i in range(FRAMES)
    )
    step = 100 / FRAMES
    y0 = PY + POND_H + 52
    lines = [
        f'<text x="{PX + 4}" y="{y0}" class="t" font-size="15" font-weight="600">hridya agrawal<tspan class="d" font-weight="400">  ·  london</tspan></text>',
        f'<text x="{PX + 4}" y="{y0 + 30}" class="t" font-size="12.5">i build tools for problems i run into. a shell that understands english,</text>',
        f'<text x="{PX + 4}" y="{y0 + 49}" class="t" font-size="12.5">a gpu video renderer, a mac launcher, games that end up in an arcade.</text>',
    ]
    colors = "".join(f".{CLASS[c]}{{fill:{c}}}" for c in COLORS)
    label = "Two ASCII koi, one red and white, one gold, swimming a figure eight through a dark pond. Hridya Agrawal, London. I build tools for problems I run into: a shell that understands English, a GPU video renderer, a Mac launcher, and games that end up in an arcade."
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(label)}"><title>Hridya Agrawal</title><style>
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-size:{FONT}px;white-space:pre}}
{colors}.t{{fill:{TEXT}}}.d{{fill:{DIM}}}
.f{{visibility:hidden;animation:k {T:.1f}s steps(1,end) infinite}}
@keyframes k{{0%{{visibility:visible}}{step:.3f}%,100%{{visibility:hidden}}}}
@media (prefers-reduced-motion:reduce){{.f{{animation:none}}.f:first-child{{visibility:visible}}}}
</style><rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{BG}" stroke="{EDGE}"/>
<rect x="{PX - 6}" y="{PY - 8}" width="{POND_W + 12}" height="{POND_H + 16}" rx="8" fill="#0f161d"/>
<g>{runs(TEXTURE)}</g><g>{frames}</g>
<line x1="{PX + 4}" x2="{W - PX - 4}" y1="{PY + POND_H + 22}" y2="{PY + POND_H + 22}" stroke="{EDGE}"/>
{"".join(lines)}</svg>'''


out = Path(__file__).resolve().parent.parent / "assets/koi.svg"
out.write_text(svg())
print(out, out.stat().st_size)
