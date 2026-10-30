# G20 — Audible encounters and a prepared expedition

Status: A+B+C implementation accepted through focused checks; final frozen release
verification and publication pending. This status must be replaced from actual
receipts before delivery. No subsequent numbered brief or creature relationships
are started. H1 and the full Emergent Expeditions arc remain open.

## Starting authority and prerequisite

The owner's extended commission authorizes autonomous implementation, coherent
commits, push and remote readback in the production `main` checkout. Start:
2026-10-30 06:02:24 UTC. No extra checkout, desktop input or owner campaign is
used. The unrelated untracked Workbench proposal remains outside scoped commits.
Wiki upkeep is not commissioned.

G19 was already delivered at
`27b032d37fed553b1acfc049e2d083f0f3c1ecab`: initial local HEAD, remote main and
verified reference agreed. Its actual 825-input frozen source manifest matched
the checkout exactly. The issued contract and full 378-test / 3704-assertion,
159-worker evidence were reviewed; 44 current G18/G19 tests passed again before
sound implementation. [Preflight](../../evidence/gameplay-g20/preflight.json)
records authority hashes, working state and remote baseline. G19 required no
unfinished prerequisite publication.

Named implementation checkpoints: start at G19; phase A
`08aabd8b94329fa2cffcdc54d7296b4138749c3d`; phase B
`c35a0cea91ced1be7b6aa122240da5580e7253e1`; phase C
`feccf26b926b9184128c060291142c5fc4d367c6`. Each has a matching
`checkpoint/gameplay-g20-…-20261030-a` tag. These focused checkpoints alone are
not verified releases.

## Delivered rules

Sound belongs to its emitting scene and records an unidentified fixed position,
kind, received strength and absolute deadline on each eligible listener. It
never supplies a hostile target, follows player movement, refreshes sight memory
or authorizes scene transfer. Genuine sight/trail supersedes and clears sound.
Ordinary AI, WanderingAI and CirclingAI investigate; AmbushAI/FleeingAI and
dormant, waiting, fleeing or hibernating states retain their special behavior.
Stone Lurkers do not wake or gain an ambush through hearing.

`engine/sound.py` holds the tuning. Cardinal open travel costs 1, closed doors
4; sealed nonwalkable walls block, with no diagonal or scene leak. Only an actual
bell terrain source may seed its own nonwalkable cell. One flood is shared per
event, capped at cost 48. Positive listener hearing produces budget
`event strength + hearing_radius - 6`; zero is deaf. Event strengths: combat 8,
dismantle 8, flint 6, musk 6, cracked bell 10, intact bell 18. Received salience
is budget minus path cost plus 1; stronger replaces, equal prefers latest
delivery, weaker never renews. A finite deadline is emission world turn +12,
inclusive. A player event at T permits ordinary decisions T+1 through T+12;
T+13 expires it. AI events can influence later scheduled actors in the same
phase, with no rewind or bonus action. Actor speed does not change the deadline.

Investigation uses normal cardinal movement credit toward the source or a
reachable adjacent approach to an occupied/nonwalkable source. Arrival ends it;
unreachable interest expires. No offscreen movement is simulated. Expiry is
rechecked before disrupted skips and on restored scene use. Optional neutral
fields are omitted; malformed shape, kind, type, strength or owning-map
coordinates reject transactionally. F9 restores clock and interest together.

Four boundaries emit once: a committed legal player/monster attack (attacker
position, including miss/dodge), successful empty-crate dismantle (crate), an
owned confirmed throw (impact), and actual bell discharge (bell coordinates).
Zero-phase attacks emit once; extra settlement does not replay them. Two actual
monster attacks emit separately. Existing bell resonance, corruption, weather,
particles and spawning remain. Footsteps, gathering, crafting and doors add no
gameplay sound. Reaction feedback is visible-only and cannot emit recursively.

An ordinary gathered `flint_shard` has a six-tile owned map-bound throw cursor.
Valid confirmation spends one unit and one phase, creates a clatter and loses
the shard without damage. Free cursor/cancel/invalid/stale steps preserve item,
time and Press; committed throwing expires Press normally. Cutting remains.
Exact-ID runtime capability covers historical null-handler shards without
rewriting any stored item field or overriding explicit nonempty handlers. The
canonical flint definition remains G19-exact; inventory and Workbench show the
current capability and expenditure through guidance. This also preserves genuine
old workshop dependency fingerprints. Legacy multi-count items lose one unit.

Musk keeps a radius-three circle and six protected charged phases including the
throw, leaving five immediately afterward. Shared current-owning-map terrain
line-of-effect blocks opaque walls, closed doors and sealed corners; impact is
covered. It does not diffuse like sound. All nonplayer AI creatures are affected,
including Hollow/Wraith/Lurker; the player is unaffected. Coverage is shared by
AI, ability suppression and pursuing/crossing checks. Overlaps form an independent
finite union. No speed banking, bonus recovery action, erased status counter or
consumed suppressed pending ambush occurs. Visible reactions give no hidden
identity. Existing hot-zone aging, cold-zone freezing, live status aging and
inactive actor-status freezing remain distinct; sound deadlines use world time.

