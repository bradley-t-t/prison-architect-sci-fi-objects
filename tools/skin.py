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
REMAKES = ("none", "pod", "slab", "console", "sanitary", "rack", "core", "crate", "bulkhead", "seat", "emitter", "vehicle", "glass", "tray", "paintdoor", "fixture", "surface", "hob", "bars")
WHITE = [(0.00, (40, 41, 44)), (0.45, (150, 152, 156)), (0.80, (226, 227, 230)), (1.00, (250, 250, 251))]


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

        if kind in ("pod", "tray"):
            # Both are drawn along the object's own length, head first. The head
            # is the end the game drew brighter: the pillow, or the head block.
            rows, cols = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1
            tall = rows >= cols
            along = (yy - ys.min()) / max(1, rows - 1) if tall else (xx - xs.min()) / max(1, cols - 1)
            cross = (xx - xs.min()) if tall else (yy - ys.min())
            span = cols if tall else rows
            vn = (cross - (span - 1) / 2) / max(1.0, (span - 1) / 2)
            head, foot = m & (along < 0.3), m & (along > 0.7)
            if head.any() and foot.any() and l[foot].mean() > l[head].mean():
                along = 1 - along
            U = along
        if kind == "pod":
            # a sleep capsule: white composite hull, graphite cradle, a segmented
            # mattress lit from beneath by light tubes, a raised smoked lid along
            # one side and a small console at the foot
            h_, s_, v_ = hsv(rgb_in[box])
            bedding_px = m & (s_ > 0.25) & (v_ > 0.3)
            if bedding_px.sum() > 0.08 * m.sum():
                own = (rgb_in[box][bedding_px] * 255).mean(0)
                tint = np.clip(own * 1.25, 0, 255)
            px[m] = ramp(WHITE, 0.50 + 0.40 * l[m])
            px[m & (d < 2.2)] = ramp(PANEL, 0.22 + 0.2 * l[m & (d < 2.2)])
            cradle = m & (d >= 5)
            px[cradle] = ramp(PANEL, 0.22 + 0.25 * l[cradle])
            bedding = m & (d >= 7) & (U > 0.05) & (U < 0.88)
            curve = (1 - 0.20 * vn ** 2)[..., None]
            foam = np.array([198, 200, 205.0]) * curve
            px[bedding] = foam[bedding]
            seam = bedding & ((U * 7.0) % 1.0 < 0.055)
            px[seam] *= 0.80
            tubes = bedding & (U > 0.27) & (U < 0.84) & (cross % 5 < 2)
            ends = np.clip(np.minimum(U - 0.27, 0.84 - U) / 0.06, 0.35, 1.0)[..., None]
            glow = (np.array([244, 246, 250.0]) * 0.86 + tint * 0.14) * curve * ends
            px[tubes] = np.clip(glow[tubes], 0, 255)
            socket = bedding & (((U > 0.255) & (U <= 0.27)) | ((U >= 0.84) & (U < 0.855)))
            px[socket] = ramp(STEEL, 0.55 + 0.2 * l[socket])
            rest = m & (d >= 7) & (U > 0.07) & (U < 0.215) & (np.abs(vn) < 0.62)
            px[rest] = (np.array([246, 247, 249.0]) * (1 - 0.14 * vn ** 2)[..., None])[rest]
            px[rest & ~nd.binary_erosion(rest, iterations=1)] *= 0.78
            lid = m & (d >= 3) & (vn > 0.64)
            glint = ((cross * 3 + (U * max(rows, cols)).astype(int)) % 23 < 3)
            smoked = np.array([58, 61, 66.0])[None, None, :] + glint[..., None] * 34
            px[lid] = smoked[lid]
            px[lid & (vn <= 0.70)] = tint * 0.85
            panel = m & (d >= 4) & (U >= 0.905)
            px[panel] = ramp(PANEL, 0.30 + 0.2 * l[panel])
            px[panel & (np.abs(vn) < 0.30) & (U > 0.925) & (U < 0.975)] = tint * 0.9
            for at, lamp in ((-0.55, (96, 232, 140)), (-0.42, (255, 96, 96))):
                px[panel & (np.abs(vn - at) < 0.05) & (U > 0.935) & (U < 0.965)] = lamp
            px[m & (d >= 3.2) & (d < 4.2) & ~lid] = tint * 0.8
        elif kind == "tray":
            # An autopsy table. The sink, tap, grating and stains are the game's
            # and all stay: only the material changes, to bright brushed steel,
            # with a lip shadow and a lit edge added on top.
            grain = (((cross * 7919) % 13) / 13.0 - 0.5) * 0.05
            px[m] = ramp(STEEL, np.clip(0.34 + 0.62 * l + grain, 0, 1)[m])
            h_, s_, v_ = hsv(rgb_in[box])
            blood = m & (s_ > 0.40) & ((h_ < 20) | (h_ > 335))
            px[blood] = np.clip(rgb_in[box][blood] * 255 * np.array([1.0, 0.55, 0.55]), 0, 255)
            lip = m & (d >= 3.9) & (d < 4.9)
            px[lip] *= 0.72
            px[m & (d >= 3.0) & (d < 3.9)] = tint * 0.75
        elif kind == "slab":
            # a satin graphite top that keeps every mark the game drew on it
            px[m] = ramp(PANEL, np.clip(0.30 + 0.55 * l, 0, 1)[m])
            sheen = np.clip(1.10 - 0.25 * (yy - ys.min()) / max(1, ys.max() - ys.min()), 0.85, 1.10)[..., None]
            px[deep] = np.clip(px[deep] * sheen[deep], 0, 255)
            px[m & (d >= 3.2) & (d < 4.2)] = tint * 0.8
        elif kind == "fixture":
            # Wash fixtures. Porcelain comes out as clean white composite with the
            # game's broad shading but none of its stains, the fittings as chrome,
            # and a bowl as dark glass with one thin line of light round its rim.
            h_, s_, v_ = hsv(rgb_in[box])
            # A stain is warm and a fitting is neutral, so only warm pixels are
            # smoothed away. Taps, basin lines, drains and drainer ridges are
            # neutral grey and keep every pixel of their shading.
            soft = nd.gaussian_filter(np.where(m, l, float(l[m].mean())), 2.5)
            stain = m & (s_ > 0.10) & ((h_ < 70) | (h_ > 320))
            tone = np.where(stain, np.maximum(soft, l), l)
            shell = m & (tone > 0.55) & ((s_ < 0.30) | stain)
            px[shell] = ramp(WHITE, np.clip(0.30 + 0.72 * tone, 0, 1)[shell])
            chrome = m & (s_ < 0.18) & (l > 0.28) & (l <= 0.55)
            px[chrome] = ramp(STEEL, np.clip(0.30 + 1.15 * (l - 0.28) / 0.27 * 0.6, 0, 1)[chrome])
            pit = nd.binary_opening(m & (d >= 3) & (l < 0.48), iterations=1)
            pits, count = nd.label(pit)
            for j in range(1, count + 1):
                bowl = pits == j
                if bowl.sum() < 40:
                    continue
                bowl = nd.binary_fill_holes(nd.binary_closing(bowl, iterations=2)) & m
                by, bx = np.nonzero(bowl)
                depth = nd.distance_transform_edt(bowl)
                glass = np.array([30, 34, 40.0])[None, :] + (depth[bowl] / max(1.0, depth.max()))[:, None] * np.array([26, 40, 52.0])
                px[bowl] = glass
                glint = bowl & (np.hypot(yy - (by.min() + 0.32 * (by.max() - by.min())), xx - (bx.min() + 0.36 * (bx.max() - bx.min()))) < 1.6)
                px[glint] = np.array([210, 236, 246.0])
                lip = nd.binary_dilation(bowl, iterations=2) & ~nd.binary_dilation(bowl, iterations=1) & m
                px[lip] = np.array([150, 214, 236.0])
        elif kind == "surface":
            # Canteen tables, benches and serving counters. The top is one
            # manufactured sheet: the game's broad light without its smears, a
            # brushed grain along its length and a panel joint every metre.
            h_, s_, v_ = hsv(rgb_in[box])
            top = nd.binary_opening(m & (l > 0.58) & (s_ < 0.22), iterations=2)
            if top.any():
                ty, tx = np.nonzero(top)
                wide = (tx.max() - tx.min()) >= (ty.max() - ty.min())
                soft = nd.gaussian_filter(np.where(top, l, float(l[top].mean())), 3.0)
                run = xx if wide else yy
                over = yy if wide else xx
                grain = (((over * 2654435761) % 7) / 7.0 - 0.5) * 0.035
                px[top] = ramp(STEEL, np.clip(0.74 + 0.22 * soft + grain, 0, 1)[top])
                joint = top & ((run - (tx.min() if wide else ty.min())) % 32 == 31)
                px[joint] *= 0.86
                edge = top & ~nd.binary_erosion(top, iterations=1)
                px[edge] *= 0.90
        elif kind == "hob":
            # An induction cooker. Each ring the game drew becomes a disc of black
            # glass with one fine heat line; the steel round it is cleaned.
            h_, s_, v_ = hsv(rgb_in[box])
            steel = m & (l > 0.55) & (s_ < 0.22)
            soft = nd.gaussian_filter(np.where(m, l, float(l[m].mean())), 2.0)
            px[steel] = ramp(STEEL, np.clip(0.70 + 0.26 * soft, 0, 1)[steel])
            dark = nd.binary_opening(m & (d >= 3) & (l < 0.32), iterations=1)
            rings, count = nd.label(nd.binary_fill_holes(nd.binary_closing(dark, iterations=2)))
            for j, sl in enumerate(nd.find_objects(rings), 1):
                disc = rings == j
                area = disc.sum()
                hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
                if area < 150 or not 0.6 < hh / max(1, ww) < 1.6 or not 0.62 < area / (hh * ww) < 0.92:
                    continue                 # a ring is round; the oven door and the shadows are not
                cy, cx = (sl[0].start + sl[0].stop - 1) / 2, (sl[1].start + sl[1].stop - 1) / 2
                # the game draws a hob as an ellipse, so the heat line is one too
                r = np.hypot((yy - cy) / (hh / 2), (xx - cx) / (ww / 2))
                px[disc] = np.array([20, 21, 24.0])[None, :] + (np.clip(1 - r, 0, 1)[disc] * 14)[:, None]
                px[disc & (np.abs(r - 0.60) < 1.5 / min(hh, ww))] = np.array([255, 122, 64.0])
                px[disc & (np.abs(r - 0.28) < 1.2 / min(hh, ww))] = np.array([120, 58, 34.0])
        elif kind == "bars":
            # A cell door. Bars in polished steel, the wooden frame in graphite,
            # and the colour band untouched.
            h_, s_, v_ = hsv(rgb_in[box])
            bar = m & (s_ < 0.20) & (l > 0.45)
            px[bar] = ramp(STEEL, np.clip(0.5 + (l - 0.62) * 2.0, 0, 1)[bar])
            frame = m & (h_ >= 8) & (h_ <= 50) & (s_ > 0.25) & (v_ < 0.50)
            px[frame] = ramp(PANEL, np.clip(0.25 + 1.2 * l, 0, 1)[frame])
        elif kind == "console":
            # Everything the base pass made of the object stays. The one addition
            # is power: a display the game drew, vivid green or cyan or the paler
            # blue of a monitor wall, is lit in its own colour with scanlines.
            h_, s_, v_ = hsv(rgb_in[box])
            vivid_px = (s_ > 0.45) & (v_ > 0.45) & (h_ >= 70) & (h_ <= 270)
            glass_px = (s_ >= 0.25) & (v_ >= 0.35) & (h_ >= 190) & (h_ <= 250)
            lit = m & (d >= 2) & (vivid_px | glass_px)
            lit = nd.binary_fill_holes(nd.binary_closing(lit, iterations=1)) & m
            spots, n_spots = nd.label(lit)
            spot_boxes = nd.find_objects(spots)
            for j, area in enumerate(nd.sum(lit, spots, range(1, n_spots + 1)) if n_spots else [], 1):
                sy, sx = spot_boxes[j - 1]
                here = spots == j
                vivid = s_[here].mean() >= 0.55 or glass_px[here].mean() >= 0.8
                # vivid and close to a rectangle: dull paint and ragged art are neither
                if area < 60 or not vivid or area < 0.75 * (sy.stop - sy.start) * (sx.stop - sx.start):
                    lit[here] = False
            px[lit] = np.clip(rgb_in[box][lit] * 255 * 1.22 + 14, 0, 250)
            px[lit & (yy % 3 == 0)] *= 0.86
        elif kind == "sanitary":
            # bright composite, the one pale thing in a dark room, with lit water
            px[m] = ramp(WHITE, np.clip(l[m] * 1.08, 0, 1))
            water = m & (d >= 3) & (l < 0.42)
            px[water] = _shade((70, 205, 255), l[water], 0.8, 1.6)
            px[m & (d >= 1.5) & (d < 2.6)] = px[m & (d >= 1.5) & (d < 2.6)] * 0.7 + tint * 0.3
        elif kind == "rack":
            # the shelves and what is on them stay; bright spines become lit modules
            px[m] = ramp(PANEL, np.clip(0.18 + 0.75 * l, 0, 1)[m])
            spine = deep & (l > 0.62)
            px[spine] = np.clip(tint * 0.35 + np.array([150, 152, 156.0]) * (0.5 + 0.6 * l[spine][:, None]), 0, 255)
        elif kind == "seat":
            # charcoal upholstery on a graphite frame, with one line of piping
            px[m] = ramp(CLOTH, np.clip(0.15 + 0.85 * l, 0, 1)[m])
            px[m & (d >= 3.2) & (d < 4.0)] = tint * 0.7
        elif kind == "emitter":
            # the housing stays as the base pass left it; only what the game drew
            # bright, the bulb or the lens, is lit
            bulb = m & (l > 0.70)
            warm = tint * 0.25 + np.array([255, 250, 238.0]) * 0.75
            px[bulb] = np.clip(warm[None, :] * (0.55 + 0.5 * l[bulb][:, None]), 0, 255)
        elif kind == "vehicle":
            # livery, markings and lights stay; only the glass is lit
            h_, s_, v_ = hsv(rgb_in[box])
            glazing = m & (d >= 2) & (h_ > 170) & (h_ < 260) & (s_ > 0.15) & (v_ > 0.3)
            px[glazing] = _shade((150, 198, 222), l[glazing], 0.6, 1.3)
        elif kind == "glass":
            # smoked glass in a graphite frame
            px[m] = ramp(PANEL, np.clip(0.2 + 0.6 * l, 0, 1)[m])
            pane = m & (d >= 2.5)
            t = ((xx * 2 + yy) % 19 < 2)
            px[pane] = np.clip(np.array([74, 80, 88.0]) * (0.75 + 0.6 * l[pane][:, None]) + t[pane][:, None] * 26, 0, 255)
            px[m & (d >= 1.5) & (d < 2.5)] = tint * 0.75
        out[box] = px
        done[box] |= m
    return done
