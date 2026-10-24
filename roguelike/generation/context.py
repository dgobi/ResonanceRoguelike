"""Durable, purpose-separated initial-generation randomness (not gameplay replay)."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import random

GENERATION_REVISION = 'wg5'
LEGACY_REVISION = 'legacy-unversioned'


def _typed(value):
    if value is None:
        return ['null']
    if type(value) in (str, int, bool):
        return [type(value).__name__, value]
    if isinstance(value, (tuple, list)):
        return ['sequence', [_typed(v) for v in value]]
    raise TypeError(f'Unsupported generation key: {type(value).__name__}')


def stable_seed(*keys) -> int:
    """BLAKE2b-128 of UTF-8 compact JSON with explicit scalar type tags."""
    payload = json.dumps(_typed(keys), ensure_ascii=False, separators=(',', ':'))
    return int.from_bytes(hashlib.blake2b(payload.encode('utf-8'), digest_size=16).digest(), 'big')


@dataclass(frozen=True)
class GenerationContext:
    world_seed: int
    scene_seed: int
    address: tuple
    revision: str = GENERATION_REVISION

    def seed(self, purpose: str, *keys) -> int:
        return stable_seed(self.revision, self.world_seed, self.scene_seed,
                           self.address, purpose, keys)

    def rng(self, purpose: str, *keys) -> random.Random:
        return random.Random(self.seed(purpose, *keys))


def map_context(local_map) -> GenerationContext:
    return getattr(local_map, 'generation_context', None) or GenerationContext(0, 0, ('standalone',))


class GenerationError(ValueError):
    """A candidate scene failed validation and must not be published."""
