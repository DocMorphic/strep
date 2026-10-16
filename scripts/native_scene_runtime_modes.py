"""Audit a full native scene while saving each root mode separately.

The engine releases each mode's observations after writing its hash-bound file.
The original runtime comparator still checks all modes, clocks and vertices.
Python retains the embedded reference and loads subsequent modes on demand;
this is a smaller working set, not a fixed memory guarantee or downsampling.
"""
import argparse
from collections.abc import Mapping
from pathlib import Path
import shutil, subprocess, zipfile
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256, now, offline_environment
import native_scene_runtime as original

AUDIT='godot_native_scene_runtime_mode_audit.gd'
GDS=tuple(n for n in original.GDS if n!='godot_native_scene_runtime_audit.gd')+(AUDIT,)
METHODS=tuple(dict.fromkeys(original.METHODS+('native_scene_runtime_modes.py',AUDIT)))
MODES=('embedded','extracted','mixed')
SCHEMA='strep-native-scene-runtime-mode-files-v1'
require=original.require


class ModeFiles(Mapping):
    """Only the embedded baseline is cached. No mode or sample is omitted."""
    def __init__(self, folder, header):
        self.folder=Path(folder).resolve();self.baseline=None
        require(isinstance(header,dict) and set(header)=={'schema','engine','modes','bootstrap'}
            and header['schema']==SCHEMA,'Complete mode-file header required')
        require(isinstance(header['modes'],dict) and set(header['modes'])==set(MODES),'All three root modes required')
        self.entries={}
        for name in MODES:
            entry=header['modes'][name]
            require(isinstance(entry,dict) and set(entry)=={'path','sha256'}
                and entry['path']==f'engine-mode-{name}.json','Fixed relative mode file required')
            digest=entry['sha256']
            require(type(digest) is str and len(digest)==64 and all(c in '0123456789abcdef' for c in digest),'Exact mode hash required')
            path=(self.folder/entry['path']).resolve()
            require(path.parent==self.folder and path.is_file(),'Mode file must stay inside its audit folder')
            self.entries[name]=(path,digest)
        require(sum(p.stat().st_size for p,_ in self.entries.values())<=1024**3,'Complete mode observations exceed 1 GiB; no partial reads')
        self.verify()

    def verify(self):
        for path,digest in self.entries.values():require(sha256(path)==digest,'Raw mode observations changed')

    def __iter__(self):return iter(MODES)
    def __len__(self):return len(MODES)
    def __getitem__(self,name):
        if name not in self.entries:raise KeyError(name)
        if name=='embedded' and self.baseline is not None:return self.baseline
        path,digest=self.entries[name]
        require(sha256(path)==digest,'Raw mode observations changed')
        value=read(path)
        require(sha256(path)==digest,'Raw mode observations changed during read')
        if name=='embedded':self.baseline=value
        return value


