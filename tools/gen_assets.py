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
    r"|PestControl\d|Hand(?!Dryer)|Face|Head|Body|Tattoo(?!Removal)|Female|OldMale|OldFemale|Male[A-Z]|\w*Warden$|Sniper\d|ElectricalSkeletal|Rat_|RobotDogDoo|RobotEyes|SignLetter|SignNumber|Stack(?:Books|Mail|Meal|Food|Plates|PrisonerLetter|ShopGoods)|ShopGoods|Books(?!helf)|FountainSpray|OutdoorSprinklerSpray|DamageCable_Spark|Ornamental_|MoreContraband|SubsidenceDamageAlert|Mac10|ChainsawWeapon|BarbedWireBat|FirstAidBackpack|SafetyGoggles|DogLeash|DogBowl|Bandana|RedFace|PoppingVein|DogPaw|RankInsignia|Photo"
    r"|PrisonUniform|StackPrisonUniform|GuardUniform|StabVest|Banner|StrikePlacard|Rat$|Dog$|GuardDog|Cat$|Bird|Chicken|Cow$|Pig$|Accountant|Actor|Warden|AnimalTherapist|Anthony|ArmedGuard|Avatar|Benedict|BountyHunter|CameraMan|Ceo|Chef|Chief$|Detective|Doctor|DogHandler|Edward|EliteOp\d*$|Farmer|Fireman|Foreman|Gardener|Guard\d*$|GuardArmour|Guard(?!Locker|Tower)[A-Z][a-z]+(Digging|Sitting|Sleeping)?$|GymInstructor|Heller|Henchman|Hostage|Hurst|InsaneInmate|Janitor|Keane|Kerry|Lawyer|Mac$|Morgan|Negotiator|NewsReporter|Nico|Orderly|PalermoDaughter|Paramedic(?!sHeli)|Parole|Priest|Prisoner(?!Bus)|Psychiatrist|Repairman|RiotGuard|SecurityGuard|Shrink|Sniper$|Soldier|Sonny|Teacher|TheDon|Therapy|TruckDriver|Tux|Waterman|Workman|Wrinkle|Zombie|Dummy|Skeletal|FrozenCharacter|HybridBody|Baked|Raw|Flour|Barley|Cereal|Fig|MixedFruit|Dough$|Cake|D11Food|D11Ingredient|D11Stack|Restaurant|Drink$|Cup$|Plate|HayBale|Fertilizer|BloodSplatter|DogDoo|RatDroppings|SpiderWeb|Ivy|Fern|BorderPlant|Topiary|WillowTree|KayuMalam|BareTree|FallenTree|Ebony|\w*Icon$|Satisfaction|Marker|Graffiti|LoveLetter|Mail(?!Box)|Newspaper|PrisonerLetter|Book$|GameBible|Painting|Canvas|Rorschach|Ak47|AssaultRifle|Axe|Crowbar|Drill|Fork|Gun$|Hammer|Knife|Lighter|Rifle|Saw$|Scissors|Screwdriver|Sheers|Shotgun|Spade|Spoon|Spatula|Whisk|RollingPin|Trowel|Rake|Mop|Tazer|StunBaton|Club|Baton|Keycard$|JailKey|MobilePhone|Medicine$|MoneyBag|GoldPocket|PianoWire|Rope$|ClimbingRope|WoodPickAxe|WoodenSpoon|Stick$|Modified|BatteringRam|RiotShield|Shackle|StraitJacket|TrackingBelt|PaperDragon|PaperLantern|Couplet|JackOLantern|PinkFlamingo|GardenGnome|MooseHead|BirthdayPresent|Gravestone|Tombstone|gravestone|ChurchStatue|OxStatue|WardenStatue|StoneWaterSpout|HeliShadow|Nothing$|Connection|Concrete$|Brick$|Wood$|SheetMetal$|Girder$)",
    re.I)

# Sprites that change colour but carry no light strip: bars and mesh, where a
# strip has no flat panel to sit on.
NO_STRIP = re.compile(r"^(d_)?(JailDoor|JailBars|SolitaryDoor|RoadGate|RoadBarrier|Fence|BarbedWire|Pipe|Drain)", re.I)

