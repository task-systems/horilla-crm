"""
Filters for the approvals app
"""

# First-party / Horilla apps
from horilla_generics.filters import HorillaFilterSet

# Local imports
from horilla_processes.approvals.models import ApprovalInstance, ApprovalRule


class ApprovalInstanceFilter(HorillaFilterSet):
    """Filter set for approval instance list views."""

    class Meta:
        """Meta options for ApprovalInstanceFilter."""

        model = ApprovalInstance
        fields = "__all__"
        exclude = ["content_type", "object_id", "content_object", "additional_info"]
        search_fields = [
            "rule__name",
            "status",
            "requested_by__first_name",
            "requested_by__last_name",
        ]


class ApprovalRuleFilter(HorillaFilterSet):
    """Filter set for approval process list view."""

    class Meta:
        """Meta options for ApprovalRuleFilter."""

        model = ApprovalRule
        fields = "__all__"
        exclude = ["additional_info", "process_config"]
        search_fields = ["name"]
