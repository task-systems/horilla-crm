"""
Views package for the approvals app.

This module re-exports public view classes so existing imports like
`from horilla_processes.approvals import views` continue to work.
"""

from .process import (  # noqa: F401
    ApprovalProcessView,
    ApprovalProcessNavbar,
    ApprovalProcessListView,
    ApprovalProcessCreateUpdateView,
    ApprovalProcessRuleCriteriaView,
    ApprovalProcessRuleComposeView,
)
from .process_rule_dynamic import (  # noqa: F401
    ApprovalProcessRuleActionFormView,
    ApprovalProcessRuleComposeDynamicView,
)
from .process_detail import (  # noqa: F401
    ApprovalProcessRuleRecordFieldsFragmentView,
    ApprovalProcessRuleActionValueWidgetView,
    ApprovalProcessDeleteView,
    ApprovalProcessDetailNavbar,
    ApprovalProcessRuleDeleteView,
    ApprovalProcessDetailView,
)
from .jobs import (  # noqa: F401
    ApprovalJobView,
    ApprovalJobNavbar,
    ApprovalJobsTabView,
    ApprovalJobListView,
)
from .jobs_detail import (  # noqa: F401
    ApprovalJobReviewView,
    ApprovalJobRespondModalView,
)
from .jobs_detail_tabs import (  # noqa: F401
    ApprovalJobFieldUpdateView,
    ApprovalJobDetailTabView,
    ApprovalJobDetailDetailsTabView,
    ApprovalJobDetailTimelineTabView,
    ApprovalJobDetailTasksTabView,
)
from .history import (  # noqa: F401
    ApprovalHistoryNavbar,
    ApprovalHistoryListView,
    ApprovalHistoryDeleteView,
    ApprovalHistoryDetailView,
    ApprovalHistoryResubmitView,
    ApprovalHistoryTaskStatusUpdateView,
    ApprovalHistoryDetailTabView,
    ApprovalHistoryDetailDetailsTabView,
    ApprovalHistoryDetailTimelineTabView,
    ApprovalHistoryDetailTasksTabView,
)

__all__ = [
    # Process
    "ApprovalProcessView",
    "ApprovalProcessNavbar",
    "ApprovalProcessListView",
    "ApprovalProcessCreateUpdateView",
    "ApprovalProcessRuleCriteriaView",
    "ApprovalProcessRuleComposeView",
    "ApprovalProcessRuleActionFormView",
    "ApprovalProcessRuleComposeDynamicView",
    "ApprovalProcessRuleRecordFieldsFragmentView",
    "ApprovalProcessRuleActionValueWidgetView",
    "ApprovalProcessDeleteView",
    "ApprovalProcessDetailNavbar",
    "ApprovalProcessDetailView",
    "ApprovalProcessRuleDeleteView",
    # Jobs
    "ApprovalJobView",
    "ApprovalJobNavbar",
    "ApprovalJobsTabView",
    "ApprovalJobListView",
    "ApprovalJobReviewView",
    "ApprovalJobRespondModalView",
    "ApprovalJobFieldUpdateView",
    "ApprovalJobDetailTabView",
    "ApprovalJobDetailDetailsTabView",
    "ApprovalJobDetailTimelineTabView",
    "ApprovalJobDetailTasksTabView",
    # History
    "ApprovalHistoryNavbar",
    "ApprovalHistoryListView",
    "ApprovalHistoryDeleteView",
    "ApprovalHistoryDetailView",
    "ApprovalHistoryResubmitView",
    "ApprovalHistoryTaskStatusUpdateView",
    "ApprovalHistoryDetailTabView",
    "ApprovalHistoryDetailDetailsTabView",
    "ApprovalHistoryDetailTimelineTabView",
    "ApprovalHistoryDetailTasksTabView",
]
