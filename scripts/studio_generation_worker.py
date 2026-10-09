"""Validate the immutable Studio request after admission, before model stages."""
import argparse
from pathlib import Path
from strep import save,now
from studio_generation_resources import validate_snapshot


def run(folder):
    folder=Path(folder).resolve()
    try:
        validate_snapshot(folder,execution=True)
        from run_actions import main
        main(folder/'resource-request.json',folder)
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),finished_at=now(),quality_approved=False,release_approved=False))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path)
    run(p.parse_args().folder)
