"""Create an explicit floor-valid treatment without changing the failed fixture."""
import argparse
import copy
from pathlib import Path
import shutil
from strep import ROOT,read,save,sha256,now
from object_floor_placement import place_above_floor


def prepare(output):
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'reports'):raise ValueError('Local report directory required')
    source=ROOT/'reports/scene-release-jobs/sphere-development-v1/authored/palm.json'
    original=read(source)['scene'];scene=copy.deepcopy(original)
    scene['objects']['box'],placement=place_above_floor(scene['objects']['box'],scene['frame_count'],clearance_m=.002,max_shift_m=.1)
    scene['objects']['box']['trajectory_provenance']='Explicit constant vertical placement from earlier sphere fixture; floor-bound recipe retained. Actor and grip-local points unchanged.'
    scene['id']='sphere-floor-development';scene['review_note']='Floor-valid authored prop treatment, not the original failed sphere scene; grip fitting still unapproved.'
    output.mkdir(parents=True,exist_ok=False)
    for entry in scene['actors'].values():
        relative=Path(entry['preview_glb']);destination=(output/relative).resolve()
        if not destination.is_relative_to(output):raise ValueError('Preview path escapes treatment')
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source.parent/relative,destination)
    save(output/'palm.json',dict(scene=scene));save(output/'placement.json',placement)
    save(output/'protocol.json',dict(at=now(),source_sha256=sha256(source),scene_sha256=sha256(output/'palm.json'),placement_sha256=sha256(output/'placement.json'),
        changed_factor='Constant prop Y translation only; both later fits use exactly this same scene and original actor motion. V8 and V9 are a paired development comparison.',
        variants=[dict(solver=8,finger_edits=False),dict(solver=9,finger_edits=True)],
        original_actor_entries_preserved=scene['actors']==original['actors'],contacts_preserved=scene['contacts']==original['contacts'],
        scope='Same one development action/actor; no new independent action coverage, training or held-out claim.',quality_approved=False,
        implementation={n:sha256(ROOT/'scripts'/n) for n in ['prepare_sphere_floor_trial.py','object_floor_placement.py','support_contact_v8.py','support_contact_v9.py','study_sphere_contact_fit.py']}))
    print(dict(output=str(output),vertical_shift_m=placement['vertical_shift_m'],continuous_floor_lower_bound_m=placement['after']['lower_bound_m']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);prepare(parser.parse_args().output)
