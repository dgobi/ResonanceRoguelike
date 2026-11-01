"""Narrow refresh of shipped AI-arc presentation; custom text stays owned."""
KNOWN = {'patient_amber_hunter': {'name': {'Patient Amber Hunter': 'Amber Shell Hunter'},
                          'description': {'An amber-shelled insect that stings, withdraws, and watches for rigid prey.': 'A '
                                                                                                                         'six-legged '
                                                                                                                         'insect '
                                                                                                                         'with '
                                                                                                                         'a '
                                                                                                                         'split '
                                                                                                                         'amber '
                                                                                                                         'shell. '
                                                                                                                         'Its '
                                                                                                                         'hooked '
                                                                                                                         'mandibles '
                                                                                                                         'glisten.'}},
 'timed_amber_hunter': {'name': {'Timed Amber Hunter': 'Amber Whine Beetle'},
                        'description': {'An amber-shelled insect that stings, withdraws, and returns after a short hold.': 'A '
                                                                                                                           'broad '
                                                                                                                           'amber '
                                                                                                                           'insect '
                                                                                                                           'with '
                                                                                                                           'twitching '
                                                                                                                           'antennae '
                                                                                                                           'and '
                                                                                                                           'pale, '
                                                                                                                           'hooked '
                                                                                                                           'mandibles.'}},
 'nettle_stalker': {'description': {'A low hunter with a numbing bite. Its victim has a short warning before the legs lock.': 'A '
                                                                                                                              'low, '
                                                                                                                              'bristling '
                                                                                                                              'hunter '
                                                                                                                              'with '
                                                                                                                              'wet '
                                                                                                                              'fangs '
                                                                                                                              'and '
                                                                                                                              'a '
                                                                                                                              'nettled '
                                                                                                                              'hide.'}},
 'drowsing_stalker': {'description': {'A low hunter whose numbing bite spreads slowly. The longer warning leaves more time to respond.': 'A '
                                                                                                                                         'low '
                                                                                                                                         'hunter '
                                                                                                                                         'with '
                                                                                                                                         'drooping '
                                                                                                                                         'eyelids '
                                                                                                                                         'and '
                                                                                                                                         'dark '
                                                                                                                                         'saliva '
                                                                                                                                         'along '
                                                                                                                                         'its '
                                                                                                                                         'jaws.'}},
 'venom_treatment': {'description': {'A bitter measured draught for numbing venom. Clears spreading numbness or locked legs without healing wounds; its protection lasts only through recovery.': 'A '
                                                                                                                                                                                                  'bitter '
                                                                                                                                                                                                  'draught '
                                                                                                                                                                                                  'that '
                                                                                                                                                                                                  'eases '
                                                                                                                                                                                                  'spreading '
                                                                                                                                                                                                  'numbness. '
                                                                                                                                                                                                  'The '
                                                                                                                                                                                                  'cork '
                                                                                                                                                                                                  'is '
                                                                                                                                                                                                  'sealed '
                                                                                                                                                                                                  'with '
                                                                                                                                                                                                  'green '
                                                                                                                                                                                                  'wax.'}},
 'measured_venom_remedy': {'description': {'A bitter measured draught for numbing venom. Clears spreading numbness or locked legs without healing wounds; its protection lasts only through recovery.': 'A '
                                                                                                                                                                                                        'bitter '
                                                                                                                                                                                                        'draught '
                                                                                                                                                                                                        'that '
                                                                                                                                                                                                        'eases '
                                                                                                                                                                                                        'spreading '
                                                                                                                                                                                                        'numbness. '
                                                                                                                                                                                                        'The '
                                                                                                                                                                                                        'cork '
                                                                                                                                                                                                        'is '
                                                                                                                                                                                                        'sealed '
                                                                                                                                                                                                        'with '
                                                                                                                                                                                                        'green '
                                                                                                                                                                                                        'wax.'}}}


def refresh(instance, identifier):
    for field, values in KNOWN.get(identifier, {}).items():
        previous = getattr(instance, field, None)
        if previous in values:
            setattr(instance, field, values[previous])


def refresh_map(local_map):
    """Floor/container Items are pickled instances rather than inventory rows."""
    items = [item for rows in local_map.floor_objects.values() for item in rows]
    items += [item for entry in local_map.container_state.values() for item in entry.get('items', [])]
    for item in items:
        refresh(item, getattr(item, 'item_id', None))
