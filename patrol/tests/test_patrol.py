import unittest
import cv2
import numpy as np
from patrol.navigation import World, Controller, MAX_SPEED_MPS
from patrol.localization import rotation, tcw, center, triangulate


def world():
    return World({'units':'m','frame':'local_xyz_z_up','bounds':{'min':[0,0,0],'max':[4,4,3]},
        'resolution_m': .25, 'clearance_m': .2,
        'verified_free':[{'min':[0,0,0],'max':[4,4,3]}],
        'objects':[{'min':[1.5,0,0],'max':[2,2.5,3]}]})


class Planning(unittest.TestCase):
    def test_detour_and_exact_endpoints(self):
        w=world();a=np.array([.7,.7,1.2]);b=np.array([3,.7,1.2]);p=w.plan(a,b)
        np.testing.assert_equal(p[0],a);np.testing.assert_equal(p[-1],b)
        self.assertTrue(all(w.segment_safe(x,y) for x,y in zip(p,p[1:])))
        self.assertGreater(np.linalg.norm(np.diff(p,axis=0),axis=1).sum(),np.linalg.norm(a-b))

    def test_thin_wall_segment(self):
        w=world();w.add_obstacle([.999,0,0],[1.001,4,3])
        self.assertFalse(w.segment_safe([.5,3,1],[1.4,3,1]))

    def test_unknown_and_bad_goals(self):
        w=world();w.free=[]
        with self.assertRaises(ValueError):w.plan([.5,.5,1],[3,3,1])
        w=world()
        for g in ([1.8,1,1],[8,2,1],[np.nan,2,1]):
            with self.assertRaises(ValueError):w.plan([.5,.5,1],g)

    def test_dynamic_replan_blocked(self):
        w=world();c=Controller(w,[[3,.7,1.2]]);p=[.7,.7,1.2]
        kwargs=dict(now=1,pose_stamp=1,valid=True,sigma_m=.01,geometry_stamp=1,
                    metric_aligned=True,camera_body_calibrated=True)
        v,state=c.tick(p,**kwargs);self.assertEqual(state,'MOVING');self.assertLessEqual(np.linalg.norm(v),MAX_SPEED_MPS+1e-8)
        w.add_obstacle([0,2.5,0],[4,3,3])
        v,state=c.tick(p,**kwargs);self.assertEqual(state,'BLOCKED');np.testing.assert_equal(v,0)

    def test_stop_guards(self):
        for override,expected in [({'valid':False},'WAIT_LOCALIZATION'),({'pose_stamp':0},'STALE_POSE'),
            ({'geometry_stamp':0},'STALE_GEOMETRY'),({'pose_stamp':2},'STALE_POSE'),
            ({'metric_aligned':False},'WAIT_CALIBRATION'),({'camera_body_calibrated':False},'WAIT_CALIBRATION'),
            ({'sigma_m':float('nan')},'WAIT_LOCALIZATION'),({'emergency':True},'EMERGENCY_STOP')]:
            kwargs=dict(now=1,pose_stamp=1,valid=True,sigma_m=.01,geometry_stamp=1,
                        metric_aligned=True,camera_body_calibrated=True);kwargs.update(override)
            v,state=Controller(world(),[[3,.7,1.2]]).tick([.7,.7,1.2],**kwargs)
            self.assertEqual(state,expected);np.testing.assert_equal(v,0)

    def test_goal_arrival(self):
        c=Controller(world(),[[.7,.7,1.2]])
        args=dict(now=1,pose_stamp=1,valid=True,sigma_m=.01,geometry_stamp=1,
                  metric_aligned=True,camera_body_calibrated=True)
        self.assertEqual(c.tick([.7,.7,1.2],**args)[1],'ARRIVED')
        self.assertEqual(c.tick([.7,.7,1.2],**args)[1],'COMPLETE')


class Geometry(unittest.TestCase):
    def test_tcw_inverse(self):
        r=rotation([0,np.sin(.3),0,np.cos(.3)]);c=np.array([1.,2.,3.]);t=-r@c
        row=np.r_[0,t,[0,np.sin(.3),0,np.cos(.3)],1]
        np.testing.assert_allclose(center(tcw(row)),c)

    def test_triangulation_with_distortion_and_cheirality(self):
        rng=np.random.default_rng(5);xyz=rng.uniform([-1,-1,3],[1,1,6],size=(60,3))
        k=np.array([[800.,0,320],[0,800,240],[0,0,1]]);d=np.array([.1,-.03,.001,.001,0.])
        p1=np.c_[np.eye(3),np.zeros(3)];p2=np.c_[np.eye(3),[-.5,0,0]]
        uv=[cv2.projectPoints(xyz,np.zeros(3),p[:,3],k,d)[0].reshape(-1,2) for p in (p1,p2)]
        out,valid=triangulate(p1,p2,*uv,k,d)
        self.assertTrue(valid.all());np.testing.assert_allclose(out,xyz,atol=1e-4)
        _,valid=triangulate(p1,p1,uv[0],uv[0],k,d);self.assertFalse(valid.any())



class RuntimeAlignment(unittest.TestCase):
    def test_calibrated_camera_to_body(self):
        from patrol.runtime import Alignment
        r_bc=np.array([[0,0,1],[1,0,0],[0,1,0.]])
        spec={'metric_verified':True,'extrinsics_verified':True,'gimbal_fixed':True,
              'metres_per_slam_unit':2.,'rotation_world_from_slam':np.eye(3).tolist(),
              'translation_world_from_slam_m':[1,2,3],
              'rotation_body_from_camera':r_bc.tolist(),'camera_origin_in_body_m':[.1,0,0]}
        alignment=Alignment(spec)
        p,r=alignment.pose({'position':[1,1,1],'rotation_cw':np.eye(3).tolist()})
        np.testing.assert_allclose(p,[3,4,4.9]);np.testing.assert_allclose(r,r_bc.T)
        spec['metric_verified']=False
        with self.assertRaises(ValueError):Alignment(spec)

    def test_reject_reflection_and_unknown_confidence(self):
        from patrol.runtime import proper_rotation
        with self.assertRaises(ValueError):proper_rotation(np.diag([1,1,-1]))
        kwargs=dict(now=1,pose_stamp=1,valid=True,sigma_m=float('inf'),geometry_stamp=1,
                    metric_aligned=True,camera_body_calibrated=True)
        v,state=Controller(world(),[[3,.7,1.2]]).tick([.7,.7,1.2],**kwargs)
        self.assertEqual(state,'WAIT_LOCALIZATION');np.testing.assert_equal(v,0)

if __name__=='__main__':unittest.main()
