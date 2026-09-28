"""Snapshot recorded development prompts/seeds before reserving release trials."""
import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import defaultdict
from pathlib import Path
from strep import ROOT, now, save, sha256

PROMPT_KEYS={'prompt','text_prompt','edit_prompt','source_prompt','compiled_prompt','instruction'}


def normalize(text):
    return ' '.join(re.findall(r'\w+',unicodedata.normalize('NFKC',text).casefold()))


def extract(data,pointer=''):
    prompts=[];seeds=[]
    if isinstance(data,dict):
        for key,value in data.items():
            location=pointer+'/'+str(key).replace('~','~0').replace('/','~1')
            if key in PROMPT_KEYS and isinstance(value,str) and normalize(value):
                prompts.append(dict(text=value,normalized=normalize(value),pointer=location,field=key))
            if key in {'seed','seeds'}:
                for index,seed in enumerate(value if isinstance(value,list) else [value]):
                    if type(seed) is int:
                        seeds.append(dict(seed=seed,pointer=location+(f'/{index}' if isinstance(value,list) else '')))
            p,s=extract(value,location);prompts.extend(p);seeds.extend(s)
    elif isinstance(data,list):
        for index,value in enumerate(data):
            p,s=extract(value,pointer+f'/{index}');prompts.extend(p);seeds.extend(s)
    return prompts,seeds


def reserved_catalog_exclusion(path,root=ROOT):
    path=path.resolve();root=root.resolve()
    if not path.is_relative_to(root/'benchmarks'):
        raise ValueError('Only an explicit benchmark reservation catalog may be exempted')
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    if (data.get('status')!='reserved_prompts_not_release_ready' or not data.get('cases')
        or any(c.get('generated') is not False for c in data['cases'])):
        raise ValueError('Exemption requires an unexecuted reservation catalog')
    return {path.relative_to(root).as_posix():sha256(path)}


def run(output,reservation=None):
    if output.exists():raise ValueError('Preserve earlier inventory snapshots')
    commands=[['rg','--files','reports','-g','*request*.json','-g','protocol.json'],
              ['rg','--files','benchmarks','-g','*.json']]
    paths=set()
    for command in commands:
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,check=True)
        paths.update(result.stdout.splitlines())
    excluded=reserved_catalog_exclusion(reservation) if reservation else {}
    files={};errors=[];prompts=defaultdict(list);seeds=defaultdict(list)
    for relative in sorted(paths):
        if Path(relative).as_posix() in excluded:continue
        path=ROOT/relative
        try:
            raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
            files[Path(relative).as_posix()]=digest
            parsed=json.loads(raw.decode('utf-8-sig'))
            found,used=extract(parsed)
            for item in found:prompts[item['normalized']].append(dict(file=Path(relative).as_posix(),**item))
            for item in used:seeds[item['seed']].append(dict(file=Path(relative).as_posix(),**item))
        except (OSError,UnicodeError,json.JSONDecodeError) as exc:
            errors.append(dict(file=Path(relative).as_posix(),error=str(exc)))
    output.mkdir(parents=True)
    save(output/'inventory.json',dict(at=now(),files=files,excluded_unexecuted_reservation_catalogs=excluded,parse_errors=errors,
        prompts=[dict(normalized=key,occurrences=rows) for key,rows in sorted(prompts.items())],
        seeds=[dict(seed=key,occurrences=rows) for key,rows in sorted(seeds.items())]))
    save(output/'summary.json',dict(at=now(),inventory_sha256=sha256(output/'inventory.json'),
        implementation_sha256=sha256(Path(__file__)),commands=commands,files=len(files),
        unique_normalized_prompts=len(prompts),unique_integer_seeds=len(seeds),parse_errors=len(errors),
        ready_for_exact_overlap_screen=not errors,held_out_fixtures_frozen=False,quality_approved=False,
        scope='Snapshot of recorded prompt-like fields in report request/protocol JSON and benchmark JSON. Seeds conservatively include any seed field, including non-model uses. This does not prove semantic novelty, absence of unrecorded development use, or checkpoint training-set independence. Refresh before release trials.'))
    print(dict(files=len(files),prompts=len(prompts),seeds=len(seeds),parse_errors=len(errors)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    parser.add_argument('--reservation',type=Path);a=parser.parse_args()
    run(a.output.resolve(),a.reservation)