# Objects whose colour is their meaning: which staff may use a door, which remote opens it.
PAINTED = re.compile(r"(Door|Gate)\w*(Red|Blue|Orange|Yellow|White|Black|Maroon|Grey|Green)|(Red|Blue|Orange|Yellow)Door|Light(Red|Green)|TrafficLight|Arrow")

# Cells of the main sheet that hold signs no sprite bank names.
KEEP_CELLS = {"objects.png": ((35, 0, 4, 14), (0, 2, 2, 2))}

# What an object is for, by its name, which picks the colour of its trim.
# First match wins; anything unmatched is security, the beam blue.
PURPOSE = (
    ("medical", r"Medical|Morgue|Doctor|Nurse|Psych|Pharma|Infirm|Surgery|Defib|Methadone"),
    ("leisure", r"Pool|Tv|TV|Weights|Book|Radio|Sofa|Arcade|Game|Gym|Piano|Guitar|Altar|Prayer|Pew|Phone|Play|Swing|Yoga|Punch"),
    ("kitchen", r"Cooker|Fridge|Sink|Serving|^Table|^Bench|Tray|Kitchen|Canteen|Dish|Oven|Freezer|Vending|Drink"),
    ("power", r"Power|Generator|Capacitor|Water|Pump|Pipe|Boiler|Switch|Cable|Electric|Light|Sprinkler|Valve|Solar|Wind|Batter"),
    ("office", r"Desk|Filing|Office|Computer|School|Visitor|Chair|Shop|Till|Mail|Parole|Court|Lectern|Whiteboard"),
    ("labour", r"Workshop|Saw|Press|Carpenter|Laundry|Ironing|Cleaning|Garden|Farm|Forestry|Recycl|Loom|Sewing|Basket|Crate|Pallet|Truck"),
)
PURPOSE = tuple((skin.ACCENT_ORDER.index(k), re.compile(v)) for k, v in PURPOSE)


# Which kinds of object are rebuilt rather than recoloured, by name. First
# match wins. See skin.REMAKES.
REMADE = (
    ("none", r"GunRack|DumbbellRack|ShopShelfGoods|DoorMat|RoadGatePosts|LightningRod|Lighter|BoatDock|HorizontalBridge|Rotor|HeliInside|BoxingRing|CrateLabel|Sign$"),
    ("console", r"DoorControl|DoorServo|DoorTimer|MachineDoor|CabinetDoor|PhoneBooth|VideoCallBooth"),
    ("tray", r"MorgueSlab|Stretcher"),
    ("console", r"BedsideCab"),
    ("pod", r"^Bed$|^SuperiorBed$|^BunkBed$|^DoubleBed$|^MedicalBed$"),
    ("console", r"Cooker|Fridge|Freezer|Tv|TV|Phone|Arcade|Vending|Machine|Computer|Cabinet|Filing|Washer|Dryer|Microwave|Monitor|Control"
                r"|Terminal|Radio|Locker|Scanner|Detector|Till|Oven|Dispenser|Jukebox|Treadmill|WorkshopSaw|WorkshopPress|DoughMixer"
                r"|AutoHarvester|AutoGatherer|AutoScythe|Cctv|Router|PASystem|SonicDeterrent|Switch|PowerExportMeter|EEG|cinemaProjector"
                r"|FireAlarm|WeatherAntenna|Boombox|FirstAidStation|Cupboard|ChestOfDrawers|Hob$"),
)
REMADE = tuple((skin.REMAKES.index(k), re.compile(v)) for k, v in REMADE)


def view_rects(x, y, w, h, rot):
    """Where a sprite's other facings sit on the sheet, in cells. A side view
    is the sprite turned, so it is h wide and w tall and sits flush with the
    sprite's bottom edge - above its top when the sprite is wider than tall."""
    if rot == 1:
        return [(x + w, y, w, h), (x + 2 * w, y + h - w, h, w), (x + 2 * w + h, y + h - w, h, w)]
    if rot == 2:
        return [(x + w, y + h - w, h, w)]
    if rot == 3:
        return [(x + w, y, w, h), (x + 2 * w, y, w, h)]
    return []


