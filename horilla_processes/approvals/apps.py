"""
App configuration for the approvals app.
"""

# First-party / Horilla imports
from horilla.apps import AppLauncher
from horilla.utils.translation import gettext_lazy as _


class HorillaApprovalsConfig(AppLauncher):
    """
    Configuration class for the approvals app in Horilla.
    """

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_processes.approvals"
    verbose_name = _("Approvals")

    url_prefix = "approvals/"
    url_module = "horilla_processes.approvals.urls"
    url_namespace = "approvals"

    auto_import_modules = [
        "registration",
        "signals",
        "menu",
    ]
