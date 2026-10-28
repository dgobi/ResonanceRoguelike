# W5H geometry repair

Baseline: `3ee22ef3c77cd56df75441076873840ef3b66fc7`; named checkpoint
`checkpoint/workbench-w5h-start-20261027`. Work remains on production `main`.

Room geometry proposals rebase on authoritative geometry fields, including absent
optional values and dimension-derived fallback coordinates. Unrelated painting
does not reset pending proposals. The resize fill resolves to an admitted legend
entry when its former entry is removed or becomes unsupported.

`node scripts/test-geometry.mjs` passes in a headless Edge page mounting the actual
React RoomGeometry controls. It exercises Source changes, Undo/Redo, one-field
arrival and fallback edits with retained companion coordinates, dimensions,
optional defaults, painting, hiding/showing a mounted document and fill changes.
The first run exposed asynchronous effect timing in the fixture's assertion;
waiting for the displayed value corrected the harness. `npm.cmd run typecheck`
passes. These are mounted browser observations, not packaged native observations.
Source edits retain localized operations and a single history entry per action.
