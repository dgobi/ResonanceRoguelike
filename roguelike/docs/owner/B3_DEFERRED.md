> **Historical B3 boundary:** C now repairs equipped-drop and the bounded ownership/transfer/crafting paths in [C_STATE](C_STATE.md). The original B3 evidence and return ZIP remain unchanged. Other limits below remain unless C_STATE explicitly resolves them.

# Boundaries after B3

B3 repairs B3-GENERATIONS and B3-DIRTY-HOT. Whole checkpoint, dirty-owner,
interruption, recovery, rollback and deletion properties now have positive tests.

The two earlier gameplay defects remain outside this persistence task and are
compared with the accepted B2 observations:

- **C-DROP-EQUIPPED:** normal drop can move an equipped blade to the floor while
  retaining its equipment reference/flag. Saving refuses unowned equipment;
  B3 reports save failure rather than silently publishing invalid ownership.
- **UI-TEXT-HEIGHT:** the authored sarcophagus label still cuts off after `If`
  at 1280×720. Content binding works; complete layout is not claimed.

Other source-reviewed boundaries remain: temporary armor hit consumers, creature
suppression/disruption, wight confirmation, salve movement timing, container item
encoding, crafting cancellation/refunds, corpse transfers, carried decay and full
RNG replay. Persisting their fields does not finish their gameplay implementations.

B3 retains generations and session/staging directories until slot retirement;
automatic disk-budget pruning is not implemented. Windows power-loss/device and
network-filesystem guarantees are not inferred from process-interruption tests.
Legacy flat slots are read-only; personal-save migration needs a separate explicit
request. Trusted local pickle payloads are not safe for untrusted interchange.

Recommend C next: inventory/floor/equipment/container ownership and transfer
transactions, beginning with equipped-drop consistency. Continue on production
`main`, preserve work with Git checkpoints, and use headless/app-local tests.
