"""Exact coverage of caller-bound discrete partner-depth observations.

This checks a journal, not meshes, source bindings or continuous clearance.
Completing a failing depth screen is still completed observation coverage.
"""
import math


def _name(value):
    return isinstance(value,str) and 0<len(value)<=80 and '\0' not in value


class PartnerCollisionClock:
    def __init__(self,frame_count,variants,actor_vertices,*,representation,tolerance_m):
        if type(frame_count) is not int or not 1<=frame_count<=10000:
            raise ValueError('Complete original integer frame count required')
        if (not isinstance(variants,(tuple,list)) or not 1<=len(variants)<=8
                or any(not _name(v) for v in variants) or len(set(variants))!=len(variants)):
            raise ValueError('Distinct complete variant names required')
        if (not isinstance(actor_vertices,dict) or not 2<=len(actor_vertices)<=8
                or any(not _name(k) or type(v) is not int or not 1<=v<=1000000 for k,v in actor_vertices.items())):
            raise ValueError('Every actor and its complete surface vertex count required')
        if representation not in ('raw','saved') or type(representation) is not str:
            raise ValueError('Explicit raw or saved representation required')
        if type(tolerance_m) not in (int,float) or not math.isfinite(tolerance_m) or not 0<tolerance_m<=1:
            raise ValueError('Explicit original positive depth screen required')
        total=frame_count*len(variants)*len(actor_vertices)*(len(actor_vertices)-1)
        if total>100000:raise ValueError('Complete condition population exceeds journal budget; no truncation')
        self._frames=frame_count;self._variants=tuple(variants);self._actors=dict(actor_vertices)
        self._representation=representation;self._tolerance=float(tolerance_m);self._rows={}
        self._expected={(f,v,a,b) for f in range(frame_count) for v in variants
            for a in actor_vertices for b in actor_vertices if a!=b}

    def add(self,observations):
        """Validate the complete supplied batch before retaining any of it."""
        if not isinstance(observations,list) or not 1<=len(observations)<=4096:
            raise ValueError('Nonempty bounded complete observation batch required')
        pending={}
        for row in observations:
            if not isinstance(row,dict):raise ValueError('Complete observation dictionary required')
            keys=('frame','mode','representation','source','target','vertices_checked',
                'max_depth_m','vertices_over_tolerance','deepest_vertex','passed_existing_depth_screen')
            if any(k not in row for k in keys):raise ValueError('Every original depth observation field required')
            f,v,a,b=(row[k] for k in ('frame','mode','source','target'))
            if (type(f) is not int or not _name(v) or not _name(a) or not _name(b)
                    or (f,v,a,b) not in self._expected or row['representation']!=self._representation):
                raise ValueError('Original complete clock, variants, actors and representation must match')
            key=(f,v,a,b)
            if key in self._rows or key in pending:raise ValueError('Duplicate condition cannot add coverage')
            count=row['vertices_checked'];failed=row['vertices_over_tolerance'];depth=row['max_depth_m'];peak=row['deepest_vertex']
            if (type(count) is not int or count!=self._actors[a] or type(failed) is not int or not 0<=failed<=count
                    or type(depth) not in (int,float) or not math.isfinite(depth) or not 0<=depth<=1e6):
                raise ValueError('Complete actor vertices and finite bounded penetration required')
            passed=depth<=self._tolerance
            if (type(row['passed_existing_depth_screen']) is not bool or row['passed_existing_depth_screen']!=passed
                    or (failed==0)!=passed or (depth==0 and peak is not None)
                    or (depth>0 and (type(peak) is not int or not 0<=peak<count))):
                raise ValueError('Depth, threshold count, peak and strict original decision must agree')
            # Ancillary broadphase data remain in the caller's immutable journal.
            # This owned snapshot retains the complete coverage/depth population.
            pending[key]={k:row[k] for k in keys}
        self._rows.update(pending)

    def report(self):
        missing=self._expected-self._rows.keys();complete=not missing;summaries={}
        for mode in self._variants:
            rows=[r for key,r in self._rows.items() if key[1]==mode]
            complete_frames=[f for f in range(self._frames) if all((f,mode,a,b) in self._rows
                for a in self._actors for b in self._actors if a!=b)]
            peak=min(rows,key=lambda r:(-r['max_depth_m'],r['frame'],r['source'],r['target'])) if rows else None
            summaries[mode]=dict(direction_queries=len(rows),complete_frames=complete_frames,
                maximum_depth_m=None if peak is None else peak['max_depth_m'],
                peak_condition=None if peak is None else {k:peak[k] for k in ('frame','source','target')},
                frames_over_tolerance=sorted({r['frame'] for r in rows if not r['passed_existing_depth_screen']}),
                vertex_exceedances=sum(r['vertices_over_tolerance'] for r in rows))
        all_checked_pass=bool(self._rows) and all(r['passed_existing_depth_screen'] for r in self._rows.values())
        return dict(schema='strep-partner-collision-clock-v1',status='complete' if complete else 'partial',
            frame_count=self._frames,representation=self._representation,original_tolerance_m=self._tolerance,
            expected_conditions=len(self._expected),observed_conditions=len(self._rows),missing_conditions=len(missing),
            first_missing_conditions=[list(k) for k in sorted(missing)[:16]],complete_original_integer_clock=complete,
            all_observed_depth_screens_pass=all_checked_pass,complete_depth_screen_pass=bool(complete and all_checked_pass),
            variants=summaries,added_physical_tolerance_m=0.,quality_approved=False,release_approved=False,adopted=False,
            source_bindings_verified=False,continuous_collision_checked=False,edge_crossings_checked=False,self_collision_checked=False,
            scope='Exact coverage of every declared variant and ordered actor pair at every original integer frame, complete source vertex counts and strict supplied depth screen. Caller-bound discrete observations only; no geometry recomputation, source/resource validation, edge/continuous/self/physical/engine/human or release approval.')