PANEL = [(0.00, (15, 15, 17)), (0.35, (34, 35, 38)), (0.70, (62, 63, 67)), (1.00, (116, 118, 123))]
# worktops and casework: a mid titanium, light enough that whatever sits on it still reads
COMPOSITE = [(0.00, (22, 22, 25)), (0.40, (92, 94, 99)), (0.75, (168, 170, 175)), (1.00, (232, 233, 236))]
CLOTH = [(0.00, (18, 18, 20)), (0.45, (52, 53, 57)), (0.80, (96, 98, 103)), (1.00, (168, 170, 176))]
STEEL = [(0.00, (10, 10, 12)), (0.30, (46, 47, 51)), (0.65, (108, 110, 115)), (0.88, (176, 178, 184)), (1.00, (234, 235, 238))]


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
    # A warm colour is one of two things. Laid on thick it is a material: a table
    # top, a door, a crate. Laid on thin it is a marking: the band that says
    # which jail door this is, a cross, a label, a spark. Materials change and
    # markings stay, and thickness is what tells them apart.
    warm = solid & (h >= 12) & (h <= 62) & (s > 0.22) & (v > 0.12)
    # Decided a whole region at a time, by how thick it is at its thickest, so a
    # door's thin bottom edge goes with the door and no scrap is left behind.
    regions, count = nd.label(warm)
    wood = np.zeros_like(warm)
    if count:
        thickest = nd.maximum(nd.distance_transform_edt(warm), regions, range(1, count + 1))
        wood = np.isin(regions, 1 + np.nonzero(np.asarray(thickest) >= 5)[0])
    # Bars, fences and doors named for a colour carry warm paint only as a
    # marking, however wide the band, and keep it.
    if no_strip is not None:
        wood &= ~no_strip
    cloth = solid & (h > 62) & (h <= 170) & (s > 0.12) & (v > 0.15)
    grey = solid & (s <= 0.22) & ~warm & ~cloth
    blue = solid & (h > 170) & (h <= 270) & (s > 0.22)

    out = rgb * 255
    # Each piece keeps its own light and shade around a light middle tone, so
    # nothing comes out darker than the game drew it.
    lab, n = nd.label(wood)
    if n:
        idx = np.arange(1, n + 1)
        mean = np.zeros(n + 1)
        mean[1:] = nd.mean(lum, lab, idx)
        t = 0.62 + (lum - mean[lab]) * 1.5
        out[wood] = ramp(COMPOSITE, t[wood])
    # Greens and blues keep most of their colour and all of their brightness.
    # Pale blue is ice, water or a lit screen, and is left exactly alone.
    for fabric, strength in ((cloth, 0.70), (blue & (v <= 0.75), 0.60)):
        grey_px = lum[fabric][:, None] * 255
        out[fabric] = np.clip(grey_px + (rgb[fabric] * 255 - grey_px) * strength, 0, 255)
    # Metal and paintwork that were already grey stay the brightness they were,
    # brought to a true neutral with a little more contrast.
    val = np.clip(0.5 + (lum[grey] - 0.5) * 1.10, 0, 1) * 255
    out[grey] = np.stack([val, val, np.clip(val * 1.012, 0, 255)], -1)

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
            # A surface with things on it has a ragged outline, and a line
            # traced round that staggers. Only a clean rectangle carries one.
            if sizes[lab - 1] < 0.90 * (y1 - y0) * (x1 - x0):
                continue
            if cut % 2 == 1:    # a pair of rails along the long side; otherwise a closed loop
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
