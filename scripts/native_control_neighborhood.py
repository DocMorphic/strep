"""Nearby existing translation controls; normal export checks stay authoritative."""
from pathlib import Path
import numpy as np
from native_contact_norms import row_regression
from native_support_feasibility import merit
from strep import save

MULTIPLIERS=(-.125,.125,-.25,.25,-.5,.5,-1.,1.,-2.,2.)


def refine(problem,proposed,origin,current,trust,output):
    """Return the first stored-key-preview admissible control, never approval.

    Each direction changes one permitted translation knot component, or the
    same component of all editable knots on that track. Rotation controls,
    frozen keys, knot/key times and author permissions are unchanged. There is
    one finite pass; no greedy restart or unconstrained per-key adjustment.
    """
    proposed=problem.edits.controls(proposed).copy();origin=problem.edits.controls(origin)
    if type(trust) not in (int,float) or not np.isfinite(trust) or not 0<trust<=.25:
        raise ValueError('Original finite trust fraction at most 0.25 required')
    if any(np.any(x<problem.lower) or np.any(x>problem.upper) for x in (origin,proposed)) or np.any(abs(proposed-origin)>trust):
        raise ValueError('Original control and trust boxes required')
    problem.check_inputs();directions=[]
    for name,actor in problem.edits.actors.items():
        for entry in actor['tracks']:
            if entry['path']!='translation':continue
            magnitude=np.max(abs(entry['source']),axis=0)+entry['maximum']
            represented=magnitude.astype(np.float32)
            if not np.isfinite(represented).all():raise ValueError('Finite translation storage range required')
            spacing=np.spacing(represented).astype(float)
            if not np.isfinite(spacing).all() or np.any(spacing<=0):raise ValueError('Positive finite translation spacing required')
            for axis in range(3):
                for ids in [entry['controls'][:,axis]]+[np.array([i]) for i in entry['controls'][:,axis]]:
                    directions.append(dict(actor=name,node=entry['node'],axis=axis,ids=ids.tolist(),step=float(spacing[axis]/entry['unit'])))
    if len(directions)*len(MULTIPLIERS)>1536:raise ValueError('Complete control neighborhood exceeds budget; no directions dropped')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    save(output/'request.json',dict(directions=directions,multipliers=list(MULTIPLIERS),trust=trust,
        original_controls=origin.tolist(),proposed_controls=proposed.tolist(),original_inputs_sha256=problem.inputs))
    records=[];selected=None;choice=None
    for direction in directions:
        for multiple in MULTIPLIERS:
            candidate=proposed.copy();candidate[direction['ids']]+=direction['step']*multiple
            row=dict(index=len(records),direction=direction,multiple=multiple,evaluated=False,preview_pass=False)
            if (np.any(candidate<problem.lower) or np.any(candidate>problem.upper)
                    or np.any(abs(candidate-origin)>trust)):
                row['rejection']='original_control_or_trust_box'
            else:
                residual=problem.model(candidate)
                np.savez_compressed(output/f"probe-{len(records):04d}.npz",controls=candidate,residual=residual,times_s=problem.times)
                source=bool(np.all(residual[:problem.protected_rows]<=0))
                contacts=bool(np.all(row_regression(current[problem.protected_rows:],residual[problem.protected_rows:])<=0))
                improved=merit(residual)<merit(current)
                row.update(evaluated=True,source_rows_pass=source,contact_rows_no_worse=contacts,merit=list(merit(residual)),preview_pass=bool(source and contacts and improved))
            records.append(row);save(output/'probes.json',records)
            if row['preview_pass']:selected=row['index'];choice=candidate;break
        if choice is not None:break
    problem.check_inputs()
    result=dict(selected_preview_probe=selected,probes=len(records),possible_probes=len(directions)*len(MULTIPLIERS),
        exported=False,quality_approved=False,release_approved=False,
        scope='Finite nearby existing control probes, first stored-key-preview admissible result. Independent export, strict edit, native/contact and full declared geometry checks are still required. No exhaustive feasibility or motion-quality claim.')
    save(output/'result.json',result);return choice,result
