"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the horilla_theme app
"""

from horilla.menu import settings_menu

# First party imports (Horilla)
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _

# First-party / Horilla apps
from horilla_theme.apps import HorillaThemeConfig
from horilla_theme.models import HorillaColorTheme

# Define your menu registration logic here


@settings_menu.register
class ThemeSettings:
    """Settings menu for Theme settings module"""

    title = HorillaThemeConfig.verbose_name
    icon = "horilla_theme/assets/icons/theme.svg"
    order = 7
    items = [
        {
            "label": HorillaColorTheme()._meta.verbose_name,
            "url": reverse_lazy("horilla_theme:color_theme_view"),
            "hx-push-url": "true",
            "hx-target": "#settings-content",
            "hx-select": "#theme-view",
            "hx-select-oob": "#settings-sidebar",
        },
    ]
