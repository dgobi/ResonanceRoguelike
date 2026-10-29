"""Admission for direct authored-room furnishings, shared with native construction.

The registry is read-only. Static presentation data is supported; system-owned
identities and behavior-bearing fields require their existing owners instead.
"""
import math

STATIC_FIELDS = {'id', 'name', 'ascii', 'description', 'blocks_movement', 'blocks_sight', 'visual_fx', 'light_emit'}
CAMPFIRES = {'campfire_unlit': 'light_campfire', 'campfire_lit': 'extinguish_campfire'}
SYSTEM_PARTS = {'vine_growth', 'vine_eyestalk', 'vine_spore_vent'}


def properties(identifier, definition):
    definition = definition if isinstance(definition, dict) else {}
    return dict(blocks_movement=bool(definition.get('blocks_movement', False)),
                declared_blocks_sight=bool(definition.get('blocks_sight', False)),
                light_emit=definition.get('light_emit', 0),
                cosmetic_fx=definition.get('visual_fx'),
                interaction=CAMPFIRES.get(identifier),
                stationary_fire=identifier == 'campfire_lit',
                sight_note='Sight uses terrain transparency; decor blocks_sight is a declaration, not applied to the FOV grid.')


def admission(data, identifier):
    definition = data.decoratives.get(identifier) if isinstance(identifier, str) else None
    rows = getattr(data, 'decorative_sources', list(data.decoratives.values()))
    matches = [r for r in rows if isinstance(r, dict) and isinstance(r.get('id'), str)
               and isinstance(identifier, str) and r['id'].casefold() == identifier.casefold()]
    reason = ''
    if not isinstance(definition, dict) or not definition or len(matches) != 1:
        reason = 'Missing or ambiguous saved decor identity (including case aliases).'
    elif definition.get('id') != identifier:
        reason = 'Resolved definition identity does not agree with its registry key.'
    elif definition.get('container'):
        reason = 'Use the container tool: this definition requires real container state and loot ownership.'
    elif definition.get('processing') or identifier in {'drying_herb', 'cooking_meat'}:
        reason = 'Requires an existing processing job; a standalone marker is not work.'
    elif identifier == 'corpse' or definition.get('interactable') == 'butcher':
        reason = 'Requires a physical corpse with source-creature identity.'
    elif identifier in SYSTEM_PARTS:
        reason = 'Requires its vine-network owner, including network-managed vents without interactable metadata.'
    elif definition.get('harvestable') or any(k in definition for k in ('harvest_item', 'depleted_id')):
        reason = 'Harvesting behavior is outside direct furnishing authoring.'
    elif identifier in CAMPFIRES:
        if definition.get('interactable') != CAMPFIRES[identifier] or set(definition) - STATIC_FIELDS - {'interactable', 'consumed_on_use', 'warmth_radius'}:
            reason = 'Campfire definition no longer matches the supported existing interaction pair.'
    elif definition.get('interactable'):
        reason = f"Unsupported interaction {definition['interactable']!r}; requires its existing system."
    elif set(definition) - STATIC_FIELDS:
        reason = 'Unsupported behavior/property fields: ' + ', '.join(sorted(set(definition) - STATIC_FIELDS)) + '.'
    if not reason:
        for key in ('blocks_movement', 'blocks_sight'):
            if key in definition and type(definition[key]) is not bool:
                reason = f'{key} must be boolean.'
        for key in ('light_emit', 'warmth_radius'):
            value = definition.get(key, 0)
            limit = 2**31-1 if key == 'light_emit' else 2**53-1
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= limit:
                reason = f'{key} must be a finite nonnegative supported number.'
        if 'visual_fx' in definition and not isinstance(definition['visual_fx'], str):
            reason = 'visual_fx must be an existing static effect name.'
    return dict(supported=not reason, reason=reason,
                properties=properties(identifier, definition or {}))
