"""Bounded ASF/AMC skeletal reference intake; no retargeting or motion cleanup.

Supported: ASF 1.10, degree angles, a zero-orientation TX/TY/TZ/RX/RY/RZ
root, rotation-only bone DOFs, and fully specified contiguous AMC frames.
Column-vector FK follows the Acclaim row-vector convention after transposition.
Physical length conversion and sample rate must be explicitly selected.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import numpy as np
from scipy.spatial.transform import Rotation
from strep import save,sha256

MAX_ASF_BYTES=262144
MAX_AMC_BYTES=8*1024**2
MAX_BONES=128
MAX_FRAMES=20000
NAME=re.compile(r'[A-Za-z][A-Za-z0-9_]{0,63}')


def numbers(tokens,count):
    if len(tokens)!=count:raise ValueError('Unexpected numeric channel count')
    try: values=np.array([float(t) for t in tokens],dtype=float)
    except (TypeError,ValueError) as exc:raise ValueError('Finite numeric channels required') from exc
    if not np.isfinite(values).all() or np.any(abs(values)>1e6):raise ValueError('Bounded finite numeric channels required')
    return values


def lines(text,budget):
    if not isinstance(text,str) or len(text.encode('utf-8'))>budget or '\x00' in text:
        raise ValueError('Bounded text reference required')
    return [line.strip() for raw in text.splitlines() if (line:=raw.split('#',1)[0]).strip()]


def parse_asf(text,*,length_convention=None,metres_per_unit=None):
    sections={};active=None
    for line in lines(text,MAX_ASF_BYTES):
        if line.startswith(':'):
            tag,*rest=line[1:].split(maxsplit=1)
            if tag not in ('version','name','units','documentation','root','bonedata','hierarchy') or tag in sections:
                raise ValueError('Unknown or repeated ASF section')
            active=tag;sections[tag]=[rest[0]] if rest else []
        elif active is None:raise ValueError('ASF content before its first section')
        else:sections[active].append(line)
    if sections.get('version')!=['1.10'] or not all(k in sections for k in ('units','root','bonedata','hierarchy')):
        raise ValueError('Complete supported ASF 1.10 required')
    def fields(rows,allowed):
        result={}
        for line in rows:
            key,*value=line.split()
            if key not in allowed or key in result:raise ValueError('Unknown or repeated ASF field')
            result[key]=value
        return result
    units=fields(sections['units'],('mass','length','angle'))
    if units.get('angle')!=['deg'] or 'length' not in units:raise ValueError('Explicit degree angles and length factor required')
    factor=float(numbers(units['length'],1)[0])
    if factor<=0:raise ValueError('Positive ASF length factor required')
    if (length_convention is None)==(metres_per_unit is None):raise ValueError('Choose exactly one explicit physical length conversion')
    if length_convention is not None:
        if length_convention!='cmu-inches':raise ValueError('Unknown physical length convention')
        scale=.0254/factor
    else:
        if type(metres_per_unit) not in (int,float) or not np.isfinite(metres_per_unit) or not 1e-9<=metres_per_unit<=1000:
            raise ValueError('Positive bounded metres-per-unit required')
        scale=float(metres_per_unit)
    root=fields(sections['root'],('order','axis','position','orientation'))
    if root.get('order')!=['TX','TY','TZ','RX','RY','RZ'] or root.get('axis')!=['XYZ']:
        raise ValueError('Supported explicit root channel/axis order required')
    root_position=numbers(root.get('position',[]),3)*scale
    if np.any(numbers(root.get('orientation',[]),3)!=0):raise ValueError('Nonzero ASF root reference orientation unsupported')
    blocks=[];block=None
    for line in sections['bonedata']:
        if line=='begin':
            if block is not None:raise ValueError('Nested ASF bone block')
            block=[]
        elif line=='end':
            if block is None:raise ValueError('Unmatched ASF bone end')
            blocks.append(block);block=None
        elif block is None:raise ValueError('ASF bone fields outside a block')
        else:block.append(line)
    if block is not None or not 1<=len(blocks)<=MAX_BONES:raise ValueError('Complete bounded ASF bone blocks required')
    bones={};ids=set()
    for block in blocks:
        simple=[];limits=[];have_limits=False
        for line in block:
            if line.startswith('limits '):
                if have_limits:raise ValueError('Repeated ASF limits')
                have_limits=True;limits.append(line.removeprefix('limits '))
            elif line.startswith('('):
                if not have_limits:raise ValueError('Unbound ASF limits continuation')
                limits.append(line)
            else:simple.append(line)
        row=fields(simple,('id','name','direction','length','axis','dof'))
        if set(row)-{'dof'}!={'id','name','direction','length','axis'}:raise ValueError('Complete ASF bone fields required')
        if len(row['id'])!=1 or not re.fullmatch(r'[1-9][0-9]*',row['id'][0]):raise ValueError('Positive integer bone ID required')
        id=int(row['id'][0]);name=row['name'][0] if len(row['name'])==1 else ''
        if id in ids or not NAME.fullmatch(name) or name=='root' or name in bones:raise ValueError('Distinct valid ASF bone IDs/names required')
        ids.add(id);direction=numbers(row['direction'],3);length=float(numbers(row['length'],1)[0])
        norm=float(np.linalg.norm(direction))
        if length<0 or not (abs(norm-1)<=1e-3 or length==0 and norm==0):raise ValueError('Nonnegative length and valid direction required')
        axis=row['axis']
        if len(axis)!=4 or sorted(axis[3])!=['X','Y','Z']:raise ValueError('Explicit ASF axis rotation order required')
        angles=numbers(axis[:3],3);dof=row.get('dof',[])
        if len(dof)>3 or len(set(dof))!=len(dof) or any(v not in ('rx','ry','rz') for v in dof):
            raise ValueError('Only distinct rotation bone DOFs are supported')
        bounds=None
        if have_limits:
            if not dof:raise ValueError('Nominal limits require bone DOFs')
            joined=' '.join(limits);pairs=re.findall(r'\(([^()]*)\)',joined)
            if re.sub(r'\([^()]*\)','',joined).strip() or len(pairs)!=len(dof):raise ValueError('One nominal limit per bone DOF required')
            bounds=np.array([numbers(pair.split(),2) for pair in pairs])
            if any(lo>hi for lo,hi in bounds):raise ValueError('Ordered nominal limits required')
        bones[name]=dict(id=id,direction=direction,length_m=length*scale,
                         axis_angles_degrees=angles,axis_order=axis[3],dof=dof,nominal_limits_degrees=bounds)
    hierarchy=sections['hierarchy']
    if not hierarchy or hierarchy[0]!='begin' or hierarchy[-1]!='end':raise ValueError('Complete ASF hierarchy required')
    parents={};known={'root',*bones}
    for line in hierarchy[1:-1]:
        parent,*children=line.split()
        if parent not in known or not children:raise ValueError('Valid hierarchy parent/children required')
        for child in children:
            if child not in bones or child in parents or child==parent:raise ValueError('Distinct existing hierarchy child required')
            parents[child]=parent
    if set(parents)!=set(bones):raise ValueError('Every ASF bone must have one parent')
    for name in bones:
        visited=set();node=name
        while node!='root':
            if node in visited:raise ValueError('Cyclic ASF hierarchy')
            visited.add(node);node=parents[node]
    return dict(names=['root',*bones],bones=bones,parents=parents,root_position_m=root_position,
                metres_per_unit=scale,length_convention=length_convention or 'explicit-metres-per-unit',
                declared_units=units,angles='degrees',column_vector_convention='C @ motion_rotation @ inverse(C); parent endpoint offset before bone rotation')


def parse_amc(text,skeleton):
    records=[];current=None;headers=set()
    required={'root',*(name for name,b in skeleton['bones'].items() if b['dof'])}
    for line in lines(text,MAX_AMC_BYTES):
        if line.startswith(':'):
            if records or current is not None or line not in (':FULLY-SPECIFIED',':DEGREES') or line in headers:
                raise ValueError('Supported AMC headers before all frames required')
            headers.add(line);continue
        if re.fullmatch(r'[0-9]+',line):
            if headers!={':FULLY-SPECIFIED',':DEGREES'}:raise ValueError('Fully specified degree AMC required')
            if current is not None:
                if not required<=set(current):raise ValueError('AMC frame omits required channels')
                records.append(current)
            if int(line)!=len(records)+1 or len(records)>=MAX_FRAMES:raise ValueError('Bounded contiguous AMC frame IDs starting at one required')
            current={};continue
        if current is None:raise ValueError('AMC channels before a frame')
        name,*values=line.split()
        if name not in skeleton['names'] or name in current:raise ValueError('Unknown or duplicate AMC bone')
        count=6 if name=='root' else len(skeleton['bones'][name]['dof'])
        current[name]=numbers(values,count)
    if current is not None:
        if not required<=set(current):raise ValueError('AMC frame omits required channels')
        records.append(current)
    if not 2<=len(records)<=MAX_FRAMES:raise ValueError('At least two complete bounded AMC frames required')
    return records


def forward_kinematics(skeleton,records):
    names=skeleton['names'];bones=skeleton['bones'];frames=len(records);lookup={n:i for i,n in enumerate(names)}
    positions=np.empty((frames,len(names),3));rotations=np.empty((frames,len(names),3,3));endpoints=np.empty_like(positions)
    local={};offsets={};nominal_violations={}
    root=np.array([r['root'] for r in records]);local['root']=Rotation.from_euler('xyz',root[:,3:],degrees=True).as_matrix()
    positions[:,0]=root[:,:3]*skeleton['metres_per_unit']+skeleton['root_position_m'];rotations[:,0]=local['root'];endpoints[:,0]=positions[:,0]
    for name,b in bones.items():
        values=np.array([r.get(name,np.zeros(len(b['dof']))) for r in records])
        c=Rotation.from_euler(b['axis_order'].lower(),b['axis_angles_degrees'],degrees=True).as_matrix()
        motion=Rotation.from_euler(''.join(v[1] for v in b['dof']),values,degrees=True).as_matrix() if b['dof'] else np.repeat(np.eye(3)[None],frames,axis=0)
        local[name]=c@motion@c.T;offsets[name]=b['direction']*b['length_m']
        limits=b['nominal_limits_degrees']
        nominal_violations[name]=None if limits is None else int(np.sum((values<limits[:,0])|(values>limits[:,1])))
    complete={'root'}
    def visit(name):
        if name in complete:return
        parent=skeleton['parents'][name];visit(parent);i=lookup[name];p=lookup[parent]
        positions[:,i]=endpoints[:,p];rotations[:,i]=rotations[:,p]@local[name]
        endpoints[:,i]=positions[:,i]+(rotations[:,i]@offsets[name][:,None])[:,:,0];complete.add(name)
    for name in bones:visit(name)
    if not np.isfinite(positions).all() or not np.isfinite(rotations).all():raise ValueError('Nonfinite skeletal reconstruction')
    return dict(joint_names=np.array(names),positions_m=positions,rotations=rotations,endpoints_m=endpoints,
                nominal_limit_violations=nominal_violations)


def read_motion(asf,amc,*,fps,length_convention=None,metres_per_unit=None):
    if type(fps) not in (int,float) or not np.isfinite(fps) or not 1<=fps<=1000:raise ValueError('Explicit finite 1-1000 Hz capture rate required')
    paths=[Path(asf),Path(amc)];snapshots=[]
    for path,budget in zip(paths,(MAX_ASF_BYTES,MAX_AMC_BYTES)):
        with path.open('rb') as stream:data=stream.read(budget+1)
        if len(data)>budget:raise ValueError('Reference file exceeds its declared capacity')
        try:text=data.decode('ascii')
        except UnicodeError as exc:raise ValueError('ASCII Acclaim references required') from exc
        snapshots.append((text,hashlib.sha256(data).hexdigest()))
    skeleton=parse_asf(snapshots[0][0],length_convention=length_convention,metres_per_unit=metres_per_unit)
    records=parse_amc(snapshots[1][0],skeleton);motion=forward_kinematics(skeleton,records)
    motion.update(times_s=np.arange(len(records),dtype=float)/fps,source_frame_ids=np.arange(1,len(records)+1),fps=float(fps))
    # Retain each numeric source channel, including angles outside nominal
    # limits. Padding is distinguished by channel counts and presence flags.
    names=skeleton['names'];values=np.zeros((len(records),len(names),6))
    counts=np.array([6 if n=='root' else len(skeleton['bones'][n]['dof']) for n in names])
    present=np.zeros((len(records),len(names)),dtype=bool)
    labels=np.full((len(names),6),'',dtype='<U2')
    for j,name in enumerate(names):
        labels[j,:counts[j]]=['tx','ty','tz','rx','ry','rz'] if name=='root' else skeleton['bones'][name]['dof']
        for i,record in enumerate(records):
            if name in record:values[i,j,:counts[j]]=record[name];present[i,j]=True
    motion.update(source_channel_values=values,source_channel_counts=counts,
                  source_channel_names=labels,source_channel_present=present)
    inputs={str(p.resolve()):s[1] for p,s in zip(paths,snapshots)}
    if any(sha256(p)!=h for p,h in inputs.items()):raise ValueError('Reference input changed during intake')
    return skeleton,motion,inputs


def export(asf,amc,output,*,fps,length_convention=None,metres_per_unit=None):
    output=Path(output)
    if output.exists():raise ValueError('Fresh reference output folder required')
    skeleton,motion,inputs=read_motion(asf,amc,fps=fps,length_convention=length_convention,metres_per_unit=metres_per_unit)
    output.mkdir(parents=True)
    np.savez_compressed(output/'skeleton-motion.npz',**{k:v for k,v in motion.items() if isinstance(v,np.ndarray)})
    report=dict(schema='strep-acclaim-reference-intake-v1',status='complete',frames=len(motion['times_s']),joints=len(motion['joint_names']),
        fps=motion['fps'],duration_s=float(motion['times_s'][-1]),metres_per_unit=skeleton['metres_per_unit'],
        length_convention=skeleton['length_convention'],declared_units=skeleton['declared_units'],
        source_bindings_sha256=inputs,implementation_sha256=sha256(__file__),output_sha256=sha256(output/'skeleton-motion.npz'),
        nominal_limit_violations=motion['nominal_limit_violations'],raw_source_files_changed=False,
        original_numeric_channels_preserved=True,nominal_limits_clamped=False,downsampled=False,filtered=False,retargeted=False,
        training_admitted=False,quality_approved=False,release_approved=False,
        scope='Complete skeletal reference FK and clock, with explicit units/rate. No skin/body surfaces, measured contacts, finger capture validity, rig transfer, correction, force/dynamics, semantics, engine or human approval.')
    save(output/'report.json',report);return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--asf',type=Path,required=True);p.add_argument('--amc',type=Path,required=True)
    p.add_argument('--fps',type=float,required=True);p.add_argument('--output',type=Path,required=True)
    units=p.add_mutually_exclusive_group(required=True);units.add_argument('--length-convention',choices=['cmu-inches']);units.add_argument('--metres-per-unit',type=float)
    a=p.parse_args();r=export(a.asf,a.amc,a.output,fps=a.fps,length_convention=a.length_convention,metres_per_unit=a.metres_per_unit)
    print(json.dumps({k:r[k] for k in ('status','frames','joints','duration_s','metres_per_unit')}))
