"""Views for opportunities module."""

# Standard library imports
from urllib.parse import urlencode

# Third-party imports (Django)
from django.apps import apps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ForeignKey
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property  # type: ignore
from django.utils.translation import gettext_lazy as _
from django.views import View

# First-party / Horilla imports
from horilla.utils.shortcuts import get_object_or_404
from horilla_activity.views import HorillaActivitySectionView
from horilla_core.decorators import (
    htmx_required,
    permission_required,
    permission_required_or_denied,
)
from horilla_core.utils import is_owner
from horilla_crm.contacts.models import ContactAccountRelationship
from horilla_crm.opportunities.filters import OpportunityFilter
from horilla_crm.opportunities.forms import OpportunityFormClass, OpportunitySingleForm
from horilla_crm.opportunities.models import (
    Opportunity,
    OpportunityContactRole,
    OpportunitySettings,
    OpportunityStage,
)
from horilla_crm.opportunities.signals import set_opportunity_contact_id
from horilla_generics.mixins import RecentlyViewedMixin
from horilla_generics.views import (
    HorillaDetailSectionView,
    HorillaDetailTabView,
    HorillaDetailView,
    HorillaHistorySectionView,
    HorillaKanbanView,
    HorillaListView,
    HorillaMultiStepFormView,
    HorillaNavView,
    HorillaNotesAttachementSectionView,
    HorillaRelatedListSectionView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla_utils.middlewares import _thread_local


class OpportunityView(LoginRequiredMixin, HorillaView):
    """Render the opportunities page."""

    nav_url = reverse_lazy("opportunities:opportunities_nav")
    list_url = reverse_lazy("opportunities:opportunities_list")
    kanban_url = reverse_lazy("opportunities:opportunities_kanban")


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
class OpportunityMultiStepFormView(LoginRequiredMixin, HorillaMultiStepFormView):
    """Multi-step form view for creating and editing opportunities."""

    form_class = OpportunityFormClass
    model = Opportunity
    total_steps = 3
    fullwidth_fields = ["description"]
    dynamic_create_fields = ["stage"]
    detail_url_name = "opportunities:opportunity_detail_view"
    dynamic_create_field_mapping = {
        "stage": {
            "fields": ["name", "order", "probability", "stage_type", "is_final"],
            "initial": {
                "order": OpportunityStage.get_next_order_for_company,
            },
        },
    }

    single_step_url_name = {
        "create": "opportunities:opportunity_single_create",
        "edit": "opportunities:opportunity_single_edit",
    }

    @cached_property
    def form_url(self):
        """Return form URL for create or update view."""
        pk = self.kwargs.get("pk")
        if pk:
            return reverse_lazy("opportunities:opportunity_edit", kwargs={"pk": pk})
        return reverse_lazy("opportunities:opportunity_create")

    step_titles = {
        "1": _("Opportunity Information"),
        "2": _("Additional Information"),
        "3": _("Description"),
    }

    def get_initial(self):
        """Get initial form data with account ID if provided."""
        initial = super().get_initial()
        account_id = self.request.GET.get("id")
        initial["account"] = account_id
        return initial


@method_decorator(htmx_required, name="dispatch")
class OpportunitySingleFormView(LoginRequiredMixin, HorillaSingleFormView):
    """opportunity Create/Update Single Page View"""

    model = Opportunity
    form_class = OpportunitySingleForm
    full_width_fields = ["description"]
    dynamic_create_fields = ["stage"]
    detail_url_name = "opportunities:opportunity_detail_view"
    dynamic_create_field_mapping = {
        "stage": {
            "fields": ["name", "order", "probability", "stage_type", "is_final"],
            "initial": {
                "order": OpportunityStage.get_next_order_for_company,
            },
        },
    }

    multi_step_url_name = {
        "create": "opportunities:opportunity_create",
        "edit": "opportunities:opportunity_edit",
    }

    @cached_property
    def form_url(self):
        """Form URL for lead"""
        pk = self.kwargs.get("pk")
        if pk:
            return reverse_lazy(
                "opportunities:opportunity_single_edit", kwargs={"pk": pk}
            )
        return reverse_lazy("opportunities:opportunity_single_create")

    def get_initial(self):
        """Get initial form data with account ID from query parameters."""
        initial = super().get_initial()
        account_id = self.request.GET.get("id")
        initial["account"] = account_id
        return initial


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("opportunities.add_opportunity"), name="dispatch"
)
class RelatedOpportunityFormView(LoginRequiredMixin, HorillaMultiStepFormView):
    """Multi-step form view for creating opportunities related to contacts."""

    form_class = OpportunityFormClass
    model = Opportunity
    total_steps = 3
    fullwidth_fields = ["description"]
    dynamic_create_fields = ["stage"]
    save_and_new = False
    dynamic_create_field_mapping = {
        "stage": {"full_width_fields": ["description"]},
    }

    @cached_property
    def form_url(self):
        """Return form URL for create or update view."""
        pk = self.kwargs.get("pk")
        if pk:
            return reverse_lazy("opportunities:opportunity_edit", kwargs={"pk": pk})
        return reverse_lazy("opportunities:opportunity_create")

    step_titles = {
        "1": _("Opportunity Information"),
        "2": _("Additional Information"),
        "3": _("Description"),
    }

    def get_initial(self):
        """Get initial form data with contact ID if provided."""
        initial = super().get_initial()
        contact_id = self.request.GET.get("id")

        if contact_id:
            Contact = apps.get_model("contacts", "Contact")
            contact = Contact.objects.filter(pk=contact_id).first()
            if contact:
                rel = contact.account_relationships.first()
                account_id = rel.account.pk if rel else None
        initial["account"] = account_id
        return initial

    def form_valid(self, form):
        step = self.get_initial_step()

        if step == self.total_steps:
            contact_id = self.request.GET.get("id")
            if contact_id:
                set_opportunity_contact_id(
                    contact_id=contact_id, company=self.request.active_company
                )
            super().form_valid(form)
            return HttpResponse(
                "<script>htmx.trigger('#tab-opportunities-btn','click');closeModal();</script>"
            )

        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        opportunity_id = self.kwargs.get("pk")
        if request.user.has_perm(
            "opportunities.change_opportunity"
        ) or request.user.has_perm("opportunities.add_opportunity"):
            return super().get(request, *args, **kwargs)

        if opportunity_id:
            opportunity = get_object_or_404(Opportunity, pk=opportunity_id)
            if opportunity.owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")


