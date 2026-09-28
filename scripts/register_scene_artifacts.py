"""Register completed diagnostic/download sidecars without changing scene data."""
import argparse
from pathlib import Path
from strep import read,save


def register(report):
    report=Path(report);manifest=read(report/'manifest.json')
    for item in manifest['scenes']:
        variant=Path(item['variants']['palm']);folder=variant.parent
        orientation=folder/'orientation-audit.json'
        if variant.name in ['candidate.json','palm.json'] and (report/orientation).is_file():item['orientation_file']=orientation.as_posix()
        if variant.name in ['candidate.json','palm.json']:
            for field,name in [('partner_file','partner-surface-audit.json'),('rigidity_file','two-hand-rigidity.json')]:
                if (report/folder/name).is_file():item[field]=(folder/name).as_posix()
        if variant.name=='candidate.json':
            scene=read(report/variant)['scene'];downloads=[]
            for actor,entry in scene['actors'].items():
                asset=Path(entry['preview_glb']);pack=asset.parent/'actor-animation.zip'
                if (report/pack).is_file():downloads.append(dict(label=f'Actor {actor} · animation ZIP',path=pack.as_posix()))
            if downloads:item['downloads']=downloads
        if (report/folder/'scene-pack.zip').is_file() and (report/folder/'portable/scene.glb').is_file():
            item['downloads']=[dict(label='Scene pack · ZIP',path=(folder/'scene-pack.zip').as_posix()),dict(label='Scene GLB',path=(folder/'portable/scene.glb').as_posix()),dict(label='Grasp / release events',path=(folder/'events.json').as_posix())]
            if (report/'godot-adapter.zip').is_file():item['downloads'].append(dict(label='Godot adapter · ZIP',path='godot-adapter.zip'))
    save(report/'manifest.json',manifest)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('report',type=Path);args=parser.parse_args();register(args.report)
