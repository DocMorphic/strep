// Role separation for human-entered packet reviews; this assigns no ratings.
export function reviewIdentity(manifest) {
  const role = manifest.review_type === undefined ? 'independent' : manifest.review_type;
  if (role === 'independent') return {
    role, schema: 'strep-human-review-v1', fields: {independent_human: true},
    title: 'Independent animation review',
    attestation: 'I am independently reviewing these clips as a human.',
    error: 'Enter a reviewer code and attest to independent human review.',
    prefix: 'strep-human-review',
  };
  if (role === 'developer') return {
    role, schema: 'strep-developer-packet-review-v1',
    fields: {human_review: true, independent_human: false, review_type: 'developer', quality_approved: false, release_approved: false},
    title: 'Developer animation review',
    attestation: 'I am personally reviewing these clips as a developer. This is not independent review or release approval.',
    error: 'Enter a reviewer code and attest to your own developer review.',
    prefix: 'strep-developer-packet-review',
  };
  throw new Error('Unknown packet review type');
}

export function reviewExport(identity, manifest, digest, reviewer, reviews) {
  const expected = reviewIdentity(manifest);
  if (identity.role !== expected.role) throw new Error('Review role mismatch');
  const reviewer_id = typeof reviewer === 'string' ? reviewer.trim() : '';
  if (!reviewer_id || reviewer_id.length > 120) throw new Error('Reviewer identifier required');
  if (!Array.isArray(reviews)) throw new Error('Reviews must be a list');
  return {schema: expected.schema, packet_id: manifest.packet_id, manifest_sha256: digest,
    reviewer_id, ...expected.fields, reviews};
}