def trim_maps(size, bank, drawn=None):
    """For every pixel, the purpose, trim cut and archetype of the sprite it
    belongs to. Facings are written first and named rectangles second, so a
    sprite always has the last word over its own ground."""
    import zlib
    shape = (size[1], size[0])
    accent, style, bare, arche, kept = (np.zeros(shape, np.uint8) for _ in range(5))
    owner = np.zeros(shape, np.int32)     # which picture a pixel belongs to: sprites that touch stay apart
    serial = [0]
    gap = np.full(shape, 9999, np.int32)   # how far each claimed pixel sits from the sprite that claimed it
    found = [s for s in sprites(bank) if s[1] * CELL < size[0] and s[2] * CELL < size[1]]
    # Toolbar pictures and icons are often a crop of the object itself, so they go
    # down first and the object they were cut from has the last word.
    found.sort(key=lambda f: not ("Toolbar" in f[0] or f[0].endswith("Icon")))

    def values(name):
        base = re.sub(r"^(d_)?", "", name)
        return (next((i for i, rx in PURPOSE if rx.search(base)), 0),
                zlib.crc32(base.encode()) % 4,
                1 if NO_STRIP.match(name) or PAINTED.search(base) else 0,
                0 if NO_STRIP.match(name) else next((i for i, rx in REMADE if rx.search(base)), 0),
                1 if KEEP.match(name) else 0)

    def write(rect, vals, far=0):
        """far is how many cells the rectangle sits from its sprite. A facing's
        place is predicted, and about one in ten predictions is wrong, so where
        two sprites claim the same ground the nearer one keeps it."""
        x, y, w, h = rect
        x0, y0 = max(0, x * CELL), max(0, y * CELL)
        x1, y1 = min(size[0], (x + w) * CELL), min(size[1], (y + h) * CELL)
        if x1 > x0 and y1 > y0:
            win = gap[y0:y1, x0:x1] >= far
            for m, v in zip((accent, style, bare, arche, kept), vals):
                m[y0:y1, x0:x1][win] = v
            serial[0] += 1
            owner[y0:y1, x0:x1][win] = serial[0]
            gap[y0:y1, x0:x1][win] = far

    for name, x, y, w, h, rot in found:
        for rect in view_rects(x, y, w, h, rot):
            write(rect, values(name), far=max(1, rect[0] - x))
    for name, x, y, w, h, rot in found:
        write((x, y, w, h), values(name))
    # A kept sprite's other pictures are not always where its rotate type puts
    # them. They are unnamed and can sit on either side of it - a stack of meals is named at
    # its fullest picture with the smaller stacks to its left - so direction is
    # no guide. What marks a sibling is that it looks like the sprite: the same
    # colours in much the same amounts. Anything else beside it is a neighbour.
    if drawn is not None:
        rgba = drawn
        solid = rgba[..., 3] > 127
        named = np.zeros(shape, bool)
        for name, x, y, w, h, rot in found:
            named[y * CELL:(y + h) * CELL, x * CELL:(x + w) * CELL] = True

        def colours(block):
            on = solid[block]
            if on.mean() < 0.03:
                return None
            hist = np.histogramdd(rgba[block][..., :3][on], bins=(4, 4, 4), range=((0, 256),) * 3)[0].ravel()
            return hist / hist.sum()

        for name, x, y, w, h, rot in found:
            if not KEEP.match(name):     # every kept sprite: the look-alike test is safe whatever the rotate type
                continue
            rows = slice(y * CELL, (y + h) * CELL)
            mine = colours((rows, slice(x * CELL, (x + w) * CELL)))
            if mine is None:
                continue
            for way in (-1, 1):
                for step in range(1, 4):            # no sprite has more than three other pictures
                    x0 = (x + way * w * step) * CELL
                    if x0 < 0 or x0 + w * CELL > size[0]:
                        break
                    block = (rows, slice(x0, x0 + w * CELL))
                    theirs = colours(block)
                    if named[block].mean() > 0.3 or theirs is None or 0.5 * np.abs(mine - theirs).sum() > 0.35:
                        break
                    kept[block] = 1
    return accent, style, bare.astype(bool), arche, kept.astype(bool), owner


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
             ("Table", "OfficeDesk", "Bookshelf"),
             ("Cooker", "Fridge", "PoolTable"))


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
        accent, style, bare, arche, kept, owner = trim_maps(img.size, os.path.join(game, bank), np.array(img))
        keep = kept | named_mask(img.size, os.path.join(game, bank), re.compile(r"(?!)"), KEEP_CELLS.get(sheet, ()))
        done = skin.reskin(img, mask=~keep, strips=False, no_strip=bare, accent=accent, style=style, arche=arche, owner=owner)
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
