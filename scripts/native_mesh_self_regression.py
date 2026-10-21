"""Complete-clock self-surface nonregression, not a collision certificate."""
import math
from native_self_surface import METHOD


def require(value,message):
    if not value:raise ValueError(message)


def _inventory(report):
    require(report['schema']=='strep-native-mesh-prop-geometry-result-v1'
        and report['all_policy_samples_evaluated'] is True and report['self_surface_method']==METHOD,
        'Complete versioned mesh self-surface observations required')
    times=report['complete_clock_s']
    require(isinstance(times,list) and times and all(type(t) in (int,float) and math.isfinite(t) and t>=0 for t in times)
        and all(a<b for a,b in zip(times,times[1:])), 'Complete increasing self-surface clock required')
    require(report['times_s']==times and report['sample_indices']==list(range(len(times)))
        and all(type(i) is int for i in report['sample_indices']) and len(report['samples'])==len(times),
        'Every declared self-surface sample required')
    entities={(kind,name):count for kind,field in [('actor','actor_faces'),('prop','prop_faces')]
        for name,count in report[field].items()}
    require(entities and all(isinstance(n,str) and n and type(c) is int and c>0 for (_,n),c in entities.items()),
        'Complete named self-surface topology required')
    result={}
    for index,(time,sample) in enumerate(zip(times,report['samples'])):
        require(type(sample['index']) is int and sample['index']==index and sample['time_s']==time,
            'Ordered self-surface samples required')
        seen=set()
        for entry in sample['self_surfaces']:
            key=(entry['kind'],entry['name']);require(key in entities and key not in seen,'Distinct complete self-surface entities required')
            seen.add(key);a=entry['audit'];n=entities[key]
            require(a['schema']=='strep-native-self-surface-v1' and a['status']=='complete'
                and a['complete_triangle_population'] is True and a['method']==METHOD and a['triangles']==n,
                'Complete matching self-surface audit required')
            digest=a['faces_sha256'];require(isinstance(digest,str) and len(digest)==64
                and all(c in '0123456789abcdef' for c in digest),'Exact topology digest required')
            tol=a['tolerance_m'];require(type(tol) in (int,float) and math.isfinite(tol) and 1e-10<=tol<=1e-4,'Explicit unchanged self-surface tolerance required')
            require(type(a['candidate_pairs']) is int and a['candidate_pairs']>=0
                and all(type(c) is int and c>=0 for c in a['counts'].values())
                and sum(a['counts'].values())==a['candidate_pairs'],'Complete self-surface pair counts required')
            pairs={};ambiguous=[]
            for row in a['records']:
                left,right=row['left_triangle'],row['right_triangle']
                require(type(left) is int and type(right) is int and 0<=left<right<n
                    and (left,right) not in pairs,'Distinct canonical original self-triangle pairs required')
                kind=row['kind'];require(kind in ('proper_crossing','coplanar_or_near_parallel_overlap','boundary_or_near_contact'),
                    'Explicit self-surface relation required')
                length=row['overlap_length_m']
                if kind=='proper_crossing':
                    require(type(length) in (int,float) and math.isfinite(length) and length>0,'Finite positive crossing interval required')
                else:ambiguous.append((left,right))
                pairs[left,right]=(kind,length)
            require(sum(kind=='proper_crossing' for kind,_ in pairs.values())==a['counts'].get('proper_crossing',0),
                'Every observed proper crossing must be retained')
            degenerate=a['degenerate_faces'];require(isinstance(degenerate,list)
                and all(type(i) is int and 0<=i<n for i in degenerate) and len(set(degenerate))==len(degenerate),
                'Complete distinct degenerate triangle identities required')
            result[(time,*key)]=dict(topology=digest,vertices=a['vertices'],triangles=n,tolerance=tol,
                pairs=pairs,ambiguous=ambiguous,degenerate=degenerate)
        require(seen==set(entities),'Missing self-surface entity')
    return result


def compare_self_surfaces(original,candidate):
    """Reject new/worse measured crossings and unknown self-surface outcomes.

    A retained pair's intersection interval may not grow. That length is not
    penetration depth. Existing crossings still fail whole-scene eligibility;
    this supplemental comparison cannot approve an already intersecting solid.
    """
    try:
        before,after=_inventory(original),_inventory(candidate)
        require(before.keys()==after.keys(),'Self-surface clock or entity population changed')
        regressions=[];unavailable=[]
        for key,a in before.items():
            b=after[key]
            require(all(a[k]==b[k] for k in ('topology','vertices','triangles','tolerance')),
                'Self-surface topology or tolerance changed')
            identity=dict(time_s=key[0],kind=key[1],name=key[2])
            if a['ambiguous'] or b['ambiguous'] or a['degenerate'] or b['degenerate']:
                unavailable.append(dict(**identity,original_ambiguous_pairs=len(a['ambiguous']),
                    candidate_ambiguous_pairs=len(b['ambiguous']),original_degenerate_faces=a['degenerate'],
                    candidate_degenerate_faces=b['degenerate']))
            for pair,(kind,length) in b['pairs'].items():
                if kind!='proper_crossing':continue
                old=a['pairs'].get(pair)
                if old is None or old[0]!='proper_crossing' or length>old[1]:
                    regressions.append(dict(**identity,triangles=list(pair),
                        reason='new-crossing' if old is None or old[0]!='proper_crossing' else 'crossing-interval-increased',
                        original_overlap_length_m=old[1] if old and old[0]=='proper_crossing' else None,
                        candidate_overlap_length_m=length))
        return dict(schema='strep-mesh-self-nonregression-v1',passed=not regressions and not unavailable,
            observations=len(before),regressions=regressions,unavailable=unavailable,
            self_collision_free_certified=False,quality_approved=False,release_approved=False,
            scope='All declared samples and original triangle identities. No new proper crossings or increased measured crossing intervals; ambiguous/degenerate comparisons fail. Not depth, valid-solid, continuous-motion or animation-quality certification.')
    except (KeyError,TypeError) as exc:
        raise ValueError('Complete structured self-surface reports required') from exc
