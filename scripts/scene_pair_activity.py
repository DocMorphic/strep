"""Observe standalone paired fitting so Studio does not overlap another worker."""
from pathlib import Path
from strep import ROOT


def matches_study(info):
    args, cwd = info.get('cmdline'), info.get('cwd')
    if not isinstance(args, list) or len(args) < 2 or not cwd:
        return False
    target = (ROOT/'scripts/study_scene_pair_fit.py').resolve()
    # Supported direct CLI invocation: python script.py prepared output.
    script = Path(args[1])
    if script.name != target.name:
        return False
    return (script if script.is_absolute() else Path(cwd)/script).resolve() == target


def external_pair_fit_busy():
    import psutil
    for process in psutil.process_iter(['cmdline', 'cwd']):
        try:
            if matches_study(process.info) and process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            continue
    return False
