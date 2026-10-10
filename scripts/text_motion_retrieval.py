"""Diagnostic motion-to-description retrieval; scores are not quality approval."""
import math


def evaluate(text_ids, text_vectors, motion_ids, motion_vectors, expected_text_ids):
    def identifiers(values, limit):
        if (not isinstance(values, list) or not 1 <= len(values) <= limit
                or any(type(v) is not str or not v or len(v) > 256 for v in values)
                or len(set(values)) != len(values)):
            raise ValueError('Distinct bounded identifiers required')
    identifiers(text_ids, 64)
    identifiers(motion_ids, 256)
    if (not isinstance(expected_text_ids, list) or len(expected_text_ids) != len(motion_ids)
            or any(t not in text_ids for t in expected_text_ids)
            or set(expected_text_ids) != set(text_ids)):
        raise ValueError('Every query requires a represented expected description')

    def vectors(values, count):
        if not isinstance(values, list) or len(values) != count:
            raise ValueError('Complete embedding population required')
        for row in values:
            if (not isinstance(row, list) or len(row) != 256
                    or any(type(v) not in (int, float) or not math.isfinite(v) for v in row)):
                raise ValueError('Finite 256-dimensional vectors required')
            if abs(math.fsum(v*v for v in row) - 1) > 1e-4:
                raise ValueError('Unit embeddings required; no implicit normalization')
    vectors(text_vectors, len(text_ids))
    vectors(motion_vectors, len(motion_ids))
    scores = [[math.fsum(a*b for a, b in zip(m, t)) / 2 + .5
               for t in text_vectors] for m in motion_vectors]
    rows = []
    for mid, expected, row in zip(motion_ids, expected_text_ids, scores):
        target = row[text_ids.index(expected)]
        top = max(row)
        rows.append(dict(motion_id=mid, expected_text_id=expected,
                         expected_score=target,
                         rank_best=1 + sum(s > target for s in row),
                         rank_worst=sum(s >= target for s in row),
                         top_text_ids=[t for t, s in zip(text_ids, row) if s == top],
                         margin_to_best_alternative=target-max(s for t, s in zip(text_ids, row)
                                                               if t != expected) if len(row)>1 else None))
    return dict(schema='strep-text-motion-retrieval-v1',
                score_definition='(dot(unit motion latent, unit text latent) + 1) / 2',
                text_ids=list(text_ids), motion_ids=list(motion_ids), scores=scores, rows=rows,
                population=len(rows), candidate_descriptions=len(text_ids),
                conservative_top1_count=sum(r['rank_worst'] <= 1 for r in rows),
                conservative_top3_count=sum(r['rank_worst'] <= 3 for r in rows),
                quality_approved=False, release_approved=False, training_admitted=False,
                scope='Development motion-to-description retrieval over the declared candidate set. Not official benchmark R-precision, calibrated correctness probability, object/partner contact, temporal-detail or human approval.')
