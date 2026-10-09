"""Account for Windows venv launchers and stop their actual worker processes."""
import psutil


def tree_rss(pid):
    try:
        parent = psutil.Process(pid)
        processes = [parent, *parent.children(recursive=True)]
    except psutil.NoSuchProcess:
        return 0
    total = 0
    for process in processes:
        try:
            total += process.memory_info().rss
        except psutil.NoSuchProcess:
            pass
    return total


def kill_tree(pid,*,reap_parent=True):
    """Stop the owned tree; Popen owners must reap their parent themselves.

    psutil's POSIX wait can consume the exit status before Popen.wait sees it.
    Keep the legacy wait behavior for callers without an owning Popen handle.
    """
    if type(reap_parent) is not bool:raise ValueError('Explicit parent reaping flag required')
    try:
        parent = psutil.Process(pid)
        processes = [*parent.children(recursive=True), parent]
    except psutil.NoSuchProcess:
        return
    for process in reversed(processes[:-1]):
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass
    try:
        parent.kill()
    except psutil.NoSuchProcess:
        pass
    psutil.wait_procs(processes if reap_parent else processes[:-1], timeout=5)