Workbench now exposes the existing typed integer hearing field, 0–1000, through
ordinary creature editing, validation, Source, Undo/Redo and publication. Saved
zero/four edits reopen and change a real factory listener's four-cost audibility.
The narrow native check also rejects stale source, preserves unrelated fields
and verifies the minimum-width layout. Existing variant/protected-source policy
is retained. This is a new package build, with package identity in final receipts;
the owner's installed application is not replaced automatically.

## Destination, reward and supplies

`barrow_ward_store_a` is one 25×15 canonical undercroft, one unchanged ordinary
Hollow Revenant, two openings, an arrival/return area, a short Common-language
physical letter and one physical Faceted Ward. No room-specific AI, solution
trigger or automatic guard removal exists. The Ward uses its existing definition
and paid offhand equipment route, competing with held torchlight. The acquired
item is used in a separately labeled positive real-combat block check.

The authored barrow profile is enabled at chance .35 with candidate weight 1,
retaining the procedural share. Geography, dungeon occurrence/seeds, entrance
machinery and laboratory are unchanged. Three seeds were predeclared before
inspection: 20261023, 29417, 20261030. They produce 259/731, 278/792 and 265/726
authored barrows, with the remainder procedural; closest declared candidates are
6, 6 and 5 chunk-Manhattan units away. Existing procedural and authored pending
assignments retain their historical meaning. New content is validated through
the existing authoring/publication and native construction/access adapters.

The sample revealed a longer destination journey than preparation alone.
A bounded .5 policy trial did not improve proximity and was reverted to .35.
Measured supply pressure justified the explicitly authorized single fallback:
`workshop_c` preserves B's geometry/material chain and adds one finite crate with
one existing torch, crow jerky and water flask. Only the two previous commercial
memberships change, preserving weight/cap/placement policy. B and old assignments
are unchanged. No starter, needs rate, torch duration, HP or fuel change exists.
Reasons and bounds are in the seed declaration, policy correction, scope
correction and workshop-fallback receipts in `evidence/gameplay-g20/`.

## Ordinary and controlled demonstrations

Final results will be read from `evidence/gameplay-g20/final-a/`. The final tool
runs a fresh original-loop ordinary start, physical flint gathering, workshop
material/supply acquisition, fire/drying and actual musk collection, return to
the laboratory, then connected travel to the ordinarily assigned destination.
Normal AI, FOV, carrying, survival and charged actions remain active. Torch use,
food/water and HP are recorded every phase.

The driver discloses full-state route and target assistance. A separate clone of
the preparation checkpoint previews at most the two tied nearest candidates in
the same declared world and 44 scene components, choosing the feasible west
destination (68,98), six crossings. Preview scenes are never installed into the
ordinary campaign. This establishes feasibility, not unaided human discovery or
balance for all worlds. Failed east-component and watch-the-guard development
attempts remain visible; no terrain or enemy edits manufacture success.

Two independent cold continuations share the exact genuinely prepared room
entry. Lure spends flint, verifies changed source-directed guard movement with
no player trail, and takes the far opening. The hidden reaction is verification
telemetry, not an omniscient UI message. Musk takes the direct opening, makes
genuine contact, spends the prepared pellet, uses the finite passage interval and
withdraws under recovered ordinary pursuit. Both acquire the Ward, demonstrate
paid torch displacement/extinguishing and relighting, save outside, cold-revisit
the altered room without generation, and return to the lab with a later paid
light choice. Neither approach requires a kill or permanent suppression.

The separate acquired-Ward continuation stages one adjacent factory Revenant
and clear lab patch, selects a positive block with RNG.random=.1, retains ordinary
dice, and advances two normal speed-budget phases through the real attack
resolver. It is labeled controlled and makes no natural damage/balance claim.
A second explicitly controlled authored corner/door arrangement reuses identical
hearing/burst runtime rules; it is not another canonical selection or ordinary
acquisition claim.

## Verification and publication

Pending frozen receipts: complete unfiltered focused discovery and production D
with runner negatives, genuine historical archive comparisons, G19/G20 original
loops, three-seed content sample, both ordinary cold branches, acquired-Ward
checks, Workbench full worker/frontend/typecheck/Rust/clippy, pinned NSIS build,
separate missing-dependency control and packaged native hearing. The release
orchestrator records commands, environment, individual process durations, actual
overlapping wall time, raw source hashes, Git blob bindings and package hashes.
The final report will replace this paragraph with observed totals and outcome.

Development corrections are retained: historical flint source dependency restored
instead of weakening validation; a test harness initially repeated an ignored
root rotation setting, then used real production orientation transforms and
verified all four; initial route/guard-watching attempts were superseded by the
disclosed bounded route and immediate bypass. Focused passing checkpoints have
never been presented as full deliveries.

Remaining publication steps: review frozen results/diff, commit scoped evidence
and this completion report, create `checkpoint/gameplay-g20-verified-20261030-a`,
push main and all five G20 checkpoint refs, read back their full remote SHAs.
No phase is deferred if all pending gates pass. Stop after published A+B+C.
