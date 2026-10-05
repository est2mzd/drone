"""Produce labelled real-video localization and independent simulated patrol."""
import json
import subprocess
import time
from pathlib import Path
import cv2
import numpy as np
from .localization import Localizer, tcw, center
from .navigation import World, Controller, CONTROL_DT_S

# USER_SETTINGS
OUTPUT_FPS = 15  # delivery video frame rate
OUTPUT_SIZE = (1280, 720)  # video width/height
LOCALIZATION_INTERVAL_S = 0.5  # sample real footage twice per second
SIMULATION_STEPS = 2400  # maximum simulated control ticks
SIMULATION_RENDER_STRIDE = 8  # accelerated patrol presentation
TRACKING_LOSS_START_S = 12.0  # inject localization loss in simulation
TRACKING_LOSS_END_S = 14.0  # localization recovery in simulation
OBSTACLE_INSERT_S = 18.0  # inject new obstacle and force replan
REFERENCE_END_S = 35.0  # descriptor map split; pose graph itself uses full recording
FONT = cv2.FONT_HERSHEY_SIMPLEX  # OpenCV drawing font


def text(frame, value, xy, color=(220,225,230), scale=.6):
    cv2.putText(frame, str(value), xy, FONT, scale, color, 1, cv2.LINE_AA)


def panel():
    return np.full((OUTPUT_SIZE[1],OUTPUT_SIZE[0],3), (25,23,20), np.uint8)


def encode(raw, target):
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(raw),'-c:v','libx264',
                    '-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True)
    raw.unlink()


def draw_world(frame, world, route, trail, p, goals):
    left, top, width, height = 700, 140, 540, 405
    def pixel(x):
        unit=(np.asarray(x)[:2]-world.lo[:2])/(world.hi[:2]-world.lo[:2])
        return int(left+unit[0]*width), int(top+(1-unit[1])*height)
    cv2.rectangle(frame,(left,top),(left+width,top+height),(65,65,65),1)
    for box in world.boxes:
        lo,hi=np.array(box['min']),np.array(box['max'])
        cv2.rectangle(frame,pixel([lo[0],hi[1]]),pixel([hi[0],lo[1]]),(85,90,105),-1)
        ex=world.margin
        cv2.rectangle(frame,pixel([lo[0]-ex,hi[1]+ex]),pixel([hi[0]+ex,lo[1]-ex]),(105,120,155),1)
        text(frame,box.get('id','object'),pixel([lo[0],hi[1]]),scale=.4)
    for g in goals:
        cv2.circle(frame,pixel(g),6,(90,175,215),1)
    for curve,color in ((route,(120,180,90)),(trail,(230,175,85))):
        if curve is not None and len(curve)>1:
            cv2.polylines(frame,[np.array([pixel(x) for x in curve])],False,color,2)
    cv2.circle(frame,pixel(p),7,(240,220,130),-1)
    text(frame,'X [m]  0                         4                          8',(700,580),scale=.5)
    text(frame,'Y [m]  6 -> 0; top view; expanded boxes = aircraft clearance',(700,610),scale=.46)
    text(frame,'green: plan | blue: actual simulated trajectory',(700,640),scale=.5)


def draw_scene(frame, world, p, direction):
    # Fixed 3D overview of simulation geometry, not a camera-derived reconstruction.
    eye=np.array([11.,-8.,10.]);target=np.array([4.,3.,.7])
    forward=target-eye;forward/=np.linalg.norm(forward)
    right=np.cross(forward,[0,0,1]);right/=np.linalg.norm(right)
    down=np.cross(forward,right);r=np.array([right,down,forward])
    def pixel(x):
        c=r@(np.asarray(x)-eye)
        return tuple((c[:2]/c[2]*650+np.array([345,345])).astype(int))
    ground=np.array([pixel(x) for x in ([0,0,0],[8,0,0],[8,6,0],[0,6,0])])
    cv2.fillConvexPoly(frame,ground,(37,39,40))
    for x in np.arange(0,world.hi[0]+.1,.5):
        cv2.line(frame,pixel([x,0,0]),pixel([x,6,0]),(54,56,56),1,cv2.LINE_AA)
    for y in np.arange(0,world.hi[1]+.1,.5):
        cv2.line(frame,pixel([0,y,0]),pixel([8,y,0]),(54,56,56),1,cv2.LINE_AA)
    faces=[]
    for box in world.boxes:
        lo,hi=np.array(box['min']),np.array(box['max'])
        corners=np.array([[lo[j] if not (i>>j)&1 else hi[j] for j in range(3)] for i in range(8)])
        for face in ([0,1,3,2],[4,5,7,6],[0,1,5,4],[2,3,7,6],[0,2,6,4],[1,3,7,5]):
            vertices=corners[face]
            depth=np.linalg.norm(vertices.mean(0)-eye)
            faces.append((depth,vertices))
    for _,vertices in sorted(faces,key=lambda x:x[0],reverse=True):
        poly=np.array([pixel(x) for x in vertices])
        color=(100,110,125) if np.ptp(vertices[:,2])==0 else (65,75,90)
        cv2.fillConvexPoly(frame,poly,color)
        cv2.polylines(frame,[poly],True,(145,155,170),1,cv2.LINE_AA)
    cv2.line(frame,pixel(p),pixel([p[0],p[1],0]),(135,175,190),1)
    cv2.circle(frame,pixel(p),7,(240,220,130),-1)
    for delta in ([.2,0,0],[-.2,0,0],[0,.2,0],[0,-.2,0]):
        cv2.circle(frame,pixel(p+delta),4,(220,200,125),1)
    text(frame,'SIMULATED 3D overview / ground-truth geometry',(25,135),scale=.52)
    text(frame,'XYZ [m], Z up; yellow marker = simulated drone',(25,520),scale=.5)


