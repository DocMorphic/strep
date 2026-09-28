import argparse
import json
from strep import ROOT, read


def main(folder):
    summary=read(folder/'summary.json')
    template=(ROOT/'scripts/combined-viewer.html').read_text(encoding='utf-8')
    html=template.replace('__COMBINED_DATA__',json.dumps(summary).replace('<','\\u003c'))
    (folder/'viewer.html').write_text(html,encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='reports/combined-controls-v1')
    main(ROOT/parser.parse_args().output)
