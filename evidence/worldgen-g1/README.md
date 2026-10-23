# G1 review evidence

The implementation and 18 acceptance contracts are documented in
[WORLDGEN_G1](../../docs/owner/WORLDGEN_G1.md). `summary.json` records source identity,
commands, environment, exact totals and deferred work. The final delivery is
`checkpoint/worldgen-g1-verified-20261023`; compare it to
`checkpoint/worldgen-g1-start-20261023-155942` for the scoped diff.

- `before/`: actual pre-edit production probes and nine baseline failures.
  The supplied Pillow atlas attempt failed because Pillow was absent; its stderr
  is retained. The successful terrain atlas was produced headlessly with pygame.
  Raw audit probes also contain out-of-scope clock/cache observations, not G1 claims.
- `after/`: updated actual terrain atlas, complete finite diagnostic, source hashes,
  and cross-interpreter semantic fingerprints for both generation orders.
- `final-focused/`: collected 110-test run, loop action evidence and real WFC
  solve/fallback outcomes. `milestone-focused/` is the earlier 106-test milestone;
  `iteration-focused/` is an earlier 83-test integration run.
- `pre-container-focused.txt`: successful 109-test run before adding the explicitly
  nonempty real-market-crate interaction fixture. `interrupted-d-console.txt` is
  the early full-gate attempt stopped to add that required test; it does not certify
  any final result. The completed final gate report and console are stored separately.
- `authoring.json`: the supplied cottage checker. It manually materializes example
  contents and is not substituted for Engine population tests.

The atlas is a terrain diagnostic, not a game screenshot. It omits decor, items,
actors and lighting. See action tests for actual doors/pickup/reading/container
interaction. The baseline/after colours were improved to distinguish dirt tracks;
geometry must be read from the arrays and seam masks, not inferred from colour alone.

No personal saves, development checkouts, dependency trees, credentials or source
archives are included. Existing historical accepted evidence is preserved.
