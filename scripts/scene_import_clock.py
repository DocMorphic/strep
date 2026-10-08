"""Complete shared scene clocks and independent GLB hierarchy comparisons.

No skin, contact, physics or motion-quality approval follows from a pose match.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from native_engine_clock import clock_echo_matches, compare_poses


def exact_echo(value):
    if type(value) is not str or len(value) != 16:
        raise ValueError('Exact Float64 little-endian clock echo required')
    try:
        raw = bytes.fromhex(value)
    except ValueError:
        raise ValueError('Canonical hexadecimal clock echo required') from None
    if len(raw) != 8 or raw.hex() != value:
        raise ValueError('Canonical hexadecimal clock echo required')
    result = float(np.frombuffer(raw, dtype='<f8')[0])
    if not np.isfinite(result) or result < 0:
        raise ValueError('Finite nonnegative clock echo required')
    return result


def shared_clock(frame_count, rate_hz, samplers):
    if type(frame_count) is not int or not 2 <= frame_count <= 1800:
        raise ValueError('Integer scene frame count from 2 to 1800 required')
    if type(rate_hz) is not int or not 30 <= rate_hz <= 240 or rate_hz % 30:
        raise ValueError('Integer rate divisible by 30 from 30 to 240 required')
    if not samplers:
        raise ValueError('At least one source animation required')
    duration = (frame_count - 1) / 30
    groups = [np.arange((frame_count - 1) * (rate_hz // 30) + 1) / rate_hz]
    for sampler in samplers:
        if abs(sampler.duration - duration) > 1e-5:
            raise ValueError('Scene and source animation durations differ')
        groups.extend(channel[2].astype(float) for channel in sampler.channels)
    # Stored float32 native times can differ from the nominal clock. Preserve
    # both, including each source's actual end key, without near-deduplication.
    times = np.unique(np.concatenate(groups))
    if not np.isfinite(times).all() or times[0] != 0 or np.any(times > duration + 1e-5):
        raise ValueError('Source keys outside scene clock')
    return times


def verify_scene(request, observed, actors, objects=None):
    """Validate a complete synchronous observation before comparing each pose.

    actors: name -> (RigAsset, AnimationSampler, authored rigid placement).
    objects: name -> (AnimationSampler, exported node index).
    """
    objects = {} if objects is None else objects
    times = np.asarray(request['sample_times_s'], float)
    nominal_end = (request['source_frame_count'] - 1) / 30
    terminal_snaps = []
    if observed['id'] != request['id'] or set(observed['actors']) != set(actors):
        raise ValueError('Complete unchanged scene actor identities required')
    if (len(observed['frames']) != len(times) or len(observed['object_frames']) != len(times)
            or len(observed['clock_samples']) != len(times)):
        raise ValueError('Complete scene sample population required')
    for i, time in enumerate(times):
        clock = observed['clock_samples'][i]
        if (not clock_echo_matches(time, exact_echo(clock['requested_time_f64le']))
                or set(clock['actors']) != set(actors)
                or set(clock['actor_times_f64le']) != set(actors)
                or set(observed['frames'][i]) != set(actors)
                or set(observed['object_frames'][i]) != set(objects)):
            raise ValueError('Scene clock or sample identities differ')
        echoes = {name: (exact_echo(v), actors[name][1].duration)
                  for name, v in clock['actor_times_f64le'].items()}
        if objects:
            durations = {s.duration for s, _ in objects.values()}
            if len(durations) != 1:
                raise ValueError('One shared object animation duration required')
            echoes['object_player'] = (exact_echo(clock['objects_time_f64le']), next(iter(durations)))
        elif clock['objects_time_s'] is not None or clock['objects_time_f64le'] is not None:
            raise ValueError('Unexpected object player clock')
        for entity, (echo, duration) in echoes.items():
            if clock_echo_matches(time, echo):
                continue
            # Godot snaps the nominal terminal sample to its stored float32
            # animation endpoint. Account for this single declared sample and
            # exact source endpoint; never apply a general clock tolerance.
            if (time != nominal_end or abs(duration - nominal_end) > 1e-5
                    or not clock_echo_matches(duration, echo)):
                raise ValueError('Actors and objects did not seek the shared clock')
            terminal_snaps.append(dict(sample_index=i, entity=entity, requested_time_s=float(time),
                                       actual_time_s=echo, source_end_time_s=duration,
                                       difference_s=echo - time))
    checks = []
    for name, (rig, sampler, placement) in actors.items():
        metadata = observed['actors'][name]
        names = [rig.document['nodes'][n]['name'] for n in rig.joints]
        found_names = metadata['bone_names']
        if (len(set(names)) != len(names) or len(found_names) != len(names)
                or len(set(found_names)) != len(names) or set(found_names) != set(names)):
            raise ValueError('Complete unique imported bone identities required')
        if (metadata['animation_index'] != 0 or metadata['loop_mode'] != 0
                or not np.isfinite(metadata['duration_s'])
                or abs(metadata['duration_s'] - sampler.duration) > 1e-6):
            raise ValueError('Original nonlooping source animation required')
        order = [rig.joints[names.index(n)] for n in found_names]
        p = np.asarray(placement['translation_m'], float)
        q = np.asarray(placement['rotation_xyzw'], float)
        if (p.shape != (3,) or q.shape != (4,) or not np.isfinite(p).all()
                or not np.isfinite(q).all() or abs(np.linalg.norm(q) - 1) > 1e-8):
            raise ValueError('Finite unit rigid actor placement required')
        transform = np.eye(4)
        transform[:3, :3] = Rotation.from_quat(q).as_matrix()
        transform[:3, 3] = p
        position_error = basis_error = 0.
        for time, frame in zip(times, observed['frames']):
            error = compare_poses(transform @ sampler.sample(time)[order], frame[name])
            position_error = max(position_error, error['position_error_m'])
            basis_error = max(basis_error, error['basis_element_error'])
        checks.append(dict(actor=name, samples=len(times), bones=len(names),
                           maximum_position_error_m=position_error,
                           maximum_basis_element_error=basis_error,
                           precision_screen=1e-4, passed=max(position_error, basis_error) <= 1e-4))
    object_checks = []
    for name, (sampler, node) in objects.items():
        pe = re = 0.
        for time, frame in zip(times, observed['object_frames']):
            error = compare_poses(sampler.sample(time)[[node]], [frame[name]])
            pe = max(pe, error['position_error_m'])
            re = max(re, error['basis_element_error'])
        object_checks.append(dict(object=name, samples=len(times), maximum_position_error_m=pe,
                                 maximum_basis_element_error=re, precision_screen=1e-5,
                                 passed=max(pe, re) <= 1e-5))
    return dict(actors=checks, objects=object_checks,
                terminal_seek_snaps=terminal_snaps,
                all_precision_screens_passed=all(c['passed'] for c in checks + object_checks),
                quality_approved=False, continuous_collision_certified=False)
