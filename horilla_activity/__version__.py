"""Version information for the horilla_activity module."""

from horilla.utils.translation import gettext_lazy as _

__version__ = "1.1.0"
__module_name__ = "Activity"
__release_date__ = ""
__description__ = _(
    "Module for tracking and managing activities such as tasks,calls, events, and emails."
)
__icon__ = "assets/icons/activity-red.svg"
__1_1_0__ = "Migrated from Django AppConfig to Horilla AppLauncher and replaced Django utilities with horilla.utils.decorators, horilla.utils.translation, and horilla.shortcuts where applicable."
