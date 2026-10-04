"""Explicit patch-only contact revisions for an existing native-fit source epoch."""
import copy
from native_contact_revision import apply
from native_scene_contacts import fields

SCHEMA = 'strep-native-scene-fit-contact-revision-v1'


def validate(receipt, original, permissions, contacts_digest, permissions_digest,
             current, current_permissions, current_digest):
    fields(receipt, ('schema', 'original_contacts_sha256',
                     'original_permissions_sha256', 'edits'), 'fit contact revision')
    if (receipt['schema'] != SCHEMA
            or receipt['original_contacts_sha256'] != contacts_digest
            or receipt['original_permissions_sha256'] != permissions_digest):
        raise ValueError('Contact revision must bind the completed fit inputs')
    # Reuse the patch/correspondence rules without treating local files as a
    # served Studio request. All non-contact scene fields are compared below.
    draft = dict(schema='strep-studio-native-scene-v1', scene=original,
                 geometry=None, object_edit=None)
    expected = apply(draft, receipt['edits'])['scene']
    if current != expected:
        raise ValueError('Fit revision changes protected scene fields or explicit patches')
    rebound = copy.deepcopy(permissions)
    rebound['contacts_sha256'] = current_digest
    if current_permissions != rebound:
        raise ValueError('Fit revision must retain every original edit permission')
    return dict(schema=SCHEMA, original_contacts_sha256=contacts_digest,
                original_permissions_sha256=permissions_digest,
                authored_contacts_sha256=current_digest,
                explicit_edits=copy.deepcopy(receipt['edits']),
                contact_intent_revised=True, original_intent_retained=True,
                original_actor_epoch_required=True, original_source_caps_required=True,
                contact_timing_and_limits_unchanged=True,
                anatomical_review_pending=True, quality_approved=False,
                training_admitted=False, release_approved=False)
