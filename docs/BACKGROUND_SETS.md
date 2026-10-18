# Complete background sets

The scenery hack now treats nine reviewed world backgrounds as sets: World 1,
Green Greens, World 3, Wario Land, Random World, Metal Gear, Kid Icarus,
Ninja Gaiden and Mario Desert. Other scenes retain the existing scenery path.

The supported executable is SHA-256
`dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806`.
The catalogue contains metadata and hashes, not copyrighted game textures.
Textures are extracted from the user's verified copy during run preparation.

The native frame list is extended before MMF loads common data, resources and
instances. Existing non-cosmetic handles, coordinates and layer membership stay
intact. Allocations and destruction use MMF's own lifecycle. Worlds with gameplay
collision objects on the background layer only accept matching scroll factors.

Cloud movement is event-driven in the original worlds. Foreign worlds receive
the original alterable-C speed once per game tick; their own worlds keep the
original events. Cached object references are rebound when reset recreates them.
World 3's native Parallaxer renderer is retained; foreign worlds also advance its
original offset event. Its texture is imported before instance creation, using
MMF's absent-source sentinel and normal image importer, avoiding stale cached
source handles after F2. Pause freezes these cosmetic updates.

Plans are bound to the active run ID. Invalid plans leave the existing scenery
path active. Image dimensions, hotspots, source common-data hashes and PNG
headers are checked. Failed image batches restore original textures; an extension
with a missing or ambiguous texture is not instantiated. Existing seeds, routes,
progress and profiles are not rewritten by this presentation update. New runs
pin the preparation module and catalogue in their existing rules bundle.

Verification on 2026-10-18: all nine source sets and nine destination worlds,
35 R resets, animation and cloud-wrap checks, non-cosmetic frame-record equality,
and slots 1 → 2 → 3 → 1 with scenery on/off/on in one process. All 341 offline
tests passed. These checks do not claim a complete playthrough of every room,
a long-running memory-leak audit, or validation of all special boss effects.

## World 3 cloud mask correction (2026-10-18)

The first animation checks missed a visible shape regression: the importer
converted the cloud texture's black colour-key mask to alpha. Parallaxer's native
renderer determines scanline origins and widths by comparing pixel colours to
the colour key, so alpha-only imports exposed the source trapezoid edges.

World 3 clouds now use RGB PNGs with the original black key, explicitly passed
to the native importer. Other background assets retain alpha handling. Existing
frozen runs repair only their two generated cloud PNGs; seeded mappings and
saved rules are unchanged. Failed repairs invalidate the plan before loading.
The live regression compares all 296 scanline starts and widths against the
unmodified original, in World 3 and another world, after R and across F2 switches.

## Graphics diagnostics and retained decoration

Ctrl+Alt+D contains independent temporary switches for background sets,
decoration, floor textures and the reviewed enemy/boss colour subset. A command
is bound to the current controller session, run and Windows game process. It
applies only at the next full level resource load; R alone may reuse images.
Loading a save clears the diagnostic override without changing its seed rules.

Ctrl+Alt+M and manual reports include a game-window-only XComposite capture when
available, capture and observation timestamps, the active background, native
status and a bounded history of 32 graphics changes. An unavailable screenshot
does not prevent the report. The desktop and other windows are never captured.

Imported background records are inserted before retained original decoration
and collision tiles. This keeps World 3's lower backdrop visible and preserves
all original gameplay record coordinates and relative ordering.

### Native object references

Imported scenery can add an object ID to MMF's per-frame object list. The engine then rebases cached object indices in event records. The runtime updates those cache fields in the injected mixed-reward context before strict validation, with bounded parsing and a fully validated batch before any writes. IDs, opcodes, operands, masks and reward assignments remain unchanged. Fast chest timing accepts its verified cache relocation. Frozen Kracko/Kid Icarus readers receive a read-only canonical view of three checksum-verified death-event blocks, only when every changed cache resolves to the original object ID. All other changes still fail validation. Existing seed rules and saved reward assignments are preserved.
