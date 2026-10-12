"""Typed corrected component starts retain the original authoring/source epoch."""
from native_component_storage_repair import ComponentAdjustedEdits
from native_storage_continuation import StorageContinuationEdits,state_for as bind_state

SCHEMA='strep-native-component-storage-continuation-v1'


def state_for(base,policy,value,corrections,files):
    return bind_state(base,policy,value,corrections,files,
        _adjusted_type=ComponentAdjustedEdits,_state_schema=SCHEMA)


class ComponentContinuationEdits(StorageContinuationEdits,ComponentAdjustedEdits):
    state_schema=SCHEMA
    adjusted_type=ComponentAdjustedEdits
