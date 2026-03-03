"""
Views for managing contacts and related accounts in the CRM system.
Includes create, update, list, and relationship views with permission checks.
"""

# Standard library imports
import logging
from functools import cached_property
from urllib.parse import urlencode

# Third-party imports (Django)
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, View

# First-party / Horilla imports
from horilla.shortcuts import get_object_or_404, render
from horilla.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required,
    permission_required_or_denied,
)
from horilla.utils.translation import gettext_lazy as _
from horilla_activity.views import HorillaActivitySectionView
from horilla_core.utils import is_owner
from horilla_crm.contacts.filters import ContactFilter
from horilla_crm.contacts.models import Contact, ContactAccountRelationship
from horilla_crm.contacts.signals import set_contact_account_id
from horilla_generics.mixins import RecentlyViewedMixin
from horilla_generics.views import (
    HorillaDetailSectionView,
    HorillaDetailTabView,
    HorillaDetailView,
    HorillaGroupByView,
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

# Local application imports
from .forms import ChildContactForm, ContactFormClass, ContactSingleForm

logger = logging.getLogger(__name__)


class ContactView(LoginRequiredMixin, HorillaView):
    """
    Render the contact page
    """

    nav_url = reverse_lazy("contacts:contacts_navbar")
    list_url = reverse_lazy("contacts:contact_list_view")
    kanban_url = reverse_lazy("contacts:contact_kanban_view")
    group_by_url = reverse_lazy("contacts:contact_group_by_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required(["contacts.view_contact", "contacts.view_own_contact"]),
    name="dispatch",
)
class ContactNavbar(LoginRequiredMixin, HorillaNavView):
    """
    Navbar View for Contact page
    """

    nav_title = Contact._meta.verbose_name_plural
    search_url = reverse_lazy("contacts:contact_list_view")
    main_url = reverse_lazy("contacts:contacts_view")
    kanban_url = reverse_lazy("contacts:contact_kanban_view")
    group_by_url = reverse_lazy("contacts:contact_group_by_view")
    model_str = "contacts.Contact"
    model_name = "Contact"
    model_app_label = "contacts"
    filterset_class = ContactFilter
    exclude_kanban_fields = "company"
    enable_actions = True
    enable_quick_filters = True

    @cached_property
    def new_button(self):
        """Create a new contact button"""
        if self.request.user.has_perm(
            "contacts.add_contact"
        ) or self.request.user.has_perm("contacts.add_own_contact"):
            return {
                "url": f"""{ reverse_lazy('contacts:contact_create_form')}?new=true""",
                "attrs": {"id": "contact-create"},
            }
        return None


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["contacts.view_contact", "contacts.view_own_contact"]
    ),
    name="dispatch",
)
class ContactListView(LoginRequiredMixin, HorillaListView):
    """
    Contact List View
    """

    model = Contact
    paginate_by = 20
    view_id = "ContactList"
    filterset_class = ContactFilter
    search_url = reverse_lazy("contacts:contact_list_view")
    main_url = reverse_lazy("contacts:contacts_view")
    enable_quick_filters = True

    def no_record_add_button(self):
        """Button to add a new contact if no records exist"""
        if self.request.user.has_perm(
            "contacts.add_contact"
        ) or self.request.user.has_perm("contacts.add_own_contact"):
            return {
                "url": f"""{ reverse_lazy('contacts:contact_create_form')}?new=true""",
                "attrs": 'id="contact-create"',
            }
        return None

    bulk_update_fields = [
        "title",
        "contact_source",
        "languages",
        "address_city",
        "address_state",
        "address_zip",
        "address_country",
        "is_primary",
    ]

    header_attrs = [
        {"email": {"style": "width: 250px;"}, "title": {"style": "width: 250px;"}},
    ]

    columns = ["first_name", "last_name", "title", "email", "phone", "contact_source"]

    contact_permissions = {
        "permission": "contacts.change_contact",
        "own_permission": "contacts.change_own_contact",
        "owner_field": "contact_owner",
    }
    actions = [
        {
            **contact_permissions,
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
            **contact_permissions,
            "action": _("Change Owner"),
            "src": "assets/icons/a2.svg",
            "img_class": "w-4 h-4",
            "attrs": """
                        hx-get="{get_change_owner_url}"
                        hx-target="#modalBox"
                        hx-swap="innerHTML"
                        onclick="openModal()"
                        """,
        },
        {
            "action": "Delete",
            "src": "assets/icons/a4.svg",
            "img_class": "w-4 h-4",
            "permission": "contacts.delete_contact",
            "own_permission": "contacts.delete_own_contact",
            "owner_field": "contact_owner",
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
            "permission": "contacts.add_contact",
            "own_permission": "contacts.add_own_contact",
            "owner_field": "contact_owner",
            "attrs": """
                            hx-get="{get_duplicate_url}?duplicate=true"
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            onclick="openModal()"
                            """,
        },
    ]

    @cached_property
    def col_attrs(self):
        """Attributes for columns in the contact list"""
        query_params = self.request.GET.dict()
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
            "permission": "contacts.view_contact",
            "own_permission": "contacts.view_own_contact",
            "owner_field": "contact_owner",
        }
        return [
            {
                "first_name": {
                    **attrs,
                }
            }
        ]


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["contacts.view_contact", "contacts.view_own_contact"]
    ),
    name="dispatch",
)
class ContactGroupByView(LoginRequiredMixin, HorillaGroupByView):
    """
    Contact Group By view
    """

    model = Contact
    view_id = "contacts-group-by"
    filterset_class = ContactFilter
    search_url = reverse_lazy("contacts:contact_list_view")
    main_url = reverse_lazy("contacts:contacts_view")
    enable_quick_filters = True
    group_by_field = "contact_source"

    columns = ["first_name", "last_name", "title", "email", "phone", "contact_source"]
    actions = ContactListView.actions

    def no_record_add_button(self):
        """Button to add a new contact if no records exist"""
        if self.request.user.has_perm(
            "contacts.add_contact"
        ) or self.request.user.has_perm("contacts.add_own_contact"):
            return {
                "url": f"""{reverse_lazy('contacts:contact_create_form')}?new=true""",
                "attrs": 'id="contact-create"',
            }
        return None

    @cached_property
    def col_attrs(self):
        """Attributes for columns in the contact group-by view"""
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
            "permission": "contacts.view_contact",
            "own_permission": "contacts.view_own_contact",
            "owner_field": "contact_owner",
        }
        return [
            {
                "first_name": {
                    **attrs,
                }
            }
        ]