def run(source,output,modes,*,engine=None):
    source=Path(source).resolve();output=Path(output).resolve()
    require(not output.exists(),'Fresh native scene runtime output required')
    engine=Path(engine or ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe').resolve()
    with worker_lock(),threadpool_limits(limits=1):
        bindings={str(p):sha256(p) for p in (source,engine)}
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        with zipfile.ZipFile(source) as archive:manifest=original.package_members(archive)
        output.mkdir();save(output/'pipeline.json',dict(status='processing',stage='source-snapshot',quality_approved=False))
        try:
            project=output/'project';project.mkdir();implementation=output/'implementation';implementation.mkdir()
            for n in METHODS:shutil.copyfile(ROOT/'scripts'/n,implementation/n)
            shutil.copyfile(source,output/'source-game-assets.zip')
            with zipfile.ZipFile(output/'source-game-assets.zip') as archive:
                require(original.package_members(archive)==manifest,'Game snapshot changed')
                for name in archive.namelist():
                    dest=project/name;dest.parent.mkdir(parents=True,exist_ok=True)
                    with archive.open(name) as src,dest.open('xb') as dst:shutil.copyfileobj(src,dst)
            config,scene,times,events=original.configure(project,manifest,modes)
            runtime=project/'runtime-v1';runtime.mkdir()
            for n in GDS:shutil.copyfile(implementation/n,runtime/n)
            save(runtime/'scene-runtime.json',config)
            (runtime/'scene.tscn').write_text('[gd_scene load_steps=2 format=3]\n[ext_resource type="Script" path="res://runtime-v1/godot_native_scene_boot.gd" id="1"]\n[node name="Strep" type="Node3D"]\nscript = ExtResource("1")\n',encoding='utf8')
            (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep native scene runtime"\nrun/main_scene="res://runtime-v1/scene.tscn"\n',encoding='utf8')
            save(output/'request.json',dict(asset_folder=str(project),config=config,source_game_zip_sha256=bindings[str(source)]))
            save(output/'pipeline.json',dict(status='processing',stage='engine-root-modes',quality_approved=False))
            with (output/'engine.log').open('w',encoding='utf8') as log:
                process=subprocess.run([str(engine),'--headless','--path',str(project),'--script','res://runtime-v1/'+AUDIT,'--',str(output/'request.json'),str(output/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,timeout=300,env=offline_environment(),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            require(process.returncode==0 and (output/'engine-output.json').is_file(),'Actual scene mode audit failed; preserved engine.log')
            header=read(output/'engine-output.json');raw=ModeFiles(output,header)
            raw_hashes={'engine-output.json':sha256(output/'engine-output.json'),**{p.name:h for p,h in raw.entries.values()}}
            asset=original.ObjectAsset(project/'objects.glb') if scene.objects else None
            if asset is not None:require(set(asset.objects)==set(scene.objects) and all(np.isin(c['times_s'],times).all() for c in asset.channels),'Complete original object clock required')
            save(output/'pipeline.json',dict(status='processing',stage='unchanged-runtime-comparator',quality_approved=False))
            result,arrays=original.compare(scene,times,events,dict(engine=header['engine'],modes=raw,bootstrap=header['bootstrap']),object_asset=asset)
            np.savez_compressed(output/'observations.npz',**arrays)
            with np.load(output/'observations.npz',allow_pickle=False) as stored:
                require(set(stored.files)==set(arrays) and all(stored[k].dtype==v.dtype and stored[k].shape==v.shape and stored[k].tobytes()==v.tobytes() for k,v in arrays.items()),'Complete runtime arrays changed')
            raw.verify()
            require(all(sha256(output/n)==h for n,h in raw_hashes.items()),'Raw mode receipt changed')
            for name,digest in manifest['files_sha256'].items():require(sha256(project/name)==digest,'Original game asset changed during runtime')
            for n,h in methods.items():require(sha256(ROOT/'scripts'/n)==sha256(implementation/n)==h,'Runtime method changed during study')
            for n in GDS:require(sha256(runtime/n)==methods[n],'Executed runtime helper changed')
            require(all(sha256(p)==h for p,h in bindings.items()) and sha256(output/'source-game-assets.zip')==bindings[str(source)],'Original source/engine/snapshot changed')
            original.make_package(output/'source-game-assets.zip',output,result,config)
            result.update(schema='strep-native-scene-runtime-mode-audit-v1',status='complete',at=now(),engine=header['engine'],
                input_sha256=bindings,implementation_sha256=methods,executed_script_sha256={n:sha256(runtime/n) for n in GDS},
                raw_mode_files_sha256=raw_hashes,files_sha256={n:sha256(output/n) for n in ('source-game-assets.zip','request.json','engine.log','observations.npz','runtime-assets.zip','package.json')},
                original_comparator_unchanged=True,complete_clock_retained=True,source_bytes_unchanged=True,arrays_roundtrip_exact=True,
                original_selected=True,real_time_playback_verified=False,quality_approved=False,physics_verified=False,training_admitted=False,release_approved=False,
                scope='Actual complete finite Godot scene/root modes, imported CPU skin and explicit confirmed event callbacks. One raw file per complete mode; original comparator. Smaller working set, not a fixed RAM guarantee. No physics, continuous geometry, GPU rendering, frame-rate or human-quality approval.')
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',quality_approved=False));return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),quality_approved=False,release_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('package');parser.add_argument('output');parser.add_argument('--modes',required=True);parser.add_argument('--engine');args=parser.parse_args()
    print(run(args.package,args.output,read(args.modes),engine=args.engine))
