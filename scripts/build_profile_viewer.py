import argparse
import json
from pathlib import Path
import numpy as np
from strep import ROOT,read


def main(folder):
    folder=Path(folder);summary=read(folder/'summary.json');characters={x['id']:x for x in read(folder/'character-summary.json')}
    quality={x['id']:x for x in read(folder/'character-quality.json')['trials']}
    permutation=np.random.default_rng(240924).permutation(len(summary['trials']))
    for index,trial in enumerate(summary['trials']):
        trial['character']=characters[trial['id']];trial['blind_order']=int(permutation[index])
        trial['character_quality']=quality[trial['id']]
    template=(ROOT/'scripts/profile-viewer.html').read_text(encoding='utf-8')
    (folder/'viewer.html').write_text(template.replace('__PILOT_DATA__',json.dumps(summary).replace('<','\\u003c')),encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);main(p.parse_args().folder)
