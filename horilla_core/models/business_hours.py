"""
This module defines the BusinessHour for managing business hours in the Horilla CRM application.
"""

# Standard library imports
import logging

# Third-party imports
from datetime import time

# Django imports
from django.utils.formats import time_format
from django.utils.html import format_html, format_html_join
from multiselectfield import MultiSelectField

# First-party / Horilla imports
from horilla.db import models
from horilla.urls import reverse_lazy
from horilla.utils.choices import DAY_CHOICES, TIMEZONE_CHOICES
from horilla.utils.translation import gettext_lazy as _

from .base import HorillaCoreModel

logger = logging.getLogger(__name__)


class BusinessHourDayMixin(models.Model):
    """
    Model to add start and end time fields for each day of the week.
    """

    monday_start = models.TimeField(
        null=True, blank=True, verbose_name=_("Monday Start Time")
    )
    monday_end = models.TimeField(
        null=True, blank=True, verbose_name=_("Monday End Time")
    )

    tuesday_start = models.TimeField(
        null=True, blank=True, verbose_name=_("Tuesday Start Time")
    )
    tuesday_end = models.TimeField(
        null=True, blank=True, verbose_name=_("Tuesday End Time")
    )

    wednesday_start = models.TimeField(
        null=True, blank=True, verbose_name=_("Wednesday Start Time")
    )
    wednesday_end = models.TimeField(
        null=True, blank=True, verbose_name=_("Wednesday End Time")
    )

    thursday_start = models.TimeField(
        null=True, blank=True, verbose_name=_("Thursday Start Time")
    )
    thursday_end = models.TimeField(
        null=True, blank=True, verbose_name=_("Thursday End Time")
    )

    friday_start = models.TimeField(
        null=True, blank=True, verbose_name=_("Friday Start Time")
    )
    friday_end = models.TimeField(
        null=True, blank=True, verbose_name=_("Friday End Time")
    )

    saturday_start = models.TimeField(
        null=True, blank=True, verbose_name=_("Saturday Start Time")
    )
    saturday_end = models.TimeField(
        null=True, blank=True, verbose_name=_("Saturday End Time")
    )

    sunday_start = models.TimeField(
        null=True, blank=True, verbose_name=_("Sunday Start Time")
    )
    sunday_end = models.TimeField(
        null=True, blank=True, verbose_name=_("Sunday End Time")
    )

    class Meta:
        """
        Abstract model for business hour day model.
        """

        abstract = True


