"""Menu registration for the Review Process module."""

# First party imports (Horilla)
from horilla.menu import sub_section_menu
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _

# First-party / Horilla apps
from horilla_processes import ProcessSettings

process = ProcessSettings()

process.items.extend(
    [
        {
            "label": _("Review Processes"),
            "url": reverse_lazy("reviews:reviews_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#review-process-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "reviews.view_reviewprocess",
            "order": 1,
        },
    ]
)


@sub_section_menu.register
class ReviewJobsSubSection:
    """My Jobs > Review Jobs sidebar link."""

    section = "my_jobs"
    verbose_name = _("Review Jobs")
    icon = "assets/icons/review.svg"
    url = reverse_lazy("reviews:review_job_view")
    app_label = "reviews"
    perm = []
    position = 1
    attrs = {
        "hx-boost": "true",
        "hx-target": "#mainContent",
        "hx-select": "#mainContent",
        "hx-swap": "outerHTML",
    }
