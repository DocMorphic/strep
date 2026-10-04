"""Independent scalar/vector and raw-key arithmetic for restoration replay.

The decoded sampler and authoring clock construction are shared with the
producer. Saved keys and native rate/contact arithmetic are recomputed here.
No numerical tolerance grants native feasibility or animation quality.
"""
import numpy as np
from scipy.spatial.transform import Rotation

def rate_values(world, joints, dt):
    selected = world[:, joints]
    p = selected[:, :, :3, 3]
    r = selected[:, :, :3, :3]
    increments = r[1:] @ r[:-1].transpose(0, 1, 3, 2)
    angular = Rotation.from_matrix(increments.reshape(-1, 3, 3)).as_rotvec().reshape(len(world) - 1, len(joints), 3) / dt
    return [np.linalg.norm(np.diff(p, axis=0), axis=2) / dt, np.linalg.norm(np.diff(p, n=2, axis=0), axis=2) / dt ** 2, np.linalg.norm(angular, axis=2), np.linalg.norm(np.diff(angular, axis=0), axis=2) / dt]

def skin(actor, ids, world, indices, reduction):
    s = actor['skin']
    w = world[indices]
    value = np.einsum('fvkij,vkj,vk->fvi', w[:, s.nodes[ids], :3, :], s.points[ids], s.weights[ids])
    (p, r) = actor['placement']
    value = value @ r.T + p
    return value.mean(axis=1, keepdims=True) if reduction == 'centroid' else value


