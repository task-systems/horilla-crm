"""
Opportunity core views package.

Submodules: base (list, navbar, kanban, group_by, delete), forms, detail, detail_sections.
"""

from horilla_crm.opportunities.views.core.base import (
    OpportunityDeleteView,
    OpportunityGroupByView,
    OpportunityKanbanView,
    OpportunityListView,
    OpportunityNavbar,
    OpportunityView,
)
from horilla_crm.opportunities.views.core.detail import (
    OpportunityActivityTabView,
    OpportunityDetailTab,
    OpportunityDetailView,
    OpportunityDetailViewTabView,
    OpportunityHistoryTabView,
    OpportunitiesNotesAndAttachments,
)
from horilla_crm.opportunities.views.core.detail_sections import (
    OpportunityContactRoleDeleteView,
    OpportunityContactRoleFormview,
    OpportunityRelatedLists,
    SelectClosedStageView,
)
from horilla_crm.opportunities.views.core.forms import (
    OpportunityChangeOwnerForm,
    OpportunityMultiStepFormView,
    OpportunitySingleFormView,
    RelatedOpportunityFormView,
)

__all__ = [
    "OpportunityView",
    "OpportunityNavbar",
    "OpportunityListView",
    "OpportunityDeleteView",
    "OpportunityKanbanView",
    "OpportunityGroupByView",
    "OpportunityMultiStepFormView",
    "OpportunitySingleFormView",
    "RelatedOpportunityFormView",
    "OpportunityChangeOwnerForm",
    "OpportunityDetailView",
    "OpportunityDetailViewTabView",
    "OpportunityDetailTab",
    "OpportunityActivityTabView",
    "OpportunitiesNotesAndAttachments",
    "OpportunityHistoryTabView",
    "OpportunityRelatedLists",
    "OpportunityContactRoleFormview",
    "OpportunityContactRoleDeleteView",
    "SelectClosedStageView",
]
