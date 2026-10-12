"""Native-checked mixed stored-key repair using the original fitting reference."""
from native_fit_storage import FitStorage
from native_component_storage_repair import ComponentAdjustedEdits
from native_component_storage_continuation import ComponentContinuationEdits,state_for
from native_component_storage_search import search

METHODS={'native_fit_component_storage.py','native_component_storage_repair.py',
    'native_component_storage_continuation.py','native_component_storage_search.py'}


class FitComponentStorage(FitStorage):
    adjusted_type=ComponentAdjustedEdits
    continuation_type=ComponentContinuationEdits
    search_method=staticmethod(search)
    state_factory=staticmethod(state_for)