@method_decorator(
    permission_required_or_denied("contacts.delete_contact", modal=True),
    name="dispatch",
)
class ContactDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """Delete a contact"""

    model = Contact

    def get_post_delete_response(self):
        """Response after a contact is deleted"""
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")


@method_decorator(
    permission_required_or_denied(
        ["contacts.view_contact", "contacts.view_own_contact"]
    ),
    name="dispatch",
)
class ContactKanbanView(LoginRequiredMixin, HorillaKanbanView):
    """
    Kanban view for Contact
    """

    model = Contact
    view_id = "Contact_Kanban"
    filterset_class = ContactFilter
    search_url = reverse_lazy("contacts:contact_list_view")
    main_url = reverse_lazy("contacts:contacts_view")
    group_by_field = "contact_source"
    actions = ContactListView.actions

    columns = ["first_name", "title", "email", "phone", "birth_date"]

    @cached_property
    def kanban_attrs(self):
        """Attributes for columns in the contact kanban"""
        query_params = self.request.GET.dict()
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        if self.request.user.has_perm(
            "contacts.view_contact"
        ) or self.request.user.has_perm("contacts.view_own_contact"):
            return f"""
                    hx-get="{{get_detail_url}}?{query_string}"
                    hx-target="#mainContent"
                    hx-swap="outerHTML"
                    hx-push-url="true"
                    hx-select="#mainContent"
                    style ="cursor:pointer",
                    """
        return None


@method_decorator(htmx_required, name="dispatch")
class ContactFormView(LoginRequiredMixin, HorillaMultiStepFormView):
    """
    Contact form view for create and edit
    """

    form_class = ContactFormClass
    model = Contact
    total_steps = 3
    fullwidth_fields = ["languages", "description"]
    detail_url_name = "contacts:contact_detail_view"
    step_titles = {
        "1": _("Contact Information"),
        "2": _("Address Information"),
        "3": _("Additional Information"),
    }

    single_step_url_name = {
        "create": "contacts:contact_single_create_form",
        "edit": "contacts:contact_single_update_form",
    }

    @cached_property
    def form_url(self):
        """Get the URL for the form, either for creating or editing a contact"""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("contacts:contact_create_form", kwargs={"pk": pk})
        return reverse_lazy("contacts:contact_update_form")


