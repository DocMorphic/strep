"""Independent transform examples and bounded, lossless reference admission."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import acclaim_motion as ac

ASF='''# Artificial public test skeleton, not downloaded motion.
:version 1.10
:name example
:units
mass 1
length .45
angle deg
:root
order TX TY TZ RX RY RZ
axis XYZ
position 0 0 0
orientation 0 0 0
:bonedata
begin
id 1
name upper
direction 1 0 0
length 2
axis 0 0 90 XYZ
dof rx
limits (-10 10)
end
begin
id 2
name lower
direction 0 1 0
length 3
axis 0 0 0 XYZ
dof rx ry rz
limits (-180 180)
       (-180 180)
       (-180 180)
end
begin
id 3
name tip
direction 0 0 1
length 1
axis 0 0 0 XYZ
end
:hierarchy
begin
root upper
upper lower
lower tip
end
'''
AMC='''# Artificial channels.
:FULLY-SPECIFIED
:DEGREES
1
root 1 2 3 0 0 0
upper 90
lower 0 0 0
2
root 4 5 6 20 30 40
upper 45
lower 15 25 35
'''


def axis(axis,degrees):
    c=np.cos(np.deg2rad(degrees));s=np.sin(np.deg2rad(degrees))
    return {'x':np.array([[1,0,0],[0,c,-s],[0,s,c]]),
            'y':np.array([[c,0,s],[0,1,0],[-s,0,c]]),
            'z':np.array([[c,-s,0],[s,c,0],[0,0,1]])}[axis]


def skeleton(text=ASF):return ac.parse_asf(text,metres_per_unit=1)


def test_parent_endpoint_and_axis_conjugation_have_independent_answers():
    s=skeleton();m=ac.forward_kinematics(s,ac.parse_amc(AMC,s))
    np.testing.assert_allclose(m['positions_m'][0],[[1,2,3],[1,2,3],[1,2,1],[1,5,1]],atol=1e-14)
    np.testing.assert_allclose(m['endpoints_m'][0,-1],[2,5,1],atol=1e-14)
    np.testing.assert_allclose(m['rotations'][0,1],axis('y',90),atol=1e-14)
    assert m['nominal_limit_violations']['upper']==2  # Not clamped.


def test_noncommuting_root_bone_and_reference_rotations():
    s=skeleton();m=ac.forward_kinematics(s,ac.parse_amc(AMC,s))
    root=axis('z',40)@axis('y',30)@axis('x',20)
    upper=root@axis('z',90)@axis('x',45)@axis('z',-90)
    lower=upper@axis('z',35)@axis('y',25)@axis('x',15)
    np.testing.assert_allclose(m['rotations'][1],[root,upper,lower,lower],atol=1e-14)
    p=np.array([4,5,6])+upper@np.array([2,0,0])
    np.testing.assert_allclose(m['positions_m'][1,2],p,atol=1e-14)
    np.testing.assert_allclose(m['endpoints_m'][1,3],p+lower@np.array([0,3,1]),atol=1e-14)


def test_cmu_conversion_and_explicit_reference_position():
    s=ac.parse_asf(ASF.replace('position 0 0 0','position 1 2 3'),length_convention='cmu-inches')
    assert s['metres_per_unit']==pytest.approx(.0254/.45)
    m=ac.forward_kinematics(s,ac.parse_amc(AMC,s))
    np.testing.assert_allclose(m['positions_m'][0,0],np.array([2,4,6])*.0254/.45)


@pytest.mark.parametrize('old,new',[
    (':version 1.10',':version 1.11'),('angle deg','angle rad'),('length .45','length 0'),
    ('order TX TY TZ RX RY RZ','order TX TY TZ RZ RY RX'),('orientation 0 0 0','orientation 0 1 0'),
    ('id 2','id 1'),('name lower','name upper'),('direction 1 0 0','direction 2 0 0'),
    ('length 2','length -2'),('axis 0 0 90 XYZ','axis 0 0 90 XXZ'),
    ('dof rx','dof tx'),('dof rx ry rz','dof rx rx rz'),('(-10 10)','(10 -10)'),
    ('       (-180 180)\n',''),('root upper','tip upper'),('lower tip','lower upper'),
    ('lower tip','lower missing'),(':name example',':name example\n:name again'),
    ('axis 0 0 0 XYZ\nend','axis 0 0 0 XYZ\nlimits (0 1)\nend')])
def test_unsupported_malformed_skeletons_reject(old,new):
    with pytest.raises(ValueError):skeleton(ASF.replace(old,new))


@pytest.mark.parametrize('kwargs',[{},dict(length_convention='unknown'),dict(metres_per_unit=0),
    dict(metres_per_unit=True),dict(metres_per_unit=float('nan')),dict(metres_per_unit=1,length_convention='cmu-inches')])
def test_length_conversion_must_be_explicit_valid_and_unambiguous(kwargs):
    with pytest.raises(ValueError):ac.parse_asf(ASF,**kwargs)


@pytest.mark.parametrize('old,new',[
    (':DEGREES',':RADIANS'),(':FULLY-SPECIFIED',''),(':DEGREES',':DEGREES\n:DEGREES'),
    ('\n1\n','\n2\n'),('\n2\n','\n3\n'),('upper 90','upper nan'),
    ('upper 90','upper 1000001'),('upper 90','upper 1 2'),('upper 90',''),
    ('upper 90','upper 90\nupper 90'),('lower 0 0 0','missing 0 0 0'),
    ('\n2\n','\n:DEGREES\n2\n')])
def test_partial_duplicate_unknown_or_invalid_motion_reject(old,new):
    with pytest.raises(ValueError):ac.parse_amc(AMC.replace(old,new),skeleton())


def test_frame_and_text_capacity_are_checked(monkeypatch):
    monkeypatch.setattr(ac,'MAX_FRAMES',1)
    with pytest.raises(ValueError):ac.parse_amc(AMC,skeleton())
    monkeypatch.setattr(ac,'MAX_ASF_BYTES',30)
    with pytest.raises(ValueError):skeleton()
    with pytest.raises(ValueError):ac.lines('x\x00',100)


def test_file_export_preserves_every_numeric_channel_and_clock(tmp_path):
    asf=tmp_path/'a.asf';amc=tmp_path/'a.amc';out=tmp_path/'out'
    asf.write_text(ASF,encoding='ascii');amc.write_text(AMC,encoding='ascii')
    old=(asf.read_bytes(),amc.read_bytes())
    r=ac.export(asf,amc,out,fps=120,length_convention='cmu-inches')
    with np.load(out/'skeleton-motion.npz',allow_pickle=False) as m:
        np.testing.assert_array_equal(m['source_frame_ids'],[1,2])
        np.testing.assert_array_equal(m['times_s'],[0,1/120])
        np.testing.assert_array_equal(m['source_channel_values'][:,1,0],[90,45])
        np.testing.assert_array_equal(m['source_channel_counts'],[6,1,3,0])
        np.testing.assert_array_equal(m['source_channel_names'][2,:3],['rx','ry','rz'])
        np.testing.assert_array_equal(m['source_channel_present'][:,3],[False,False])
    assert r['frames']==2 and r['joints']==4 and not r['training_admitted']
    assert r['original_numeric_channels_preserved'] and not r['nominal_limits_clamped']
    assert old==(asf.read_bytes(),amc.read_bytes())
    with pytest.raises(ValueError,match='Fresh'):ac.export(asf,amc,out,fps=120,metres_per_unit=1)


@pytest.mark.parametrize('fps',[0,True,float('nan'),1001])
def test_rate_is_required_and_bounded(tmp_path,fps):
    with pytest.raises(ValueError,match='capture rate'):ac.read_motion(tmp_path/'a',tmp_path/'b',fps=fps,metres_per_unit=1)


def test_byte_capacity_before_decode(tmp_path,monkeypatch):
    p=tmp_path/'a';p.write_bytes(b'\xff'*31);monkeypatch.setattr(ac,'MAX_ASF_BYTES',30)
    with pytest.raises(ValueError,match='capacity'):ac.read_motion(p,p,fps=120,metres_per_unit=1)
