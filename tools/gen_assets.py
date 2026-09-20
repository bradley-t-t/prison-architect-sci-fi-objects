"""Builds every generated file the Sci-Fi Objects mod ships.

Outputs, relative to the mod root (the parent of this tools/ folder):
  data/objects.png               the game's object sheet, re-skinned
  data/objects_d11_2.png         the same for the sheet the expansions added
  data/objectsTexture_d11.png    and for the one before it
  data/shapes/objects-maps.png   the colours the game's 3D shapes are painted from

Usage: python gen_assets.py <the game's data folder, unpacked from main.dat>

Nothing here is drawn by hand. skin.py reads what each pixel is made of and
repaints it, so every view of every object changes together and an object the
game adds later is covered the day it arrives. What should stay as the game
drew it, the living, the edible and the signs, is left out by name below.
"""

import os
import re
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skin  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL = 32          # a sprite bank measures in cells this many pixels across

# Sprites the re-skin leaves alone: plants, food, fire, rubbish, what people
# carry and wear, and the signs the game draws over things.
KEEP = re.compile(
    r"^(d_)?(Tree|Bush|Plant|Flower|Hedge|Shrub|Grass|Crop|Seed|Vegetable|Fruit|Potato|Pumpkin|Corn|Wheat|Herb"
    r"|StackGrass|StackTrees|StackLogs|RawWood|Log"
    r"|Fire$|StrikeFire|Food|StaffFood|Ingredient|StackIngredients|StackMeals|Meal|Garbage|Rubble"
    r"|Booze|Cigs|BagOfDrugs|Poison|Pills|Needle|Alert|Powered|NoEntry|EscapeIcon|CrookedMarker"
    r"|WaterIcon|WaterOffIcon|Wave$|DoorLockedOpen|Light$"
    r"|Hand|Face|Head|Body|Tattoo|Bandana|RedFace|PoppingVein|DogPaw|RankInsignia|Photo"
    r"|PrisonUniform|StackPrisonUniform|GuardUniform|StabVest|Banner|StrikePlacard|Rat$|Dog$|GuardDog|Cat$|Bird|Chicken|Cow$|Pig$)",
    re.I)

# Sprites that change colour but carry no light strip: bars and mesh, where a
# strip has no flat panel to sit on.
NO_STRIP = re.compile(r"^(d_)?(JailDoor|JailBars|SolitaryDoor|RoadGate|RoadBarrier|Fence|BarbedWire|Pipe|Drain)", re.I)

# Cells of the main sheet that hold signs no sprite bank names.
KEEP_CELLS = {"objects.png": ((35, 0, 4, 14), (0, 2, 2, 2))}

# Who and what the 3D re-skin leaves alone, by the name of the shape.
KEEP_SHAPES = re.compile(
    r"^(armedGuard|chef|chief|doctor|dogHandler|fireman|foreman|gardener|guard|guardDog|janitor|paramedic|priest"
    r"|prisoner|riotGuard|sniper|sonny|warden|workman|tree|ingredient|stackingredients|stacklogs|foodtray"
    r"|stackfoodtrays)", re.I)

SHEETS = (("objects.png", "objects.spritebank"),
          ("objects_d11_2.png", "objects_d11_2.spritebank"),
          ("objectsTexture_d11.png", "objects_d11.spritebank"))


def sprites(bank):
    with open(bank, encoding="utf-8", errors="replace") as f:
        text = f.read()
    for m in re.finditer(r"Name (\S+)\s+x (\d+)\s+y (\d+)\s+w (\d+)\s+h (\d+)\s+RotateType (\d+)", text):
        name = m.group(1)
        x, y, w, h, rot = (int(v) for v in m.groups()[1:])
        yield name, x, y, w, h, rot


def named_mask(size, bank, pattern, cells=()):
    """True where a sprite whose name matches sits, and over the given cells."""
    mask = np.zeros((size[1], size[0]), bool)
    rects = [(x, y, w, h) for name, x, y, w, h, _ in sprites(bank) if pattern.match(name)]
    for x, y, w, h in list(rects) + list(cells):
        x0, y0 = x * CELL, y * CELL
        if x0 >= size[0] or y0 >= size[1]:
            continue          # a sprite on another sheet
        mask[y0:y0 + h * CELL, x0:x0 + w * CELL] = True
    return mask


