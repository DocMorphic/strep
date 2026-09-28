import json
from strep import ROOT,read
from apply_control_study import FOLDER
from build_soma_preview import main as build_human

def main():
    build_human(FOLDER)
    data={'analysis':read(FOLDER/'analysis.json'),'text':read(FOLDER/'text/summary.json'),
        'directCharacters':read(FOLDER/'direct/character-summary.json')}
    template=(ROOT/'scripts/control-viewer.html').read_text(encoding='utf-8')
    (FOLDER/'viewer.html').write_text(template.replace('__CONTROL_DATA__',json.dumps(data).replace('<','\\u003c')),encoding='utf-8')

if __name__=='__main__':main()