@method_decorator(htmx_required, name="dispatch")
class OpportunityChangeOwnerForm(LoginRequiredMixin, HorillaSingleFormView):
    """Form view for changing opportunity owner."""

    model = Opportunity
    fields = ["owner"]
    full_width_fields = ["owner"]
    modal_height = False
    form_title = _("Change Owner")

    @cached_property
    def form_url(self):
        """Return form URL for change owner view."""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "opportunities:opportunity_change_owner", kwargs={"pk": pk}
            )
        return None

    def get(self, request, *args, **kwargs):
        opportunity_id = self.kwargs.get("pk")
        if request.user.has_perm(
            "opportunities.change_opportunity"
        ) or request.user.has_perm("opportunities.add_opportunity"):
            return super().get(request, *args, **kwargs)

        if opportunity_id:
            opportunity = get_object_or_404(Opportunity, pk=opportunity_id)
            if opportunity.owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")


@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityDetailView(RecentlyViewedMixin, LoginRequiredMixin, HorillaDetailView):
    """Detail view for opportunities."""

    model = Opportunity
    pipeline_field = "stage"
    tab_url = reverse_lazy("opportunities:opportunity_detail_view_tabs")
    actions = OpportunityListView.actions
    breadcrumbs = [
        ("Sales", "leads:leads_view"),
        ("Opportunites", "opportunities:opportunities_view"),
    ]

    body = [
        "name",
        "amount",
        "expected_revenue",
        "quantity",
        "close_date",
        "probability",
        "forecast_category",
    ]

    def get_badges(self):
        """Get badges for opportunity detail view based on stage type."""
        badges = []
        obj = self.get_object()

        if obj.stage and hasattr(obj.stage, "stage_type"):
            stage_type = obj.stage.stage_type
            if stage_type == "won":
                badges.append(
                    {
                        "label": _("Closed Won"),
                        "class": "bg-green-600",
                        "icon": "fa-solid fa-check",
                        "icon_class": "text-green-600",
                        "icon_bg_class": "bg-green-100",
                    }
                )
            elif stage_type == "lost":
                badges.append(
                    {
                        "label": _("Closed Lost"),
                        "class": "bg-red-600",
                        "icon": "fa-solid fa-times",
                        "icon_class": "text-red-600",
                        "icon_bg_class": "bg-red-100",
                    }
                )

        return badges

    def get_pipeline_choices(self):
        """
        Override to group Closed Won and Closed Lost into a single "Closed" option.
        """
        if not self.pipeline_field:
            return []
        try:
            obj = self.get_object()
        except Http404:
            return []

        field = self.model._meta.get_field(self.pipeline_field)
        current_value = getattr(obj, self.pipeline_field)

        pipeline = []

        if isinstance(field, ForeignKey):
            related_model = field.related_model
            order_field = None
            try:
                order_field = related_model._meta.get_field("order")
            except Exception:
                pass
            queryset = related_model.objects.all()

            if (
                hasattr(related_model, "company")
                and hasattr(obj, "company")
                and obj.company
            ):
                queryset = queryset.filter(company=obj.company)

            if order_field:
                queryset = queryset.order_by("order")

            current_order = (
                getattr(current_value, "order", None) if current_value else None
            )
            current_id = current_value.id if current_value else None
            current_stage_type = (
                getattr(current_value, "stage_type", None) if current_value else None
            )

            closed_won_stage = None
            closed_lost_stage = None
            closed_stage_order = None
            is_current_closed = False
            is_closed_lost = current_stage_type == "lost"

            for related_obj in queryset:
                stage_type = getattr(related_obj, "stage_type", None)

                # Collect closed stages
                if stage_type == "won":
                    closed_won_stage = related_obj
                    if related_obj.id == current_id:
                        is_current_closed = True
                        closed_stage_order = getattr(related_obj, "order", None)
                elif stage_type == "lost":
                    closed_lost_stage = related_obj
                    if related_obj.id == current_id:
                        is_current_closed = True
                        closed_stage_order = getattr(related_obj, "order", None)
                else:
                    # Regular open stages
                    is_completed = False
                    is_current = related_obj.id == current_id
                    is_final = getattr(related_obj, "is_final", False)

                    # If current stage is "Closed Lost", don't mark other stages as completed
                    # They should appear gray/ash instead of green
                    if not is_closed_lost and current_order is not None:
                        related_order = getattr(related_obj, "order", None)
                        is_completed = (
                            related_order is not None and related_order < current_order
                        )

                    pipeline.append(
                        (
                            str(related_obj),
                            related_obj.id,
                            is_completed,
                            is_current,
                            is_final,
                            False,  # Not closed won
                        )
                    )

            # Add "Closed" as a single option if closed stages exist
            if closed_won_stage or closed_lost_stage:
                # Determine if closed is completed (if current stage is after closed stages)
                is_closed_completed = False
                if current_order is not None and closed_stage_order is not None:
                    is_closed_completed = closed_stage_order < current_order
                elif (
                    current_stage_type not in ["won", "lost"]
                    and current_order is not None
                ):
                    # If we have a closed stage order, check if current is after it
                    if closed_won_stage:
                        closed_order = getattr(closed_won_stage, "order", None)
                        if closed_order and current_order > closed_order:
                            is_closed_completed = True
                    elif closed_lost_stage:
                        closed_order = getattr(closed_lost_stage, "order", None)
                        if closed_order and current_order > closed_order:
                            is_closed_completed = True

                # If current stage is closed, show the actual stage name
                if is_current_closed and current_value:
                    # Check if it's closed (won or lost) - both need custom styling
                    is_closed = current_stage_type in ["won", "lost"]
                    # Show the actual closed stage name
                    pipeline.append(
                        (
                            str(
                                current_value
                            ),  # Show actual stage name (e.g., "Closed Won" or "Closed Lost")
                            current_value.id,
                            is_closed_completed,
                            True,  # This is the current stage
                            True,  # Mark as final stage
                            is_closed,  # Flag to indicate if it's closed (won or lost) for custom styling
                        )
                    )
                else:
                    # Show "Closed" option that opens the selection modal
                    pipeline.append(
                        (
                            _("Closed"),
                            "closed",  # Special identifier for closed stage
                            is_closed_completed,
                            False,  # Not current if we're showing "Closed"
                            True,  # Mark as final stage
                            False,  # Not closed won
                        )
                    )
        else:
            return []

        return pipeline

    @cached_property
    def final_stage_action(self):
        """Final stage action for opportunity - opens closed stage selection modal."""
        return {
            "hx-get": reverse_lazy(
                "opportunities:select_closed_stage", kwargs={"pk": self.object.pk}
            ),
            "hx-target": "#modalBox",
            "hx-swap": "innerHTML",
            "onclick": "openModal()",
        }

    def get_pipeline_custom_colors(self):
        """
        Get custom colors for pipeline stages.
        Returns a dict with bg_color, text_color, and hover_color (optional).
        If None, default colors will be used.
        """
        obj = self.get_object()
        if obj.stage and hasattr(obj.stage, "stage_type"):
            stage_type = obj.stage.stage_type
            if stage_type == "won":
                return {
                    "bg_color": "bg-green-600",
                    "text_color": "text-white",
                    "hover_color": None,  # No hover for closed won
                }
            elif stage_type == "lost":
                return {
                    "bg_color": "bg-red-600",
                    "text_color": "text-white",
                    "hover_color": None,  # No hover for closed lost
                }
        return None


