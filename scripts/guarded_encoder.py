"""Supervise the offload experiment without consuming all available system RAM."""
import subprocess
import sys
import time
from pathlib import Path

import psutil
from strep import ROOT, now, save
from process_monitor import tree_rss, kill_tree


def main():
    report = {'started_at': now(), 'status': 'running', 'peak_rss_bytes': 0}
    log = ROOT / 'reports/encoder-offload.log'
    with log.open('w', encoding='utf-8') as stream:
        process = subprocess.Popen([sys.executable, '-u', str(ROOT / 'scripts/embedding_cache.py'),
                                    str(ROOT / 'models/prompt-cache-v0-offload'), '--offload'],
                                   cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                rss = tree_rss(process.pid)
                report['peak_rss_bytes'] = max(report['peak_rss_bytes'], rss)
                available = psutil.virtual_memory().available
                # Allow paging while reserving enough physical RAM for the desktop.
                if available < 600 * 1024**2 or rss > 7 * 1024**3:
                    report.update(status='stopped_by_memory_guard', available_bytes_at_stop=available)
                    kill_tree(process.pid)
                    break
                time.sleep(1)
        finally:
            if process.poll() is None:
                kill_tree(process.pid)
            report['exit_code'] = process.wait()
    if report['status'] == 'running':
        report['status'] = 'complete' if report['exit_code'] == 0 else 'failed'
    report.update(finished_at=now(), log=str(log))
    save(ROOT / 'reports/encoder-offload.json', report)
    print(report)


if __name__ == '__main__':
    main()
