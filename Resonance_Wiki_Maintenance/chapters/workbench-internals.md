# Workbench: from controls to a published file

Workbench edits bounded families; it is not a general Python IDE. Follow the source entitlement, not just the visible field. A Source tab can retain data the form does not understand without granting it runtime meaning or permission to alter a protected source.

## One edit through three layers

```text
React Authoring / ContentEditor / family controls
    -> validated draft request and identity
Rust verified project path + one-file publication authority
    -> Python worker bridge -> family adapter -> production validator/preview
    <- diagnostics, retained fields, dependencies, candidate identity
Review & apply -> confirm one file -> byte-checked reopen
```

Read `workbench/src/Authoring.tsx`, `ContentEditor.tsx`, the appropriate family editor, `workbench/src-tauri/src/`, `workbench/worker/bridge.py`, and `roguelike/engine/content_authoring.py`. The registry advertises eleven families. A family descriptor carries schema, references, views and operations; source-specific capability further narrows them.

The worker's `family_validation` stages data for a candidate and invokes real adapters. Publishing first checks the source/draft/dependency identities again. The host refuses changed inputs instead of silently overwriting them. Incoming references are useful impact clues, not a complete dependency graph for every manual Python consumer.

## Add a supported field deliberately

First identify the actual runtime consumer. If no consumer exists, a new control would only author an inert field. Implement or commission the behavior separately, with time/state/save rules. Then extend the owning adapter's bounded schema, capability and validation; expose references only through supported vocabulary. Update context/preview to show the observable effect where practical. Preserve unknown/read-only fields during form edits.

Add the React control in the relevant family editor or generic schema renderer. Check create/edit eligibility on both original source and candidate: editing the candidate into an eligible shape must not grant a protected original a new operation. Keep Rust source/path authority aligned. Run focused worker tests, frontend tests/typecheck and host tests for touched boundaries, then an app-local publish/reopen journey in a disposable fixture. Do not infer a native-host pass from a mocked frontend test.

A useful example is an additional supported numeric food field: definition → factory/use consumer → adapter range/type check → controlled UI → draft validation → one-file publish → fresh-instance use. The handbook's new Python practice capabilities deliberately stop short of adding Workbench controls; they use the manual route and are visibly unsupported by the current item adapter.

## Captured Test room

Save dependencies, then save the ordinary immediate `layouts/` room. **Test room** freezes code/data/assets/runtime and injects an explicit session root before startup. **Reset current test** restarts that same capture. **Test latest saved version** captures current saved inputs; it does not use parked or dirty drafts. The selected room's ID does not enroll it into a natural world—[L07](#L07) adds that route.

The native room journey in `scripts/run-room-tests.mjs` tests these distinctions with owned app-local events. Older `run-sys-5.mjs` publishes into the production project despite disposable app state; do not use it as general practice. The guide launcher instead creates a bounded payload every time and never publishes.

## Build and environment

Using an existing packaged Workbench needs its executable, bridge and bundled Python kept together, plus the platform's WebView runtime. Building it needs the project's recorded Node 24, npm lockfile, Rust/Cargo/Tauri prerequisites and prepared pinned Python runtime. From `workbench/`, use `npm.cmd ci` for dependency restoration, `npm.cmd run typecheck`, `npm.cmd test`, and the README's build/runtime-preparation commands. Initial package acquisition is not guaranteed offline. Reading this handbook never invokes these commands.

The source map includes project-owned Workbench code and scripts; installed node modules, compiled target directories and browser binaries are not documentation inputs. Execution receipts record versions separately.