@method_decorator(htmx_required, name="dispatch")
class ContactsSingleFormView(LoginRequiredMixin, HorillaSingleFormView):
    """Account Create/Update Single Page View"""

    model = Contact
    form_class = ContactSingleForm
    full_width_fields = ["description"]
    detail_url_name = "contacts:contact_detail_view"

    multi_step_url_name = {
        "create": "contacts:contact_create_form",
        "edit": "contacts:contact_update_form",
    }

    @cached_property
    def form_url(self):
        """Form URL for lead"""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "contacts:contact_single_update_form", kwargs={"pk": pk}
            )
        return reverse_lazy("contacts:contact_single_create_form")


@method_decorator(htmx_required, name="dispatch")
class RelatedContactFormView(LoginRequiredMixin, HorillaMultiStepFormView):
    """
    Contact form view for create and edit
    """

    form_class = ContactFormClass
    model = Contact
    total_steps = 3
    fullwidth_fields = ["languages", "description"]
    save_and_new = False
    step_titles = {
        "1": _("Contact Information"),
        "2": _("Address Information"),
        "3": _("Additional Information"),
    }

    def form_valid(self, form):
        step = self.get_initial_step()

        if step == self.total_steps:
            account_id = self.request.GET.get("id")
            if account_id:
                set_contact_account_id(
                    account_id=account_id, company=self.request.active_company
                )
            super().form_valid(form)
            return HttpResponse(
                "<script>htmx.trigger('#tab-contact_relationships-btn','click');closeModal();</script>"
            )

        return super().form_valid(form)

    @cached_property
    def form_url(self):
        """Get the URL for the form, either for creating or editing a contact"""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("contacts:contact_create_form", kwargs={"pk": pk})
        return reverse_lazy("contacts:contact_update_form")

    def get(self, request, *args, **kwargs):
        contact_id = self.kwargs.get("pk")
        if request.user.has_perm("contacts.change_contact") or request.user.has_perm(
            "contacts.add_contact"
        ):
            return super().get(request, *args, **kwargs)

        if contact_id:
            contact = get_object_or_404(Contact, pk=contact_id)
            if contact.contact_owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")


@method_decorator(htmx_required, name="dispatch")
class ContactChangeOwnerFormView(LoginRequiredMixin, HorillaSingleFormView):
    """
    Change owner form
    """

    model = Contact
    fields = ["contact_owner"]
    full_width_fields = ["contact_owner"]
    modal_height = False
    form_title = _("Change Owner")

    @cached_property
    def form_url(self):
        """Get the URL for changing the owner of a contact"""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("contacts:contact_change_owner", kwargs={"pk": pk})
        return None

    def get(self, request, *args, **kwargs):
        contact_id = self.kwargs.get("pk")
        if request.user.has_perm("contacts.change_contact") or request.user.has_perm(
            "contacts.add_contact"
        ):
            return super().get(request, *args, **kwargs)

        if contact_id:
            contact = get_object_or_404(Contact, pk=contact_id)
            if contact.contact_owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")


@method_decorator(
    permission_required_or_denied(
        ["contacts.view_contact", "contacts.view_own_contact"]
    ),
    name="dispatch",
)
class ContactDetailView(RecentlyViewedMixin, LoginRequiredMixin, HorillaDetailView):
    """
    Detail view for contact
    """

    model = Contact
    breadcrumbs = [
        ("People", "contacts:contacts_view"),
        ("Contacts", "contacts:contacts_view"),
    ]
    body = [
        "first_name",
        "title",
        "email",
        "phone",
        "birth_date",
        "contact_owner",
        "assistant",
    ]

    tab_url = reverse_lazy("contacts:contact_detail_view_tabs")
    actions = ContactListView.actions


@method_decorator(
    permission_required_or_denied(
        ["contacts.view_contact", "contacts.view_own_contact"]
    ),
    name="dispatch",
)
class ContactDetailViewTabs(LoginRequiredMixin, HorillaDetailTabView):
    """
    Tab Views for Contact Detail view
    """

    def __init__(self, **kwargs):
        request = getattr(_thread_local, "request", None)
        self.request = request
        self.object_id = self.request.GET.get("object_id")
        super().__init__(**kwargs)

    urls = {
        "details": "contacts:contact_details_tab",
        "activity": "contacts:contact_activity_tab",
        "related_lists": "contacts:contact_related_list_tab",
        "notes_attachments": "contacts:contacts_notes_attachements",
        "history": "contacts:contact_history_tab",
    }


@method_decorator(
    permission_required_or_denied(
        ["contacts.view_contact", "contacts.view_own_contact"]
    ),
    name="dispatch",
)
class ContactDetailTab(LoginRequiredMixin, HorillaDetailSectionView):
    """
    Details tab of contact detail view
    """

    model = Contact
    excluded_fields = [
        "company",
        "id",
        "is_active",
        "additional_info",
        "created_at",
        "created_by",
        "updated_at",
        "updated_by",
        "history",
    ]