def shape_masks(shapes_dir, size):
    """Where on the 3D colour sheet the shapes that change, and the shapes
    that do not, take their colours from."""
    from PIL import ImageDraw
    change = Image.new("1", size, 0)
    keep = Image.new("1", size, 0)
    for name in sorted(os.listdir(shapes_dir)):
        if not name.endswith(".obj"):
            continue
        uv, faces = [], []
        with open(os.path.join(shapes_dir, name), errors="replace") as f:
            for line in f:
                if line.startswith("vt "):
                    p = line.split()
                    uv.append((float(p[1]) % 1.0, float(p[2]) % 1.0))
                elif line.startswith("f "):
                    idx = [int(v.split("/")[1]) for v in line.split()[1:] if "/" in v and v.split("/")[1]]
                    if len(idx) >= 3:
                        faces.append(idx)
        draw = ImageDraw.Draw(keep if KEEP_SHAPES.match(name) else change)
        for idx in faces:
            pts = [(uv[i - 1][0] * size[0], (1 - uv[i - 1][1]) * size[1]) for i in idx if 0 < i <= len(uv)]
            if len(pts) >= 3:
                draw.polygon(pts, fill=1, outline=1)
    # The game filters this sheet as it draws, so a changed region is padded
    # by two pixels or the old colour shows along its edge.
    from scipy import ndimage as ndi
    change = ndi.binary_dilation(np.asarray(change, bool), iterations=2)
    return change, np.asarray(keep, bool)


# What the Workshop card shows, as rows of sprites from the main sheet.
CARD_ROWS = (("Bed", "BunkBed", "Toilet", "Sink", "ShowerHead", "Door"),
             ("Table", "OfficeDesk"),
             ("Bench", "PoolTable"))


def card_art(sheet, bank):
    """The re-skinned furniture on a clear ground, for the Workshop card."""
    where = {name: (x, y, w, h) for name, x, y, w, h, _ in sprites(bank)}
    rows = []
    for names in CARD_ROWS:
        cuts = []
        for name in names:
            x, y, w, h = where[name]
            cuts.append(sheet.crop((x * CELL, y * CELL, (x + w) * CELL, (y + h) * CELL)))
        rows.append(cuts)
    gap = 24
    width = max(sum(c.width for c in cuts) + gap * (len(cuts) - 1) for cuts in rows)
    height = sum(max(c.height for c in cuts) for cuts in rows) + gap * (len(rows) - 1)
    art = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    top = 0
    for cuts in rows:
        tall = max(c.height for c in cuts)
        left = (width - sum(c.width for c in cuts) - gap * (len(cuts) - 1)) // 2
        for c in cuts:
            art.alpha_composite(c, (left, top + (tall - c.height) // 2))
            left += c.width + gap
        top += tall + gap
    return art.resize((width * 2, height * 2), Image.NEAREST)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    game = sys.argv[1]
    out = os.path.join(ROOT, "data")
    os.makedirs(os.path.join(out, "shapes"), exist_ok=True)
    for sheet, bank in SHEETS:
        img = Image.open(os.path.join(game, sheet)).convert("RGBA")
        keep = named_mask(img.size, os.path.join(game, bank), KEEP, KEEP_CELLS.get(sheet, ()))
        bare = named_mask(img.size, os.path.join(game, bank), NO_STRIP)
        done = skin.reskin(img, mask=~keep, no_strip=bare)
        done.save(os.path.join(out, sheet), optimize=True)
        if sheet == "objects.png":
            card_art(done, os.path.join(game, bank)).save(os.path.join(ROOT, "tools", "card-art.png"), optimize=True)
        print("wrote", sheet, "leaving", int(keep.sum() / (CELL * CELL)), "cells as the game drew them")
    maps = Image.open(os.path.join(game, "shapes", "objects-maps.png")).convert("RGBA")
    change, keep = shape_masks(os.path.join(game, "shapes"), maps.size)
    skin.reskin(maps, mask=change & ~keep, strips=False).save(os.path.join(out, "shapes", "objects-maps.png"), optimize=True)
    print("wrote shapes/objects-maps.png")


if __name__ == "__main__":
    main()
