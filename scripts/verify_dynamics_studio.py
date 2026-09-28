"""Verify completed Studio root-cleanup jobs, packages and actual engine import."""
import argparse
import hashlib
from pathlib import Path
import urllib.request
import zipfile
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from audit_authoring_intent import check_files
from verify_authored_root_correction import inspect, samples
from run_godot_rig_import import run as import_engine
from verify_joint_root_correction import inspect as joint_inspect


def run(jobs, output):
    output.mkdir(parents=True, exist_ok=False)
    rows, cases = [], []
    with threadpool_limits(limits=1):
        for job in jobs:
            folder = ROOT/'reports/rig-jobs'/job
            request, result = read(folder/'request.json'), read(folder/'result.json')
            assert read(folder/'pipeline.json')['status'] == 'complete'
            assert read(folder/'freeze.json')['request_sha256'] == sha256(folder/'request.json')
            check_files(folder, request['files'])
            check_files(folder/'implementation', request['implementation'])
            original = ROOT/'reports/rig-jobs'/request['source_job']/request['input_variant']/'character.glb'
            assert sha256(original) == request['input_glb_sha256'] == sha256(folder/'input/character.glb')
            audit = read(folder/'dynamics-audit.json')
            joint_context=request['inherited_contact'].get('kind')=='joint_edit'
            if audit['status'] == 'improved':
                observed = inspect(folder/'input/character.glb', folder/'transfer/character.glb',
                    folder/'baseline/character.glb', folder/'original-contact-spec.json', result['frames'], request['policy'])
                assert observed['all_checks_passed']
                if joint_context:
                    joint_audit=joint_inspect(folder/'solver',folder/'transfer/character.glb',request['policy'],
                        source=folder/'input/character.glb',original=folder/'baseline/character.glb')
                    assert joint_audit['all_checks_passed']
                    observed['joint']=joint_audit
            else:
                assert audit['status'] == 'input_retained'
                assert sha256(folder/'input/character.glb') == sha256(folder/'transfer/character.glb')
                observed = {'unchanged_input': True}
            if request['inherited_contact']['status'] in ('rejected', 'infeasible', 'unsupported'):
                assert result['correction_status'] == 'rejected'
            assert not result['human_approved']
            if joint_context:
                parent=ROOT/'reports/rig-jobs'/request['source_job']
                for name in ('joint-targets.json','joint-spec.json','joint-edit.json'):
                    assert sha256(folder/name)==sha256(parent/name)
            variants = []
            for variant, record in result['variants'].items():
                path = folder/variant/'character.glb'
                assert sha256(path) == record['sha256']
                _, worlds = samples(path, result['frames'])
                track = read(folder/variant/'root-motion.json')
                expected = worlds[::2, result['root_node']]
                assert np.max(np.abs(np.asarray(track['positions_m'])-expected[:, :3, 3])) < 1e-9
                assert np.max(np.abs(Rotation.from_quat(track['rotations_xyzw']).as_matrix()-expected[:, :3, :3])) < 1e-6
                assert np.array_equal(track['times_s'], np.arange(result['frames'], dtype=np.float32)/30)
                spec = read(folder/variant/'contact-spec.json')
                assert spec.pop('glb_sha256') == record['sha256']
                original_spec = read(folder/'original-contact-spec.json')
                original_spec.pop('glb_sha256')
                assert spec == original_spec
                sidecars = []
                for name in ('contacts.json', 'events.json', 'timeline.json'):
                    source = folder/'input'/name
                    if source.exists():
                        assert sha256(source) == sha256(folder/variant/name)
                        sidecars.append(name)
                with urllib.request.urlopen('http://127.0.0.1:8768'+record['glb']) as response:
                    assert hashlib.sha256(response.read()).hexdigest() == record['sha256']
                variants.append(dict(id=variant, sidecars_preserved=sidecars, exact_root_track=True, http_hash=True))
                cases.append(dict(id=job+'-'+variant, path=str(path), sha256=record['sha256'],
                                  frames=result['frames'], fps=30, sample_by_time=True))
            package = folder/'character-animation.zip'
            assert sha256(package) == result['package_sha256']
            with zipfile.ZipFile(package) as archive:
                names = archive.namelist()
                assert len(names) == len(set(names))
                assert set(request['files']).issubset(names)
                for name in names:
                    assert hashlib.sha256(archive.read(name)).hexdigest() == sha256(folder/name)
                assert any('license' in n.lower() for n in names)
            with urllib.request.urlopen('http://127.0.0.1:8768'+result['package']) as response:
                assert hashlib.sha256(response.read()).hexdigest() == result['package_sha256']
            rows.append(dict(id=job, status=audit['status'], independent=observed, variants=variants,
                             package_members=len(names), frozen_inputs=True, source_unchanged=True,
                             inherited_status=result['correction_status']))
            save(output/(job+'.json'), rows[-1])
            print(job, audit['status'], flush=True)
    save(output/'manifest.json', dict(cases=cases))
    import_engine(output, output/'engine')
    save(output/'completion.json', dict(at=now(), jobs=rows, engine_actor_frames=sum(c['frames'] for c in cases),
        engine_verification_sha256=sha256(output/'engine/verification.json'), implementation_sha256=sha256(__file__),
        human_approved=False, scope='Development integration: independent exported geometry guards, immutable inputs, original targets, root tracks, HTTP packages and all-frame Godot joints. No animator or semantic approval.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('jobs', nargs='+')
    args = parser.parse_args()
    run(args.jobs, args.output.resolve())
