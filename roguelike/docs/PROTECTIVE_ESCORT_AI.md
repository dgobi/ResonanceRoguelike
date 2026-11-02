# Protective escort (AI-7)

`protective_escort` is version 6 of the registered ordinary melee composite
recipes. It protects the player in its owning active scene. Availability is
authored placement and isolated room testing. No normal population or starter
companion is added.

Use **E**, select a normally visible, physically reachable adjacent escort, then
Enter. The prompt shows its current order: choose **Follow** or **Hold here** with
Up/Down and confirm Enter. Acceptance costs exactly one charged world phase;
browsing, cancellation and rejected stale confirmation are free. Full player
paralysis prevents acceptance. The ordinary scheduler supplies any ensuing ally
action; the command grants no additional opportunity.

Follow keeps 1–2 tiles of space from the last actually observed player. Hold saves
the escort's current tile as its instance post; later Hold commands can replace
it. Its original spawn remains unchanged. Bumping this registered ally tries a
deterministic adjacent yield, then a reciprocal passage swap. Both movements must
be legal, with free destinations, capability/terrain and corner/decor checks.
Paralysed or otherwise immobile escorts cannot yield. Failed passage is free and
does not attack. Player entry uses normal effects, hooks and movement debt,
including sprint/momentum accounting. Other neutral actors retain their existing
bump behavior. Explicit player attacks remain possible.

The role grants no hidden coordinates. Own creature sight refreshes separate ward
evidence; debug reveal, the player's screen and anonymous sound grant none.
After lost sight it seeks bounded last sight, then its last reached holding area.
Follow remains Follow. Newly seen player movement permits a new rejoin attempt.
Threats must be living supported ordinary local actors seen through the escort's
own perception and hostile under its explicit faction list. The player is never
escort prey. Protection radius identifies relevant threats, not sensing range.
Stable threat commitment survives a marginally nearer rival. Immediate seen
contact defence may interrupt without refilling or replacing that commitment.

Every pursuit step stays within maximum excursion of the Hold post or last
observed ward reference. Pursuit spends one unit per granted opportunity,
including melee/contact interruptions. Sight deadlines use charged phases and
remain valid through their inclusive deadline. Exhaustion, invalid prey, lost
evidence or eight failed moves commits to physical return. Return has 32 route
opportunities, eight consecutive failures and a 12-opportunity blocked retry;
changed local route conditions can retry earlier. An unchanged unreachable threat
stays retired until changed observed position, genuine lost/new sight or changed
local route conditions. Retirement retains at most 16 references. Routes use the
existing bounded 512-cell/16-step search and commitment checks. Two escorts use
ordinary occupancy with deterministic choices; they never swap one another.

Ordinary combat supplies damage, armour, suppression/disruption, death and
remains. Enemies hostile to `player` can target the aligned escort when their own
perception/AI permits. This is directional faction membership, not blanket
retaliation. Ally kills do not fire player-only kill hooks or award player credit.
Full numbing paralysis allows evidence expiry but no physical action or banked
recovery burst. No healing, teleporting, equipment or immortality is added.

Successful scene departure clears local ward/threat/sound evidence and pending
orders, preserving position, HP, identity, order and Hold post in the old scene.
It freezes under the existing scene cache policy, never follows stairs/chunks,
and never uses the offscene pursuer path. Failed departure preserves commitment.
On return, a living Follow escort needs new lawful sight; Hold retains its post.
F5/F9 and cold loads preserve effective tuning and instance evidence/budgets
without advancing time or replaying orders. Strict version-6 validation precedes
save installation; versions 1–5 keep their prior schemas and meanings.

## Authoring

In `workbench/Launch Workbench.vbs`, open an eligible ordinary melee creature,
**Begin edit → Save as new variant**, choose a new ID, **Creature AI: composite →
Behaviour recipe: Protective escort**. Set **Faction label: player**, clear old
hostiles and explicitly add intended hostile tokens (e.g. `hollow`). Player
self-hostility, other escort factions and special/ranged/NPC hosts reject.
Art, body, unknown metadata and protected fields retain their authority.

| Field | Default | Bounds / values |
| --- | --- | --- |
| `initial_order` | `follow` | `follow`, `hold` |
| `follow_spacing` | 2 | integer 1–2 tiles |
| `protection_radius` | 4 | integer 1–7 tiles |
| `excursion_radius` | 6 | integer 2–8, strictly greater than protection radius |
| `pursuit_budget` | 18 | integer 1–32 ordinary opportunities |
| Definition `pursuit_timeout` | 20 if absent | integer 0–10000 charged phases since sight |

Distances are Chebyshev (eight-direction tiles). Wander radius is inactive.
The fixed capability is `melee`; `scene_scope` is `active_scene` and both
`can_cross_chunks` / `can_use_stairs` must be false. Recipe changes require a new
ID. Same-recipe tuning and initial order edits are supported on the same ID;
saved actors retain their effective profile and current orders.

Validate, review the exact diff, apply and reopen. Place the saved creature in an
authored room and save that room. **Test room**, **Reset current test**, **Stop**
and **Test latest saved version** run the actual game in disposable saves. Reset
retains captured dependencies; latest saved excludes dirty dependency drafts.
The privileged bounded inspector exposes order/post, lawful ward and threat
evidence, chosen action, retirement reason and budgets without observing or
advancing anything itself.

`ash_escort` (Follow, spacing 2, protection 4, pursuit 18) and `stone_escort`
(Hold, spacing 1, protection 3, pursuit 12) share combat, art/body, player faction,
explicit `hollow` hostility, sight/hearing/darkvision, speed 1 and excursion 6.
Both inherit the ordinary Hollow Revenant's 12-phase sight timeout.
`ai7_escort_lane` has a narrow door lane and open side route. Try orders, passage,
occlusion and rejoining. `ai7_escort_threat` pairs the Stone Escort with the
existing Barrow Sentinel and an obstacle/withdrawal area. Approach the opening,
wait for a real response, then withdraw to compare Hold and Follow. Results
depend on ordinary combat and position; the ally can fall permanently.

No recruitment, multi-scene roster, dialogue, support consumables,
target-specific attack command or general actor-to-actor ward system is supported.
