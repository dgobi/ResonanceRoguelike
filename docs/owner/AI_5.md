# AI-5: full paralysis and restrained encounter feedback

Runtime/content/editor verification boundary: `6f6044485bce5dbd052c23fc44fcdf38ccab4872`.
Starting production main: `721c71e0769a575968d414393552458dce3c74aa`.
Initial implementation: `6a8b3695e287a4c7c856c124d155905b6aaa8f00`;
perk presentation and actual free-inspection repairs lead to the runtime boundary above.
A subsequent verification-only commit, `29a356123334336ae57dfdfd673b3c049044b64e`, updates the retained AI-3
native driver; its own final-package run passed separately. The final delivery
adds this report and evidence. Runtime, content, editor and guide inputs remain
those verified above; the exact verifier delta is in
[input-delta.json](../../evidence/ai-5/input-delta.json).

Numbing venom now fully paralyses the living player and supported ordinary
WanderingAI/CompositeAI victims, including a hunter that receives a dose.
Voluntary movement/sprint/travel, attacks/movesets/throws/reactions, item
use/equip/pickup/drop/transfer, crafting, harvesting, containers, dismantling and
placement cannot commit. Active dodge and shield blocking are suppressed in the
combat resolver; passive armour/resistance and ordinary critical/damage/death
rules remain. One pure actor/Fighter predicate guards actual committers,
including stale confirmations and zero-time inventory-output crafting.
Perks are explicitly view-only. Health, Lexicon, look/map/log and other browsing,
cancellation, save/load and exit remain free; the final native
[Health panel](../../evidence/ai-5/paralysed.png) shows the real condition and binding.

Each **`.` / keypad 5 Wait** while helpless passes one ordinary charged phase.
AI, needs, effects, fuel consumption and existing processing continue; rain
collection and Press grants do not. Rejected commands consume no resource or
phase and add no repeated denial tutorial. A warning action still settles time
it legitimately owes; onset prevents extra-action grants even if those owed
phases later reach recovery. No deferred physical command is executed on recovery.

Fresh defaults and both insect examples use **W3/P3/R4**. Other explicit timing,
including valid P1/P2 and the Nettle/Drowsing examples, is preserved. Warning
permits normal action and owned remedy use at any HP, including full HP: one unit,
one charged phase, no healing; the stock recovery snapshot goes 4 -> 3 on that paid phase.
Full-stage self-treatment rejects without item/time/effect changes. No refresh,
stacking, recovery-chain stun, automatic remedy use or source-death cure was added.
Delivery acceptance stays separate from attack commitment, hit, damage and death.

This intentionally changes severe-stage availability in older saves. The genuine
pre-change archive was captured at `721c71e` before runtime edits, with a P2 dose
at phase 488, one severe phase left and a confirmed/closed hunter committed through
489. New runtime load, free inspection, F5/F9 and a separate cold process retain
its exact dose counters/parameters/identity/provenance/timestamps and hunter
profile/commitment/deadline/budgets. It now blocks physical action and reaches
recovery at its original phase 489 boundary. Saved source P2 tuning remains P2;
new applications copy that effective tuning. No reset, extension, redose, revival
or respawn was used to display the correction. See
[legacy provenance](../../evidence/ai-5/legacy-provenance.json) and
[acceptance](../../evidence/ai-5/acceptance.json).

Normal feedback is short and sensory. The first successful retreat step earns
“skitters away with a chittering whine”; a blocked retreat does not. Return prose
requires real approach movement. Creature cues use normal player vision, and a
compatible optional boolean retains withdrawal-tell state across saving mid-retreat.
Onset/recovery describe bodily sensations, without timers, enemy reasoning or
immunity coaching. Known shipped saved remedy descriptions and insect names
refresh only on exact ID/value matches, including floor/container instances;
custom prose, unrelated fields and historical logs stay owned. Explicit runtime
debug false omits combat formulas; diagnostic mode and internal formula results remain.

The existing IDs `patient_amber_hunter` (**Amber Shell Hunter**) and
`timed_amber_hunter` (**Amber Whine Beetle**) retain one shared implementation,
matched art/body/combat/speed/retreat values and distinct observed-paralysis versus
finite-hold policies. Only commissioned timing/prose changed; no additional combat
or loadout tuning was needed. The ordinary Amber Sting Beetle remains non-venom.
Actual packaged controls duplicated that seed into an unsaved draft and validated
registered W3/P3/R4 defaults, then edited, validated, reviewed/applied and reopened
both existing policy variants. All published bytes reconcile with their receipts.
No extra catalogue entry was published. Development actual-control authoring is
separate from the fresh final-package lifecycle run.

