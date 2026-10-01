"""Orthographic mesh inspection of completed rigid-contact diagnostics."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from strep import read, save, sha256, now


def run(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh inspection output required')
    result = read(source/'result.json')
    if result['status'] != 'complete': raise ValueError('Completed diagnostic required')
    verified = {str(source/'result.json'): sha256(source/'result.json')}
    for name in ('request.json', 'best-geometry.npz'):
        if sha256(source/name) != result['outputs'][name]: raise ValueError('Changed geometry evidence')
        verified[str(source/name)] = result['outputs'][name]
    request = read(source/'request.json'); geometry = np.load(source/'best-geometry.npz', allow_pickle=False)
    output.mkdir(); shutil.copyfile(__file__, output/Path(__file__).name)
    canvas = Image.new('RGB', (1500, 1010), '#edf1f6'); draw = ImageDraw.Draw(canvas)
    font_path = Path('C:/Windows/Fonts/segoeui.ttf')
    font = lambda size: ImageFont.truetype(str(font_path), size) if font_path.exists() else ImageFont.load_default()
    draw.text((24, 12), 'Hand contact marker inspection - actual source mesh', fill='#142235', font=font(25))
    draw.text((24, 49), 'Red: authored anchor. Blue: local surface normal. Grey: hand region. No anatomical or animation approval.', fill='#34455a', font=font(16))
    rows = []
    for i, label in enumerate(('left', 'right')):
        points = geometry[label]; faces = geometry[label+'_faces']; ids = np.asarray(request['region_vertices'][i])
        center = np.asarray(request['target']['centers_m'][i]); normal = np.asarray(request['target']['normals'][i])
        relative = points-center; heights = relative@normal
        tangent = relative-np.outer(heights, normal)
        _, _, vh = np.linalg.svd(tangent[ids], full_matrices=False)
        up = vh[0]; right = np.cross(up, normal); right /= np.linalg.norm(right); up = np.cross(normal, right)
        basis = np.stack([right, up, normal], axis=1); local = relative@basis*1000
        distances = np.linalg.norm(relative[ids], axis=1); neighbourhoods = []
        for radius in (.005, .01, .02, .05):
            nearby = ids[distances <= radius]
            neighbourhoods.append(dict(radius_m=radius, vertices=len(nearby),
                maximum_outward_height_m=None if not len(nearby) else float(heights[nearby].max()),
                vertices_above_half_gap=int(np.count_nonzero(heights[nearby] > request['target']['separation_m']/2))))
        highest = int(ids[np.argmax(heights[ids])])
        rows.append(dict(actor=i, region_vertices=len(ids), highest_vertex=highest,
            maximum_outward_height_m=float(heights[highest]), neighbourhoods=neighbourhoods))
        for j, (angle, title) in enumerate(((0., 'Facing marker normal'), (np.pi/2, 'Side profile'), (np.pi/4, 'Oblique'))):
            view = np.array([[np.cos(angle), 0, np.sin(angle)], [0, 1, 0], [-np.sin(angle), 0, np.cos(angle)]])
            p = local@view.T; lo, hi = p[ids, :2].min(0), p[ids, :2].max(0)
            scale = min(425/(hi[0]-lo[0]), 350/(hi[1]-lo[1])); mid = (lo+hi)/2
            origin = np.array([j*500+250, i*445+290])
            xy = origin+(p[:, :2]-mid)*[scale, -scale]
            tris = p[faces]; n = np.cross(tris[:, 1]-tris[:, 0], tris[:, 2]-tris[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1)[:, None], 1e-15)
            shades = (120+95*np.abs(n@np.array([.2, .3, .9327]))).clip(0, 255).astype(int)
            for index in np.argsort(tris[:, :, 2].mean(1)):
                grey = int(shades[index]); draw.polygon([tuple(v) for v in xy[faces[index]]], fill=(grey, grey, grey))
            marker = origin-mid*[scale, -scale]
            tip = origin+((np.array([0., 0., 15.])@view.T)[:2]-mid)*[scale, -scale]
            draw.line([tuple(marker), tuple(tip)], fill='#237dce', width=3)
            draw.ellipse((marker[0]-5, marker[1]-5, marker[0]+5, marker[1]+5), fill='#d32a48')
            draw.text((j*500+20, i*445+94), f'Actor {i+1}: {title}', fill='#142235', font=font(18))
            draw.line([(j*500+30, i*445+491), (j*500+30+20*scale, i*445+491)], fill='#233648', width=3)
            draw.text((j*500+30, i*445+463), '20 mm', fill='#233648', font=font(14))
    draw.text((24, 973), 'Orthographic software rendering; approximate triangle ordering. Quantitative intersection results remain authoritative.', fill='#34455a', font=font(15))
    canvas.save(output/'hands.png')
    save(output/'inspection.json', dict(at=now(), source=str(source), verified_files=verified, actors=rows,
        image_sha256=sha256(output/'hands.png'), renderer_sha256=sha256(output/Path(__file__).name),
        scope='Outward height is measured relative to the marker tangent plane, not penetration depth or an infeasibility certificate.', quality_approved=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('source', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); run(args.source, args.output)
