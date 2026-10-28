# W5F — common creature authoring and truthful references

The twelve current Actor definitions now use the registered shared document
lifecycle. Six ordinary sources support bounded same-ID editing and new-ID
variants; the six ID-bound special Actors support same-ID editing while keeping
their behavior. Vine configuration, player, ambiguous and unsupported sources
remain inspectable with specific limits. Safe read-only Actor construction is
separate from write permission. No demonstration creature edits ship in game data.

## Revisions and inputs

| Boundary | Revision |
| --- | --- |
| Reviewed checkout and initial `origin/main` | `d942c3d52e53f091a6a2070e947caaf3b3c19b06` |
| Reference/identity correction | `e10238f9df2fdafca15284630e557ae826ca3dae` |
| Shared family implementation, guides, frontend/host/worker and package inputs | `3a1b4d1df7a0f734f677d1c757bc7c4e8f73c407` |
| Final native fixture input | `a3e83be21078a5e57c334780ac043db3547e9c6f` |
| Final controlled encounter/restore test input | `8a8746221dd30017c2f7ff968513409a0a3937d1` |
| Final existing-item journey synchronization | `40b47c317ade414a871d9f3d0daf6a4bb7a80a0f` |
| Final startup journey synchronization | `a032f7b1348465567ca29b19bff54b9cfbfd9679` |
| Evidence commit | Annotated `checkpoint/workbench-w5f-verified-20261027`; exact pushed SHA in the external handoff |

The post-implementation commits change only verification scripts. Packaged
frontend/host/bridge and selected-game implementation bytes remain identical.
The [machine receipt](w5f-verification.json) identifies 101 source files with Git
and tested-worktree hashes, package bytes, commands and ignored artifact hashes.
All 75 W5E Git hashes and 75 original tested-worktree hashes were reconciled before
the work. Start and reference/identity checkpoints retain the reviewed boundaries.
The existing `main` checkout was used throughout; no branch or development copy
was created. Fixture projects contain only disposable test inputs.

## Behavior and policy

`creature-common-1` registers explicit source-specific operations. The original
inspection freezes the permitted subset in the host; controls, validation,
review/apply and recovery all honor it. Candidate fields and stored recovery
metadata cannot promote the source. The independent host write/recovery boundary
is `roguelike/data/entities/creatures/`; ID collision checks include all entities.
The legacy single-creature slot and dedicated worker route were removed. The old
native singleton journey is replaced by the shared three-process creature journey.

Typed groups cover name/description, atomic mirrored HP, natural armour, strict
attack dice/bonus/verb, sight/darkvision, wander radius, pursuit timeout and speed.
Only ordinary new variants can choose another registered AI. Raw and recovered
source receive the same type/bound/reserved-`Player` checks. Same-ID identity,
tile, AI, bodies, ability settings and other protected/unknown data cannot change.
Exact-source primitives preserve unedited spans, missing fields, CRLF, escapes
and nested metadata. Invalid JSON remains recoverable without review authority.
Hearing, hostility and legacy Fighter values are explained without promising
unimplemented behavior. Exact bounds, corpus and activation rules are in the
[creature guide](../../roguelike/docs/CREATURE_AUTHORING.md).

Barrow Wight displays **Body supplied by inline limbs**, its stable special
binding, and why duplication is unavailable. The absent `body_id`'s implicit
unused fallback is informational; an authored unused fallback is distinguished.
An active missing body still blocks. Inactive `spawn_zones` is separate from
inbound saved layout placements and actual zone `creatures` declarations, with
paths and consumer meanings. Zone population tests chance in declaration order
and observes a maximum; its `weight` is not consumed. Neither reference rows nor
factory construction establish natural encounters. Saving a variant enrolls it
in no selector.

The named `data/zones/dungeon/barrow.json` remains byte-for-byte unchanged:
`66fd0580090053471a0b3d523242a893b54ce7d8c4700e0a4cbb1696f2f7da25`.
Only the obsolete duplicate `dungeon.json` was removed (original SHA-256
`3c09f624e3241b1973e034aa6d61090087bebf4e62102cfb39797b0b2b0323c9`).
No direct path consumer was found. One case-insensitive barrow ID remains;
creature entries, structures, ambient light, category, tags and loot inputs are
unchanged. The differing terrain palette has no runtime Python consumer. A
disposable duplicate still produces the meaningful catalogue warning.

Look descriptions, knowledge, speed/essence details, active/off-map pursuit,
adjacent stair/chunk definition checks and callouts now reuse
`effect_lifecycle.creature_id`. Presentation tiles and the existing ability
dispatcher remain intact. No save format, transition mechanic or restoration
policy was changed. W5E's report now accurately says its 42 cases accumulate
`_visible_rows`; its original provenance is retained.

## Observed production and native results

The final native journey uses three actual packaged WebView2 processes and
isolated project/settings/recovery roots. Two creature drafts plus an invalid
item draft remain independent across keep/close, cold restart and abrupt exit.
Invalid BOM/Unicode source survives; review authority does not. Special clone and
forged variant intent are refused without deleting stored text. A changed ability
module revokes applicable evidence, and stale apply is refused without writing.
The source encoding must still be accepted by the production JSON loader; draft
preservation does not make a BOM-prefixed definition loadable.

