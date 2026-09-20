# Sci-Fi Objects

A Prison Architect mod. It re-skins the game's objects as dark sci-fi hardware,
in the 2D view and the 3D one, so a prison built with Sci-Fi Security's laser
doors and fences is furnished to match. It changes art and nothing else: no
object, price, room or rule is touched.

## What changes

| The game draws | The mod draws |
| :--- | :--- |
| Wood and cardboard laid on thick: table tops, desks, shelves, sheds | A light titanium composite that keeps the grain, the shading and everything sitting on it |
| Greens and blues: baize, bedding, upholstery | The same colour, quieter, at the same brightness |
| Metal and paintwork that is already grey | The same brightness, brought to a true neutral |
| Pale blue: ice, water, a lit screen | Left exactly alone |
| Beds, bunks, double and medical beds | A sleep capsule: composite hull, headrest, rows of light tubes, a raised smoked lid, a console at the foot, accented in the colour of the bed's own bedding |
| The autopsy table | Brushed steel, with its sink, tap, grating and stains all kept |
| Toilet, sink, shower head, kitchen sink | Clean white composite with the stains gone and every fitting kept; a toilet bowl is dark glass with one line of light round its rim |
| Canteen table, bench, serving table and their small versions | One brushed steel sheet, the smears gone, with a panel joint every metre |
| Cooker | Induction: each ring is a disc of black glass with a fine heat line, on cleaned steel |
| Doors: plain, double, staff, solitary, remote, visiting, secure, and the wooden ones outside | A powered two-leaf plate: a milled seam where the leaves meet, a recessed panel in each, chevrons cut at the leading edges and one status lamp. A door painted for a reason keeps that colour as the finish of the plate, so a staff door is still green and a visiting door still maroon; a wooden one becomes steel |
| Cell doors | Each bar is a machined mullion, lit down its middle and shaded at both edges, braced across once and set in a graphite rail with a lock block. The openings stay open and the colour that grades a door stays on it |
| Drains | A milled steel collar round a sunken well, with every hole the game drilled re-cut with depth |
| Displays the game drew: monitor walls, arcade and machine screens | Lit in their own colour, with scanlines |
| Built floors in grey: concrete, tiles, paving, ceramic, checkered, hexagonal, triangular | A true neutral at the same brightness; concrete, concrete tiles and paving stone get a lit top edge and a shaded bottom edge, so each slab reads as a panel |
| Built floors in brown: wood, dark wood, laminate, reclaimed brick, mosaic, iron | Titanium composite with the boards, bricks and pattern kept, and each one as dark or light as it was |
| Metal and grate floors | Neutral steel with more contrast |
| Built walls: concrete, perimeter, tiled, block, brick, the painted walls and every security grade | Neutral, or composite for brick, with each grade's colour band kept |

## What never changes

A warm colour is one of two things. Laid on thick it is a material, and changes.
Laid on thin it is a marking, the cross on a first aid kit or the label on a
bag, and stays. Doors and gates named for a colour keep all of it however wide
the band, because the colour is what says who may use them, and so do bars,
fences, traffic lights and arrows.

Three doors are left as the game drew them, because a steel plate would be
worse than what is there. The keycard door is already the future. The
ornamental gates and the mesh fence gates are openwork, and a solid plate
would fill them in. The secret door is meant to pass for a bookshelf, so it
goes on being a bookshelf, in titanium like every other shelf.

Nothing is made darker than the game drew it, and nothing is drawn over an
object: no outlines, no indicator rows, no glow. People, animals, plants, food,
fire, contraband, tools, weapons, uniforms and the signs and icons the game
draws over things are left exactly as the game drew them. A kept sprite's other
pictures are often unnamed in the sprite bank, so the generator also keeps any
picture beside one that shares its colours. An icon cropped from an object
follows that object.

## Which pictures belong to an object

A sprite bank names one picture of an object and the game finds the other
facings by rotate type. Measured over all 233 sprites of rotate type 1, the
second and third pictures resemble their sprite about nine times in ten, and the
fourth only three times in ten, because the game mostly mirrors the side view
and that ground belongs to a neighbour. So the fourth is claimed only when it
matches the third. A small sprite lying inside another's picture and sharing its
colours is a reused texture, the crate label being a square of the white canteen
table, and follows its host.

## Walls and floors

`tools/gen_tiles.py` re-materials the tileset one named material at a time, so
grass, dirt, sand, water, roads and every other natural tile stay as the game
drew them. The art deco wall keeps its gold, and the Solaco and cargo floors are
blue steel with hazard stripes already, so they stay too.

The game takes `tilesetpadded.png` whole from one mod, and Sci-Fi Security
already ships one carrying its laser fences. So the generator builds on
Security's file and leaves every cell that differs from the game's own alone,
and both mods ship the same result. Whichever loads last, the fences and the
floors are both there.

```bash
python tools/gen_tiles.py "<the game's unpacked data folder>" <Security's tileset> <out.png>
```

A tile is 64 pixels inside a 72 pixel cell. A floor's padding wraps round from
its opposite edge and a wall's repeats its own edge, and the generator keeps
both.

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
| `data/tilesetpadded.png` | The re-materialled walls and floors, with Sci-Fi Security's fences in it |
| `tools/gen_tiles.py` | Builds the tileset |

Install by copying `manifest.txt`, `thumbnail.png` and `data/` into a folder
under the game's `mods` directory and turning the mod on in the game.

## Conflicts

The game keeps one copy of each object sheet, from the last mod in the load
order that ships one. Any other mod that replaces `objects.png` or the 3D
colour sheet wins or loses to this one whole. Mods that add their own objects
in their own `sprites.png` are unaffected and keep their own look.

The tileset works the same way. Sci-Fi Security ships the identical file, so
the two never fight; a third mod that replaces `tilesetpadded.png` and loads
later takes the floors, the walls and the fences back to its own.