@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityDetailViewTabView(LoginRequiredMixin, HorillaDetailTabView):
    """Detail view tab view for opportunities."""

    def __init__(self, **kwargs):
        request = getattr(_thread_local, "request", None)
        self.request = request
        self.object_id = self.request.GET.get("object_id")
        super().__init__(**kwargs)

    urls = {
        "details": "opportunities:opportunity_details_tab",
        "activity": "opportunities:opportunity_activity_detail_view",
        "related_lists": "opportunities:opportunity_related_lists",
        "notes_attachments": "opportunities:opportunity_notes_attachments",
        "history": "opportunities:opportunity_history_tab_view",
    }


@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityDetailTab(LoginRequiredMixin, HorillaDetailSectionView):
    """Detail tab view for opportunities."""

    model = Opportunity
    non_editable_fields = ["expected_revenue"]
    excluded_fields = [
        "id",
        "created_at",
        "additional_info",
        "updated_at",
        "history",
        "is_active",
        "created_by",
        "updated_by",
        "company",
        "forecast_category",
    ]


@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityActivityTabView(LoginRequiredMixin, HorillaActivitySectionView):
    """
    Activity Tab View
    """

    model = Opportunity


@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunitiesNotesAndAttachments(
    LoginRequiredMixin, HorillaNotesAttachementSectionView
):
    """Notes and attachments section view for opportunities."""

    model = Opportunity


