"""Feature registration for Review Process."""

# First party imports (Horilla)
from horilla.registry.feature import register_feature

# First-party / Horilla apps
from horilla_processes.integration import (
    register_pre_approval_sync,
    register_suppress_approval_if,
)

# Local party imports
from .list_visibility import patch_horilla_list_queryset
from .utils import record_has_pending_review_jobs, refresh_review_jobs_for_record

register_feature(
    "reviews",
    "reviews_models",
    include_models=[
        ("leads", "Lead"),
        ("opportunities", "Opportunity"),
        ("accounts", "Account"),
        ("contacts", "Contact"),
    ],
)


patch_horilla_list_queryset()

register_pre_approval_sync(refresh_review_jobs_for_record)
register_suppress_approval_if(record_has_pending_review_jobs)
