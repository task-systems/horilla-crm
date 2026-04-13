"""Views for duplicate-rule workflows."""

# Standard library imports
from functools import cached_property
from urllib.parse import urlencode

# Third-party imports (Django)
from django.contrib.auth.mixins import LoginRequiredMixin

# First-party / Horilla imports
from horilla.http import HttpResponse
from horilla.urls import reverse_lazy
from horilla.utils.decorators import htmx_required, method_decorator
from horilla.utils.translation import gettext_lazy as _

# First-party / Horilla apps
from horilla_duplicates.filters import DuplicateRuleFilter
from horilla_duplicates.forms import DuplicateRuleForm
from horilla_duplicates.models import DuplicateRule, DuplicateRuleCondition
from horilla_generics.views import (
    HorillaListView,
    HorillaModalDetailView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)


class DuplicateRuleView(LoginRequiredMixin, HorillaView):
    """
    Main view for duplicate rules page
    """

    template_name = "duplicates/duplicate_rule_view.html"
    nav_url = reverse_lazy("horilla_duplicates:duplicate_rule_nav_view")
    list_url = reverse_lazy("horilla_duplicates:duplicate_rule_list_view")


@method_decorator(htmx_required, name="dispatch")
class DuplicateRuleNavView(LoginRequiredMixin, HorillaNavView):
    """
    Navbar view for Duplicate Rules
    """

    nav_title = DuplicateRule._meta.verbose_name_plural
    search_url = reverse_lazy("horilla_duplicates:duplicate_rule_list_view")
    main_url = reverse_lazy("horilla_duplicates:duplicate_rule_view")
    model_name = "DuplicateRule"
    model_app_label = "horilla_duplicates"
    filterset_class = DuplicateRuleFilter
    nav_width = False
    gap_enabled = False
    all_view_types = False
    filter_option = False
    reload_option = False
    one_view_only = True

    @cached_property
    def new_button(self):
        """New button configuration for the navbar."""
        if self.request.user.has_perm("horilla_duplicates.add_duplicaterule"):
            return {
                "url": f"""{reverse_lazy('horilla_duplicates:duplicate_rule_create_view')}?new=true""",
                "attrs": {"id": "duplicate-rule-create"},
            }
        return None


@method_decorator(htmx_required, name="dispatch")
class DuplicateRuleListView(LoginRequiredMixin, HorillaListView):
    """
    List view of Duplicate Rules
    """

    model = DuplicateRule
    view_id = "duplicate-rule-list"
    search_url = reverse_lazy("horilla_duplicates:duplicate_rule_list_view")
    main_url = reverse_lazy("horilla_duplicates:duplicate_rule_view")
    filterset_class = DuplicateRuleFilter
    bulk_update_two_column = True
    table_width = False
    bulk_delete_enabled = False
    table_height_as_class = "h-[calc(_100vh_-_260px_)]"
    bulk_select_option = False
    list_column_visibility = False
    store_ordered_ids = True

    columns = [
        "name",
        "content_type",
        "matching_rule",
        "action_on_create",
        "action_on_edit",
    ]

    actions = [
        {
            "action": "Edit",
            "src": "assets/icons/edit.svg",
            "img_class": "w-4 h-4",
            "permission": "horilla_duplicates.change_duplicaterule",
            "attrs": """
                        hx-get="{get_edit_url}?new=true"
                        hx-target="#modalBox"
                        hx-swap="innerHTML"
                        onclick="openModal()"
                        """,
        },
        {
            "action": "Delete",
            "src": "assets/icons/a4.svg",
            "img_class": "w-4 h-4",
            "permission": "horilla_duplicates.delete_duplicaterule",
            "attrs": """
                    hx-get="{get_delete_url}"
                    hx-target="#deleteModeBox"
                    hx-swap="innerHTML"
                    hx-trigger="click"
                    hx-vals='{{"check_dependencies": "false"}}'
                    onclick="openDeleteModeModal()"
                """,
        },
    ]

    col_attrs = [
        {
            "name": {
                "hx-get": "{get_detail_view_url}",
                "hx-target": "#detailModalBox",
                "hx-swap": "innerHTML",
                "onclick": "openDetailModal();",
                "hx-push-url": "false",
            }
        }
    ]


@method_decorator(htmx_required, name="dispatch")
class DuplicateRuleFormView(LoginRequiredMixin, HorillaSingleFormView):
    """
    Form view for creating and updating Duplicate Rule with optional conditions
    """

    model = DuplicateRule
    form_class = DuplicateRuleForm
    full_width_fields = ["description", "alert_message"]
    condition_fields = ["field", "operator", "value", "logical_operator"]
    condition_model = DuplicateRuleCondition
    condition_field_title = _("Conditions")
    condition_related_name = "conditions"
    condition_order_by = ["order", "created_at"]
    content_type_field = "content_type"
    condition_hx_include = "[name='content_type']"
    return_response = HttpResponse(
        "<script>closeModal();$('#reloadButton').click();$('#detailViewReloadButton').click();</script>"
    )

    @cached_property
    def form_url(self):
        """Get the URL for the form view."""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "horilla_duplicates:duplicate_rule_update_view", kwargs={"pk": pk}
            )
        return reverse_lazy("horilla_duplicates:duplicate_rule_create_view")


class DuplicateRuleDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """
    Delete view for DuplicateRule
    """

    model = DuplicateRule

    def get_post_delete_response(self):
        """Return response after successful deletion"""
        return HttpResponse("<script>$('#reloadButton').click();</script>")


@method_decorator(htmx_required, name="dispatch")
class DuplicateRuleDetailView(LoginRequiredMixin, HorillaModalDetailView):
    """
    Detail view for DuplicateRule
    """

    model = DuplicateRule
    title = _("Details")
    header = {
        "title": "name",
        "subtitle": "",
        "avatar": "",
    }

    body = [
        "name",
        "description",
        "content_type",
        "matching_rule",
        "action_on_create",
        "action_on_edit",
        "show_duplicate_records",
        "alert_title",
        "alert_message",
    ]

    actions = [
        {
            "action": "Edit",
            "src": "assets/icons/edit_white.svg",
            "img_class": "w-3 h-3 flex gap-4 filter brightness-0 invert",
            "permission": "horilla_duplicates.change_duplicaterule",
            "attrs": """
                class="w-24 justify-center px-4 py-2 bg-primary-600 text-white rounded-md text-xs flex items-center gap-2 hover:bg-primary-800 transition duration-300 disabled:cursor-not-allowed"
                hx-get="{get_edit_url}?new=true"
                hx-target="#modalBox"
                hx-swap="innerHTML"
                onclick="openModal();"
            """,
        },
        {
            "action": "Delete",
            "src": "assets/icons/a4-red.svg",
            "img_class": "svg-themed w-3 h-3",
            "permission": "horilla_duplicates.delete_duplicaterule",
            "attrs": """
                    class="w-24 justify-center px-4 py-2 bg-[white] rounded-md text-xs flex items-center gap-2 border border-primary-500 hover:border-primary-600 transition duration-300 disabled:cursor-not-allowed text-primary-600"
                    hx-get="{get_delete_url}"
                    hx-target="#deleteModeBox"
                    hx-swap="innerHTML"
                    hx-trigger="click"
                    hx-vals='{{"check_dependencies": "false"}}'
                    onclick="openDeleteModeModal();"
                    hx-on::after-request="closeDetailModal();"
                """,
        },
    ]
