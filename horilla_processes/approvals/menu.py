"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the approvals app
"""

from horilla.menu import sub_section_menu

# First-party / Horilla imports
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _

# Local imports
from horilla_processes import ProcessSettings

process = ProcessSettings()
process.items.extend(
    [
        {
            "label": _("Approval Processes"),
            "url": reverse_lazy("approvals:approval_process_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#approval-process-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "approvals.view_approvalrule",
            "order": 2,
        },
    ]
)


@sub_section_menu.register
class ApprovalProcessSubSection:
    """My Jobs > Approval Jobs sidebar link."""

    section = "my_jobs"
    verbose_name = _("Approval Jobs")
    icon = "assets/icons/approval.svg"
    url = reverse_lazy("approvals:approval_job_view")
    app_label = "approvals"
    perm = []
    position = 2
    attrs = {
        "hx-boost": "true",
        "hx-target": "#mainContent",
        "hx-select": "#mainContent",
        "hx-swap": "outerHTML",
    }