class BusinessHour(BusinessHourDayMixin, HorillaCoreModel):
    """
    Model to handle business hours with support for:
    - 24/7 operations
    - Weekdays only (Mon-Fri)
    - Custom hours with different times per day
    """

    BUSINESS_HOUR_TYPES = [
        ("24_7", _("24 Hours x 7 days")),
        ("24_5", _("24 Hours x 5 days")),
        ("custom", _("Custom Hours")),
    ]

    TIMING_CHOICES = [
        ("same", _("Same Hour Every Day")),
        ("different", _("Different Hour Per Day")),
    ]

    DAY_LABELS = {
        "mon": _("Monday"),
        "tue": _("Tuesday"),
        "wed": _("Wednesday"),
        "thu": _("Thursday"),
        "fri": _("Friday"),
        "sat": _("Saturday"),
        "sun": _("Sunday"),
    }

    WEEK_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

    # Basic Information
    name = models.CharField(
        max_length=255, help_text=_("Business Hour Name"), verbose_name=_("Name")
    )
    time_zone = models.CharField(
        max_length=100,
        choices=TIMEZONE_CHOICES,
        default="UTC",
        verbose_name=_("Time Zone"),
    )

    # Business Hour Type
    business_hour_type = models.CharField(
        max_length=10,
        choices=BUSINESS_HOUR_TYPES,
        default="24_7",
        help_text=_("Type of business hours"),
        verbose_name=_("Business Hour Type"),
    )

    # Week Configuration
    week_start_day = models.CharField(
        max_length=10,
        choices=DAY_CHOICES,
        default="monday",
        help_text=_("Week Start Day"),
        verbose_name=_("Week Start Day"),
    )
    week_days = MultiSelectField(choices=DAY_CHOICES, blank=True)

    # Timing Configuration (for custom hours)
    timing_type = models.CharField(
        max_length=10,
        choices=TIMING_CHOICES,
        default="same",
        blank=True,
        null=True,
        help_text=_("Same hours every day or different hours per day"),
        verbose_name=_("Timing Type"),
    )

    # For "Same Hour Every Day"
    default_start_time = models.TimeField(
        null=True,
        blank=True,
        help_text=_("Default start time"),
        verbose_name=_("Default Start Time"),
    )
    default_end_time = models.TimeField(
        null=True,
        blank=True,
        help_text=_("Default end time"),
        verbose_name=_("Default End Time"),
    )

    # Status
    is_default = models.BooleanField(
        default=False,
        help_text=_("Default Business Hour"),
        verbose_name=_("Is Default"),
    )

    class Meta:
        """
        Meta options for the BusinessHour model.
        """

        verbose_name = _("Business Hour")
        verbose_name_plural = _("Business Hours")
        ordering = ["-is_default", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_business_hour_type_display()})"

    def save(self, *args, **kwargs):
        if self.is_default:
            BusinessHour.objects.filter(is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)

    def get_active_days(self):
        """
        Returns a list of days with defined business hours.
        """
        days = []
        for day in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]:
            if getattr(self, f"{day}_start") or getattr(self, f"{day}_24hr"):
                days.append(day.capitalize())
        return days

    def get_avatar(self):
        """
        Method will retun the api to the avatar or path to the profile image
        """
        url = f"https://ui-avatars.com/api/?name={self.name}&background=random"
        return url

    def get_edit_url(self):
        """
        Get the URL for editing the business hour
        """
        return reverse_lazy(
            "horilla_core:business_hour_update_form", kwargs={"pk": self.pk}
        )

    def is_default_hour(self):
        """
        Return Yes/No for default business hour
        """
        return "Yes" if self.is_default else "No"

    def get_delete_url(self):
        """
        Get the URL for deleting the business hour
        """
        return reverse_lazy(
            "horilla_core:business_hour_delete_view", kwargs={"pk": self.pk}
        )

    def get_detail_url(self):
        """
        Get the URL for business hour detail view
        """
        return reverse_lazy(
            "horilla_core:business_hour_detail_view", kwargs={"pk": self.pk}
        )

    def get_formatted_week_days(self):
        """
        Returns a formatted HTML representation of the business hours.
        """

        def format_time_value(value):
            if not value:
                return "--:--"
            return time_format(value, "P")

        # Normalize selected weekdays
        raw_week_days = self.week_days
        if isinstance(raw_week_days, (list, tuple)):
            selected = list(raw_week_days)
        elif isinstance(raw_week_days, str) and raw_week_days.strip():
            selected = [
                p.strip() for p in raw_week_days.replace(",", " ").split() if p.strip()
            ]
        else:
            selected = []

        # 24 / 7
        if self.business_hour_type == "24_7":
            return format_html(
                "{}<br><strong>(24 Hours)</strong>",
                "Monday - Sunday",
            )

        # 24 / 5
        if self.business_hour_type == "24_5":
            selected_set = set(selected) if selected else set(self.WEEK_ORDER[:5])

            selected_labels = [
                self.DAY_LABELS[d] for d in self.WEEK_ORDER if d in selected_set
            ]
            # Resolve lazy translations to strings so format_html renders them correctly
            labels_text = ", ".join(str(label) for label in selected_labels)

            if selected_set == set(self.WEEK_ORDER[:5]):
                return format_html(
                    "<span style='white-space: nowrap;'>{}<span style='font-weight:bold;'> (24 Hours)</span></span>",
                    labels_text,
                )

            if selected_set == set(self.WEEK_ORDER):
                return format_html(
                    "<span style='white-space: nowrap;'>"
                    "Monday – Sunday"
                    "<span style='font-weight:bold;'> (24 Hours)</span>"
                    "</span>"
                )

            return format_html(
                "<span style='white-space: nowrap;'>{}<span style='font-weight:bold;'> (24 Hours)</span></span>",
                labels_text,
            )

        # CUSTOM
        if self.business_hour_type == "custom":

            # Same timing for all days
            if self.timing_type == "same":
                start = format_time_value(self.default_start_time)
                end = format_time_value(self.default_end_time)

                labels = [self.DAY_LABELS[d] for d in self.WEEK_ORDER if d in selected]

                if labels == [self.DAY_LABELS[d] for d in self.WEEK_ORDER[:5]]:
                    return format_html(
                        "Monday - Friday<br><strong>({} – {})</strong>",
                        start,
                        end,
                    )

                if labels == [self.DAY_LABELS[d] for d in self.WEEK_ORDER]:
                    return format_html(
                        "Monday - Sunday<br><strong>({} – {})</strong>",
                        start,
                        end,
                    )

                if labels:
                    return format_html(
                        "{}<br><strong>({} – {})</strong>",
                        ", ".join(labels),
                        start,
                        end,
                    )

                return format_html("{} – {}", start, end)

            # Different timing per day
            if self.timing_type == "different":

                def is_midnight(t):
                    return t is None or t == time(0, 0)

                rows = []

                for day_code in self.WEEK_ORDER:
                    day_label = self.DAY_LABELS[day_code]
                    is_open = day_code in selected
                    prefix = day_label.lower()

                    if is_open:
                        start_val = getattr(self, f"{prefix}_start", None)
                        end_val = getattr(self, f"{prefix}_end", None)

                        if is_midnight(start_val) and is_midnight(end_val):
                            time_range = "Closed"
                        else:
                            time_range = "{} – {}".format(
                                format_time_value(start_val),
                                format_time_value(end_val),
                            )
                    else:
                        time_range = "Closed"

                    rows.append((day_label, time_range))

                return format_html(
                    "<table class='text-left align-top space-y-1'>{}</table>",
                    format_html_join(
                        "",
                        "<tr class='text-sm'>"
                        "<td class='pr-4 text-gray-600 whitespace-nowrap w-24 mb-5'>{}</td>"
                        "<td class='font-semibold text-black whitespace-nowrap'>{}</td>"
                        "</tr>",
                        rows,
                    ),
                )

        return format_html("—")