The wight is published at the same ID with name `W5F native Wight`, mirrored HP37,
armour6, sight3 and `2d5`. Exact draft, saved and reopened SHA-256 are
`7e48dead8167c56baa10a7addac21e7b39c735374eb46a603bd1fe8be3df7536`.
The ordinary `w5f_native_variant` shares `hollow_revenant`'s tile, uses AmbushAI,
HP19, its own description, speed1.25 and pursuit2. Its exact draft/saved/reopened
hash is `65628f3efa45e7d9edbba23e0587e068f4450dc995d406882e990f61ff07abb5`.
Original ordinary-source bytes and the other recovery copies remain intact.
Receipt generations and exact invalid-draft hashes are recorded in the JSON.

That saved variant is selected, constructed and published through the existing
authored-submap controls. The saved room hash is
`fd357faee6a604723d910fb3056446a024e7a8b9ae1ea43d7807cd6222eeeebf`.
A separate packaged-Python process reads those exact native-published files,
calls production `preview/create_submap`, then runs the resulting Actor through
`Engine._advance_turn`, AmbushAI and the real attack resolver: HP19, correct ID,
own description, four observed damage and a 0.25 scheduling remainder.

A distinct controlled runtime fixture checks visible/last-known Look prose,
rendered own-ID knowledge and essence, speed, callouts, actual monster attack,
active pursuit and the real off-map pursuer loop against deliberately different
tile-linked template values. It observes five damage from `1d1` plus four,
pursuit expiry at two, and a 0.25 speed remainder. The hibernating stone lurker
keeps `stone_lurker` identity while presenting as rock and after waking. A
same-tile new-ID wight clone receives no special binding.

The injured-wight fixture serializes real component state, changes only its
disposable definition, then restores in a fresh process:

| Value | Saved/restored | Fresh actor |
| --- | --- | --- |
| Name | Barrow Wight | W5F fresh Wight |
| Current / maximum HP | 7 / 20 | 41 / 41 |
| Natural armour | 3 | 9 |
| Sight / darkvision | 7 / true | 2 / false |
| Wander radius | 5 | 3 |
| Identity / AI | barrow_wight / AmbushAI | barrow_wight / AmbushAI |

The restored actor reads current description, `1d1` plus four, changed attack
verb, speed1.25 and pursuit2. Its normal engine turn still produces +0.005
corruption and a pulse. Changing sight does not change the separate ability
radius. These are controlled consumer observations, not balance or natural-world
selection claims. No running game cache or personal campaign was edited.

## Final checks

All commands ran locally; ignored evidence is under `workbench/.artifacts/`.
The receipt distinguishes actual observations from source inspection and records
the exact commands, logs and hashes.

| Gate | Result |
| --- | --- |
| Frontend / TypeScript | 59 tests in 16 files; typecheck passes |
| Rust / clippy | 55 tests, including existing W4D cases; warnings denied |
| Full worker/family suite | 59 passes, one expected dependency-absence skip; 511.046 seconds |
| Missing-dependency negative | Passes separately using the installed interpreter without game packages |
| Production persistence/combat/ownership/readers | 38 passes; normal Python 3.11 with the pinned Workbench dependency payload |
| Controlled restore/identity + native-published encounter | Packaged Python passes; fresh process and actual game routes |
| Windows release / NSIS | Complete pinned runtime, matching source bridge and installer built with locked dependencies |
| Native creatures | Three processes; multi-family recovery, invalid source, entitlement/freshness, exact publication and saved layout route |
| Native earlier guarantees | Recovery/competing ownership, workspace/lost reopen response, texts/physical use, typography, submaps, items and recipes pass |
| Startup smoke | Four isolated launch/project-change/restart scenarios pass |

The first embedded-runtime invocation of older production tests could not resolve
their subprocess imports; the final 38-case run uses an isolated standard-runtime
environment pointing at the same pinned dependency files. No game/test assertion
was relaxed. The new controlled fixture directly passes with packaged Python.
The final package was completed before native launches to avoid Windows file locks.
The item journey now waits for verified publication and permits bounded fresh
validation/review after a no-write host `BUSY`, rather than immediately reading
an output that may not yet exist. Other failures still fail the journey.
Startup smoke waits for the requested creature validation, since W5F inspection
already provides an initial construction receipt.

## Preservation and limits

All 8,137 captured files outside the scoped changes retain SHA-256 and modification
times, including the owner plan, font assets, launcher/settings sources, wiki and
existing content. All shipped creature definitions remain unchanged. No personal
save scan was performed; probes use explicit disposable save roots and the worker
read guard remains tested. The owner plan remains untracked and outside commits.

The UI factory receipt proves construction and explicitly reports that ability
execution was not observed there. Separate controlled runtime evidence above
establishes the tested dispatch and interactions. Natural selection, balance,
special-ability registration/editing, body/harvest editing, NPC/player/vine
systems, campaign migration, wiki work and other milestones remain outside W5F.
