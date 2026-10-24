# G7 wiki and authoring review

Reviewed repository: `8e56d36d72537e8b32c3666dd5d19723d1afdf3a`.
Review only; no repository files were modified.

## 1. Reproduced authoring input overwrite

`tools/structure_authoring.py:128–144` checks only the positional `candidate`
against the JSON report path, although the command now reads compound recipes,
repeatable child drafts, policies and other configuration files. It writes derived
SVGs without checking their resolved targets. Earlier branches also write editor
catalogs and initialize drafts before the final report guard.

Four disposable probes all exited zero and reported success while destroying an
input. See `collision-probes/collision-matrix.json`, per-case receipts and exact
before-input bytes. `probe_output_collisions.py` reproduces them using a supplied
repository and interpreter; complete after-payloads remain in its recorded `/tmp`
work directory, with exact byte counts and SHA-256 hashes retained in the receipts.

| Case | Before | After | Result |
| --- | ---: | ---: | --- |
| `--output` equals `--compound` | 1,248 bytes | 1,795,751 bytes | Recipe replaced by preview report. |
| `--output` equals `--child` | 1,951 bytes | 1,795,750 bytes | Child replaced by preview report. |
| `--init-compound` plus report output naming existing child draft | 1,951 bytes | 213 bytes | Initializer reports preservation, then report overwrites that child. |
| Derived `review.svg` is a symlink to recipe | 1,248 bytes | 225,234 bytes | Generated plan SVG follows link and replaces recipe. |

This is an owner-draft preservation defect, not evidence of generated-world save
corruption. Normal distinct output paths still work. Correct it before expanding
the authoring interface.

### Bounded repair and tests

Build one canonical list of read inputs: positional candidate, `--compound`, every
`--child`, `--poi-config`, `--selection-config`, `--config`, `--access`, and the
editor catalog when checking it. Guard every write target, including the JSON
report, base and per-preview/per-site SVGs, initialization's three draft paths and
an explicitly refreshed editor catalog. Preserve normal deliberate catalog
refresh and chosen evidence-output replacement; this is not a general ban on
overwriting outputs.

Preflight predictable path collisions before any mutation. Stage dynamically
determined report/diagram outputs in memory, validate their resolved destinations
against inputs and protected roots, then write. Detect both lexical/resolved
aliases and same-file aliases when paths already exist. Initialization targets
must be protected even if absent until that command creates them. An error should
identify the colliding input and output and leave every source/draft byte intact.

Required regressions: the four observed cases above; parameterized JSON output
collisions for the other read flags; an ordinary separate-path positive; existing
repeat-initialization sentinel positive; no early editor-catalog or draft mutation
when a later output collision is rejected. The existing workflow test at
`tools/verify_g7_authoring.py:35–42,87` checks repeated initialization with distinct
output paths, which does not cover these cases. CLI has no `--diagram` option;
the generated SVG paths at lines 137,140,144 are the diagram write surface.

## 2. Wiki is an explicitly historical G6 edition

`Resonance_Wiki_Maintenance/wiki-config.json` pins edition 1.0/G6 to
`4d7a7892e1afffb8d872ed4a8fd442984d14e7d5`. The 60-file package was imported by
`4c9d46b` after the final G7 tested input commit. No compiled owner wiki HTML is
tracked in the repository. Current package text should not be treated as a current
G7 owner guide.

Concrete stale instructions:

- `chapters/world-generation.md:3,36–59`: wg6/format 4; one building per rural
  site; explicitly says multi-building compounds are unavailable.
- `chapters/rural-sites.md:3,56–82`: v1 single-site policy and old single-only
  capacity/selection explanation.
- `chapters/structure-reference.md:81`: placement-context list omits compound.
- `chapters/layout-painter.md:44–55`: no compound workflows; output-safety claim
  must be backed by the repair above.
- `chapters/generation-troubleshooting.md:20`: only G3–G5-to-G6 adapters and g6-v1.
- `chapters/maintenance.md:3,19,39,62`: initial edition and revision workflow.

Catch up world planning, mixed-parent policy, full compound authoring/installation,
required usable goals, effective child rotations, private/shared reservations,
parent versus child counts, optional omission, saved recipes versus consumed
children, format 5/wg7 and G6 compatibility. Preserve G6 material with historical
labels. Explicitly distinguish installing an old v1 policy (opting out of
compounds) from extending the installed v2 policy.

The current G7 guide already supplies six practical workflows at
`roguelike/docs/STRUCTURE_AUTHORING.md:967–1180`; the wiki should reconcile these
with its own how-to chapters, not merely embed the guide as another source file.

## 3. Wiki maintenance now has a self-reference defect

This builder was originally delivered outside the repository. Once its package
became tracked, the present workflow ceased to be sustainable:

- `build_wiki.py:384` requires `HEAD == wiki-config.commit`; line 385 rejects any
  tracked changes. Editing the tracked config to current HEAD makes it dirty;
  committing that change moves HEAD again.
- `:28,379` fingerprints all tracked files, including source-manifest and
  build-report; `:386` and `:372` then overwrite them. A refreshed manifest can
  thus immediately drift because its own previous bytes were included.
- `:167` blindly includes every tracked Markdown file, so the current tree's 31
  wiki chapters become duplicate historical source articles as well as guides.
- `validate_wiki.py:145–148,278,330` uses current HEAD and the same unrestricted
  Markdown inventory; it needs the same explicit source-snapshot contract.

Read-only drift check reports exit 2: 37 changed files, zero missing, 132 added.
Receipt is `wiki-drift.json`. Normal build rejects the current G7 HEAD before
creating an output. The repository has 1,216 tracked files versus 1,084 in the old
manifest, 99 Markdown files, and 60 tracked wiki-package files.

### Minimal sustainable contract

Separate the reviewed game/document source revision, wiki authoring inputs and
generated outputs. Read source blobs at the reviewed revision, or require exact
identity of an explicitly enumerated input scope at that revision. Exclude the
wiki source subtree from the game's original-source archive; hash its authored
chapters, examples, CSS/JS, builder/validator and config separately. Exclude the
manifest, build reports, generated HTML and review outputs from their own inputs.
Record delivery HEAD separately from the reviewed input revision; a later
documentation-only commit must not invalidate an unchanged reviewed game source.
Do not simply remove clean/source checks or refresh fingerprints to silence drift.

Test two unchanged builds/drift checks, a documentation-only commit after the
source snapshot, changed source inputs, edited wiki sources, missing inputs and
stale output negatives. Builder/validator must agree on source scope/revision.
Make output/report locations explicit so a review never silently rewrites tracked
maintenance inputs. Retain the prior edition and its audit rather than relabeling
its tests as current.

`build_wiki.py:123–141,203,261–278` also hardcodes G6 labels and initial-edition
checks/environment; changing only JSON metadata would still publish stale claims.
Replace them with edition evidence or deliberately reviewed content. Audit pinned
links in current guides, not only source articles/data; the existing validator's
HEAD checks do not cover every prose code link.

## 4. Next-arc authoring boundaries

G7 provides recipe JSON composition and a browser editor for individual child
layouts, not a graphical compound/street planner. This is a deliberate scope
boundary and does not need an editor rewrite. Forthcoming street/settlement work
needs complete editable policy/geometry examples, controlled placement previews
that force each supported frontage, and actual populated scenes that use the same
runtime fitter/materializer. Preserve child transform permissions; a new street
direction must not silently grant forbidden quarter turns to existing buildings.
Include ordinary selected-world examples separately from forced fixtures, and
update the offline wiki as part of the same feature's delivery acceptance.