@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityHistoryTabView(LoginRequiredMixin, HorillaHistorySectionView):
    """
    History Tab View
    """

    model = Opportunity


@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityRelatedLists(LoginRequiredMixin, HorillaRelatedListSectionView):
    """Related lists section view for opportunities."""

    model = Opportunity

    @cached_property
    def related_list_config(self):
        """Return related list configuration for opportunities."""
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        pk = self.request.GET.get("object_id")
        referrer_url = "opportunity_detail_view"
        contact_col_attrs = [
            {
                "first_name": {
                    "permission": "contacts.view_contact",
                    "own_permission": "contacts.view_own_contact",
                    "owner_field": "contact_owner",
                    "hx-get": f"{{get_detail_url}}?referrer_app={self.model._meta.app_label}&referrer_model={self.model._meta.model_name}&referrer_id={pk}&referrer_url={referrer_url}&{query_string}",
                    "hx-target": "#mainContent",
                    "hx-swap": "outerHTML",
                    "hx-push-url": "true",
                    "hx-select": "#mainContent",
                }
            }
        ]
        config = {
            "custom_related_lists": {
                "contact": {
                    "app_label": "contacts",
                    "model_name": "Contact",
                    "intermediate_model": "OpportunityContactRole",
                    "intermediate_field": "contact",
                    "related_field": "opportunity",
                    "config": {
                        "title": _("Contact Roles"),
                        "columns": [
                            (
                                self.model._meta.get_field("contact_roles")
                                .related_model._meta.get_field("contact")
                                .related_model._meta.get_field("first_name")
                                .verbose_name,
                                "first_name",
                            ),
                            (
                                self.model._meta.get_field("contact_roles")
                                .related_model._meta.get_field("contact")
                                .related_model._meta.get_field("last_name")
                                .verbose_name,
                                "last_name",
                            ),
                            (
                                self.model._meta.get_field("contact_roles")
                                .related_model._meta.get_field("role")
                                .verbose_name,
                                "opportunity_roles__role",
                            ),
                            (
                                self.model._meta.get_field("contact_roles")
                                .related_model._meta.get_field("is_primary")
                                .verbose_name,
                                "opportunity_roles__is_primary",
                            ),
                        ],
                        "can_add": self.request.user.has_perm(
                            "opportunities.add_opportunitycontactrole"
                        )
                        and (
                            (
                                is_owner(Opportunity, pk)
                                and self.request.user.has_perm(
                                    "opportunities.change_own_opportunity"
                                )
                            )
                            or self.request.user.has_perm(
                                "opportunities.change_opportunity"
                            )
                        ),
                        "add_url": reverse_lazy(
                            "opportunities:add_opportunity_contact_role"
                        ),
                        "actions": [
                            {
                                "action": "edit",
                                "src": "/assets/icons/edit.svg",
                                "img_class": "w-4 h-4",
                                "permission": "opportunities.change_opportunitycontactrole",
                                "own_permission": "opportunities.change_own_opportunitycontactrole",
                                "owner_field": "created_by",
                                "intermediate_model": "OpportunityContactRole",
                                "intermediate_field": "contact",
                                "parent_field": "opportunity",
                                "attrs": """
                                    hx-get="{get_opportunity_contact_role_edit_url}"
                                    hx-target="#modalBox"
                                    hx-swap="innerHTML"
                                    onclick="event.stopPropagation();openModal()"
                                    hx-indicator="#modalBox"
                                    """,
                            },
                            {
                                "action": "Delete",
                                "src": "assets/icons/a4.svg",
                                "img_class": "w-4 h-4",
                                "permission": "opportunities.delete_opportunitycontactrole",
                                "attrs": """
                                        hx-post="{get_opportunity_contact_role_delete_url}"
                                        hx-target="#deleteModeBox"
                                        hx-swap="innerHTML"
                                        hx-trigger="click"
                                        hx-vals='{{"check_dependencies": "true"}}'
                                        onclick="openDeleteModeModal()"
                                        """,
                            },
                        ],
                        "col_attrs": contact_col_attrs,
                    },
                },
            },
        }
        add_perm = (
            is_owner(Opportunity, pk)
            and self.request.user.has_perm("opportunities.change_own_opportunity")
        ) or self.request.user.has_perm("opportunities.change_opportunity")
        if OpportunitySettings.is_team_selling_enabled():
            custom_buttons = []
            if (
                self.request.user.has_perm("opportunities.add_opportunityteammember")
                and add_perm
            ):
                custom_buttons.extend(
                    [
                        {
                            "label": _("Add Team"),
                            "url": reverse_lazy("opportunities:add_default_team"),
                            "attrs": """
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            onclick="openModal()"
                            hx-indicator="#modalBox"
                        """,
                            "icon": "fa-solid fa-users",
                            "class": "text-xs px-4 py-1.5 bg-primary-600 rounded-md hover:bg-primary-800 transition duration-300 text-white",
                        },
                        {
                            "label": _("Add Members"),
                            "url": reverse_lazy("opportunities:add_opportunity_member"),
                            "attrs": """
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            onclick="openModal()"
                            hx-indicator="#modalBox"
                        """,
                            "icon": "fa-solid fa-user-plus",
                            "class": "text-xs px-4 py-1.5 bg-white border border-primary-600 text-primary-600 rounded-md hover:bg-primary-50 transition duration-300",
                        },
                    ]
                )
            config["opportunity_team_members"] = {
                "title": "Opportunity Team",
                "columns": [
                    (
                        self.model._meta.get_field("opportunity_team_members")
                        .related_model._meta.get_field("user")
                        .verbose_name,
                        "user",
                    ),
                    (
                        self.model._meta.get_field("opportunity_team_members")
                        .related_model._meta.get_field("team_role")
                        .verbose_name,
                        "get_team_role_display",
                    ),
                ],
                "can_add": False,
                "custom_buttons": custom_buttons,
                "actions": [
                    {
                        "action": "Edit",
                        "src": "/assets/icons/edit.svg",
                        "img_class": "w-4 h-4",
                        "permission": "opportunities.change_opportunityteammember",
                        "attrs": """
                                    hx-get="{get_edit_url}"
                                    hx-target="#modalBox"
                                    hx-swap="innerHTML"
                                    onclick="event.stopPropagation();openModal()"
                                    hx-indicator="#modalBox"
                                    """,
                    },
                    {
                        "action": "Delete",
                        "src": "/assets/icons/a4.svg",
                        "img_class": "w-4 h-4",
                        "permission": "opportunities.delete_opportunityteammember",
                        "attrs": """
                                    hx-post="{get_delete_url}"
                                    hx-target="#deleteModeBox"
                                    hx-swap="innerHTML"
                                    hx-trigger="click"
                                    hx-vals='{{"check_dependencies": "true"}}'
                                    onclick="openDeleteModeModal()"
                                    """,
                    },
                ],
            }
            if OpportunitySettings.is_split_enabled():
                splits_custom_buttons = []
                if (
                    self.request.user.has_perm("opportunities.add_opportunitysplit")
                    and add_perm
                ):
                    splits_custom_buttons.append(
                        {
                            "label": _("Manage Opportunity Splits"),
                            "url": reverse_lazy(
                                "opportunities:manage_opportunity_splits"
                            ),
                            "attrs": """
                            hx-target="#contentModalBox"
                            hx-swap="innerHTML"
                            onclick="openContentModal()"
                        """,
                            "class": "text-xs px-4 py-1.5 bg-primary-600 rounded-md hover:bg-primary-800 transition duration-300 text-white",
                        }
                    )
                config["splits"] = {
                    "title": _("Opportunity Splits"),
                    "columns": [
                        (
                            self.model._meta.get_field("splits")
                            .related_model._meta.get_field("user")
                            .verbose_name,
                            "user",
                        ),
                        (
                            self.model._meta.get_field("splits")
                            .related_model._meta.get_field("split_type")
                            .verbose_name,
                            "split_type",
                        ),
                        (
                            self.model._meta.get_field("splits")
                            .related_model._meta.get_field("split_percentage")
                            .verbose_name,
                            "split_percentage",
                        ),
                        (
                            self.model._meta.get_field("splits")
                            .related_model._meta.get_field("split_amount")
                            .verbose_name,
                            "split_amount",
                        ),
                    ],
                    "can_add": False,
                    "custom_buttons": splits_custom_buttons,
                }
                if self.request.user.has_perm("opportunities.delete_opportunitysplit"):
                    config["splits"]["action_method"] = "actions"

        return config

    def get_excluded_related_lists(self):
        """
        Dynamically determine which related lists to exclude based on settings
        """
        excluded = ["contact_roles"]

        # If Team Selling is DISABLED, exclude opportunity_team_members from showing
        if not OpportunitySettings.is_team_selling_enabled():
            excluded.append("opportunity_team_members")
        if not OpportunitySettings.is_split_enabled():
            excluded.append("splits")

        return excluded

    @property
    def excluded_related_lists(self):
        """Property wrapper for excluded_related_lists."""
        return self.get_excluded_related_lists()

    @excluded_related_lists.setter
    def excluded_related_lists(self, value):
        """Setter to allow parent view to set the value (but we ignore it)"""
        # We ignore the setter since we calculate dynamically
        pass


