"""Re-skins a sheet of the game's object sprites as dark sci-fi hardware.

Works on the pixels, by what each one is made of. The game paints wood in
tans and oranges, cloth in greens and metal and porcelain in greys, all inside
a near-black outline, so a pixel's hue says what it is:

  wood and cardboard   dark gunmetal panels, lit from the same side
  cloth and plastics   deep teal
  metal and porcelain  dark blue alloy
  outlines             blue-black
  reds and blues       kept, pushed toward neon

Panels then get lit trim a little in from their edge, with a soft glow around
it. Every object is built from the same three materials, which is what holds
a room together; what varies is the trim. Its colour says what the object is
for (ACCENTS), and its cut is one of four (a closed loop, corner brackets, a
dashed loop, a pair of rails), picked from the object's name so every view of
one object matches. Big panels are also split by plate seams and carry a
short row of status lights.
"""

import numpy as np
from PIL import Image
from scipy import ndimage as nd

STRIP = np.array([95, 216, 255], float)      # the blue beam of Sci-Fi Security

# Trim colour by what an object is for. All sit at one brightness and one
# saturation, so a canteen and a cell block read as one prison.
ACCENTS = {
    "security": (95, 216, 255),     # doors, cells, cameras: the beam blue
    "medical": (110, 255, 196),
    "kitchen": (255, 190, 92),
    "power": (255, 146, 64),
    "leisure": (196, 140, 255),
    "office": (204, 236, 255),
    "labour": (255, 220, 84),
}
ACCENT_ORDER = list(ACCENTS)
PANEL = [(0.00, (14, 18, 26)), (0.35, (30, 38, 50)), (0.70, (52, 64, 82)), (1.00, (96, 114, 140))]
CLOTH = [(0.00, (8, 26, 34)), (0.45, (20, 70, 88)), (0.80, (44, 124, 150)), (1.00, (120, 200, 222))]
STEEL = [(0.00, (8, 11, 18)), (0.30, (36, 46, 62)), (0.65, (86, 104, 130)), (0.88, (150, 172, 200)), (1.00, (214, 232, 250))]


def ramp(stops, t):
    t = np.clip(t, 0, 1)
    out = np.zeros(t.shape + (3,))
    xs = [s[0] for s in stops]
    for c in range(3):
        out[..., c] = np.interp(t, xs, [s[1][c] for s in stops])
    return out


