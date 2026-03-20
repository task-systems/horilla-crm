"""
AppLauncher for the horilla_theme app
"""

# First party imports (Horilla)
from horilla.apps import AppLauncher
from horilla.utils.translation import gettext_lazy as _


class HorillaThemeConfig(AppLauncher):
    """App configuration class for horilla_theme."""

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_theme"
    verbose_name = _("Theme Manager")

    auto_import_modules = [
        "menu",
        "signals",
        "registration",
    ]

    url_prefix = "theme/"
    url_module = "horilla_theme.urls"
