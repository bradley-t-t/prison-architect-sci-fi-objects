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

# Some kinds of object are not recoloured but rebuilt: the game's drawing gives
# the outline, the size and where the light falls, and everything inside the
# outline is drawn again. Because it works from the outline it holds for every
# view of an object and on every sheet.
REMAKES = ("none", "pod", "slab", "console", "sanitary", "rack", "core", "crate", "bulkhead", "seat", "emitter", "vehicle", "glass")
WHITE = [(0.00, (26, 36, 52)), (0.45, (132, 154, 182)), (0.80, (214, 230, 244)), (1.00, (246, 252, 255))]


def _shade(colour, lum, lo=0.55, hi=1.25):
    return np.clip(np.asarray(colour, float)[None, :] * (lo + (hi - lo) * lum[:, None]), 0, 255)


def remake(out, lum, solid, dist, arche, accent, rgb_in, owner=None):
    """Redraws every object whose kind has a remake. Returns where it drew."""
    done = np.zeros(solid.shape, bool)
    lab, n = nd.label(solid & (arche > 0))
    if owner is not None and n:
        # Sprites packed edge to edge would label as one object and be drawn as
        # one. Pairing each component with the picture that owns it splits them.
        pair = lab.astype(np.int64) * (int(owner.max()) + 1) + owner
        pair[lab == 0] = 0
        _, inverse = np.unique(pair, return_inverse=True)
        lab = inverse.reshape(lab.shape).astype(np.int32)
        n = int(lab.max())
    if not n:
        return done
    sizes = nd.sum(solid, lab, range(1, n + 1))
    for i, box in enumerate(nd.find_objects(lab), 1):
        if box is None or sizes[i - 1] < 260:
            continue
        m = lab[box] == i
        ys, xs = np.nonzero(m)
        kind = REMAKES[int(np.bincount(arche[box][m]).argmax())]
        tint = np.array(ACCENTS[ACCENT_ORDER[int(np.bincount(accent[box][m]).argmax())]], float)
        h, w = m.shape
        yy, xx = np.mgrid[0:h, 0:w]
        d = dist[box]
        l = lum[box]
        px = out[box]
        deep = m & (d >= 5)
        rim = m & (d >= 3.2) & (d < 5)

        if kind == "pod":
            # a shell with a glass canopy over whoever is in it
            px[m] = ramp(PANEL, l[m] * 0.9)
            t = (yy - ys.min()) / max(1, ys.max() - ys.min())
            glass = np.stack([20 + 50 * t, 70 + 120 * t, 100 + 130 * t], -1)
            streak = ((xx * 2 + yy) % 29 < 4) | ((xx * 2 + yy) % 29 == 9)
            glass = glass * (0.75 + 0.5 * l[..., None]) + streak[..., None] * 38
            px[deep] = np.clip(glass[deep], 0, 255)
            px[rim] = tint * 0.9 + px[rim] * 0.1
        elif kind == "slab":
            # a dark work surface ruled into a grid, lit along its edge
            px[m] = ramp(PANEL, l[m] * 0.8)
            grid = ((xx % 8 == 0) | (yy % 8 == 0)) & deep
            px[deep] = ramp(PANEL, 0.18 + l[deep] * 0.35)
            px[grid] = px[grid] * 0.6 + tint * 0.4
            px[rim] = tint * 0.85 + px[rim] * 0.15
        elif kind == "console":
            # the game's casing, and everything dark and flat on it lit up as a
            # display: a television's screen, a cooker's rings, a machine's slot
            px[m] = ramp(PANEL, l[m])
            # only a dark patch that is a minority of the casing reads as a
            # display; an object that is dark all over keeps its casing
            dark = m & (d >= 2.5) & (l < 0.30)
            dark = nd.binary_opening(dark, iterations=1)
            patches, found = nd.label(dark)
            screen = np.zeros_like(dark)
            budget = 0.8 * m.sum()      # the rectangle test below is what rejects artwork
            areas = nd.sum(dark, patches, range(1, found + 1)) if found else []
            slots = nd.find_objects(patches)
            for idx in np.argsort(areas)[::-1]:
                if areas[idx] < 120 or areas[idx] > budget:
                    continue
                # a display is a rectangle; a ragged blob is artwork
                sy, sx = slots[idx]
                if areas[idx] < 0.7 * (sy.stop - sy.start) * (sx.stop - sx.start):
                    continue
                screen |= patches == idx + 1
                budget -= areas[idx]
            # a patch the game drew bright and saturated is a display already lit
            h_, s_, v_ = hsv(rgb_in[box])
            # displays are drawn green, cyan or blue; orange and skin are people
            # and hazard paint. Holes are closed, since a screen's pale
            # highlights would otherwise break it into scraps.
            # The game draws a display one of two ways: vivid green or cyan, or
            # the paler blue of a monitor wall. The darkest rectangle on an
            # object is usually its base, so darkness alone is never the test.
            vivid_px = (s_ > 0.45) & (v_ > 0.45) & (h_ >= 70) & (h_ <= 270)
            glass_px = (s_ >= 0.25) & (v_ >= 0.35) & (h_ >= 190) & (h_ <= 250)
            lit = m & (d >= 2) & (vivid_px | glass_px)
            lit = nd.binary_fill_holes(nd.binary_closing(lit, iterations=1)) & m
            spots, n_spots = nd.label(lit)
            spot_boxes = nd.find_objects(spots)
            for j, area in enumerate(nd.sum(lit, spots, range(1, n_spots + 1)) if n_spots else [], 1):
                sy, sx = spot_boxes[j - 1]
                # vivid and close to a rectangle: dull paint and ragged art are neither
                here = spots == j
                vivid = s_[here].mean() >= 0.55 or glass_px[here].mean() >= 0.8
                if area < 60 or not vivid or area < 0.75 * (sy.stop - sy.start) * (sx.stop - sx.start):
                    lit[spots == j] = False
            screen &= ~lit
            # a powered display: brightest at its centre, with scanlines
            if screen.any():
                sd = nd.distance_transform_edt(screen)
                glow = np.clip(sd / max(3.0, sd.max()), 0, 1)[..., None]
                face = (np.array([14, 62, 92], float) + tint * 0.22) * (0.75 + 0.75 * glow)
                px[screen] = np.clip(face[screen], 0, 255)
                px[screen & (yy % 3 == 0)] *= 0.72
            edge = screen & ~nd.binary_erosion(screen, iterations=1)
            px[edge] = tint * 0.85
            # a lit face keeps the game's own light and dark, so a wall of
            # monitors is not one flat colour, and never washes out to white
            face = tint * 0.45 + np.array([30, 150, 190.0])
            px[lit] = np.clip(face[None, :] * (0.45 + 0.75 * l[lit][:, None]), 0, 235)
            px[lit & (yy % 3 == 0)] *= 0.8
            # buttons and indicator lamps stay the colour the game gave them.
            # Only small patches count, so painted artwork does not come back.
            keys = m & (s_ > 0.5) & (v_ > 0.5) & ~lit & ~screen
            klab, kn = nd.label(keys)
            if kn:
                small = np.isin(klab, 1 + np.nonzero(nd.sum(keys, klab, range(1, kn + 1)) <= 40)[0])
                px[small] = np.clip(rgb_in[box][small] * 255 * 1.15 + 10, 0, 255)
            # one row of indicator lamps, low on the casing
            row = int(ys.min() + 0.82 * (ys.max() - ys.min()))
            lamps = m & (d >= 2) & ~screen & (yy >= row) & (yy < row + 2) & (xx % 6 < 2)
            px[lamps] = np.where(((xx // 6) % 3 == 0)[lamps][:, None], np.array([255, 96, 96.0]), tint)
        elif kind == "sanitary":
            # bright composite, the one pale thing in a dark room, with lit water
            px[m] = ramp(WHITE, np.clip(l[m] * 1.08, 0, 1))
            water = m & (d >= 3) & (l < 0.42)
            px[water] = _shade((70, 205, 255), l[water], 0.8, 1.6)
            px[m & (d >= 1.5) & (d < 2.6)] = px[m & (d >= 1.5) & (d < 2.6)] * 0.7 + tint * 0.3
        elif kind == "rack":
            # a frame of data slats: what was a bright spine is a lit slat
            px[m] = ramp(PANEL, l[m] * 0.9)
            slat = deep & (yy % 5 < 3)
            lit = slat & (l > 0.45) & (((xx // 4) + (yy // 5)) % 3 == 0)
            px[slat] = _shade((34, 96, 118), l[slat], 0.6, 1.2)
            px[lit] = _shade(tint, l[lit], 0.8, 1.2)
        elif kind == "core":
            # plant with a live core showing through its casing
            px[m] = ramp(PANEL, l[m])
            cy, cx = ys.mean(), xs.mean()
            r = np.hypot(yy - cy, xx - cx)
            reach = 0.32 * min(ys.max() - ys.min(), xs.max() - xs.min()) + 3
            glow = np.clip(1 - r / reach, 0, 1)[..., None] ** 1.4
            ring = (np.abs(r - reach * 0.55) < 0.8) | (np.abs(r - reach) < 0.8)
            inside = m & (d >= 2.5)
            px[inside] = px[inside] * (1 - 0.85 * glow[inside]) + np.array([255, 236, 190.0]) * 0.85 * glow[inside] * 0.5 + tint * 0.85 * glow[inside] * 0.5
            px[inside & ring] = tint
        elif kind == "crate":
            # a sealed container with a hazard band and a lid lamp
            px[m] = ramp(PANEL, l[m])
            mid = (yy > ys.min() + 0.42 * (ys.max() - ys.min())) & (yy < ys.min() + 0.66 * (ys.max() - ys.min()))
            band = m & (d >= 2.5) & mid
            stripe = ((xx + yy) % 10 < 5)
            px[band & stripe] = _shade((255, 214, 64), l[band & stripe], 0.7, 1.1)
            px[band & ~stripe] = np.array([14, 16, 20.0])
            lamp = m & (np.hypot(yy - (ys.min() + 5), xx - xs.mean()) < 2.2)
            px[lamp] = tint
        elif kind == "bulkhead":
            # a plated door with a lit seam down its length
            px[m] = ramp(PANEL, 0.15 + l[m] * 0.7)
            tall = (ys.max() - ys.min()) >= (xs.max() - xs.min())
            along = xx - xs.mean() if tall else yy - ys.mean()
            seam = deep & (np.abs(along) < 1.2)
            plate = deep & ((yy if tall else xx) % 12 == 0)
            px[plate] = px[plate] * 0.55
            px[seam] = tint
            px[rim] = px[rim] * 0.55 + tint * 0.45
        elif kind == "seat":
            # a moulded shell with a lit cushion
            px[m] = ramp(PANEL, l[m] * 0.85)
            pad = m & (d >= 4)
            px[pad] = _shade(tint * 0.55 + np.array([10, 30, 40.0]), l[pad], 0.5, 1.2)
        elif kind == "emitter":
            # a housing around a core of light
            px[m] = ramp(PANEL, l[m])
            r = np.hypot(yy - ys.mean(), xx - xs.mean())
            reach = 0.45 * min(ys.max() - ys.min(), xs.max() - xs.min()) + 2
            glow = np.clip(1 - r / reach, 0, 1)[..., None] ** 0.8
            px[m] = px[m] * (1 - glow[m]) + (tint * 0.5 + np.array([255, 255, 255.0]) * 0.5) * glow[m]
        elif kind == "vehicle":
            # a dark hull, lit glass and a running light round the body
            px[m] = ramp(PANEL, l[m])
            h_, s_, v_ = hsv(rgb_in[box])
            glass = m & (d >= 2) & (h_ > 170) & (h_ < 260) & (s_ > 0.15)
            px[glass] = _shade((90, 210, 255), l[glass], 0.6, 1.4)
            px[m & (d >= 2.2) & (d < 3.2)] = tint * 0.8
        elif kind == "glass":
            # a pane of held light
            px[m] = ramp(PANEL, l[m])
            t = ((xx * 2 + yy) % 17 < 3)
            pane = m & (d >= 2.5)
            px[pane] = np.clip(np.array([30, 120, 160.0]) * (0.7 + 0.7 * l[pane][:, None]) + t[pane][:, None] * 50, 0, 255)
            px[m & (d >= 1.5) & (d < 2.5)] = tint
        out[box] = px
        done[box] |= m
    return done
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


def reskin(img, mask=None, strips=True, no_strip=None, accent=None, style=None, arche=None, owner=None):
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

    remade = np.zeros(solid.shape, bool)
    if arche is not None and accent is not None:
        keep_out = ~mask if mask is not None else np.zeros(solid.shape, bool)
        dist = nd.distance_transform_edt(solid)
        remade = remake(out, lum, solid & ~keep_out, dist, arche, accent, rgb, owner)
        # an outline stays an outline
        dark = solid & (lum < 0.13)
        out[dark & remade] = ramp(PANEL, lum[dark & remade])

    if strips:
        # a light strip a little inside the edge of every panel big enough to carry one
        # Grain, rivets and handles are closed over first, so the strip runs
        # as one clean line and not around every mark on the surface.
        wood = wood & ~remade
        grey = grey & ~remade
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
