import math,random,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from rigid_support_point_bounds import rigid_point_movement,composed_angle_bound
from support_centroid_bounds import bound


class BoundsTests(unittest.TestCase):
    def test_zero_motion(self):
        r=rigid_point_movement([1,2,3],[0,0,0],1,0,0)
        self.assertEqual(r['geometric_upper_bound_m'],0)
        self.assertFalse(r['applicability_verified'])
        self.assertFalse(r['formal_interval_certificate'])
    def test_pivot_point_and_stored_response(self):
        c=1+2**-24;a=[2,-3,1]
        r=rigid_point_movement([c*x for x in a],a,c,.03,180)
        self.assertEqual(r['rotation_allowance_m'],0)
        self.assertGreater(r['translation_allowance_m'],.03)
    def test_tight_rotation_translation_alignment(self):
        for c in (1.,1+2**-24,-.5,0.):
            with self.subTest(response=c):
                radius=.2;theta=math.pi/3;distance=.03
                chord=[radius*(math.cos(theta)-1),radius*math.sin(theta),0]
                length=math.hypot(*chord)
                motion=[x+abs(c)*distance*x/length for x in chord]
                r=rigid_point_movement([radius,0,0],[0,0,0],c,distance,60)
                self.assertAlmostEqual(math.hypot(*motion),r['geometric_upper_bound_m'],places=14)
    def test_world_translation_covariance_with_nonunit_response(self):
        c=1+2**-24;p=[.2,.1,-.3];a=[.1,-.2,.4];t=[10,-20,30]
        old=rigid_point_movement(p,a,c,.03,45)
        new=rigid_point_movement([x+c*y for x,y in zip(p,t)],[x+y for x,y in zip(a,t)],c,.03,45)
        self.assertAlmostEqual(old['geometric_upper_bound_m'],new['geometric_upper_bound_m'],places=13)
    def test_half_turn_saturates_radius(self):
        r=rigid_point_movement([.3,.4,0],[0,0,0],1,.03,180)
        self.assertAlmostEqual(r['geometric_upper_bound_m'],1.03)
        self.assertEqual(composed_angle_bound([90,90,90]),180)
    def test_chain_sum(self):
        self.assertEqual(composed_angle_bound([15,15,15]),45)
        self.assertEqual(composed_angle_bound([0]),0)
    def test_point_motion_can_exceed_ankle_budget(self):
        # This target is reached by a 30-degree rotation about an unmoved pivot.
        # Reusing its 30 mm translation budget would falsely reject the target.
        p=[.1,0,0];target=[.1*math.cos(math.pi/6),0,.1*math.sin(math.pi/6)]
        self.assertAlmostEqual(math.hypot(*target),math.hypot(*p))
        self.assertGreater(math.dist(p,target),.03)
        naive=bound([p],target,[0,1,0],0,0,0,.03)
        allowance=rigid_point_movement(p,[0,0,0],1,.03,30)
        correct=bound([p],target,[0,1,0],0,0,0,allowance['maximum_point_displacement_m'])
        self.assertEqual(naive['status'],'incompatible_support_target')
        self.assertEqual(correct['status'],'not_ruled_out')
        self.assertFalse(correct['feasibility_proven'])
    def test_far_target_is_still_ruled_out(self):
        p=[.1,0,0];allowance=rigid_point_movement(p,[0,0,0],1,.03,30)
        self.assertEqual(bound([p],[.3,0,0],[0,1,0],0,0,0,allowance['maximum_point_displacement_m'])['status'],'incompatible_support_target')
    def test_sampled_rigid_transforms_stay_within_bound(self):
        rng=random.Random(711)
        for index in range(200):
            axis=[rng.uniform(-1,1) for _ in range(3)];norm=math.hypot(*axis);axis=[x/norm for x in axis]
            point=[rng.uniform(-2,2) for _ in range(3)];pivot=[rng.uniform(-1,1) for _ in range(3)]
            c=rng.choice([1,1+2**-24,-.5]);limit=rng.uniform(0,180);theta=math.radians(rng.uniform(0,limit));distance=.03
            v=[p-c*a for p,a in zip(point,pivot)];dot=sum(x*y for x,y in zip(axis,v))
            cross=[axis[1]*v[2]-axis[2]*v[1],axis[2]*v[0]-axis[0]*v[2],axis[0]*v[1]-axis[1]*v[0]]
            rotated=[x*math.cos(theta)+y*math.sin(theta)+z*dot*(1-math.cos(theta)) for x,y,z in zip(v,cross,axis)]
            shift=[rng.uniform(-1,1) for _ in range(3)];size=math.hypot(*shift);shift=[x/size*distance for x in shift]
            new=[v+c*(a+s) for v,a,s in zip(rotated,pivot,shift)]
            actual=math.dist(new,point);upper=rigid_point_movement(point,pivot,c,distance,limit)['maximum_point_displacement_m']
            self.assertLessEqual(actual,upper,index)
    def test_invalid_bounds_reject(self):
        for field,value in [('response',True),('response',float('nan')),('translation',-.01),('translation',True),('angle',181),('angle',float('inf'))]:
            with self.subTest(field=field,value=value):
                args=dict(response=1,translation=.03,angle=45);args[field]=value
                with self.assertRaises(ValueError):rigid_point_movement([0,0,0],[0,0,0],args['response'],args['translation'],args['angle'])
        for value in ([],[True],[-1],[181],[float('nan')],None,[0]*65):
            with self.subTest(chain=value):
                with self.assertRaises(ValueError):composed_angle_bound(value)

if __name__=='__main__':unittest.main()