@method_decorator(
    permission_required_or_denied(
        ["contacts.view_contact", "contacts.view_own_contact"]
    ),
    name="dispatch",
)
class ContactActivityTab(LoginRequiredMixin, HorillaActivitySectionView):
    """
    Activity tab for contact detail view
    """

    model = Contact


@method_decorator(
    permission_required_or_denied(
        ["contacts.view_contact", "contacts.view_own_contact"]
    ),
    name="dispatch",
)
class ContactsNotesAndAttachments(
    LoginRequiredMixin, HorillaNotesAttachementSectionView
):
    """Notes and Attachments tab for contact detail view"""

    model = Contact


@method_decorator(
    permission_required_or_denied(
        ["contacts.view_contact", "contacts.view_own_contact"]
    ),
    name="dispatch",
)
class ContactHistorytab(LoginRequiredMixin, HorillaHistorySectionView):
    """
    History tab for contact detail view
    """

    model = Contact


@method_decorator(
    permission_required_or_denied(
        ["contacts.view_contact", "contacts.view_own_contact"]
    ),
    name="dispatch",
)
class ContactRelatedListsTab(LoginRequiredMixin, HorillaRelatedListSectionView):
    """
    Related lists ab for contact detail view
    """

    model = Contact
    excluded_related_lists = [
        "opportunity_roles",
        "contact_campaign_members",
        "account_relationships",
    ]

    @cached_property
    def related_list_config(self):
        """Configuration for related lists in the contact detail view"""
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        pk = self.request.GET.get("object_id")
        referrer_url = "contact_detail_view"

        return {
            "custom_related_lists": {
                "campaigns": {
                    "app_label": "campaigns",
                    "model_name": "Campaign",
                    "intermediate_model": "CampaignMember",
                    "intermediate_field": "members",
                    "related_field": "contact",
                    "config": {
                        "title": _("Related Campaigns"),
                        "columns": [
                            (
                                Contact._meta.get_field("contact_campaign_members")
                                .related_model._meta.get_field("campaign")
                                .related_model._meta.get_field("campaign_name")
                                .verbose_name,
                                "campaign_name",
                            ),
                            (
                                Contact._meta.get_field("contact_campaign_members")
                                .related_model._meta.get_field("campaign")
                                .related_model._meta.get_field("status")
                                .verbose_name,
                                "get_status_display",
                            ),
                            (
                                Contact._meta.get_field("contact_campaign_members")
                                .related_model._meta.get_field("campaign")
                                .related_model._meta.get_field("start_date")
                                .verbose_name,
                                "start_date",
                            ),
                            (
                                Contact._meta.get_field("contact_campaign_members")
                                .related_model._meta.get_field("member_status")
                                .verbose_name,
                                "members__get_member_status_display",
                            ),
                        ],
                        "can_add": self.request.user.has_perm(
                            "campaigns.add_campaignmember"
                        )
                        and (
                            (
                                is_owner(Contact, pk)
                                and self.request.user.has_perm(
                                    "contacts.change_own_contact"
                                )
                            )
                            or self.request.user.has_perm("contacts.change_contact")
                        ),
                        "add_url": reverse_lazy("campaigns:add_contact_to_campaign"),
                        "actions": [
                            {
                                "action": "edit",
                                "src": "/assets/icons/edit.svg",
                                "img_class": "w-4 h-4",
                                "permission": "campaigns.change_campaignmember",
                                "own_permission": "campaigns.change_own_campaignmember",
                                "owner_field": "created_by",
                                "intermediate_model": "CampaignMember",
                                "intermediate_field": "campaign",
                                "parent_field": "contact",
                                "attrs": """
                                        hx-get="{get_edit_contact_to_campaign_url_for_contact}?new=true"
                                        hx-target="#modalBox"
                                        hx-swap="innerHTML"
                                        onclick="event.stopPropagation();openModal()"
                                        hx-indicator="#modalBox"
                                        """,
                            },
                            (
                                {
                                    "action": "Delete",
                                    "src": "assets/icons/a4.svg",
                                    "img_class": "w-4 h-4",
                                    "permission": "campaigns.delete_campaignmember",
                                    "attrs": """
                                        hx-post="{get_delete_contact_to_campaign_url_for_contact}"
                                        hx-target="#deleteModeBox"
                                        hx-swap="innerHTML"
                                        hx-trigger="click"
                                        hx-vals='{{"check_dependencies": "true"}}'
                                        onclick="openDeleteModeModal()"
                                    """,
                                }
                            ),
                        ],
                        "col_attrs": [
                            (
                                {
                                    "campaign_name": {
                                        "hx-get": f"{{get_detail_view_url}}?referrer_app={self.model._meta.app_label}&referrer_model={self.model._meta.model_name}&referrer_id={pk}&referrer_url={referrer_url}&{query_string}",
                                        "hx-target": "#mainContent",
                                        "hx-swap": "outerHTML",
                                        "hx-push-url": "true",
                                        "hx-select": "#mainContent",
                                        "permission": "campaigns.view_campaign",
                                        "own_permission": "campaigns.view_own_campaign",
                                        "owner_field": "campaign_owner",
                                    }
                                }
                                if self.request.user.has_perm("campaigns.view_campaign")
                                else {}
                            )
                        ],
                    },
                },
                "opportunities": {
                    "app_label": "opportunities",
                    "model_name": "Opportunity",
                    "intermediate_model": "OpportunityContactRole",
                    "intermediate_field": "opportunity",
                    "related_field": "contact",
                    "config": {
                        "title": _("Related Opportunities"),
                        "columns": [
                            (
                                Contact._meta.get_field("opportunity_roles")
                                .related_model._meta.get_field("opportunity")
                                .related_model._meta.get_field("name")
                                .verbose_name,
                                "name",
                            ),
                            (
                                Contact._meta.get_field("opportunity_roles")
                                .related_model._meta.get_field("opportunity")
                                .related_model._meta.get_field("account")
                                .verbose_name,
                                "account__name",
                            ),
                            (
                                Contact._meta.get_field("opportunity_roles")
                                .related_model._meta.get_field("opportunity")
                                .related_model._meta.get_field("stage")
                                .verbose_name,
                                "stage__name",
                            ),
                            (
                                Contact._meta.get_field("opportunity_roles")
                                .related_model._meta.get_field("opportunity")
                                .related_model._meta.get_field("amount")
                                .verbose_name,
                                "amount",
                            ),
                            (
                                Contact._meta.get_field("opportunity_roles")
                                .related_model._meta.get_field("opportunity")
                                .related_model._meta.get_field("close_date")
                                .verbose_name,
                                "close_date",
                            ),
                            (
                                Contact._meta.get_field("opportunity_roles")
                                .related_model._meta.get_field("opportunity")
                                .related_model._meta.get_field("probability")
                                .verbose_name,
                                "probability",
                            ),
                        ],
                        "can_add": self.request.user.has_perm(
                            "opportunities.add_opportunitycontactrole"
                        )
                        and (
                            (
                                is_owner(Contact, pk)
                                and self.request.user.has_perm(
                                    "opportunities.change_own_opportunity"
                                )
                            )
                            or self.request.user.has_perm(
                                "opportunities.change_opportunity"
                            )
                        ),
                        "add_url": reverse_lazy(
                            "opportunities:related_contact_opportunity_create"
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
                                "intermediate_field": "opportunity",
                                "parent_field": "contact",
                                "attrs": """
                                    hx-get="{get_edit_url}?new=true"
                                    hx-target="#modalBox"
                                    hx-swap="innerHTML"
                                    onclick="event.stopPropagation();openModal()"
                                    hx-indicator="#modalBox"
                                    """,
                            },
                            (
                                {
                                    "action": "Delete",
                                    "src": "assets/icons/a4.svg",
                                    "img_class": "w-4 h-4",
                                    "permission": "opportunities.delete_opportunitycontactrole",
                                    "attrs": """
                                        hx-post="{get_delete_url}"
                                        hx-target="#deleteModeBox"
                                        hx-swap="innerHTML"
                                        hx-trigger="click"
                                        hx-vals='{{"check_dependencies": "true"}}'
                                        onclick="openDeleteModeModal()"
                                    """,
                                }
                            ),
                        ],
                        "col_attrs": [
                            {
                                "name": {
                                    "hx-get": f"{{get_detail_url}}?referrer_app={self.model._meta.app_label}&referrer_model={self.model._meta.model_name}&referrer_id={pk}&referrer_url={referrer_url}&{query_string}",
                                    "hx-target": "#mainContent",
                                    "hx-swap": "outerHTML",
                                    "hx-push-url": "true",
                                    "hx-select": "#mainContent",
                                    "permission": "opportunities.view_opportunity",
                                    "own_permission": "opportunities.view_own_opportunity",
                                    "owner_field": "owner",
                                }
                            }
                        ],
                    },
                },
                "account_relationships": {
                    "app_label": "accounts",
                    "model_name": "Account",
                    "intermediate_model": "ContactAccountRelationship",
                    "intermediate_field": "contact_relationships",
                    "related_field": "contact",
                    "config": {
                        "title": _("Related Accounts"),
                        "can_add": self.request.user.has_perm(
                            "contacts.add_contactaccountrelationship"
                        )
                        and (
                            (
                                is_owner(Contact, pk)
                                and self.request.user.has_perm(
                                    "contacts.change_own_contact"
                                )
                            )
                            or self.request.user.has_perm("contacts.change_contact")
                        ),
                        "add_url": reverse_lazy(
                            "contacts:create_contact_account_relation"
                        ),
                        "columns": [
                            (
                                ContactAccountRelationship._meta.get_field("account")
                                .related_model._meta.get_field("name")
                                .verbose_name,
                                "name",
                            ),
                            (
                                ContactAccountRelationship._meta.get_field("account")
                                .related_model._meta.get_field("account_number")
                                .verbose_name,
                                "account_number",
                            ),
                            (
                                ContactAccountRelationship._meta.get_field("account")
                                .related_model._meta.get_field("annual_revenue")
                                .verbose_name,
                                "annual_revenue",
                            ),
                            (
                                ContactAccountRelationship._meta.get_field(
                                    "role"
                                ).verbose_name,
                                "contact_relationships__role",
                            ),
                        ],
                        "actions": [
                            {
                                "action": _("Edit"),
                                "src": "assets/icons/edit.svg",
                                "img_class": "w-4 h-4",
                                "permission": "contacts.change_contactaccountrelationship",
                                "own_permission": "contacts.change_own_contactaccountrelationship",
                                "owner_field": "created_by",
                                "intermediate_model": "ContactAccountRelationship",
                                "intermediate_field": "account",
                                "parent_field": "contact",
                                "attrs": """
                                    hx-get="{get_edit_contact_account_relation_url}?new=true"
                                    hx-target="#modalBox"
                                    hx-swap="innerHTML"
                                    onclick="openModal()"
                                    """,
                            },
                            (
                                {
                                    "action": "Delete",
                                    "src": "assets/icons/a4.svg",
                                    "img_class": "w-4 h-4",
                                    "permission": "contacts.delete_contactaccountrelationship",
                                    "attrs": """
                                        hx-post="{get_delete_related_accounts_url}"
                                        hx-target="#deleteModeBox"
                                            hx-swap="innerHTML"
                                            hx-trigger="click"
                                            hx-vals='{{"check_dependencies": "true"}}'
                                            onclick="openDeleteModeModal()"
                                    """,
                                }
                            ),
                        ],
                        "col_attrs": [
                            {
                                "name": {
                                    "hx-get": f"{{get_detail_url}}?referrer_app={self.model._meta.app_label}&referrer_model={self.model._meta.model_name}&referrer_id={pk}&referrer_url={referrer_url}&{query_string}",
                                    "hx-target": "#mainContent",
                                    "hx-swap": "outerHTML",
                                    "hx-push-url": "true",
                                    "hx-select": "#mainContent",
                                    "permission": "accounts.view_account",
                                    "own_permission": "accounts.view_own_account",
                                    "owner_field": "account_owner",
                                }
                            }
                        ],
                    },
                },
            },
            "child_contacts": {
                "title": _("Child Contacts"),
                "can_add": (
                    is_owner(Contact, pk)
                    and self.request.user.has_perm("contacts.change_own_contact")
                )
                or self.request.user.has_perm("contacts.change_contact"),
                "add_url": reverse_lazy("contacts:create_child_contact"),
                "columns": [
                    (Contact._meta.get_field("title").verbose_name, "title"),
                    (Contact._meta.get_field("first_name").verbose_name, "first_name"),
                    (Contact._meta.get_field("last_name").verbose_name, "last_name"),
                    (Contact._meta.get_field("email").verbose_name, "email"),
                ],
                "actions": [
                    (
                        {
                            "action": "Delete",
                            "src": "assets/icons/a4.svg",
                            "img_class": "w-4 h-4",
                            "permission": "contacts.change_contact",
                            "own_permission": "contacts.change_own_contact",
                            "owner_field": "contact_owner",
                            "attrs": """
                            hx-delete="{get_child_contact_delete_url}"
                            hx-on:click="hxConfirm(this,'Are you sure you want to remove this child contact relationship?')"
                            hx-target="#deleteModeBox"
                            hx-swap="innerHTML"
                            hx-trigger="confirmed"
                    """,
                        }
                    ),
                ],
                "col_attrs": [
                    {
                        "title": {
                            "hx-get": f"{{get_detail_url}}?referrer_app={self.model._meta.app_label}&referrer_model={self.model._meta.model_name}&referrer_id={pk}&referrer_url={referrer_url}&{query_string}",
                            "hx-target": "#mainContent",
                            "hx-swap": "outerHTML",
                            "hx-push-url": "true",
                            "hx-select": "#mainContent",
                            "permission": "contacts.view_contact",
                            "own_permission": "contacts.view_own_contact",
                            "owner_field": "contact_owner",
                        }
                    }
                ],
                "custom_buttons": [
                    {
                        "label": _("View Hierarchy"),
                        "url": reverse_lazy("contacts:contact_hierarchy"),
                        "attrs": """
                                        hx-target="#modalBox"
                                        hx-swap="innerHTML"
                                        onclick="openModal()"
                                        hx-indicator="#modalBox"
                                    """,
                        "icon": "fa-solid fa-sitemap",
                        "class": "text-xs px-4 py-1.5 bg-white border border-primary-600 text-primary-600 rounded-md transition duration-300",
                    },
                ],
            },
        }