def oracles(source, problem, permissions, source_world, clock, uniform, caps):
    rate_ids=np.searchsorted(clock,uniform)
    np.testing.assert_array_equal(clock[rate_ids],uniform)
    dt=uniform[1]-uniform[0]
    def native_conditions(controls, worlds):
        rows = []
        cursor = 0
        for (name, declaration) in permissions['actors'].items():
            original = source.actors[name]
            reader = original['sampler']
            for track in declaration['tracks']:
                channel = next((c for c in reader.channels if c[:2] == (track['node'], track['path'])))
                keyclock = channel[2].astype(float)
                ids = np.arange(1, len(keyclock) - 1)
                allowed = (keyclock[:-2] >= declaration['window_s'][0]) & (keyclock[2:] <= declaration['window_s'][1])
                for (first, last) in declaration['protected_s']:
                    allowed &= ~((keyclock[:-2] < last) & (keyclock[2:] > first))
                ids = ids[allowed]
                knots = np.asarray(declaration['knots_s'])
                width = 3 * (len(knots) - 2)
                weights = np.array([np.interp(keyclock[ids], knots, np.eye(len(knots))[k]) for k in range(1, len(knots) - 1)]).T
                normalized = weights @ controls[cursor:cursor + width].reshape(-1, 3)
                cursor += width
                rows.extend(np.linalg.norm(normalized, axis=1) - 1)
            joints = original['rig'].joints
            current = worlds[name][rate_ids]
            old = source_world[name][rate_ids]
            displacement = np.linalg.norm(current[:, joints, :3, 3] - old[:, joints, :3, 3], axis=2)
            limit = declaration['maximum_joint_displacement_m']
            rows.extend(((displacement - limit) / limit).ravel())
            for (i, value) in enumerate(rate_values(current, joints, dt)):
                bound = caps[f'{name}_metric_{i}']
                rows.extend(((value - bound - 1e-05) / np.maximum(bound, 0.001)).ravel())
        assert cursor == len(controls)
        for data in problem.rows:
            entry = data['entry']
            row = entry['authored']
            target = row['target']
            indices = data['ids']
            left = skin(source.actors[row['actor']], entry['ids'], worlds[row['actor']], indices, row['reduction'])
            if target['space'] == 'actor':
                right = skin(source.actors[target['actor']], entry['target_ids'], worlds[target['actor']], indices, target['reduction'])
            elif target['space'] == 'world':
                right = np.repeat(entry['target_ids'][None], len(indices), axis=0)
            else:
                (p, r) = source.object_poses(target['object'], data['times'])
                right = np.einsum('fij,vj->fvi', r, entry['target_ids']) + p[:, None]
            error = left - right
            if target['space'] == 'object':
                error = np.einsum('fvi,fij->fvj', error, r)
            limit = row['limits']['position_m']
            rows.extend(((np.linalg.norm(error, axis=2) - limit) / max(limit, 0.0001)).ravel())
            for population in data['populations']:
                ids = np.searchsorted(data['times'], population['times_s'])
                assert len(ids) >= 2
                speed = np.linalg.norm(np.diff(error[ids], axis=0), axis=2) * population['rate_hz']
                limit = row['limits']['relative_speed_m_s']
                rows.extend(((speed - limit) / max(limit, 0.001)).ravel())
        return np.asarray(rows)

    def reconstruct_curve_keys(current, controls):
        cursor = 0
        key_count = 0
        for (name, declaration) in permissions['actors'].items():
            original = source.actors[name]
            proposed = current.actors[name]
            assert original['rig'].document['nodes'] == proposed['rig'].document['nodes']
            np.testing.assert_array_equal(original['rig'].inverse, proposed['rig'].inverse)
            reader = original['sampler']
            other = proposed['sampler']
            selected = set()
            assert len(reader.channels) == len(other.channels) and reader.duration == other.duration
            for track in declaration['tracks']:
                key = (track['node'], track['path'])
                selected.add(key)
                before = next((c for c in reader.channels if c[:2] == key))
                after = next((c for c in other.channels if c[:2] == key))
                assert before[4] == after[4] == 'LINEAR'
                np.testing.assert_array_equal(before[2], after[2])
                keyclock = before[2].astype(float)
                ids = np.arange(1, len(keyclock) - 1)
                allowed = (keyclock[:-2] >= declaration['window_s'][0]) & (keyclock[2:] <= declaration['window_s'][1])
                for (first, last) in declaration['protected_s']:
                    allowed &= ~((keyclock[:-2] < last) & (keyclock[2:] > first))
                ids = ids[allowed]
                knots = np.asarray(declaration['knots_s'])
                width = 3 * (len(knots) - 2)
                weights = np.array([np.interp(keyclock[ids], knots, np.eye(len(knots))[k]) for k in range(1, len(knots) - 1)]).T
                unit = np.deg2rad(track['maximum_change']) if track['path']=='rotation' else track['maximum_change']
                delta = weights @ controls[cursor:cursor + width].reshape(-1, 3) * unit
                cursor += width
                expected = before[3].copy()
                changed = np.any(delta != 0, axis=1)
                if track['path']=='rotation':
                    angle = np.linalg.norm(delta, axis=1)
                    factor = np.divide(np.sin(angle / 2), angle, out=np.full_like(angle, 0.5), where=angle != 0)
                    b = np.c_[delta * factor[:, None], np.cos(angle / 2)]
                    a = before[3][ids].astype(float)
                    q = np.c_[a[:, 3, None] * b[:, :3] + b[:, 3, None] * a[:, :3] + np.cross(a[:, :3], b[:, :3]), a[:, 3] * b[:, 3] - np.sum(a[:, :3] * b[:, :3], axis=1)]
                    q *= np.where(np.sum(q * a, axis=1) < 0, -1.0, 1.0)[:, None]
                    expected[ids[changed]] = q[changed].astype(np.float32)
                else:
                    assert track['path']=='translation'
                    expected[ids[changed]] = (before[3][ids[changed]]+delta[changed]).astype(np.float32)
                np.testing.assert_array_equal(expected, after[3])
                key_count += len(ids)
            for (before, after) in zip(reader.channels, other.channels):
                assert before[:2] == after[:2] and before[4] == after[4]
                np.testing.assert_array_equal(before[2], after[2])
                if before[:2] not in selected:
                    np.testing.assert_array_equal(before[3], after[3])
        assert cursor == len(controls)
        return key_count

    def native_vector_population(controls, worlds):
        vectors=[]; bounds=[]; scales=[]; cursor=0
        def add(value, bound, scale):
            value=np.asarray(value).reshape(-1,3); vectors.append(value)
            bounds.append(np.broadcast_to(bound,(len(value),)).copy())
            scales.append(np.broadcast_to(scale,(len(value),)).copy())
        for name, declaration in permissions['actors'].items():
            actor=source.actors[name]
            for track in declaration['tracks']:
                assert track['path'] in ('rotation','translation')
                c=next(c for c in actor['sampler'].channels if c[:2]==(track['node'],track['path']))
                times=c[2].astype(float); ids=np.arange(1,len(times)-1)
                mask=(times[:-2]>=declaration['window_s'][0])&(times[2:]<=declaration['window_s'][1])
                for first,last in declaration['protected_s']:mask&=~((times[:-2]<last)&(times[2:]>first))
                ids=ids[mask]; knots=declaration['knots_s']; width=3*(len(knots)-2)
                weights=np.array([np.interp(times[ids],knots,np.eye(len(knots))[k]) for k in range(1,len(knots)-1)]).T
                add(weights@controls[cursor:cursor+width].reshape(-1,3),1.,1.); cursor+=width
            joints=actor['rig'].joints; current=worlds[name][rate_ids]; original=source_world[name][rate_ids]
            limit=declaration['maximum_joint_displacement_m']
            add(current[:,joints,:3,3]-original[:,joints,:3,3],limit,limit)
            selected=current[:,joints]; positions=selected[:,:,:3,3]; rotations=selected[:,:,:3,:3]
            relative=rotations[1:]@rotations[:-1].transpose(0,1,3,2)
            angular=Rotation.from_matrix(relative.reshape(-1,3,3)).as_rotvec().reshape(len(current)-1,len(joints),3)/dt
            rates=[np.diff(positions,axis=0)/dt,np.diff(positions,n=2,axis=0)/dt**2,angular,np.diff(angular,axis=0)/dt]
            for i,value in enumerate(rates):
                bound=caps[f'{name}_metric_{i}']; add(value,(bound+1e-5).ravel(),np.maximum(bound,.001).ravel())
        assert cursor==len(controls)
        for data in problem.rows:
            entry=data['entry']; row=entry['authored']; target=row['target']; ids=data['ids']
            left=skin(source.actors[row['actor']],entry['ids'],worlds[row['actor']],ids,row['reduction'])
            if target['space']=='actor':right=skin(source.actors[target['actor']],entry['target_ids'],worlds[target['actor']],ids,target['reduction'])
            elif target['space']=='world':right=np.repeat(entry['target_ids'][None],len(ids),axis=0)
            else:
                p,r=source.object_poses(target['object'],data['times']);right=np.einsum('fij,vj->fvi',r,entry['target_ids'])+p[:,None]
            error=left-right
            if target['space']=='object':error=np.einsum('fvi,fij->fvj',error,r)
            limit=row['limits']['position_m'];add(error,limit,max(limit,.0001))
            for population in data['populations']:
                selected=np.searchsorted(data['times'],population['times_s'])
                limit=row['limits']['relative_speed_m_s'];add(np.diff(error[selected],axis=0)*population['rate_hz'],limit,max(limit,.001))
        return np.concatenate(vectors),np.concatenate(bounds),np.concatenate(scales)

    return native_conditions, reconstruct_curve_keys, native_vector_population
