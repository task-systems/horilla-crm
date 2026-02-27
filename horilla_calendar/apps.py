"""Configuration for the calendar app in Horilla."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HorillaCalendarConfig(AppConfig):
    """Configuration class for the Horilla Calendar app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_calendar"
    verbose_name = _("Calendar")

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "/calendar/",
                "view_or_include": "horilla_calendar.api.urls",
                "name": "horilla_calendar_api",
                "namespace": "horilla_calendar",
            }
        ]

    def ready(self):
        """Register calendar URLs and load menu/signals; defer to parent ready()."""
        try:
            # Auto-register this app's URLs and add to installed apps
            from django.urls import include, path

            from horilla.urls import urlpatterns

            # Add app URLs to main urlpatterns
            urlpatterns.append(
                path("calendar/", include("horilla_calendar.urls")),
            )

            __import__("horilla_calendar.menu")  # noqa: F401
            __import__("horilla_calendar.signals")  # noqa:F401
        except ImportError:
            # Handle errors silently to prevent app load failure
            pass

        super().ready()