def hsv(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-6
    rc = np.where(m, (mx - r) / np.where(m, d, 1), 0)
    gc = np.where(m, (mx - g) / np.where(m, d, 1), 0)
    bc = np.where(m, (mx - b) / np.where(m, d, 1), 0)
    h = np.where(mx == r, bc - gc, np.where(mx == g, 2 + rc - bc, 4 + gc - rc))
    h = (h / 6) % 1
    s = np.where(mx > 1e-6, d / np.where(mx > 1e-6, mx, 1), 0)
    return h * 360, s, mx


def reskin(img, mask=None, strips=True, no_strip=None, accent=None, style=None):
    """accent and style are maps the size of the image: an index into
    ACCENT_ORDER and a trim cut from 0 to 3 for every pixel, or None for the
    beam blue in a closed loop everywhere."""
    a = np.asarray(img.convert("RGBA")).astype(float)
    rgb, alpha = a[..., :3] / 255, a[..., 3] / 255
    h, s, v = hsv(rgb)
    lum = rgb @ np.array([0.299, 0.587, 0.114])
    solid = alpha > 0.5
    wood = solid & (h >= 12) & (h <= 62) & (s > 0.22) & (v > 0.18)
    cloth = solid & (h > 62) & (h <= 170) & (s > 0.12) & (v > 0.15)
    grey = solid & (s <= 0.22) & ~wood & ~cloth
    blue = solid & (h > 170) & (h <= 270) & (s > 0.22)
    red = solid & ((h < 12) | (h > 330)) & (s > 0.35)

    out = rgb * 255
    # Each piece of wood keeps its own light and shade around the same middle
    # grey, so a pale table and a dark desk come out as the same material.
    lab, n = nd.label(wood)
    if n:
        idx = np.arange(1, n + 1)
        mean = np.zeros(n + 1)
        mean[1:] = nd.mean(lum, lab, idx)
        t = 0.42 + (lum - mean[lab]) * 2.4
        out[wood] = ramp(PANEL, t[wood])
    out[cloth] = ramp(CLOTH, lum[cloth] ** 1.15)
    out[grey] = ramp(STEEL, lum[grey] ** 1.1)
    # neon up what is already blue or red
    for m, tint in ((blue, np.array([0.55, 0.95, 1.25])), (red, np.array([1.2, 0.75, 0.85]))):
        out[m] = np.clip(out[m] * tint + 10, 0, 255)

    if strips:
        # a light strip a little inside the edge of every panel big enough to carry one
        # Grain, rivets and handles are closed over first, so the strip runs
        # as one clean line and not around every mark on the surface.
        body = nd.binary_closing(wood, iterations=3)
        body = nd.binary_fill_holes(body) & solid
        body = nd.binary_opening(body, iterations=3)
        # A flat sheet of pale metal, a canteen table or a bench, is a panel too.
        plate = nd.binary_opening(nd.binary_closing(grey & (lum > 0.5), iterations=2), structure=np.ones((3, 3)), iterations=9)
        plab, pn = nd.label(plate)
        if pn:
            psizes = nd.sum(plate, plab, range(1, pn + 1))
            body |= np.isin(plab, 1 + np.nonzero(psizes >= 3000)[0])
        inner = nd.binary_erosion(body, iterations=5)
        blab, bn = nd.label(body)
        if bn:
            sizes = nd.sum(body, blab, range(1, bn + 1))
            big = np.isin(blab, 1 + np.nonzero(sizes >= 1400)[0])
        else:
            big = np.zeros_like(body)
        inner &= big
        loop = inner & ~nd.binary_erosion(inner, iterations=2)
        H, W = body.shape
        yy, xx = np.mgrid[0:H, 0:W]
        line = np.zeros_like(body)
        seam = np.zeros_like(body)
        leds = np.zeros_like(body)
        colour = np.zeros((H, W, 3)) + STRIP
        for lab, box in enumerate(nd.find_objects(blab), 1):
            if box is None or sizes[lab - 1] < 1400:
                continue
            here = np.zeros_like(body)
            here[box] = blab[box] == lab
            cy, cx = (box[0].start + box[0].stop) // 2, (box[1].start + box[1].stop) // 2
            cut = int(style[cy, cx]) if style is not None else 0
            tint = np.array(ACCENTS[ACCENT_ORDER[int(accent[cy, cx])]], float) if accent is not None else STRIP
            ring = loop & here
            y0, y1, x0, x1 = box[0].start, box[0].stop, box[1].start, box[1].stop
            if cut == 1:        # corner brackets
                arm = max(6, min(y1 - y0, x1 - x0) // 4)
                near_x = (xx < x0 + 5 + arm) | (xx >= x1 - 5 - arm)
                near_y = (yy < y0 + 5 + arm) | (yy >= y1 - 5 - arm)
                ring &= near_x & near_y
            elif cut == 2:      # dashed loop
                ring &= ((xx + yy) // 6) % 2 == 0
            elif cut == 3:      # a pair of rails along the long side
                if x1 - x0 >= y1 - y0:
                    ring &= (xx > x0 + 9) & (xx < x1 - 10)
                else:
                    ring &= (yy > y0 + 9) & (yy < y1 - 10)
            line |= ring
            colour[here] = tint
            # plate seams across a long panel, and status lights in a corner
            core = nd.binary_erosion(here, iterations=8)
            if sizes[lab - 1] >= 5000:
                long_x = x1 - x0 >= y1 - y0
                span = (x1 - x0) if long_x else (y1 - y0)
                for k in range(1, max(2, span // 72)):
                    at = (x0 if long_x else y0) + k * span // max(2, span // 72)
                    seam |= core & ((xx == at) if long_x else (yy == at))
            if sizes[lab - 1] >= 2600:
                ys, xs = np.nonzero(core)
                if len(ys):
                    ly, lx = ys.min() + 1, xs.max() - 1
                    for k in range(3):
                        spot = (yy >= ly) & (yy < ly + 2) & (xx <= lx - k * 4) & (xx > lx - k * 4 - 2) & core
                        leds |= spot
        if no_strip is not None:
            line &= ~no_strip
            leds &= ~no_strip
            seam &= ~no_strip
        out[seam] = out[seam] * 0.55
        lit = np.roll(seam, 1, axis=1) | np.roll(seam, 1, axis=0)
        lit &= body & ~seam
        out[lit] = np.clip(out[lit] * 1.18 + 6, 0, 255)
        glow = nd.gaussian_filter((line | leds).astype(float), 2.2) * 1.6
        glow = np.clip(glow, 0, 1) * solid
        out = out * (1 - 0.55 * glow[..., None]) + colour * 0.55 * glow[..., None]
        out[line] = colour[line] * 0.85 + out[line] * 0.15
        out[leds] = colour[leds] * 0.95 + 12

    res = np.dstack([np.clip(out, 0, 255), a[..., 3]])
    if mask is not None:
        res = np.where(mask[..., None], res, a)
    return Image.fromarray(res.astype(np.uint8), "RGBA")
