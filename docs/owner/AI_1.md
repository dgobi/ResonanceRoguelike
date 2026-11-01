# AI-1: authorable strike and withdraw

Implementation is complete at runtime boundary
`b4b90b67860a4db093f1457a4e15d13a02ef75af`. The final test-inventory boundary is
`f43501680e7e8c901b11bdd8d1df00f706023ab7`. The earlier implementation boundary
was `b62b3276276b588166b465cf5408b838d28ebd4b`.
All applicable final gates pass. Implementation and source checkpoints have
been pushed to `origin` and verified by remote readback. The complete checkpoint
identifies the documentation/evidence delivery commit itself.

Work stayed in the production checkout on `main`. The initial revision was
`749420b9018cdc0e5ed78d85e50abbe46561fb2f`. The unrelated untracked Workbench
proposal, personal campaigns, wiki edition and reference pack were preserved.
There was no branch, worktree, extra development checkout or visited-scene
regeneration. Test saves, frozen room captures, settings and recovery roots were
disposable and independently owned.

## Owner capability and settings

An eligible ordinary melee source can create a new-ID `composite` variant using
Workbench's existing controls, exact Source/history, validation, Diff, reviewed
one-file publication and verified reopen. Supported composite profiles allow
same-ID tuning. Save/reopen a creature before selecting it in an authored room;
Test room runs the actual captured game. Reset retains the capture, latest saved
recaptures saved inputs, and dirty dependency drafts stay excluded.

| Saved ID | Trigger | Retreat tiles | Full hold opportunities | Withdrawal budget |
| --- | --- | --- | --- | --- |
| `grave_skirmisher` / Grave Skirmisher | `hit` | 2 | 1 | 6 |
| `grave_harrier` / Grave Harrier | `committed_attack` | 4 | 3 | 8 |

Both were authored through packaged Workbench controls from Hollow Revenant,
including duplication, validation/publication/reopen and same-ID tuning. They
retain matched combat statistics, art, body, remains, speed 0.8 and explicit
pursuit timeout 12. Both use one `CompositeAI`, without example-ID decisions.
The paired `ai1_skirmisher_room` and `ai1_harrier_room` are matched 17 x 11 saved
authored layouts. Neither creature joins natural population tables. Explicit
placement/testing is the availability boundary; `spawn_zones` remains inactive.

The registered representation is `ai_type: "composite"`, embedded `ai_profile`,
integer version 1, recipe `strike_and_withdraw`. Fixed roles are ordinary
`melee`, `defensive_melee` cornered response and `active_scene` scope. Defaults
are hit / distance 2 / hold 1 / budget 6; bounds are 2-8 / 0-12 / 1-32.
The game validates the same effective contract used by Workbench, including
strict numeric types and unsupported version/recipe/combination diagnostics.
The authoring contract is `creature-composite-4`; no profile catalogue or arbitrary
condition language was added.

Distance is Chebyshev tiles. Withdrawal/hold use granted ordinary actor
opportunities; phase transitions grant no action. Lost-contact age instead uses
charged world phases: definition `pursuit_timeout`, default 20, valid through
last sight + timeout, expiring next phase. Zero allows no later-phase trail.
Visible sight refreshes every phase without replacing retained prey; hearing
remains anonymous. Evidence observation/expiry also runs on charged phases when
slow scheduling or disruption grants no decision; no opportunity counters advance.
Failed withdrawal spends its finite budget, then fights legal
contacts or abandons. Defensive hits cannot repeatedly rearm an unchanged failed
route. Approach/return has 32 opportunities and eight without route progress;
route search is bounded to 512 cells and 16 steps.

The resolver runs once. `hit` is authoritative contact, including zero damage
through mitigation; it promises no affliction. Miss/dodge and the invincibility
shortcut qualify only as committed attempts. Illegal/rejected attacks do not
qualify. The legacy boolean attack wrapper, Crow range and separately pending
Lurker reaction retain their contracts.

Saved composite actors explicitly reconstruct their saved AI/profile and retain
phase, stable local target reference, sight evidence, opportunity budgets,
progress/rearm state and speed fraction. Same-ID profile edits affect fresh
instances; existing saved behavioural profiles (including pursuit timeout) stay
frozen. Other stat/description/item and legacy policies are unchanged. Malformed
profiles/state or missing definitions use safe-load rejection; stale individual
targets cancel commitment. Legacy rows gain no empty composite fields.

Composite v1 cannot enter chunk/stair/live-pursuer/arrival transfer paths.
Successful departure cancels local intent once; failed transitions, F5/F9 and
same-scene reconstruction do not. Location, health, identity and physical remains
persist on revisit, with no respawn or offscene tactical catch-up.

## Evidence and player responses