@method_decorator(htmx_required, name="dispatch")
class OpportunityContactRoleFormview(LoginRequiredMixin, HorillaSingleFormView):
    """Form view for creating and editing opportunity contact roles."""

    model = OpportunityContactRole
    fields = ["is_primary", "role", "contact", "opportunity"]
    full_width_fields = ["is_primary", "role", "contact"]
    modal_height = False
    form_title = _("Add Contact Role")
    hidden_fields = ["opportunity"]
    save_and_new = False

    def form_valid(self, form):
        """Handle form validation and create contact-account relationship."""
        super().form_valid(form)
        opportunity_contact_role = form.instance
        contact = opportunity_contact_role.contact
        opportunity = opportunity_contact_role.opportunity
        role = opportunity_contact_role.role

        # Automatically create related ContactAccountRelationship
        if opportunity.account:
            ContactAccountRelationship.objects.get_or_create(
                contact=contact,
                account=opportunity.account,
                defaults={"role": role},
                company=self.request.active_company,
            )

        return HttpResponse(
            "<script>htmx.trigger('#tab-contact-btn', 'click');closeModal();</script>"
        )

    def get_initial(self):
        """Get initial form data with opportunity ID if provided."""
        initial = super().get_initial()
        obj_id = self.request.GET.get("id")
        if obj_id:
            initial["opportunity"] = obj_id
        return initial

    @cached_property
    def form_url(self):
        """Return form URL for create or update view."""
        if self.kwargs.get("pk"):
            return reverse_lazy(
                "opportunities:edit_opportunity_contact_role",
                kwargs={"pk": self.kwargs.get("pk")},
            )
        return reverse_lazy("opportunities:add_opportunity_contact_role")

    def get(self, request, *args, **kwargs):

        opportunity_id = request.GET.get("id")
        if request.user.has_perm(
            "opportunities.change_opportunitycontactrole"
        ) or request.user.has_perm("opportunities.add_opportunitycontactrole"):
            return super().get(request, *args, **kwargs)

        if opportunity_id:
            opportunity = get_object_or_404(Opportunity, pk=opportunity_id)
            if opportunity.owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("accounts.delete_opportunitycontactrole", modal=True),
    name="dispatch",
)
class OpportunityContactRoleDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """
    Delete view for Opportunity Contact Role
    """

    model = OpportunityContactRole

    def get_post_delete_response(self):
        return HttpResponse(
            "<script>htmx.trigger('#tab-contact-btn','click');</script>"
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["opportunities.change_opportunity", "opportunities.change_own_opportunity"]
    ),
    name="dispatch",
)
class SelectClosedStageView(LoginRequiredMixin, View):
    """View to select between Closed Won and Closed Lost stages."""

    def get(self, request, *args, **kwargs):
        """Render the closed stage selection modal."""
        opportunity = get_object_or_404(Opportunity, pk=kwargs.get("pk"))

        # Get closed won and closed lost stages for the company
        company = opportunity.company if hasattr(opportunity, "company") else None
        closed_won_stage = None
        closed_lost_stage = None
        current_stage = (
            opportunity.stage
            if hasattr(opportunity, "stage") and opportunity.stage
            else None
        )
        current_stage_id = current_stage.id if current_stage else None

        if company:
            closed_won_stage = OpportunityStage.objects.filter(
                company=company, stage_type="won"
            ).first()
            closed_lost_stage = OpportunityStage.objects.filter(
                company=company, stage_type="lost"
            ).first()

        context = {
            "opportunity": opportunity,
            "closed_won_stage": closed_won_stage,
            "closed_lost_stage": closed_lost_stage,
            "current_stage": current_stage,
            "current_stage_id": current_stage_id,
        }

        return render(
            request,
            "opportunities/select_closed_stage.html",
            context,
        )

    def post(self, request, *args, **kwargs):
        """Handle the selection of closed won or closed lost."""
        opportunity = get_object_or_404(Opportunity, pk=kwargs.get("pk"))
        stage_id = request.POST.get("stage_id")

        if not stage_id:
            return HttpResponse(
                "<script>alert('Please select a stage');</script>",
                status=400,
            )

        try:
            stage = OpportunityStage.objects.get(pk=stage_id)
            # Verify it's a closed stage
            if stage.stage_type not in ["won", "lost"]:
                return HttpResponse(
                    "<script>alert('Invalid stage selected');</script>",
                    status=400,
                )

            # Update the opportunity stage
            opportunity.stage = stage
            opportunity.save()

            return HttpResponse(
                "<script>closeModal();$('#reloadButton').click();</script>"
            )
        except OpportunityStage.DoesNotExist:
            return HttpResponse(
                "<script>alert('Stage not found');</script>",
                status=404,
            )