def _build_contact_tree(contact):
    """Build tree of contact and descendants for <details> hierarchy."""
    return {
        "contact": contact,
        "children": [_build_contact_tree(c) for c in contact.child_contacts.all()],
    }


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["contacts.view_contact", "contacts.view_own_contact"]
    ),
    name="dispatch",
)
class ContactHierarchyView(LoginRequiredMixin, View):
    """Modal view showing contact hierarchy with expand/collapse (no JS)."""

    def get(self, request, *args, **kwargs):
        """Get method for contact hierarchy"""

        contact_id = request.GET.get("id")
        if not contact_id:
            return render(request, "error/403.html", {"modal": True})
        contact = get_object_or_404(Contact, pk=contact_id)
        root = _build_contact_tree(contact)
        return render(
            request,
            "contact_hierarchy_modal.html",
            {"root": root},
        )


@method_decorator(htmx_required, name="dispatch")
class AddRelatedAccountsFormView(LoginRequiredMixin, HorillaSingleFormView):
    """
    Create and update form for adding related accounts into contacts
    """

    model = ContactAccountRelationship
    modal_height = False
    fields = ["contact", "account", "role"]
    form_title = _("Add Account Contact Relationships")
    full_width_fields = ["account", "contact", "role"]
    hidden_fields = ["contact"]
    save_and_new = False

    def get(self, request, *args, **kwargs):
        contact_id = request.GET.get("id")
        if request.user.has_perm(
            "contacts.change_contactaccountrelationship"
        ) or request.user.has_perm("contacts.add_contactaccountrelationship"):
            return super().get(request, *args, **kwargs)

        if contact_id:
            contact = get_object_or_404(Contact, pk=contact_id)
            if contact.contact_owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")

    def form_valid(self, form):
        super().form_valid(form)
        return HttpResponse(
            "<script>htmx.trigger('#tab-account_relationships-btn', 'click');closeModal();</script>"
        )

    def get_initial(self):
        initial = super().get_initial()
        obj_id = self.request.GET.get("id")
        if obj_id:
            initial["contact"] = obj_id
        return initial

    @cached_property
    def form_url(self):
        """Get the URL for creating or editing a contact-account relationship"""
        if self.kwargs.get("pk"):
            return reverse_lazy(
                "contacts:edit_contact_account_relation",
                kwargs={"pk": self.kwargs.get("pk")},
            )
        return reverse_lazy("contacts:create_contact_account_relation")


