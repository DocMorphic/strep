"""Run complete declared model-free source coverage in explicit file shards."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / '.github/model-free-source-tests.json'


def inventory(path=MANIFEST, root=ROOT):
    if path.stat().st_size > 128*1024:
        raise ValueError('Source test manifest exceeds its complete-data budget')
    data = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(data, dict) or set(data) != {'schema', 'python_tests', 'node_tests'}
            or data['schema'] != 'strep-model-free-source-tests-v1'):
        raise ValueError('Explicit source test inventory required')
    for key, suffix in [('python_tests', 'py'), ('node_tests', 'mjs')]:
        names = data[key]
        if (not isinstance(names, list) or not 1 <= len(names) <= 2048
                or any(type(n) is not str or not re.fullmatch(r'tests/test_[a-zA-Z0-9_\-]+\.'+suffix, n) for n in names)
                or len(set(names)) != len(names)):
            raise ValueError('Distinct complete test paths required')
        if any(not (root/n).is_file() or not (root/n).resolve().is_relative_to(root.resolve()) for n in names):
            raise ValueError('Every declared source test must exist inside the checkout')
    return data


def partition(names, index, count):
    if (type(index) is not int or type(count) is not int
            or not 1 <= count <= min(16, len(names)) or not 0 <= index < count):
        raise ValueError('Explicit nonempty source shard required')
    return names[index::count]


def run(mode, index, count, *, list_only=False):
    data = inventory()
    if mode == 'python':
        names = partition(data['python_tests'], index, count)
        commands = [[sys.executable, '-m', 'pytest', '-q', *names]]
    elif mode == 'node':
        if index != 0 or count != 1:
            raise ValueError('Node coverage runs once per operating system without sharding')
        names = data['node_tests']
        commands = [['node', name] for name in names]
    else:
        raise ValueError('Explicit Python or Node source suite required')
    if list_only:
        print(json.dumps(dict(mode=mode, shard_index=index, shard_count=count, tests=names)))
        return 0
    for command in commands:
        completed = subprocess.run(command, cwd=ROOT)
        if completed.returncode:
            return completed.returncode
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['python', 'node'], default='python')
    parser.add_argument('--shard-index', type=int, default=0)
    parser.add_argument('--shard-count', type=int, default=1)
    parser.add_argument('--list', action='store_true', dest='list_only')
    args = parser.parse_args()
    return run(args.mode, args.shard_index, args.shard_count, list_only=args.list_only)


if __name__ == '__main__':
    raise SystemExit(main())
