"""Offline software preview of actual SOMA skin and the authored sphere track."""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from floor_contact import Surface


def run(first,second,output):
    first,second,output=[Path(v).resolve() for v in (first,second,output)];skin=dict(np.load(ASSET,allow_pickle=False));surface=Surface(skin)
    motions=[dict(np.load(folder/'motion.npz',allow_pickle=False)) for folder in [first,second]]
    for folder in [first,second]:
        if sha256(folder/'motion.npz')!=read(folder/'result.json')['motion_sha256']:raise ValueError('Preview motion changed')
    release=read(second/'protocol.json');study=ROOT/release['base_study'];protocol=read(study/'protocol.json');fit=ROOT/protocol['study']/'fit'
    summary=read(fit/'summary.json');context=read(fit/'assets'/summary['trials'][0]['id']/'A'/'recipe.json')['contact']['scene_context'];obj=next(o for o in context['primitives'] if o['id']==protocol['object_id'])
    if obj['geometry']['shape']!='sphere':raise ValueError('Sphere preview required')
    output.mkdir(parents=True,exist_ok=False)
    font_path=Path('C:/Windows/Fonts/segoeui.ttf')
    font=lambda size:ImageFont.truetype(str(font_path),size) if font_path.exists() else ImageFont.load_default()
    title_font,small_font=font(21),font(15);width,height=480,570
    target=np.array([0.,.83,.28]);forward=np.array([2.2,1.25,3.0])-target;forward/=np.linalg.norm(forward)
    right=np.cross([0,1,0],forward);right/=np.linalg.norm(right);up=np.cross(forward,right);axes=np.stack([right,up,forward],1);scale=245.
    def project(v):
        coords=(v-target)@axes;return np.c_[width/2+coords[:,0]*scale,height*.55-coords[:,1]*scale],coords[:,2]
    sv=[];sf=[];rings,segments=16,32
    for i in range(rings+1):
        theta=np.pi*i/rings
        for j in range(segments):
            phi=2*np.pi*j/segments;sv.append([np.sin(theta)*np.cos(phi),np.cos(theta),np.sin(theta)*np.sin(phi)])
    for i in range(rings):
        for j in range(segments):
            a=i*segments+j;b=i*segments+(j+1)%segments;c=(i+1)*segments+j;d=(i+1)*segments+(j+1)%segments
            sf.extend([[a,c,b],[b,c,d]])
    sv,sf=np.array(sv),np.array(sf);faces=np.concatenate([skin['faces'],sf+len(skin['bind_vertices'])]);light=np.array([-.3,.8,1.]);light/=np.linalg.norm(light)
    colors=np.concatenate([np.tile([160,168,177],(len(skin['faces']),1)),np.tile([78,149,206],(len(sf),1))])
    def render(motion,frame,label):
        canvas=Image.new('RGB',(width,height),(235,239,245));draw=ImageDraw.Draw(canvas)
        for x in range(-3,4):
            for z in range(-3,4):
                corners=np.array([[x*.4,0,z*.4],[(x+1)*.4,0,z*.4],[(x+1)*.4,0,(z+1)*.4],[x*.4,0,(z+1)*.4]])
                points,_=project(corners);draw.polygon([tuple(p) for p in points],fill=(222,228,235) if (x+z)%2 else (231,235,241))
        body=surface.vertices(motion['global_rot_mats'][frame],motion['posed_joints'][frame]);sphere=sv*obj['geometry']['radius_m']+obj['positions_m'][frame];vertices=np.concatenate([body,sphere]);points,depth=project(vertices)
        tri=vertices[faces];normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
        shading=.48+.52*np.maximum(0,normal@light);shade=np.clip(colors*shading[:,None],0,255).astype(np.uint8)
        for f in np.argsort(depth[faces].mean(1)):
            draw.polygon([tuple(p) for p in points[faces[f]]],fill=tuple(shade[f]))
        draw.rectangle((0,0,width,57),fill=(247,249,252));draw.text((20,14),label,font=title_font,fill=(30,43,60))
        draw.rectangle((0,height-52,width,height),fill=(247,249,252));phase='Grasp' if frame<=121 else 'Release / return';draw.text((20,height-37),f'{phase}  |  frame {frame}  |  {frame/30:.2f}s',font=small_font,fill=(49,65,85))
        return canvas
    images=[];labels=['Prior 12-frame return','Candidate 24-frame return']
    frames=list(range(100,180,3))
    for frame in frames:
        canvas=Image.new('RGB',(width*2+2,height+34),(250,251,253))
        for i,motion in enumerate(motions):canvas.paste(render(motion,frame,labels[i]),(i*(width+2),0))
        ImageDraw.Draw(canvas).text((20,height+7),'Actual SOMA mesh • 10 fps software preview • development motion, not approved',font=small_font,fill=(69,83,101))
        images.append(canvas)
    images[0].save(output/'comparison.gif',save_all=True,append_images=images[1:],duration=100,loop=0,optimize=False)
    images[10].save(output/'comparison-frame130.png')
    save(output/'preview.json',dict(at=now(),first=first.relative_to(ROOT).as_posix(),second=second.relative_to(ROOT).as_posix(),source_sha256=[sha256(f/'motion.npz') for f in [first,second]],mesh_sha256=sha256(ASSET),frames=frames,preview_fps=10,scope='Offline painter-order triangle rasterization of actual animated skin; approximate occlusion/lighting, no GPU fidelity or visual-quality approval.',quality_approved=False))
    print(dict(frames=len(frames),gif=str(output/'comparison.gif')),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('first',type=Path);parser.add_argument('second',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();run(args.first,args.second,args.output)
