"""Indexed complete storage exchanges without allocating every proposal.

Only planner storage changes: authoring policy remains at most 64 absolute
one-neighbor corrections. Every exported proposal still needs original motion,
contact and scene gates. A finite traversal prefix is not exhaustive search.
"""
from bisect import bisect_right
from native_storage_exchange_plan import FIELDS, _row, _seed


class ExchangeIndex:
    """Bind a complete option/seed snapshot and address its original ordering.

    The candidate budget covers the whole population before traversal. At most
    1,024 options times 64 restorations can produce 65,536 candidates. Options,
    seed rows and returned proposals never share mutable caller dictionaries.
    """

    def __init__(self, corrections, options, maximum_corrections, *, maximum_candidates=65536):
        used = _seed(corrections, maximum_corrections)
        if (not isinstance(options, list) or len(options) > 1024
                or type(maximum_candidates) is not int
                or not 1 <= maximum_candidates <= 65536):
            raise ValueError('Explicit complete option and indexed candidate budgets required')
        seen = set()
        counts = []
        exchanges = []
        for option in options:
            identity = _row(option, option=True)
            absolute = identity + (option['step'],)
            if absolute in seen:
                raise ValueError('Duplicate absolute option')
            seen.add(absolute)
            if (identity not in used and option['step'] == 0
                    or identity in used and option['step'] == used[identity]['step']):
                raise ValueError('A proposal must change an existing absolute value')
            exchange = identity not in used and len(used) == maximum_corrections
            exchanges.append(exchange)
            counts.append(len(corrections) if exchange else 1)
        if sum(counts) > maximum_candidates:
            raise ValueError('Complete exchange population exceeds the indexed candidate budget')
        self._seed = tuple(tuple(row[k] for k in FIELDS) for row in corrections)
        self._options = tuple(tuple(row[k] for k in FIELDS) for row in options)
        self._counts = tuple(counts)
        self._exchanges = tuple(exchanges)
        offsets = [0]
        for count in counts:
            offsets.append(offsets[-1] + count)
        self._offsets = tuple(offsets)

    def __len__(self):
        return self._offsets[-1]

    def proposal_at(self, index):
        """Return one detached original-order proposal; reject negative indices."""
        if type(index) is not int or not 0 <= index < len(self):
            raise ValueError('Candidate index must belong to the complete population')
        option_index = bisect_right(self._offsets, index) - 1
        choice = dict(zip(FIELDS, self._options[option_index]))
        # Direct proposals at a one-correction capacity have count one too;
        # decide by identity, not group size.
        restored = (dict(zip(FIELDS, self._seed[index - self._offsets[option_index]]))
                    if self._exchanges[option_index] else None)
        return dict(choice=choice, restored=restored)

    def diagonal_indices(self):
        """Traverse every proposal once with the original diagonal ordering.

        Round-robin across options, rotating each restoration list by the
        option's original position. Callers must declare and retain any finite
        probe limit separately; this iterator never silently drops options.
        """
        for turn in range(max(self._counts, default=0)):
            for i, count in enumerate(self._counts):
                if turn < count:
                    yield self._offsets[i] + (turn + i) % count
