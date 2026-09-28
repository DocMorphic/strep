"""Render the rig/height comparison with exact-job links into Studio."""
import html
from pathlib import Path
from urllib.parse import urlencode
from strep import ROOT,read,save


def build():
    baseline=ROOT/'reports/rig-diversity-transfer-v1';study=ROOT/'reports/rig-diversity-height-v1'
    before={c['id']:c for c in read(baseline/'ground-comparison.json')['checks']}
    after={c['id']:c for c in read(study/'ground-comparison.json')['checks']}
    requests={c['id']:c for c in read(baseline/'manifest.json')['jobs']};rows=[];comparison=[]
    cm=lambda v:'—' if v is None else f'{v*100:.2f}'
    for case in read(study/'manifest.json')['cases']:
        a,b=before[case['baseline_id']],after[case['id']];asset=requests[case['baseline_id']]['payload']['asset_id']
        urls=['http://127.0.0.1:8768/studio?'+urlencode(dict(character=asset,rig_job=identifier)) for identifier in (case['baseline_id'],case['id'])]
        worsened=b['floor_depth_m']>a['floor_depth_m']+.00001
        name={'CesiumMan':'CesiumMan','Superhero_Female_FullBody':'Quaternius female','Superhero_Male_FullBody':'Quaternius male'}[case['rig']]
        rows.append(f'''<tr data-rig="{html.escape(case['rig'])}"><td>{name}</td><td>{html.escape(case['action'])}</td>
<td>{cm(a['floor_depth_m'])} → <strong class="{'regression' if worsened else ''}">{cm(b['floor_depth_m'])}</strong></td>
<td>{cm(a['predicted_foot_region_hover_max_m'])} → {cm(b['predicted_foot_region_hover_max_m'])}</td>
<td>{'Manual sole setup needed' if b['sole_draft_error'] else 'Automatic sole draft'}</td>
<td><a href="{html.escape(urls[0])}">Baseline</a> · <a href="{html.escape(urls[1])}">Height candidate</a></td></tr>''')
        comparison.append(dict(rig=case['rig'],action=case['action'],baseline=a,calibrated=b,floor_worsened=worsened,studio_urls=urls))
    save(study/'comparison.json',dict(cases=comparison,promoted=False,independent_human_review=False))
    page='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Strep · Rig diversity</title>
<style>body{font:15px system-ui,sans-serif;background:#edf1f6;color:#172233;margin:0}main{max-width:1200px;margin:36px auto;padding:0 24px}h1{font-size:34px;margin-bottom:6px}p{line-height:1.55;max-width:1000px}.badge{display:inline-block;background:#fff8e7;border:1px solid #dac38e;padding:7px 12px;border-radius:8px}.panel{background:#ffffffc9;border:1px solid #d3dce8;border-radius:14px;padding:18px;margin:20px 0;overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:11px 9px;border-bottom:1px solid #e0e5ec;text-align:left;vertical-align:top}th{color:#526274;font-size:12px}td:nth-child(3),td:nth-child(4){white-space:nowrap;font-variant-numeric:tabular-nums}.regression{color:#a62c26}a{color:#0863ba}select{font:inherit;padding:7px;border:1px solid #bcc9d8;border-radius:7px}summary{cursor:pointer;font-weight:600}</style>
<main><h1>Rig diversity &amp; height calibration</h1><p>Seven actions, three character assets, two rig families. These are development comparisons on reused seed-77 motion, not a held-out release study.</p><span class="badge">42 retained exports · No default promotion · Animator review pending</span>
<div class="panel"><strong>Hovering and penetration are separate failures.</strong><p>A constant offset derived from neutral meshes reduces standing hover, but increases floor penetration in other poses. All regressions remain in the table. This calibration does not solve changing support, mesh intersections or motion quality.</p><p>Values below are centimetres, baseline → height candidate. Hover uses the lowest vertex in a region weighted to the foot/toes during predicted support. It is a coarse diagnostic, and those support predictions are unconfirmed. Zero in either column is not a quality pass.</p>
<label>Character <select id="rigFilter"><option value="">All characters</option><option value="CesiumMan">CesiumMan</option><option value="Superhero_Female_FullBody">Quaternius female</option><option value="Superhero_Male_FullBody">Quaternius male</option></select></label>
<table><thead><tr><th>Character</th><th>Action</th><th>Floor depth (cm)</th><th>Foot-region hover (cm)</th><th>Sole contact setup</th><th>Inspect exact clip in Studio</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<div class="panel"><details><summary>Evidence and remaining limits</summary><p><a href="comparison.json">Comparison data</a> · <a href="ground-comparison.json">Ground measurements</a> · <a href="export-validation.json">GLB validation</a> · <a href="../godot-rig-height-v1/verification.json">Godot verification</a> · <a href="preservation-verification.json">All-frame edit preservation</a> · <a href="package-http-verification.json">Package checks</a></p>
<p>Godot checks imported joints across every frame; it does not establish GPU rendering, physics, independent semantic quality or animator cleanup time. Neutral calibration changes only a constant vertical offset and is kept separate from the baseline. The Quaternius female and male models share one skeleton family; they are not two independent rig designs.</p>
<p>RobotExpressive remains unsupported: two skins, morph targets, non-unit scales and a different leg hierarchy. Its original asset and <a href="../../assets/characters/robot-expressive/compatibility-audit.json">compatibility audit</a> are retained. RiggedFigure imports, but shares Cesium's rig family and was not counted as an additional independent family.</p>
<p>Asset sources: <a href="https://quaternius.com/packs/universalbasecharacters.html">Quaternius Universal Base Characters (CC0)</a>, <a href="https://github.com/KhronosGroup/glTF-Sample-Assets/tree/main/Models/CesiumMan">CesiumMan</a>, <a href="https://github.com/mrdoob/three.js/tree/dev/examples/models/gltf/RobotExpressive">RobotExpressive</a>. Original files and source license records are preserved.</p></details></div></main>
<script>document.getElementById('rigFilter').onchange=e=>{for(const row of document.querySelectorAll('tbody tr'))row.hidden=!!e.target.value&&row.dataset.rig!==e.target.value;};</script>'''
    (study/'review.html').write_text(page,encoding='utf8')


if __name__=='__main__':build()