@method_decorator(htmx_required, name="dispatch")
class AddChildContactFormView(LoginRequiredMixin, FormView):
    """
    Form view to select an existing campaign and assign it as a child contact.
    """

    template_name = "single_form_view.html"
    form_class = ChildContactForm
    header = True

    def get(self, request, *args, **kwargs):
        contact_id = request.GET.get("id")
        if request.user.has_perm(
            "contacts.change_contactaccount"
        ) or request.user.has_perm("contacts.add_contact"):
            return super().get(request, *args, **kwargs)

        if contact_id:
            contact = get_object_or_404(Contact, pk=contact_id)
            if contact.contact_owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")

    def get_form_kwargs(self):
        """
        Pass the request to the form for queryset filtering and validation.
        """
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_initial(self):
        """Prepopulate the form with initial data if needed."""
        initial = super().get_initial()
        parent_id = self.request.GET.get("id")

        if parent_id:
            try:
                parent_contact = Contact.objects.get(pk=parent_id)
                initial["parent_contact"] = parent_contact.id  # Pass ID, not object
                company = getattr(self.request, "active_company", None)
                initial["company"] = company
            except Contact.DoesNotExist:
                logger.error("Parent contact with ID %s not found", parent_id)

        return initial

    def get_context_data(self, **kwargs):
        """
        Add context data for the template.
        """
        context = super().get_context_data(**kwargs)
        context["form_title"] = _("Add Child Contact")
        context["full_width_fields"] = ["contact"]

        form_url = self.get_form_url()

        context["form_url"] = str(form_url)
        context["modal_height"] = False
        context["view_id"] = "add-child-contact-form-view"
        context["condition_fields"] = []
        context["header"] = self.header
        context["field_permissions"] = {}  # No model, so no field permissions

        context["hx_attrs"] = {
            "hx-post": str(form_url),
            "hx-target": "#modalBox",
            "hx-swap": "innerHTML",
        }

        return context

    def form_valid(self, form):
        """
        Update the selected contact's parent_contact field and return HTMX response.
        """

        if not self.request.user.is_authenticated:
            messages.error(
                self.request, _("You must be logged in to perform this action.")
            )
            return self.form_invalid(form)

        selected_contact = form.cleaned_data["contact"]
        parent_contact = form.cleaned_data.get("parent_contact")

        if not parent_contact:
            form.add_error(None, _("No parent contact specified in the request."))
            return self.form_invalid(form)

        try:
            if selected_contact.id == parent_contact.id:
                form.add_error("contact", _("A contact cannot be its own parent."))
                result = self.form_invalid(form)

            elif selected_contact.parent_contact:
                form.add_error(
                    "contact", _("This contact already has a parent contact.")
                )
                result = self.form_invalid(form)

            else:
                selected_contact.parent_contact = parent_contact
                selected_contact.updated_at = timezone.now()
                selected_contact.updated_by = self.request.user
                selected_contact.save()
                messages.success(
                    self.request, _("Child contact assigned successfully!")
                )
                result = HttpResponse(
                    "<script>htmx.trigger('#tab-child_contacts-btn', 'click');closeModal();</script>"
                )

        except ValueError:
            form.add_error(None, _("Invalid parent contact ID format."))
            result = self.form_invalid(form)

        except Exception:
            form.add_error(
                None,
                _("An unexpected error occurred while assigning the child contact."),
            )
            result = self.form_invalid(form)

        return result

    def get_form_url(self):
        """
        Get the form URL for submission.
        """
        return reverse_lazy("contacts:create_child_contact")


