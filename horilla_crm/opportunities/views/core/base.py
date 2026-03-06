"""Opportunity list, navbar, kanban, group-by and delete views."""

# Standard library imports
from urllib.parse import urlencode

# Third-party imports (Django)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.functional import cached_property  # type: ignore

from horilla.http import HttpResponse

# First-party / Horilla imports
from horilla.urls import reverse_lazy
from horilla.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required,
    permission_required_or_denied,
)
from horilla.utils.translation import gettext_lazy as _
from horilla_crm.opportunities.filters import OpportunityFilter
from horilla_crm.opportunities.models import Opportunity
from horilla_generics.views import (
    HorillaGroupByView,
    HorillaKanbanView,
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaView,
)


class OpportunityView(LoginRequiredMixin, HorillaView):
    """Render the opportunities page."""

    nav_url = reverse_lazy("opportunities:opportunities_nav")
    list_url = reverse_lazy("opportunities:opportunities_list")
    kanban_url = reverse_lazy("opportunities:opportunities_kanban")
    group_by_url = reverse_lazy("opportunities:opportunities_group_by")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityNavbar(LoginRequiredMixin, HorillaNavView):
    """Navigation bar view for opportunities."""

    nav_title = Opportunity._meta.verbose_name_plural
    search_url = reverse_lazy("opportunities:opportunities_list")
    main_url = reverse_lazy("opportunities:opportunities_view")
    filterset_class = OpportunityFilter
    kanban_url = reverse_lazy("opportunities:opportunities_kanban")
    group_by_url = reverse_lazy("opportunities:opportunities_group_by")
    model_name = "Opportunity"
    model_app_label = "opportunities"
    exclude_kanban_fields = "owner"
    enable_actions = True
    enable_quick_filters = True

    @cached_property
    def new_button(self):
        """Return new button configuration for opportunities."""
        if self.request.user.has_perm(
            "opportunities.add_opportunity"
        ) or self.request.user.has_perm("opportunities.add_own_opportunity"):
            return {
                "url": f"""{reverse_lazy("opportunities:opportunity_create")}?new=true""",
                "attrs": {"id": "opportunity-create"},
            }
        return None


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityListView(LoginRequiredMixin, HorillaListView):
    """
    Opportunity List view
    """

    model = Opportunity
    view_id = "opportunity-container"
    filterset_class = OpportunityFilter
    search_url = reverse_lazy("opportunities:opportunities_list")
    main_url = reverse_lazy("opportunities:opportunities_view")
    enable_quick_filters = True
    bulk_update_fields = ["owner", "opportunity_type", "lead_source"]
    header_attrs = [
        {"email": {"style": "width: 300px;"}, "title": {"style": "width: 200px;"}},
    ]

    @cached_property
    def col_attrs(self):
        """Return column attributes for opportunity list view."""
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        attrs = {
            "hx-get": f"{{get_detail_url}}?{query_string}",
            "hx-target": "#mainContent",
            "hx-swap": "outerHTML",
            "hx-push-url": "true",
            "hx-select": "#mainContent",
            "permission": "opportunities.view_opportunity",
            "own_permission": "opportunities.view_own_opportunity",
            "owner_field": "owner",
        }
        return [
            {
                "name": {
                    **attrs,
                }
            }
        ]

    def no_record_add_button(self):
        """Return add button configuration when no records exist."""
        if self.request.user.has_perm(
            "opportunities.add_opportunity"
        ) or self.request.user.has_perm("opportunities.add_own_opportunity"):
            return {
                "url": f"""{ reverse_lazy('opportunities:opportunity_create')}?new=true""",
                "attrs": 'id="opportunity-create"',
            }
        return None

    columns = [
        "name",
        "amount",
        "close_date",
        "stage",
        "opportunity_type",
        "primary_campaign_source",
    ]

    opp_permissions = {
        "permission": "opportunities.change_opportunity",
        "own_permission": "opportunities.change_own_opportunity",
        "owner_field": "owner",
    }

    actions = [
        {
            **opp_permissions,
            "action": _("Edit"),
            "src": "assets/icons/edit.svg",
            "img_class": "w-4 h-4",
            "attrs": """
                    hx-get="{get_edit_url}?new=true"
                    hx-target="#modalBox"
                    hx-swap="innerHTML"
                    onclick="openModal()"
                    """,
        },
        {
            **opp_permissions,
            "action": _("Change Owner"),
            "src": "assets/icons/a2.svg",
            "img_class": "w-4 h-4",
            "attrs": """
                    hx-get="{get_change_owner_url}?new=true"
                    hx-target="#modalBox"
                    hx-swap="innerHTML"
                    onclick="openModal()"
                    """,
        },
        {
            "action": "Delete",
            "src": "assets/icons/a4.svg",
            "img_class": "w-4 h-4",
            "permission": "opportunities.delete_opportunity",
            "own_permission": "opportunities.delete_own_opportunity",
            "owner_field": "owner",
            "attrs": """
                        hx-post="{get_delete_url}"
                        hx-target="#deleteModeBox"
                        hx-swap="innerHTML"
                        hx-trigger="click"
                        hx-vals='{{"check_dependencies": "true"}}'
                        onclick="openDeleteModeModal()"
                    """,
        },
        {
            "action": _("Duplicate"),
            "src": "assets/icons/duplicate.svg",
            "img_class": "w-4 h-4",
            "permission": "opportunities.add_opportunity",
            "own_permission": "opportunities.add_own_opportunity",
            "owner_field": "owner",
            "attrs": """
                            hx-get="{get_duplicate_url}?duplicate=true"
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            onclick="openModal()"
                            """,
        },
    ]


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("opportunities.delete_opportunity", modal=True),
    name="dispatch",
)
class OpportunityDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """View for deleting opportunities."""

    model = Opportunity

    def get_post_delete_response(self):
        """Return response after deleting opportunity."""
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityKanbanView(LoginRequiredMixin, HorillaKanbanView):
    """
    Lead Kanban view
    """

    model = Opportunity
    view_id = "opportunity-kanban"
    filterset_class = OpportunityFilter
    search_url = reverse_lazy("opportunities:opportunities_list")
    main_url = reverse_lazy("opportunities:opportunities_view")
    group_by_field = "stage"

    actions = OpportunityListView.actions

    @cached_property
    def kanban_attrs(self):
        """
        Returns attributes for kanban cards (as a dict).
        """
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")

        query_string = urlencode(query_params)
        return {
            "hx-get": f"{{get_detail_url}}?{query_string}",
            "hx-target": "#mainContent",
            "hx-swap": "outerHTML",
            "hx-push-url": "true",
            "hx-select": "#mainContent",
            "permission": "opportunities.view_opportunity",
            "own_permission": "opportunities.view_own_opportunity",
            "owner_field": "owner",
        }

    columns = [
        "name",
        "amount",
        "owner",
        "close_date",
        "expected_revenue",
    ]


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityGroupByView(LoginRequiredMixin, HorillaGroupByView):
    """
    Opportunity Group By view
    """

    model = Opportunity
    view_id = "opportunity-group-by"
    filterset_class = OpportunityFilter
    search_url = reverse_lazy("opportunities:opportunities_list")
    main_url = reverse_lazy("opportunities:opportunities_view")
    enable_quick_filters = True
    group_by_field = "stage"

    columns = [
        "name",
        "amount",
        "close_date",
        "stage",
        "opportunity_type",
        "primary_campaign_source",
    ]
    actions = OpportunityListView.actions

    @cached_property
    def col_attrs(self):
        """Return column attributes for opportunity group by view."""
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        attrs = {
            "hx-get": f"{{get_detail_url}}?{query_string}",
            "hx-target": "#mainContent",
            "hx-swap": "outerHTML",
            "hx-push-url": "true",
            "hx-select": "#mainContent",
            "permission": "opportunities.view_opportunity",
            "own_permission": "opportunities.view_own_opportunity",
            "owner_field": "owner",
        }
        return [
            {
                "name": {
                    **attrs,
                }
            }
        ]