Launch `workbench/Launch Workbench.vbs`. Open saved `ai4_patient_opening`,
`ai4_timed_opening` or `ai4_rival_ground`, then Test room. Reset retains its capture;
Test latest saved version excludes dirty dependency drafts. The
[numbing guide](../../roguelike/docs/NUMBING_VENOM_AI.md) and
[patient guide](../../roguelike/docs/PATIENT_VENOM_AI.md) explain exact clocks,
warning counterplay, lawful sight, policy differences and saved-instance behaviour.
The author control is **Full paralysis (charged phases)**; remedy help distinguishes
warning use from severe rejection. Stable IDs and author-visible policy choices remain.

All verification below was newly executed in this task on the supported Windows,
CPython 3.11 pinned runtime, Node 24 and Rust environment in
[environment.json](../../evidence/ai-5/environment.json).
[Commands and identities](../../evidence/ai-5/commands.json), the
[artifact inventory](../../evidence/ai-5/inventory.json), compressed logs,
input manifests and receipts retain exact source/input boundaries. No historical
AI-3/AI-4 pass count is substituted for fresh certification.

| Gate | Executed result |
| --- | --- |
| Unfiltered focused | 534 passed; stable inputs |
| Unfiltered production-D | 3704 passed across 159 workers; stable inputs |
| Complete affected Workbench worker | 45 cases across ten modules |
| Frontend / host / startup | 93 / 71 / 15 passed |
| Typecheck / clippy / portable and debug builds | Passed |
| Desktop / AI-5 native lifecycle / retained AI-3 native verifier | Passed |
| AI-5 ordinary family / updated AI-3 ordinary family | 6 / 6 scenarios passed |
| Independent cold comparisons | 4 passed, including genuine old P2 and new full-stage continuation |

The ordinary family uses saved rooms, seed 20261027, combat RNG 17, AI RNG 19,
normal loadout/visibility/damage and actual pickup/use handlers, without injected
conditions, owned remedies or attack results. In the untreated anchor, a real
sting at 484 deals 3 damage; warning ends at 487. Three helpless Waits advance
488/489/490. Lawful sight permits a close at 488 and real attacks for 3 and 4 damage
at 489/490 while paralysis applies. End 490 restores action with recovery 4.
Hidden warning treatment distinguishes the policies; positional escape works;
after-close severe treatment rejects. A real ordinary rival stays helpless for
three phases and then damages its source after recovery, without a stored burst.
New focused fixtures separately cover actual full-HP remedy use, active defences,
valid owned crafting/transfer, stale modal commits, fuel/needs, free panel opening,
custom prose and malformed records. These controlled setups are disclosed in
[acceptance.json](../../evidence/ai-5/acceptance.json), not represented as ordinary play.

Material development failures and repairs are retained in
[attempts.json](../../evidence/ai-5/attempts.json): changed-input capture rejection,
fixture preparation errors, a locked owned test executable, misleading perk prompts
and the H/L movement-key overlap exposed by visual QA. Interrupted runs are not
final passes. The retained AI-3 native script still had its former cure-success
expectation; it was corrected and run on the final package after the runtime
freeze, with only that verification script changing.

Portable executable: `workbench/src-tauri/target/release/resonance-workbench.exe`.
SHA-256: `94f8c989113aee4520d938f564f5b3b7fad7542e85ac05a1cd00aa7706b25216`.
[Package/capture identity](../../evidence/ai-5/package.json) binds the tested bytes.
These are headless, scripted rules and app-local controls for explicitly placed
active-scene encounters, not unaided discovery, a full replay or a balance verdict.
Natural populations, allied rescue, cross-scene hunts and later arc stages were not
commissioned. NSIS installation and clean-machine provisioning were not rerun.

Work remained on production main. The owner's untracked proposal is unchanged
and excluded from task commits; personal campaigns were not opened. No task branch,
worktree or development checkout was created. Wiki/reference-pack upkeep was not
performed. See [preservation](../../evidence/ai-5/preservation-final.json).

Named start, implementation, frozen-input, verification-tool and verified-input
checkpoints were published with main by atomic push, followed by object and peeled
revision readback in [publication.json](../../evidence/ai-5/publication.json).
The a/b input checkpoints retain superseded development boundaries; c identifies
the verified runtime and d the separately corrected verifier with identical runtime
inputs. The completion checkpoint `checkpoint/ai-5-complete-20261101-a` identifies
this subsequent report/evidence delivery. Its exact final commit, all remote tag
objects/peeled revisions and final main are in the final handoff and local
`.baseline/ai-5/final-publication.json`; a report cannot embed its own eventual hash.

AI-5 stops here.