@method_decorator(htmx_required, name="dispatch")
class ChildContactDeleteView(LoginRequiredMixin, View):
    """
    View to remove parent-child relationship from a contact.
    """

    def delete(self, request, pk, *args, **kwargs):
        """
        Handle DELETE request to remove parent contact relationship.
        """
        child_contact = get_object_or_404(Contact, pk=pk)

        has_permission = (
            request.user.has_perm("contacts.change_contact")
            or child_contact.contact_owner == request.user
            or (
                child_contact.parent_contact
                and child_contact.parent_contact.contact_owner == request.user
            )
        )

        if not has_permission:
            messages.error(
                request, _("You don't have permission to perform this action.")
            )
            return HttpResponse(
                "<script>htmx.trigger('#tab-child_contacts-btn', 'click');</script>",
                status=403,
            )

        parent_contact = child_contact.parent_contact

        if not parent_contact:
            messages.warning(request, _("This contact doesn't have a parent contact."))
            return HttpResponse(
                "<script>htmx.trigger('#tab-child_contacts-btn', 'click');</script>"
            )

        try:
            child_contact.parent_contact = None
            child_contact.updated_at = timezone.now()
            child_contact.updated_by = request.user
            child_contact.save()

            messages.success(
                request,
                _(
                    f"Successfully removed {child_contact} from {parent_contact}'s child contacts."
                ),
            )

            return HttpResponse(
                "<script>htmx.trigger('#tab-child_contacts-btn', 'click');</script>"
            )

        except Exception:
            messages.error(
                request, _("An error occurred while removing the child contact.")
            )
            return HttpResponse(
                "<script>htmx.trigger('#tab-child_contacts-btn', 'click');</script>",
            )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        "contacts.delete_contactaccountrelationship", modal=True
    ),
    name="dispatch",
)
class RelatedContactDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """View for deleting related contact account relationships."""

    model = ContactAccountRelationship

    def get_post_delete_response(self):
        return HttpResponse(
            "<script>htmx.trigger('#tab-account_relationships-btn','click');</script>"
            "<script>htmx.trigger('#tab-contact_relationships-btn','click');</script>"
        )