def simulation(world):
    c=Controller(world,world.spec['patrol_goals']);p=np.array(world.spec['start'],float)
    log=[];added=False
    for step in range(SIMULATION_STEPS):
        t=step*CONTROL_DT_S
        if t>=OBSTACLE_INSERT_S and not added:
            world.add_obstacle([4.6,3.5,0],[5.1,4.6,2.8],'new_box');added=True
        valid=not TRACKING_LOSS_START_S<=t<TRACKING_LOSS_END_S
        v,state=c.tick(p,t,t,valid,.02,t,True,True)
        candidate=p+v*CONTROL_DT_S
        if np.linalg.norm(v)>0 and not world.segment_safe(p,candidate):
            raise AssertionError('Simulator collision')
        log.append({'t':round(t,2),'position':p.tolist(),'velocity':v.tolist(),'state':state,
                    'goal_index':c.goal_index,'path':None if c.path is None else c.path.tolist(),
                    'obstacle_inserted':added, 'objects':[dict(box) for box in world.boxes]})
        p=candidate
        if state=='COMPLETE':break
    if log[-1]['state']!='COMPLETE':
        raise RuntimeError('Patrol did not complete; inspect log')
    return log


def run(a):
    a.output_dir.mkdir(parents=True,exist_ok=True)
    raw=a.output_dir/'demo_raw.avi'
    writer=cv2.VideoWriter(str(raw),cv2.VideoWriter_fourcc(*'MJPG'),OUTPUT_FPS,OUTPUT_SIZE)
    if not writer.isOpened():raise RuntimeError('Video writer unavailable')
    loc=Localizer(a.map);poses=np.atleast_2d(np.loadtxt(a.poses))
    cap=cv2.VideoCapture(str(a.video));fps=cap.get(cv2.CAP_PROP_FPS)
    duration=cap.get(cv2.CAP_PROP_FRAME_COUNT)/fps
    logs=[];trail=[];reference=[]
    timestamps=np.arange(5.5,min(duration,57),LOCALIZATION_INTERVAL_S)
    points=loc.xyz
    bounds_lo=np.percentile(points[:,[0,2]],2,axis=0)
    bounds_hi=np.percentile(points[:,[0,2]],98,axis=0)
    pose_centres=np.array([center(tcw(row)) for row in poses if row[-1]==1])[:,[0,2]]
    bounds_lo=np.minimum(bounds_lo,pose_centres.min(0))-.1
    bounds_hi=np.maximum(bounds_hi,pose_centres.max(0))+.1
    def map_pixel(x):
        unit=(np.asarray(x)[[0,2]]-bounds_lo)/(bounds_hi-bounds_lo)
        return tuple((np.array([715,520])+unit*np.array([490,-310])).astype(int))
    for t in timestamps:
        cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,img=cap.read()
        if not ok:continue
        started=time.perf_counter();est=loc.estimate(img);elapsed=time.perf_counter()-started
        row=poses[np.argmin(abs(poses[:,0]-t))]
        log={'t':float(t),'inference_s':elapsed,'split':'held_out_descriptors' if t>=REFERENCE_END_S else 'reference_interval',**est}
        ref=center(tcw(row)) if row[-1]==1 else None
        if est['valid'] and ref is not None:
            log['difference_from_orb_slam_units']=float(np.linalg.norm(np.array(est['position'])-ref))
        logs.append(log)
        canvas=panel()
        text(canvas,'01 / REAL MINI 3 VIDEO: map-relative visual localization',(25,42),scale=.8)
        text(canvas,'Offline map: frames before 35s | PnP queries: 2 Hz | no metric scale / no aircraft commands',(25,80),scale=.56)
        if est['valid']:
            r=np.array(est['rotation_cw']);p=np.array(est['position']);tv=-r@p
            pixels=cv2.projectPoints(points,cv2.Rodrigues(r)[0],tv,loc.k,loc.d)[0].reshape(-1,2)
            good=(points@r.T+tv)[:,2]>0
            for uv in pixels[good][::12]:
                if 0<=uv[0]<img.shape[1] and 0<=uv[1]<img.shape[0]:
                    cv2.circle(img,tuple(uv.astype(int)),2,(90,220,120),-1)
            trail.append(p)
        if ref is not None:reference.append(ref)
        canvas[140:500,25:665]=cv2.resize(img,(640,360))
        for xy in points[::8]:cv2.circle(canvas,map_pixel(xy),1,(65,65,65),-1)
        for curve,color in ((reference,(125,135,155)),(trail,(230,170,75))):
            if len(curve)>1:cv2.polylines(canvas,[np.array([map_pixel(x) for x in curve])],False,color,2)
        text(canvas,'XZ map [SLAM units, arbitrary scale]',(710,140),scale=.55)
        text(canvas,'gray: ORB pose | blue: estimated camera pose',(710,565),scale=.5)
        state='LOCALIZED (research output)' if est['valid'] else 'LOST -> zero command'
        text(canvas,f't={t:.1f}s   {state}',(25,550),(110,215,150) if est['valid'] else (110,140,230))
        text(canvas,f'inliers={est["inliers"]}  CPU={elapsed*1000:.0f}ms  split={log["split"]}',(25,585),scale=.5)
        if est['valid']:text(canvas,f'reprojection RMS={est["rms_px"]:.2f}px',(25,620),scale=.5)
        text(canvas,'Camera pose only. World/body calibration and live geometry remain required.',(25,685),scale=.57)
        for _ in range(3):writer.write(canvas)
    cap.release()
    world=World.load(a.world);sim=simulation(world);world=World.load(a.world)
    trail=[];lastdir=np.array([1.,0,0]);inserted=False
    for i,event in enumerate(sim):
        p=np.array(event['position']);v=np.array(event['velocity']);trail.append(p)
        if event['obstacle_inserted'] and not inserted:
            world.add_obstacle([4.6,3.5,0],[5.1,4.6,2.8],'new_box');inserted=True
        if np.linalg.norm(v)>0:lastdir=v.copy()
        if i%SIMULATION_RENDER_STRIDE and event['state']!='COMPLETE':continue
        canvas=panel();draw_scene(canvas,world,p,lastdir.copy())
        text(canvas,'02 / SIMULATION: coordinate patrol + obstacle avoidance',(25,42),scale=.8)
        text(canvas,'Ground-truth simulated pose and geometry; separate scene from Mini 3 footage',(25,80),scale=.58)
        draw_world(canvas,world,event['path'],trail,p,world.spec['patrol_goals'])
        text(canvas,f't={event["t"]:.1f}s  {event["state"]}',(25,570),scale=.68)
        text(canvas,f'xyz [m] = {np.round(p,2)}',(25,610),scale=.6)
        text(canvas,f'speed={np.linalg.norm(v):.2f}m/s  goal={min(event["goal_index"]+1,len(world.spec["patrol_goals"]))}/4',(25,648),scale=.6)
        text(canvas,'12-14s: tracking loss -> STOP | 18s: new obstacle -> REPLAN',(25,690),scale=.6)
        writer.write(canvas)
        if event['state']=='COMPLETE':
            for _ in range(OUTPUT_FPS*2):writer.write(canvas)
            cv2.imwrite(str(a.output_dir/'patrol_preview.jpg'),canvas)
    writer.release();encode(raw,a.output_dir/'mini3_patrol_demo.mp4')
    held=[x for x in logs if x['split']=='held_out_descriptors'];valid=[x for x in held if x['valid']]
    errors=[x['difference_from_orb_slam_units'] for x in valid if 'difference_from_orb_slam_units' in x]
    summary={'real_video':str(a.video),'descriptor_map_landmarks':len(points),
             'held_out_samples':len(held),'held_out_localized':len(valid),
             'median_difference_from_orb_slam_units':float(np.median(errors)) if errors else None,
             'max_difference_from_orb_slam_units':float(np.max(errors)) if errors else None,
             'p95_inference_ms':float(np.percentile([x['inference_s']*1000 for x in logs],95)),
             'simulation_complete':sim[-1]['state']=='COMPLETE','simulation_duration_s':sim[-1]['t'],
             'tracking_loss_zero_velocity':all(np.linalg.norm(x['velocity'])==0 for x in sim if TRACKING_LOSS_START_S<=x['t']<TRACKING_LOSS_END_S),
             'limitations':['Same-recording validation; ORB pose graph uses full video.',
               'ORB comparison is not independent ground truth; units are not metres.',
               'Simulation map/pose are ground truth, not inferred from real video.',
               'No live flight, camera/body calibration or online obstacle reconstruction tested.']}
    for name,data in [('localization_log.json',logs),('simulation_log.json',sim),('validation.json',summary)]:
        (a.output_dir/name).write_text(json.dumps(data,ensure_ascii=False,indent=2))
    print(json.dumps(summary,ensure_ascii=False,indent=2))
