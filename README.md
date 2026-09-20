# Sci-Fi Objects

A Prison Architect mod. It re-skins the game's objects as dark sci-fi hardware,
in the 2D view and the 3D one, so a prison built with Sci-Fi Security's laser
doors and fences is furnished to match. It changes art and nothing else: no
object, price, room or rule is touched.

## What changes

| The game draws | The mod draws |
| :--- | :--- |
| Wood and cardboard: tables, desks, doors, shelves, pool tables | Gunmetal panels with a blue light strip set in from the edge |
| Cloth and green plastics: bedding, sofas, bins | Deep teal |
| Metal and porcelain: sinks, toilets, showers, benches, cookers, fridges | Dark blue alloy, with a light strip on any large flat sheet |
| Outlines | Blue-black |
| Reds and blues already on an object | Kept, pushed toward neon |

Every object is built from the same three materials, which is what holds a room
together. What varies is the lit trim. Its colour says what the object is for:

| Trim | Objects |
| :--- | :--- |
| Beam blue | Doors, cells, cameras and anything else not listed |
| Green | Medical beds, the morgue, the infirmary |
| Amber | Cookers, fridges, sinks, serving and canteen tables |
| Orange | Power, water and the rest of the utilities |
| Violet | Pool tables, televisions, weights, bookshelves, phones |
| Ice white | Desks, filing cabinets, chairs, visitor tables |
| Yellow | Workshop, laundry, cleaning and farm equipment |

Its cut is one of four, a closed loop, corner brackets, a dashed loop or a pair
of rails, picked from the object's name so every view of one object matches. Big
panels are also split by plate seams and carry a short row of status lights.

The beam blue is the blue of a Laser Door's beam. Bars, mesh and pipes change
colour but carry no strip, because there is no flat panel for one to sit on.

People, animals, plants, food, fire, contraband, uniforms and the signs the game
draws over things are left exactly as the game drew them.

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
