"""Portable exact checker for contradictory generated surface halfspaces.

This verifies arithmetic on represented constants, not mesh collision or the
feasibility of a different motion. No optimizer, model or asset loader runs.
"""
import hashlib
import json
import math
from fractions import Fraction

SCHEMA='strep-native-halfspace-contradiction-v1'


def _number(value,low,high):
    return type(value) in (int,float) and low<=value<=high and math.isfinite(value)


def _regions(regions):
    if not isinstance(regions,list) or not 1<=len(regions)<=16384:
        raise ValueError('One to 16384 complete region records required')
    total=0
    for region in regions:
        if not isinstance(region,dict) or set(region)!={'vertices','normal_world','offset_m','sign','minimum_gap_m'}:
            raise ValueError('Complete explicit region fields required')
        vertices=region['vertices'];normal=region['normal_world'];total+=len(vertices) if isinstance(vertices,list) else 100001
        if (not isinstance(vertices,list) or not vertices or total>100000
                or any(type(v) is not int or not 0<=v<=10**9 for v in vertices)
                or len(set(vertices))!=len(vertices)
                or not isinstance(normal,list) or len(normal)!=3
                or any(not _number(x,-2,2) for x in normal)
                or abs(math.sqrt(math.fsum(x*x for x in normal))-1)>1e-8
                or type(region['sign']) is not int or region['sign'] not in (-1,1)
                or not _number(region['offset_m'],-1e6,1e6) or not _number(region['minimum_gap_m'],0,.1)):
            raise ValueError('Bounded vertices, unit normal, sign and finite physical distances required')


def region_digest(regions):
    _regions(regions)
    raw=json.dumps(regions,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _rational(value):
    if type(value) is not str or not 1<=len(value)<=4096:
        raise ValueError('Bounded canonical rational weight required')
    try:result=Fraction(value)
    except (ValueError,ZeroDivisionError) as exc:raise ValueError('Finite canonical rational weight required') from exc
    if str(result)!=value:raise ValueError('Canonical rational weight required')
    return result


def verify(regions,certificate):
    digest=region_digest(regions)
    if (not isinstance(certificate,dict) or set(certificate)!={'schema','regions_sha256','vertex','support'}
            or certificate['schema']!=SCHEMA or certificate['regions_sha256']!=digest
            or type(certificate['vertex']) is not int or not 0<=certificate['vertex']<=10**9
            or not isinstance(certificate['support'],list) or not 1<=len(certificate['support'])<=4):
        raise ValueError('Bounded certificate bound to the complete region request required')
    normal=[Fraction(0)]*3;bound=Fraction(0);weight_sum=Fraction(0);seen=set()
    for entry in certificate['support']:
        if (not isinstance(entry,dict) or set(entry)!={'region_index','weight_rational'}
                or type(entry['region_index']) is not int or not 0<=entry['region_index']<len(regions)
                or entry['region_index'] in seen):
            raise ValueError('One to four distinct existing region indices required')
        seen.add(entry['region_index']);region=regions[entry['region_index']]
        if certificate['vertex'] not in region['vertices']:raise ValueError('Every supported region must contain the same declared vertex')
        weight=_rational(entry['weight_rational'])
        if weight<0:raise ValueError('Nonnegative contradiction weights required')
        sign=region['sign'];axis=[-sign*Fraction(float(x)) for x in region['normal_world']]
        limit=-sign*Fraction(float(region['offset_m']))-Fraction(float(region['minimum_gap_m']))
        normal=[x+weight*y for x,y in zip(normal,axis)];bound+=weight*limit;weight_sum+=weight
    if weight_sum!=1 or any(normal) or bound>=0:
        raise ValueError('Exact unit weight sum, zero combined normal and strictly negative bound required')
    return dict(schema=SCHEMA,status='verified',regions_sha256=digest,vertex=certificate['vertex'],
        supported_regions=len(seen),sum_weights_rational=str(weight_sum),weighted_normal_rational=[str(x) for x in normal],
        weighted_bound_rational=str(bound),weighted_bound_approx_m=float(bound),
        contradiction_established=True,quality_approved=False,release_approved=False,
        scope='Exact arithmetic contradiction for one vertex in these represented linear proxy regions. '
              'No claim that true mesh separation, another proxy choice, a rig or a different motion is infeasible. '
              'Caller binds actor/time/assets; no geometry predicates, inference, training or motion approval.')


if __name__=='__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('regions',type=Path);parser.add_argument('certificate',type=Path);args=parser.parse_args()
    print(json.dumps(verify(json.loads(args.regions.read_text(encoding='utf-8')),json.loads(args.certificate.read_text(encoding='utf-8'))),indent=2))
