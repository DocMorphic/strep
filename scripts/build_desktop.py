"""Bundle the local desktop shell around the existing action-generation engine."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def render():
    scripts=ROOT/'scripts';html=(scripts/'desktop-shell.html').read_text(encoding='utf8')
    html=html.replace('__CONTROL_CENTER__',(scripts/'control-center.html').read_text(encoding='utf8'))
    html=html.replace('__CHARACTER_STUDIO__',(scripts/'character-studio.html').read_text(encoding='utf8'))
    html=html.replace('__CORRECTION_REVIEW__',(scripts/'correction-review.html').read_text(encoding='utf8'))
    html=html.replace('__CHARACTER_CONTACTS__',(scripts/'character-contacts.html').read_text(encoding='utf8'))
    html=html.replace('__CHARACTER_CLIP_EDIT__',(scripts/'character-clip-edit.html').read_text(encoding='utf8'))
    html=html.replace('__CHARACTER_TRANSITION__',(scripts/'character-transition.html').read_text(encoding='utf8'))
    html=html.replace('__CHARACTER_LOOP__',(scripts/'character-loop.html').read_text(encoding='utf8'))
    html=html.replace('__CHARACTER_EVENTS__',(scripts/'character-events.html').read_text(encoding='utf8'))
    for tag,name in [('__CSS__','desktop-shell.css'),('__DESKTOP_JS__','desktop-shell.js'),('__ENGINE__','action-studio-engine.js')]:
        source=(scripts/name).read_text(encoding='utf8')
        if name=='action-studio-engine.js':
            source='import {createMotionProfileEditor} from "/motion-profile-editor.js";\n'+(scripts/'contact-editor.js').read_text(encoding='utf8')+'\n'+"import {createPoseGuideEditor} from '/pose-guide-editor.js';\nimport {createRigJointEditor} from '/rig-joint-editor.js';\nimport {createRigPostureEditor} from '/rig-posture-editor.js';\n"+source+'\n'+(scripts/'scene-viewer.js').read_text(encoding='utf8')+'\n'+(scripts/'character-contacts.js').read_text(encoding='utf8')+'\n'+(scripts/'character-clip-edit.js').read_text(encoding='utf8')+'\n'+(scripts/'character-transition.js').read_text(encoding='utf8')+'\n'+(scripts/'character-loop.js').read_text(encoding='utf8')+'\n'+(scripts/'character-events.js').read_text(encoding='utf8')+'\n'+(scripts/'generation-history.js').read_text(encoding='utf8')+'\n'+(scripts/'rig-result-selection.js').read_text(encoding='utf8')+'\n'+(scripts/'character-studio.js').read_text(encoding='utf8')
        if name=='action-studio-engine.js':
            source+='\n'+(scripts/'developer-feedback.js').read_text(encoding='utf8')+'\n'+(scripts/'correction-review.js').read_text(encoding='utf8')
        if name=='desktop-shell.css':
            source+='\n'+(scripts/'desktop-interactions.css').read_text(encoding='utf8')
            source+='\n'+(scripts/'control-center.css').read_text(encoding='utf8')
            source+='\n'+(scripts/'character-studio.css').read_text(encoding='utf8')
        if name=='desktop-shell.js':
            source=source.replace('__WINDOW_MANAGER__',(scripts/'desktop-window-manager.js').read_text(encoding='utf8')+'\n'+(scripts/'control-center.js').read_text(encoding='utf8'))
        html=html.replace(tag,source)
    return html

def main():
    (ROOT/'scripts/action-studio.html').write_text(render(),encoding='utf8')
if __name__=='__main__':main()
