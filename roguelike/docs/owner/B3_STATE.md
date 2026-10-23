# B3 checkpoint contract — 23 October 2026

The accepted Arc A/B1/B2 history is merged into production `main` at `d179c08`.
All B3 implementation and tests use `G:\GameDev\RoguelikeProject` directly.
The owner's work was checkpointed before integration; no development checkout,
worktree or task branch is created. See `AGENTS.md` for the ongoing preference.

## What a checkpoint owns

A full save captures player/component state, the world record, every previously
persisted cold scene, every session scene written by travel/eviction, every hot
surface/submap, and the current scene's live actors. The precedence is cold base,
session disk, hot entries, then active scene. All hot entries are conservatively
treated as potentially dirty because map layers also change in place.

Each generation contains `world.json`, `player.json`, `meta.json`, `chunks/*.pkl`
and a manifest of every payload's byte length and SHA-256. The payload is still
development save v2; the outer checkpoint container is version 1. Old clients
cannot treat the new directory layout as a flat v2 save. Map pickle files remain
trusted local data, not a safe interchange format for untrusted downloaded saves.

`slot_N/.sessions/<id>/chunks` is a mutable working cache. Its base is one
immutable generation under `slot_N/generations/g-<id>`. Travel and eviction only
write that session. F5 in nondebug mode publishes a full checkpoint; the existing
surface-boundary autosave also publishes a full checkpoint. Stairs alone do not
advance the checkpoint. Cold scenes are preserved, not simulated while unloaded.

Example: save grass, change it to dirt and descend. F9 returns the saved grass,
player, world and timers together. Change an inactive hot map to mud and save
elsewhere: a new process now sees mud. Offscreen processing ticks captured by a
full save continue from their saved remaining duration.

## Publication and interruption

The writer takes a nonblocking kernel lock for this slot and checks that HEAD
has not changed since load/save. It writes a unique pending generation, flushes
each file, writes its manifest, seals the directory, verifies its contents, backs
up the committed ancestor reference, then atomically replaces `HEAD.json`.
Only that last replacement publishes a checkpoint. A terminated writer before
publication leaves the old checkpoint; termination after publication leaves the
new complete checkpoint. Kernel locks release automatically on process death.

Failed writes report failure and keep the previous published checkpoint. Failed
eviction leaves the dirty entry in memory. Concurrent/stale writers cannot
silently overwrite a newer checkpoint. Load checks that HEAD stayed unchanged
while it reconstructed the state; a racing publication requires retrying load.

File flushes and same-volume atomic replacement are tested against process
termination and injected I/O failure. Python does not expose directory fsync on
Windows. This is not a claim of universal power-loss, device-failure, network
filesystem or malicious-file safety.

## Recovery, rollback and replacement

Readers consider only generations named by HEAD and BACKUP, newest first. They
check all payload hashes, including inactive scenes, then validate/reconstruct
world, player, actors and derived components before replacing live owners. A bad
generation falls back to the previous complete published generation with a
visible recovery message. Read failures leave the current live graph and save
bytes intact. Recovery itself never repairs or rewrites files.

`SaveManager.load(engine, previous=True)` explicitly restores the previous
published checkpoint. F9 restores the latest valid published checkpoint. Saving
after recovery/rollback starts a new timeline whose previous reference is the
restored generation. No new rollback hotkey or slot-selection UI is introduced.

Unreferenced generations are never auto-promoted. If the first write dies while
only a partial staging directory exists, the deliberate seed/new-game path is
still available. A sealed generation with no publication references is preserved
and reported as unrecoverable; this also avoids silently starting over when both
reference files were lost. The still-running original session can retry a failed
save. With all published generations invalid, startup refuses to enter play.

Generations and abandoned working/staging directories are retained until explicit
slot retirement. No automatic history pruning races an older running reader.
This favors recovery and auditability at the cost of disk growth; it is not a
bounded-storage retention implementation. Only referenced generations participate
in automatic recovery, even when older directories remain on disk.

## Compatibility and deletion scope

Existing flat B1/B2 v2 slots can be loaded without modification. Saving into such
a slot is refused with a read-only/implicit-migration explanation. No personal
save migration is authorized or performed. Existing v1/unsupported or incomplete
slots continue to be rejected; new test campaigns use new disposable save roots.

Slot IDs are bounded integers. Path redirections, including Windows junctions,
are refused. `delete_slot()` retires exactly its `slot_N` directory under the
configured root before cleaning the retired directory. A cleanup failure can
leave that retired directory for inspection; it never broadens deletion scope.
Death and debug F11 use this API. Death-screen quit no longer deletes the saves
root. Other slots and unrelated files in that root survive these routes.

The B1 identity and B2 component contracts remain in effect. C transfer/equipped
drop, unfinished effect consumers, UI text layout and full RNG replay remain
separate; see [B3_DEFERRED](B3_DEFERRED.md).
