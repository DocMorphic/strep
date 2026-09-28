"""Verify reversible transition contract in a real Studio-generated package."""
import argparse
import hashlib
from pathlib import Path
from urllib.request import urlopen
import zipfile
from strep import ROOT,read,save,sha256,now
from study_reverse_export import run as export_cycle


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    save(output/'pipeline.json',dict(at=now(),status='exporting',quality_approved=False))
    try:
        export_cycle(output/'cycle')
        proof=read(output/'cycle/verification.json');folder=ROOT/'reports/rig-jobs'/proof['job']
        result=read(folder/'result.json');meta=read(folder/'transfer/runtime-cycle.json')['playback']['crossfade']
        assert meta['direction']=='forward_and_latest_transition_reverse'
        assert meta['reverse_history']=='latest_transition_only' and meta['reverse_default']=='silent'
        assert meta['frame_methods']==['advance_frames','rewind_frames']
        assert meta['reverse_notifications_undo_gameplay'] is False
        checked={}
        with zipfile.ZipFile(folder/'character-animation.zip') as archive:
            for name,source in [('transfer/godot_cycle_blend.gd',ROOT/'scripts/godot_cycle_blend.gd'),('transfer/GODOT-BLENDS.md',ROOT/'integrations/godot/BLENDS.md'),('source/implementation/godot_cycle_blend.gd',ROOT/'scripts/godot_cycle_blend.gd'),('source/implementation/rig_runtime_cycle.py',ROOT/'scripts/rig_runtime_cycle.py')]:
                assert archive.read(name)==source.read_bytes(),name
                checked[name]=sha256(source)
        downloads={}
        for key,name in [('runtime_blend_adapter','godot_cycle_blend.gd'),('runtime_blend_readme','GODOT-BLENDS.md')]:
            body=urlopen('http://127.0.0.1:8768'+result[key],timeout=30).read();digest=hashlib.sha256(body).hexdigest()
            assert digest==sha256(folder/'transfer'/name)
            downloads[key]=dict(url=result[key],sha256=digest,bytes=len(body))
        save(output/'verification.json',dict(at=now(),job=proof['job'],cycle_verification_sha256=sha256(output/'cycle/verification.json'),crossfade_contract=meta,archive_sources=checked,downloads=downloads,quality_approved=False))
        save(output/'pipeline.json',dict(at=now(),status='complete',quality_approved=False))
    except BaseException as exc:
        save(output/'pipeline.json',dict(at=now(),status='failed',error=str(exc),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();run(a.output)
