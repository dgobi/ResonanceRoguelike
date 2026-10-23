"""Immutable checkpoint containers. Payload schema remains development save v2.

Only HEAD/BACKUP references publish generations. An abandoned staging directory
or an unreferenced complete generation is never promoted during recovery.
"""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import uuid

GENERATION = re.compile(r"g-[0-9a-f]{32}\Z")
SCENE = re.compile(r"(?:-?\d+_-?\d+|[A-Za-z0-9_-]+)\.pkl\Z")


class CheckpointError(ValueError):
    pass


def no_links(path: Path) -> Path:
    """Reject redirected save paths, including Windows directory junctions."""
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if part.is_symlink() or getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise CheckpointError(f"Redirected save path refused: {part}")
    return path


def encoded(value) -> bytes:
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode('utf-8')


def record(data: bytes) -> dict:
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def sync_directory(path):
    # Windows does not expose directory fsync through Python. Atomic replace and
    # flushed file contents protect process interruption, not all power failures.
    if os.name != 'nt':
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def write_file(path: Path, data: bytes):
    no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def atomic_write(path: Path, data: bytes):
    temp = path.with_name('.' + path.name + '-' + uuid.uuid4().hex + '.tmp')
    try:
        write_file(temp, data)
        os.replace(temp, no_links(path))
        sync_directory(path.parent)
    finally:
        if temp.exists():
            temp.unlink()


@contextmanager
def slot_lock(slot: Path):
    """Kernel lock is released on process death; persistent lock bytes are benign."""
    slot = no_links(slot)
    lock = no_links(slot.parent / ('.' + slot.name + '.lock'))
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('a+b') as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise CheckpointError('Save slot is busy in another process') from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class CheckpointStore:
    def __init__(self, slot):
        self.slot = no_links(Path(slot))
        self.errors = []

    def token(self):
        path = self.slot / 'HEAD.json'
        return record(path.read_bytes()) if no_links(path).is_file() else None

    def references(self):
        refs = []
        self.errors = []
        for name in ('HEAD.json', 'BACKUP.json'):
            path = self.slot / name
            if not no_links(path).exists():
                continue
            try:
                value = json.loads(path.read_bytes())
                if (type(value.get('checkpoint_version')) is not int or value['checkpoint_version'] != 1
                        or not isinstance(value.get('current'), str) or not GENERATION.fullmatch(value['current'])
                        or (value.get('previous') is not None and
                            (not isinstance(value['previous'], str) or not GENERATION.fullmatch(value['previous'])))):
                    raise CheckpointError('Invalid checkpoint reference')
                for generation in (value['current'], value.get('previous')):
                    if generation and generation not in refs:
                        refs.append(generation)
            except (ValueError, TypeError, AttributeError) as error:
                self.errors.append(f'{name}: {error}')
        return refs

    def validate(self, generation):
        if not isinstance(generation, str) or not GENERATION.fullmatch(generation):
            raise CheckpointError('Invalid generation identifier')
        root = no_links(self.slot / 'generations' / generation)
        manifest = json.loads(no_links(root / 'manifest.json').read_bytes())
        if (type(manifest.get('checkpoint_version')) is not int or manifest['checkpoint_version'] != 1
                or manifest.get('generation') != generation or not isinstance(manifest.get('files'), dict)):
            raise CheckpointError('Invalid checkpoint manifest')
        files = manifest['files']
        if not {'world.json', 'player.json', 'meta.json'} <= set(files):
            raise CheckpointError('Incomplete checkpoint manifest')
        actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
        if actual != set(files) | {'manifest.json'}:
            raise CheckpointError('Checkpoint file set mismatch (missing scene or metadata)')
        for name, expected in files.items():
            if name not in ('world.json', 'player.json', 'meta.json') and not (
                    name.startswith('chunks/') and SCENE.fullmatch(name[7:])):
                raise CheckpointError(f'Invalid checkpoint member {name!r}')
            path = no_links(root / name)
            if record(path.read_bytes()) != expected:
                raise CheckpointError(f'Checkpoint checksum mismatch: {name}')
        return root

    def candidates(self):
        refs = self.references()
        candidates = []
        for generation in refs:
            try:
                candidates.append((generation, self.validate(generation)))
            except (OSError, ValueError, TypeError, AttributeError) as error:
                self.errors.append(f'{generation}: {error}')
        return candidates

    def legacy(self):
        # A damaged published slot must never fall back to unrelated flat files.
        if any((self.slot / name).exists() for name in ('HEAD.json', 'BACKUP.json', 'generations')):
            return None
        return self.slot if (self.slot / 'meta.json').exists() else None

    def publish(self, payloads, previous, expected_token, fault=lambda phase: None):
        with slot_lock(self.slot):
            if self.token() != expected_token:
                raise CheckpointError('Checkpoint changed in another session; reload before saving')
            if self.legacy() is not None:
                raise CheckpointError('Legacy flat slot is read-only; no implicit save migration')
            generation = 'g-' + uuid.uuid4().hex
            parent = self.slot / 'generations'
            stage = no_links(parent / ('.pending-' + generation[2:]))
            stage.mkdir(parents=True)
            fault('stage_created')
            files = {}
            for name, data in sorted(payloads.items()):
                if name not in ('world.json', 'player.json', 'meta.json') and not (
                        name.startswith('chunks/') and SCENE.fullmatch(name[7:])):
                    raise CheckpointError(f'Invalid checkpoint member {name!r}')
                write_file(stage / name, data)
                files[name] = record(data)
                fault('payload:' + name)
            write_file(stage / 'manifest.json', encoded(dict(checkpoint_version=1, generation=generation, files=files)))
            sync_directory(stage / 'chunks')
            sync_directory(stage)
            fault('manifest_written')
            target = no_links(parent / generation)
            os.replace(stage, target)
            sync_directory(parent)
            self.validate(generation)
            fault('generation_ready')
            # Back up ONLY a committed, validated ancestor, never a corrupt head
            # or an unreferenced generation left by a failed publication.
            if previous:
                self.validate(previous)
                atomic_write(self.slot / 'BACKUP.json', encoded(dict(
                    checkpoint_version=1, current=previous, previous=None)))
            fault('backup_written')
            head = encoded(dict(checkpoint_version=1, current=generation, previous=previous))
            # Keep the pointer-write boundary separately injectable in tests.
            temp = self.slot / ('.HEAD-' + uuid.uuid4().hex + '.tmp')
            write_file(temp, head)
            fault('head_written')
            os.replace(temp, no_links(self.slot / 'HEAD.json'))
            sync_directory(self.slot)
            fault('published')
            # Return this publication's token while still under the lock. A
            # later writer must not be adopted by a post-unlock HEAD read.
            return generation, target, record(head)

    def delete(self):
        """Retire precisely this slot. Never delete its saves root or other slots."""
        slot = no_links(self.slot)
        if not re.fullmatch(r'slot_\d+', slot.name) or slot == slot.parent:
            raise CheckpointError('Invalid deletion target')
        with slot_lock(slot):
            if not slot.exists():
                return
            # Refuse nested redirections before any recursive deletion.
            for child in slot.rglob('*'):
                no_links(child)
            retired = no_links(slot.parent / ('.deleted-' + slot.name + '-' + uuid.uuid4().hex))
            assert retired.parent == slot.parent and retired != slot
            os.replace(slot, retired)
            sync_directory(slot.parent)
            # If cleanup fails, the retired directory remains recoverable and is
            # never mistaken for a new/live slot. No other path is removed.
            shutil.rmtree(retired)
