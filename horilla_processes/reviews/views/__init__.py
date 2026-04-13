"""Aggregate view modules for the `reviews.views` package."""

from horilla_processes.reviews.views.core import (
    ReviewProcessView,
    ReviewProcessNavbar,
    ReviewProcessDetailNavbar,
    ReviewProcessListView,
    ReviewProcessFormView,
    ReviewProcessModelDependentFieldsView,
    ReviewProcessDeleteView,
    ReviewRuleDeleteView,
    ReviewProcessDetailView,
    ReviewRuleFormView,
    ReviewProcessApproverFieldsToggleView,
)

from horilla_processes.reviews.views.review_job import (
    ReviewJobView,
    ReviewJobNavbar,
    ReviewJobListView,
    ReviewJobDetailView,
    ReviewJobFieldReviewView,
)

from horilla_processes.reviews.views.helper import (
    _is_record_owned_by_user,
    _get_record_owner_users,
    _get_sibling_jobs,
    _aggregate_field_status,
    _aggregate_field_comment,
    _check_and_complete_all_jobs,
)


__all__ = [
    # Review Processs
    "ReviewProcessView",
    "ReviewProcessNavbar",
    "ReviewProcessDetailNavbar",
    "ReviewProcessListView",
    "ReviewProcessFormView",
    "ReviewProcessModelDependentFieldsView",
    "ReviewProcessDeleteView",
    "ReviewRuleDeleteView",
    "ReviewProcessDetailView",
    "ReviewRuleFormView",
    "ReviewProcessApproverFieldsToggleView",
    # Review Job
    "ReviewJobView",
    "ReviewJobNavbar",
    "ReviewJobListView",
    "ReviewJobDetailView",
    "ReviewJobFieldReviewView",
    # Review Job Helpers
    "_is_record_owned_by_user",
     "_get_record_owner_users",
    "_get_sibling_jobs",
    "_aggregate_field_status",
    "_aggregate_field_comment",
    "_check_and_complete_all_jobs",
]
