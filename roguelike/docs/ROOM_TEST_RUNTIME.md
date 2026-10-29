# Disposable Workbench room runtime

W5J supplies use the same capture/reset/latest boundary. Save items and room first;
parked drafts do not overlay capture. Opt-in app-local diagnostics also record
transient instance identities, selected rows, needs/HP and actual turn-advance
calls. Its once-only `supplies-injured` fixture sets hunger/thirst to 0.8 and HP to
max minus 15; subsequent actions run normal input/handlers. This is verification
setup, not an owner scenario editor. See [supplies](ITEM_AUTHORING.md).

W5M uses the same capture for saved ordinary equipment. Opt-in observations add
exact slot-to-inventory-row references, physical/discounted carrying weight,
effective AV and bounded traces around the **real** combat resolver as invoked by
ordinary outgoing/incoming callers. The trace returns the original result and
does not alter RNG or rules. The equipment journey uses no item, slot, AV,
discount, creature or health injection. Definition/factory evidence remains
distinct from these owned-use observations. Its separate ordinary-save fixture
loads in a fresh process/catalogue after a bag revision: copied common fields and
depleted generated room survive while definition-owned reductions change, including
over-capacity conservation and ordinary pickup refusal. Immutable captured restore
is a separate proof. See [equipment ownership](ITEM_AUTHORING.md#equipment-ownership-and-activation).

`room_test.py` implements `workbench-room-test-1` for an eligible saved ordinary
`room` (`authored-room-2`, `authored_submap`). It never invokes `main.py`'s campaign
startup/restart loop. The native host supplies every path and a unique snapshot
and session identity; renderer requests contain only a supported action and an
already owned document token.

## Frozen inputs

The host enumerates only top-level game entry/config files, engine/components/
entities/generation/rendering/world Python, consumed JSON/text data, Fonts/UI/
sprites assets, the two fixed room documentation references and requirements.
It separately copies the packaged pinned Python runtime. It does not traverse
personal saves, environments, Git, recovery or earlier sessions. Enumeration is
bounded by depth, file count and bytes. Reparse/symlink paths and external resource
references fail. Every copied file is checked against its source manifest; complete
saved-input inventories are rechecked after copy and captured production validation.
Accepted game/runtime files are read-only and reverified on every bootstrap.

The manifest binds logical project/source, room path/hash, complete file hashes,
contract/descriptor identity, runtime hashes, seed and fixed player profile.
Imports use the captured game and copied pinned runtime with isolated Python flags
and a controlled working directory. Bytecode is disabled; temporary files,
diagnostics, readiness, stop markers, save generations and working caches live
outside the payload. Required sprite sheets and glyph sheets must load. Saved
typography uses its production complete-profile fallback and reports diagnostics.
Unrelated loadable unsupported content is retained; required room/readable
dependencies receive focused checks without a repository-wide cleanup gate.
The preflight also constructs the actual staged foyer/player, equips its light
and enters the room through production descent before accepting a replacement.
Missing ordinary starting items fail that preflight. Optional UI panel absence or
decoding failure retains the game's plain-panel fallback with explicit warnings.

## Gameplay and persistence ownership

`SaveManager(save_root=...)` is injected into `Engine` before any startup probing,
checkpoint restoration or cache lookup. Ordinary `SaveManager()` defaults remain
`saves/slot_0`. There is no global save-directory mutation. `engine/player_setup.py`
shares normal components and six starter items with ordinary `main.py`; a real
tallow torch is used/equipped through ItemSystem. `debug_mode=False` is a supported
per-engine option so ordinary F5/F9 and controls are available without rewriting
the project's configuration.

The test builds a one-chunk world and a small wall-bounded foyer with physical
stairs_down linked to one `SubMap` (`room-test-instance`). That instance is distinct
from both layout definition ID and host session ID. Normal `_try_descend` and
`create_submap` populate and enter the room, own the surface cache and retain actual
entry/return metadata. Normal ascent and return reuse cached scenes. Attempts to
cross a chunk boundary explain the test limit. Movement, reach, combat, needs,
lighting and AI within those scenes use ordinary production rules.

F5/F9 restore only this session's state and retain missing-owned-cache refusal.
`--session <host-owned session.json> --load` is the supported bounded fresh-process
checkpoint bootstrap, used by verification without adding a resume-library UI.
Quit/death exits this entry point; Workbench Reset remains available. Reset uses
the same frozen inputs, seed and profile with fresh mutable state. A seed describes
generation inputs, not deterministic combat replay.

## Native lifetime and cleanup

Game ownership has a separate mutex/generation from the request worker. Capture
and validation run asynchronously; cancellation/project replacement invalidates
unfinished work. At most one game runs per host. Capturing a newer version leaves
the previous test usable until the new capture validates. A successful replacement
reaps the prior child and discards only its positively identified mutable root.
If later process startup fails, the captured version remains available for reset
and the failure is disclosed.

Readiness requires a completed actual rendered frame/input loop and matching
contract/session/snapshot/PID. Startup has a 45-second deadline. The host drains
both pipes into bounded diagnostics, records real exit codes, gracefully requests
Stop, then terminates/reaps after two seconds if needed. Each owned child has a
Windows Job Object with kill-on-close; abrupt host termination kills its processes.
Ordinary close retains the existing authoring flush/recovery handshake.

Payloads live under the system temporary `ResonanceWorkbenchRoomTests` directory.
The ownership marker binds the creating PID and exact application path. Normal
cleanup is RAII-owned. Each later capture scans at most 128 directory entries and
removes at most four dead-owner payloads of this installation after complete bounded
link checks. Active owners, foreign installations and malformed roots are retained.
No user-selected directory becomes a cleanup target. Former captured tests are not
restored after Workbench restart.

An opt-in packaged fixture feeds only ordinary pygame keyboard events and captures
actual frames/observations under the owned mutable root. It is enabled by a native
process environment flag, never renderer-selected executable/commands/paths.

## Preparation tests

The captured runtime includes saved recipes, item definitions, processing
messages and relevant code. W5K uses ordinary CraftScreen input and placement,
then ordinary turns, floor pickup and supply use. Confirmation includes the
first processing tick. Reset keeps the earlier recipe/item capture; latest-saved
testing captures revisions. Synthetic authoring probes establish no placement
or completed preparation. Cold compatibility uses a separate owned ordinary save.
See [recipe authoring](RECIPE_AUTHORING.md) for captured job/current output rules.

## Furnished room tests

W5L captures direct furnishings with the same game-owned admission/construction
used by preview, assignment admission and native lazy generation. No event supplies
the demonstration's decor or heat. The existing needs-only fixture may establish
measurable supply use; ordinary actions apply afterward. Opt-in observations expose
actual light emitters and visible cells beyond the player's circle, so extinguishing
the player torch through normal controls can establish the static lamp's FOV
contribution. This is not an added RGB-lighting rule. Campfire interaction changes
the map-owned ID and persists through ordinary leave/return and cold saves.

The host can still validate an older immutable `authored-room-1` capture with its
own captured runner; new captures require the current room contract. Frozen-capture
restoration and fresh-catalogue compatibility remain separate checks. An already
generated ordinary save keeps actual old furnishing positions, changed fire state
and removed objects after a same-ID room revision. Missing owned scene/cache data
still refuses regeneration.
