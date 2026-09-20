#!/usr/bin/env python3
"""Re-materials the man-made walls and floors of the game's tileset.

Usage: python gen_tiles.py <materials folder> <source tilesetpadded.png> <out.png> [<out2.png> ...]

Every wall and floor in the game is one file, tilesetpadded.png, and the game
keeps a single copy of it: the one from the last mod in the load order. Sci-Fi
Security already ships that file with its laser fences drawn into the cells the
game leaves empty. So the source is Security's tileset, only the cells of the
materials listed below are touched, and the same result is written into both
mods. Whichever loads last, walls, floors and fences are all there.

A material is treated by name, never by guessing from its colour, and is only
ever re-materialled: brick keeps its mortar joints, a wooden floor its plank
lines, a tiled floor its grout. Natural ground, carpets, the rustic and ruined
walls, and the colour bands of the security-sector walls are left as drawn.
"""
import os
import re
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skin  # noqa: E402

CELL, PAD, TILE = 72, 4, 64
WALL_BLOCK = (7, 4)          # a Connected wall is a block of pieces this many cells

# material -> how it is re-materialled
#   neutral    what is grey becomes a true neutral with a little more contrast; colour stays
#   composite  warm brick and wood become titanium, keeping every joint and line
#   metal      neutral, with the contrast of bare plate
FLOORS = {
    "ConcreteFloor": "neutral", "ConcreteTiles": "neutral", "PavingStone": "neutral", "CeramicFloor": "neutral",
    "FancyTiles": "neutral", "NewCheckeredFloor": "neutral", "HexagonalTiles": "neutral",
    "TriangularTiles": "neutral", "SolacoFloor": "neutral",
    "WoodenFloor": "composite", "DarkWoodFloor": "composite", "LaminateFlooringFR": "composite",
    "ReclaimedBrickFloor": "composite", "MosaicFloor": "composite", "NewIronFloor": "composite",
    "MetalFloor": "metal", "NewCargoFloor": "metal", "GrateFloor": "metal",
}
WALLS = {
    "ConcreteWall": "neutral", "PerimeterWall": "neutral", "NewTiledWall": "neutral", "NewBBlockWall": "neutral",
    "BlueWall": "neutral", "BurgundyWall": "neutral", "GreenWall": "neutral",
    "WallMinSec": "neutral", "WallMedSec": "neutral", "WallMaxSec": "neutral", "WallInsaneSec": "neutral",
    "WallProtective": "neutral", "WallDeathRowSec": "neutral", "WallSuperMaxSec": "neutral",
    "BrickWall": "composite",
}
BEVELLED = {"ConcreteFloor", "ConcreteTiles", "PavingStone"}     # one plate to a tile


def materials(folder):
    found = {}
    for name in ("materials.txt", "materials_dlc.txt"):
        path = os.path.join(folder, name)
        if not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8", errors="replace").read()
        for block in re.findall(r"BEGIN Material(.*?)\nEND", text, re.S):
            label = re.search(r"Name\s+(\S+)", block)
            kind = re.search(r"SpriteType\s+(\S+)", block)
            cells = [(int(a), int(b)) for a, b in re.findall(r"BEGIN Sprite\d+\s+x\s+(\d+)\s+y\s+(\d+)", block)]
            if label and kind and cells:
                found[label.group(1)] = (kind.group(1), cells)
    return found


def cells_of(kind, cells):
    if kind == "Connected":
        (x, y), (w, h) = cells[0], WALL_BLOCK
    elif kind == "Linked":
        # The concrete wall names four of its pieces; the set is the wall block at
        # the sheet's origin.
        (x, y), (w, h) = (0, 0), WALL_BLOCK
    else:
        (x, y), (w, h) = cells[0], (cells[1] if len(cells) > 1 else (1, 1))
    return [(x + i, y + j) for j in range(h) for i in range(w)]


def vivid_share(cell):
    """How much of a cell is vivid green or yellow."""
    rgb = cell[..., :3].astype(float) / 255
    h, s, v = skin.hsv(rgb)
    on = cell[..., 3] > 127
    if on.sum() < 50:
        return 0.0
    return float((on & (s > 0.45) & (v > 0.4) & (h >= 35) & (h <= 170)).sum()) / float(on.sum())


def foreign_cells(sheet, cells):
    """A wall block is a grid of pieces, and the game fills its spare corners
    with other things: a toolbar icon, tufts of grass. Such a cell is vivid
    where the wall is not. A wall whose own band is green or yellow is vivid
    in every piece, so a cell is judged against the rest of its block."""
    shares = {}
    for cx, cy in cells:
        box = sheet[cy * CELL:(cy + 1) * CELL, cx * CELL:(cx + 1) * CELL]
        if box.shape[:2] == (CELL, CELL) and (box[..., 3] > 0).any():
            shares[(cx, cy)] = vivid_share(box)
    if not shares:
        return set()
    usual = float(np.median(list(shares.values())))
    return {c for c, share in shares.items() if share > 0.12 and share > 3 * usual + 0.05}


