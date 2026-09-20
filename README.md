# Sci-Fi Objects

A Prison Architect mod. It re-skins the game's objects as dark sci-fi hardware,
in the 2D view and the 3D one, so a prison built with Sci-Fi Security's laser
doors and fences is furnished to match. It changes art and nothing else: no
object, price, room or rule is touched.

## What changes

| The game draws | The mod draws |
| :--- | :--- |
| Wood and cardboard laid on thick: table tops, desks, shelves, plain doors, sheds | A light titanium composite that keeps the grain, the shading and everything sitting on it |
| Greens and blues: baize, bedding, upholstery | The same colour, quieter, at the same brightness |
| Metal and paintwork that is already grey | The same brightness, brought to a true neutral |
| Pale blue: ice, water, a lit screen | Left exactly alone |
| Beds, bunks, double and medical beds | A sleep capsule: composite hull, headrest, rows of light tubes, a raised smoked lid, a console at the foot, accented in the colour of the bed's own bedding |
| The autopsy table | Brushed steel, with its sink, tap, grating and stains all kept |
| Displays the game drew: monitor walls, arcade and machine screens | Lit in their own colour, with scanlines |

## What never changes

A warm colour is one of two things. Laid on thick it is a material, and changes.
Laid on thin it is a marking, the cross on a first aid kit or the label on a
bag, and stays. Doors and gates named for a colour keep all of it however wide
the band, because the colour is what says who may use them, and so do bars,
fences, traffic lights and arrows.

Nothing is made darker than the game drew it, and nothing is drawn over an
object: no outlines, no indicator rows, no glow. People, animals, plants, food,
fire, contraband, tools, weapons, uniforms and the signs and icons the game
draws over things are left exactly as the game drew them. A kept sprite's other
pictures are often unnamed in the sprite bank, so the generator also keeps any
picture beside one that shares its colours. An icon cropped from an object
follows that object.

## How it is built

Nothing is painted by hand. `tools/skin.py` reads each pixel's hue to tell what
it is made of and maps it through a colour ramp for that material, keeping the
game's own light and shade. `tools/gen_assets.py` runs it over the three object
sheets and the 3D colour sheet:

```bash
python tools/gen_assets.py "<the game's unpacked data folder>"
```

The game's art is inside `main.dat`, which is a RAR archive. The sprite banks
say which cells hold what, so the sprites that stay are masked out by name. On
the 3D sheet the shapes share colour swatches with the people, so the generator
reads every shape's texture coordinates and changes only what objects use and
no person does.

## Layout

| Path | Holds |
| :--- | :--- |
| `data/objects.png`, `data/objects_d11_2.png`, `data/objectsTexture_d11.png` | The re-skinned 2D sheets |
| `data/shapes/objects-maps.png` | The re-skinned 3D colour sheet |
| `tools/skin.py` | The pixel filter |
| `tools/gen_assets.py` | Builds every sheet and the card art |

Install by copying `manifest.txt`, `thumbnail.png` and `data/` into a folder
under the game's `mods` directory and turning the mod on in the game.

## Conflicts

The game keeps one copy of each object sheet, from the last mod in the load
order that ships one. Any other mod that replaces `objects.png` or the 3D
colour sheet wins or loses to this one whole. Mods that add their own objects
in their own `sprites.png` are unaffected and keep their own look.