[Authoring receipts](../../evidence/ai-1/authoring.json) distinguish initial actual
control-based creation from final packaged validation. Initial development
attempts exposed stale source review and harness assumptions about no-op drafts,
button labels and key names; they are not represented as successful final runs.
The [final native lifecycle](../../evidence/ai-1/native-lifecycle.json.gz) passes
both real approach/strike/withdraw/hold/return cycles, visibility-gated tells,
reset/stop/latest saved, dirty-dependency exclusion, and F5/F9 in both withdrawal
and holding for both examples without advancing time or tactical opportunities.
Each capture identifies
exact content, runtime, seed, room, contract and instance diagnostic boundary.
Factory construction is reported separately from actual game execution.

[Player-response evidence](../../evidence/ai-1/responses-summary.json) compares
wait, reposition and sustained pressure for both saved examples. Only disclosed
setup is saved-room selection and combat/AI RNG seeds; health, equipment, terrain,
needs and positions use the ordinary room bootstrap. Inputs use game handlers.
Both variants allowed four ordinary reposition actions after withdrawal began
without another hit. Continued encounters still inflicted damage. Sustained
pressure defeated both; the wider variant entered cornered fallback under
pressure. The short and wide visible cycles have different retreat distances and
full hold periods. This is controlled tactical evidence, not global replay,
unaided discovery, fun or final balance certification.

The privileged room-test inspector is read-only and bounded to 16 actual actors
and 16 recent opportunities each. It exposes identity, effective profile, phase,
retained target, evidence age/provenance, action/reason, result and consumed
opportunity. Normal feedback reveals no hidden identity or private counter.

## Verification and distribution

The final input revision passes both unfiltered gates with unchanged source:

| Gate | Result |
| --- | --- |
| Focused regressions | 465 passed |
| Production-D | 3,704 checks passed across 159 workers |
| Workbench worker | 122 cases: 121 passed, one expected embedded-runtime skip |
| Frontend / native host | 91 / 71 passed |
| Startup | 15 passed |
| TypeScript / clippy / release build / packaged desktop smoke | Passed |
| Final packaged actual-game lifecycle | Both cycles and four F5/F9 phase checks passed |

The missing-dependency control separately passes on development CPython.
[Gate commands and environment](../../evidence/ai-1/gates.json),
[full focused receipt](../../evidence/ai-1/final-e/focused/run.json) and
[production-D summary](../../evidence/ai-1/production-d-summary.json) retain the
actual input boundary, results and evidence hashes. The only change after the
runtime boundary is two catalogue-test expectations, accounting for both new rooms.
[Retention checks](../../evidence/ai-1/retention.json) establish byte-identical
captured game/content/resources and packaged frontend/host inputs.

[Package receipt](../../evidence/ai-1/package.json) identifies the rebuilt usable
Workbench executable, bridge, pinned runtime, frontend/host inputs and native
capture. Launch normally with `workbench/Launch Workbench.vbs`. The release
executable SHA-256 is
`d11462856010f5a7281c016c78449ae085a21e092c0d4eaaa60fa950769409b5`.
NSIS installation/clean-machine provisioning was not rerun. Source rules load
from the selected checkout; running tests retain their immutable captures.

The affected [creature-authoring guide](../../roguelike/docs/CREATURE_AUTHORING.md)
and Workbench README cover controls, trigger semantics, clocks, explicit placement,
local scope and fresh-versus-saved policy. No wiki changes or recurring release
gate were introduced. Venom/paralysis, observation-sensitive speed, allies,
cross-scene pursuit and natural encounter enrollment remain outside AI-1.

## Checkpoints and publication

| Reference | Revision |
| --- | --- |
| `checkpoint/ai-1-start-20261031-a` | `749420b9018cdc0e5ed78d85e50abbe46561fb2f` |
| `checkpoint/ai-1-implementation-20261031-a` | `b62b3276276b588166b465cf5408b838d28ebd4b` |
| `checkpoint/ai-1-verified-inputs-20261031-a` | `f0e254da64f80542ac224cfa6c32d3eef6e4ecc5` |
| `checkpoint/ai-1-clock-inputs-20261031-a` | `38e14f0270a5898ff8f9e30be1bc40895b3d4132` |
| `checkpoint/ai-1-final-inputs-20261031-a` | `b4b90b67860a4db093f1457a4e15d13a02ef75af` |
| `checkpoint/ai-1-catalogue-tests-20261031-a` | `f43501680e7e8c901b11bdd8d1df00f706023ab7` |
| `checkpoint/ai-1-complete-20261031-a` | This documentation/evidence delivery commit |

[Publication receipt](../../evidence/ai-1/publication.json) records the exact
remote `main` implementation identity and all six source checkpoint tag objects
and peeled commits. The documentation/evidence delivery is then pushed to `main`
with `checkpoint/ai-1-complete-20261031-a`; its exact final SHA and the seven
checkpoint readbacks are reported in the handoff. The final readback is retained
locally at `.baseline/ai-1/final-publication.json` to avoid embedding a commit's
own hash inside itself. Delivery changes only this completion record and evidence.

AI-1 stops here. No next-stage work was queued.
