"""horilla_duplicates merge-related views."""


from .generic import GenericDuplicateDetailView, DuplicateWarningModalView
from .potential import PotentialDuplicatesTabView
from .merge_flow import (
    MergeDuplicatesCompareView,
    MergeDuplicatesSummaryView,
    MergeDuplicatesView,
)

__all__ = [
    "GenericDuplicateDetailView",
    "DuplicateWarningModalView",
    "PotentialDuplicatesTabView",
    "MergeDuplicatesCompareView",
    "MergeDuplicatesSummaryView",
    "MergeDuplicatesView",
]
