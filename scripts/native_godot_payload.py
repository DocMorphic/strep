"""Export original LINEAR joint keys for Godot's native Animation resource."""


def payload(rig, sampler, digest):
    names = [rig.document['nodes'][n].get('name') for n in rig.joints]
    if any(not name or ':' in name or '/' in name for name in names) or len(set(names)) != len(names):
        raise ValueError('Unique plain bone names required')
    channels = []
    for node, path, times, values, mode in sampler.channels:
        if node not in rig.joints or mode != 'LINEAR':
            raise ValueError('Native Godot adapter currently supports LINEAR joint TRS only')
        channels.append(dict(bone=rig.document['nodes'][node]['name'], path=path,
            times_s=times.astype(float).tolist(), values=values.tolist(), interpolation=mode))
    return dict(schema_version=1, source_sha256=digest, duration_s=sampler.duration, name=sampler.name,
                channels=channels, loop=False)