def rematerial(rgba, mode, mid=0.5):
    rgb = rgba[..., :3].astype(float) / 255
    h, s, v = skin.hsv(rgb)
    lum = rgb @ np.array([0.299, 0.587, 0.114])
    out = rgb * 255
    grey = s <= 0.25
    gain = 1.22 if mode == "metal" else 1.08
    val = np.clip(0.5 + (lum - 0.5) * gain, 0, 1) * 255
    out[grey] = np.stack([val, val, np.clip(val * 1.012, 0, 255)], -1)[grey]
    if mode == "composite":
        # One continuous mapping for the whole material. Sorting pixels into grey
        # and warm at a threshold maps neighbours either side of it differently,
        # which shows as speckle on brown. Only a vivid cool marking is left out.
        marking = (s > 0.45) & (h > 62) & (h < 345)
        # a dark material stays the darker one, so iron, brick and wood do not all land on one grey
        t = np.clip(0.30 + 0.55 * mid + (lum - mid) * 1.35, 0, 1)
        out = np.where(marking[..., None], rgb * 255, skin.ramp(skin.COMPOSITE, t.ravel()).reshape(rgb.shape))
    res = rgba.copy()
    res[..., :3] = np.clip(out, 0, 255).astype(np.uint8)
    return res


def main():
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    folder, source, outs = sys.argv[1], sys.argv[2], sys.argv[3:]
    sheet = np.array(Image.open(source).convert("RGBA"))
    vanilla_path = os.path.join(folder, "tilesetpadded.png")
    vanilla = np.array(Image.open(vanilla_path).convert("RGBA")) if os.path.exists(vanilla_path) else sheet
    known = materials(folder)
    done, skipped, bevels = 0, [], 0
    for table in (FLOORS, WALLS):
        for name, mode in table.items():
            if name not in known:
                skipped.append(name + " (not in materials)")
                continue
            block = cells_of(*known[name])
            # the mid-tone is the material's, not each tile's, so tiles stay the same brightness
            tones = [sheet[cy * CELL:(cy + 1) * CELL, cx * CELL:(cx + 1) * CELL] for cx, cy in block]
            tones = [c for c in tones if c.shape[:2] == (CELL, CELL) and (c[..., 3] > 127).any()]
            mid = float(np.median(np.concatenate([(c[..., :3][c[..., 3] > 127] / 255.0) @ np.array([0.299, 0.587, 0.114]) for c in tones]))) if tones else 0.5
            odd = foreign_cells(sheet, block) if table is WALLS else set()
            for cx, cy in block:
                box = (slice(cy * CELL, (cy + 1) * CELL), slice(cx * CELL, (cx + 1) * CELL))
                if sheet[box].shape[:2] != (CELL, CELL) or not (sheet[box][..., 3] > 0).any():
                    continue
                if (cx, cy) in odd:
                    skipped.append("%s cell %d,%d (not a piece of the wall: an icon or plants share its block)" % (name, cx, cy))
                    continue
                if not np.array_equal(sheet[box], vanilla[box]):
                    skipped.append("%s cell %d,%d (another mod's drawing sits there)" % (name, cx, cy))
                    continue
                cell = rematerial(sheet[box], mode, mid)
                inner = cell[PAD:PAD + TILE, PAD:PAD + TILE]
                wraps = np.array_equal(np.pad(sheet[box][PAD:PAD + TILE, PAD:PAD + TILE], ((PAD, PAD), (PAD, PAD), (0, 0)), mode="wrap"), sheet[box])
                if name in BEVELLED and wraps:
                    # one plate to a tile: a light edge above and to the left, a dark one below and to the right
                    plate = inner.astype(float)
                    plate[0, :, :3] *= 1.07
                    plate[:, 0, :3] *= 1.07
                    plate[-1, :, :3] *= 0.80
                    plate[:, -1, :3] *= 0.80
                    inner = np.clip(plate, 0, 255).astype(np.uint8)
                    cell = np.pad(inner, ((PAD, PAD), (PAD, PAD), (0, 0)), mode="wrap")
                    bevels += 1
                sheet[box] = cell
                done += 1
    for out in outs:
        Image.fromarray(sheet).save(out, optimize=True)
        print("wrote", out)
    print("re-materialled %d cells, %d of them bevelled" % (done, bevels))
    for line in skipped:
        print("  skipped:", line)


if __name__ == "__main__":
    main()
