"""Local sampled depth regression, supplementary to complete geometry checks."""
import math


def require(condition,message):
    if not condition:raise ValueError(message)


def finite(value):return type(value) in (int,float) and math.isfinite(value)


def _depths(sample):
    values={}
    def add(key,value,*,unavailable=False):
        require(key not in values,'Duplicate local geometry depth identity')
        require(value is None if unavailable else finite(value) and value>=0,'Finite nonnegative local geometry depth required')
        values[key]=value
    def name(value):
        require(isinstance(value,str) and bool(value),'Named geometry participant required')
        return value
    def participant(value):
        require(isinstance(value,list) and len(value)==2 and value[0] in ('actor','prop'),'Typed geometry participant required')
        return (value[0],name(value[1]))
    def containment(pair,left,right,typed):
        expected={(left,right),(right,left)};seen=set()
        for row in pair['vertex_containment']:
            source=participant(row['source']) if typed else ('actor',name(row['source']))
            target=participant(row['target']) if typed else ('actor',name(row['target']))
            require((source,target) in expected and (source,target) not in seen,'Two distinct original containment directions required')
            seen.add((source,target));require(type(row['available']) is bool,'Explicit containment availability required')
            add(('containment',*source,*target),row['max_depth_m'] if row['available'] else None,unavailable=not row['available'])
        require(seen==expected,'Complete bidirectional containment required')
    base=sample['base_scene']
    for row in base['world_planes']:add(('plane','actor',name(row['actor']),name(row['plane'])),row['maximum_depth_m'])
    for row in sample['mesh_world_planes']:add(('plane','prop',name(row['prop']),name(row['plane'])),row['maximum_depth_m'])
    for row in base['actor_objects']:add(('primitive','actor',name(row['actor']),name(row['object'])),row['maximum_depth_upper_m'])
    for row in sample['mesh_primitive_pairs']:add(('primitive','prop',name(row['prop']),name(row['object'])),row['maximum_depth_upper_m'])
    for row in base['actor_pairs']:
        require(isinstance(row['actors'],list) and len(row['actors'])==2,'Two actor identities required')
        left,right=[('actor',name(n)) for n in row['actors']];require(left!=right,'Distinct actor pair required')
        containment(row,left,right,False)
    for row in sample['mesh_pairs']:
        left,right=participant(row['left']),participant(row['right']);require(left!=right,'Distinct mesh pair required')
        containment(row,left,right,True)
    return values


def _compare_depths(original,candidate):
    """No available per-time/query depth may increase; unknown depths cannot pass.

    No slack or new tolerance is introduced. Query upper bounds, not inferred
    physical penetration distances, are compared for primitive contacts. This
    is not a triangle, self-collision, continuous-time or quality certificate.
    Source/provenance validation remains the caller's responsibility.
    """
    for report in (original,candidate):
        require(report['schema']=='strep-native-mesh-prop-geometry-result-v1' and report['all_policy_samples_evaluated'] is True,
                'Complete mesh geometry report required')
        times=report['complete_clock_s'];require(isinstance(times,list),'Explicit complete geometry clock required');count=len(times)
        require(count>0 and all(finite(t) and t>=0 for t in times) and all(a<b for a,b in zip(times,times[1:])),
                'Finite increasing complete geometry clock required')
        require(report['times_s']==times and all(finite(t) for t in report['times_s'])
                and report['sample_indices']==list(range(count)) and all(type(i) is int for i in report['sample_indices']) and len(report['samples'])==count,
                'Every original geometry sample required')
        for index,row in enumerate(report['samples']):
            require(type(row['index']) is int and row['index']==index and row['time_s']==times[index] and row['base_scene']['time_s']==times[index],
                    'Ordered complete geometry samples required')
    for key in ('complete_clock_s','limits','clock_mode','actor_faces','prop_faces'):
        require(original[key]==candidate[key],'Geometry clock, limits and participant topology counts must remain unchanged')
    require(original.get('containment_method','legacy-signed-distance')==candidate.get('containment_method','legacy-signed-distance'),
            'Containment methods differ; reevaluate both original and candidate under one version')
    regressions=[];unavailable=[];observations=0
    for before,after in zip(original['samples'],candidate['samples']):
        previous,current=_depths(before),_depths(after)
        require(previous.keys()==current.keys(),'Local geometry depth population changed')
        for key,value in previous.items():
            observations+=1;next_value=current[key]
            if value is None or next_value is None:
                unavailable.append(dict(time_s=before['time_s'],query=list(key),original_available=value is not None,candidate_available=next_value is not None))
            elif next_value>value:
                regressions.append(dict(time_s=before['time_s'],query=list(key),original_depth_m=value,candidate_depth_m=next_value,increase_m=next_value-value))
    require(observations>0,'At least one local geometry depth observation required')
    return dict(schema='strep-local-mesh-depth-regression-v1',passed=not regressions and not unavailable,
                observations=observations,regressions=regressions,unavailable=unavailable,
                maximum_increase_m=max((r['increase_m'] for r in regressions),default=0.),
                quality_approved=False,release_approved=False,
                scope='Complete declared sample clock and depth-query identities only. No increase in any available local measured depth; unavailable comparisons fail. Existing geometry checks remain mandatory; no motion-quality or continuous collision approval.')


def compare_depths(original,candidate):
    """Compare complete compatible sampled depth reports, failing closed."""
    try:return _compare_depths(original,candidate)
    except (KeyError,TypeError) as exc:raise ValueError('Complete structured local geometry depth reports required') from exc
