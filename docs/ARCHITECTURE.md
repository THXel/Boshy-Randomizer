# Runtime architecture

## Maintained source and deployed layout

`tools/layout.py` maps domain directories to stable deployed filenames. Python
modules and native sources keep their names; shared helpers keep `PY/`, public
catalogues keep `INI/`, and artwork keeps its existing resource paths. Duplicate
runtime destinations and linked sources are rejected before a build changes.

`tools/build.py` assembles that map in a temporary directory, invokes the native
compiler helpers, binds generated integrity hashes, and publishes `build/runtime/`.
Both package formats consume this same verified build. The mapping and hashes
are recorded with the build, so package creation cannot silently use stale source.

This boundary is deliberate. Frozen runs load flat module names and hash resource
paths. Moving source directly into import packages would change those contracts.
The deployment shape remains stable while the authoring tree becomes navigable.
There is one maintained copy of each module; files in `build/` are generated.

## Main execution paths

- **Menu:** application entry → `native_menu_host` → `MenuController` → `Menu` + `Renderer` +
  `MenuGame`. The native game window hosts menu interaction; the Python controller
  coordinates actions. Loading presentation is separate from audio muting.
- **Save deletion:** loading cover with preserved audio → `LiveSession.transaction`
  → `SessionStore.delete` → native save/profile reload → close cover. The game
  process stays alive. The delete journal and backup remain authoritative.
- **Start/resume:** validate the save and its binding → select `Rules` → activate
  its profile → start `Player`. Compatible runs attach to the menu process;
  archived incompatible native payloads retain the existing cold-start path.
- **Gameplay:** native telemetry → completion/reward guards → durable progress
  → acknowledged transition. Observed boss HP alone is not a universal exit.
- **Saved rules:** `runtime_versions.Rules` verifies an immutable bundle before
  loading it. Narrow, versioned repairs fix known defects without rerolling the
  saved seed, options, route or rewards.
- **Presentation:** graphics/audio modules prepare plans; native patches apply
  them. Tracker and diagnostics consume state without owning progression.
- **Platform:** Windows/Linux APIs handle processes, windows, paths, audio and
  filesystem locking. Rule selection stays shared.

## Ownership rules

1. Edit `src/`, `assets/`, `tests/` and `tools/`; never patch generated runtime files.
2. Keep installation data, imported games, saves and downloaded soundpacks outside
   the source and build trees. Never treat a private runtime as a packaging source.
3. Add regression coverage at the boundary that failed: native rendering for
   object/image ownership, saved-rule fixtures for compatibility, runtime tests
   for menu/session behavior, and tooling tests for assembly/package boundaries.
4. Preserve evidence levels. A compiler or unit-test success is not proof of a
   natural boss victory, audible playback or Windows VM installation.

## Menu controller internals

`app/native_menu_host.py` is the stable entry point. `app/menu_controller.py`
owns processes, save transactions, loading covers and cleanup. `app/menu_gameplay.py`
polls runs and presents results without owning the menu process. Native slot
selection belongs to `menu/menu_navigation.py`. A `RunExit` value carries the
return-to-menu decision and whether the result screen created a new-run draft.

Python uses Black with the checked-in `pyproject.toml`. Handwritten C and headers
use `.clang-format`; generated catalogue tables are not reformatted. Run
`python tools/check_style.py` after installing `requirements/development.txt`.
Import order is preserved. Legacy repair tests use fixed regression fixtures,
so formatting current code cannot accidentally remove their historical defect.
