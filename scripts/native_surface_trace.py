"""Atomic completed-iteration receipts; recording never approves a proposal."""
import copy
from pathlib import Path
from strep import save, sha256


class SurfaceTrace:
    def __init__(self, output, request):
        self.output, self.request = Path(output), Path(request)
        if self.output.exists():
            raise ValueError('Fresh surface iteration trace required')
        self.request_digest = sha256(self.request)
        self.output.mkdir(parents=True)
        self.files = []

    def __call__(self, iteration):
        if sha256(self.request) != self.request_digest:
            raise ValueError('Surface fit request changed during trace')
        number = iteration.get('iteration')
        if type(number) is not int or number != len(self.files)+1 or not 1 <= number <= 16:
            raise ValueError('Complete sequential surface iterations required')
        path = self.output / f'{number:02d}.json'
        if path.exists():
            raise ValueError('Iteration receipt cannot replace existing evidence')
        save(path, dict(schema='strep-native-surface-iteration-v1',
            request_sha256=self.request_digest, iteration=copy.deepcopy(iteration),
            original_selected=True, quality_approved=False, release_approved=False,
            scope='Completed optimizer iteration only. Accepted means local solver retention; original asset remains selected. Interrupted jobs require their terminal guard record. No motion or release approval.'))
        self.files.append(dict(path=path.name, sha256=sha256(path)))
