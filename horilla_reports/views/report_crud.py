"""CRUD views for creating, updating, and managing reports."""

import copy
from functools import cached_property

# Third-party imports (Django)
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.contrib.contenttypes.models import ContentType
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import DetailView

from horilla.http import Http404, HttpNotFound, HttpResponse, RefreshResponse
from horilla.shortcuts import get_object_or_404, redirect, render

# First-party / Horilla imports
from horilla.urls import reverse_lazy
from horilla.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required_or_denied,
)
from horilla.utils.translation import gettext_lazy as _
from horilla_generics.forms import HorillaModelForm
from horilla_generics.views import HorillaSingleFormView
from horilla_reports.forms import ChangeChartReportForm, ReportForm
from horilla_reports.models import Report, ReportFolder
from horilla_reports.views.report_detail import ReportDetailView
from horilla_reports.views.toolkit.report_helper import (
    TEMP_REPORT_FIELDS,
    create_temp_report_with_preview,
)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["reports.view_report", "reports.view_own_report"]),
    name="dispatch",
)
class ChangeChartTypeView(LoginRequiredMixin, HorillaSingleFormView):
    """View for changing the chart type (bar, line, pie, etc.) of a report."""

    model = Report
    fields = ["chart_type"]
    modal_height = False
    full_width_fields = ["chart_type"]
    form_class = ChangeChartReportForm

    @cached_property
    def form_url(self):
        """Return the form URL for the change chart type view."""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("horilla_reports:change_chart_type", kwargs={"pk": pk})
        return None


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["horilla_reports.view_report", "horilla_reports.view_own_report"]
    ),
    name="dispatch",
)
class ChangeChartFieldView(LoginRequiredMixin, HorillaSingleFormView):
    """View for changing the primary and secondary chart fields for a report."""

    model = Report
    fields = ["chart_field", "chart_field_stacked"]
    modal_height = False
    full_width_fields = ["chart_field", "chart_field_stacked"]
    save_and_new = False

    def get_form_class(self):
        report = get_object_or_404(Report, pk=self.kwargs["pk"])

        # Check if we have preview data in session
        session_key = f"report_preview_{report.pk}"
        preview_data = self.request.session.get(session_key, {})

        if preview_data:
            temp_report = self.create_temp_report(report, preview_data)
        else:
            temp_report = report

        field_choices = []

        # Add row groups to choices
        for field_name in temp_report.row_groups_list:
            try:
                field = temp_report.model_class._meta.get_field(field_name)
                verbose_name = field.verbose_name.title()
                field_choices.append((field_name, f"{verbose_name} (Row Group)"))
            except Exception:
                field_choices.append((field_name, f"{field_name.title()} (Row Group)"))

        # Add column groups to choices
        for field_name in temp_report.column_groups_list:
            try:
                field = temp_report.model_class._meta.get_field(field_name)
                verbose_name = field.verbose_name.title()
                field_choices.append((field_name, f"{verbose_name} (Column Group)"))
            except Exception:
                field_choices.append(
                    (field_name, f"{field_name.title()} (Column Group)")
                )

        # Add empty choice for clearing the field
        field_choices.insert(0, ("", "-- Select Chart Field --"))

        class ChartFieldForm(HorillaModelForm):
            """Dynamically generated form for selecting chart fields."""

            chart_field = forms.ChoiceField(
                choices=field_choices,
                label="Primary Chart Field",
                required=False,  # Allow empty selection
                widget=forms.Select(attrs={"class": "w-full p-2 border rounded"}),
            )

            chart_field_stacked = forms.ChoiceField(
                choices=field_choices,
                label="Secondary Field (For Stacked Charts)",
                required=False,  # Allow empty selection
                widget=forms.Select(attrs={"class": "w-full p-2 border rounded"}),
            )

            class Meta:
                """Meta options for ChartFieldForm."""

                model = Report
                fields = ["chart_field", "chart_field_stacked"]

        return ChartFieldForm

    def get_initial(self):
        """Get initial form data from preview or database"""
        report = get_object_or_404(Report, pk=self.kwargs["pk"])

        session_key = f"report_preview_{report.pk}"
        preview_data = self.request.session.get(session_key, {})

        initial = super().get_initial()

        if preview_data:
            initial["chart_field"] = preview_data.get("chart_field", "")
            initial["chart_field_stacked"] = preview_data.get("chart_field_stacked", "")
        else:
            initial["chart_field"] = report.chart_field or ""
            initial["chart_field_stacked"] = report.chart_field_stacked or ""

        return initial

    def create_temp_report(self, original_report, preview_data):
        """Create a temporary report object with preview data applied"""
        temp_report = copy.copy(original_report)

        for field in TEMP_REPORT_FIELDS:
            if field in preview_data:
                setattr(temp_report, field, preview_data[field])
        return temp_report

    def form_valid(self, form):
        report = get_object_or_404(Report, pk=self.kwargs["pk"])
        chart_field_value = form.cleaned_data.get("chart_field")
        chart_field_stacked_value = form.cleaned_data.get("chart_field_stacked")

        # Check if we have preview data in session (preview mode)
        session_key = f"report_preview_{report.pk}"
        preview_data = self.request.session.get(session_key, {})

        if preview_data:
            preview_data["chart_field"] = chart_field_value
            preview_data["chart_field_stacked"] = chart_field_stacked_value
            self.request.session[session_key] = preview_data
            self.request.session.modified = True
        else:
            report.chart_field = chart_field_value
            report.chart_field_stacked = chart_field_stacked_value
            report.save(update_fields=["chart_field", "chart_field_stacked"])

        return HttpResponse("<script>$('#reloadButton').click();closeModal();</script>")

    @cached_property
    def form_url(self):
        """Return the form URL for changing the chart field (preview-aware)."""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("horilla_reports:change_chart_field", kwargs={"pk": pk})
        return None


@method_decorator(htmx_required, name="dispatch")
class CreateReportView(LoginRequiredMixin, HorillaSingleFormView):
    """View for creating new reports with module, columns, and folder selection."""

    model = Report
    fields = ["name", "module", "folder", "selected_columns", "report_owner"]
    modal_height = False
    form_class = ReportForm
    hidden_fields = ["report_owner"]
    full_width_fields = ["name", "module", "folder", "selected_columns"]
    detail_url_name = "horilla_reports:report_detail"

    @cached_property
    def form_url(self):
        """Return the form URL for creating a new report."""
        return reverse_lazy("horilla_reports:create_report")

    def get_initial(self):
        """Set initial folder from query param and report_owner to current user."""
        initial = super().get_initial()
        pk = self.request.GET.get("pk")
        initial["folder"] = pk if pk else None
        initial["report_owner"] = self.request.user
        return initial

    def form_invalid(self, form):
        module_id = self.request.POST.get("module") or (
            form.instance.module.id if form.instance.module else None
        )
        selected_values = self.request.POST.getlist("selected_columns") or (
            form.instance.selected_columns.split(",")
            if form.instance.selected_columns
            else []
        )
        choices = []
        if module_id:
            try:
                content_type = ContentType.objects.get(id=module_id)
                temp_report = Report(module=content_type)
                fields = temp_report.get_available_fields()
                choices = [
                    (field["name"], f"{field['verbose_name']}") for field in fields
                ]
            except ContentType.DoesNotExist:
                choices = []

        form.fields["selected_columns"].choices = choices
        form.fields["selected_columns"].widget.choices = choices
        if selected_values:
            form.fields["selected_columns"].widget.value = selected_values
        return super().form_invalid(form)


@method_decorator(htmx_required, name="dispatch")
class UpdateReportView(LoginRequiredMixin, HorillaSingleFormView):
    """View for updating report name and basic information."""

    model = Report
    fields = ["name"]
    modal_height = False
    full_width_fields = ["name"]
    detail_url_name = "horilla_reports:report_detail"

    @cached_property
    def form_url(self):
        """Return the form URL for updating a report."""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("horilla_reports:update_report", kwargs={"pk": pk})
        return None

    def get(self, request, *args, **kwargs):
        """Allow GET only if user has change/add permission or is the report owner."""
        report_id = self.kwargs.get("pk")
        if request.user.has_perm(
            "horilla_reports.change_report"
        ) or request.user.has_perm("horilla_reports.add_report"):
            return super().get(request, *args, **kwargs)

        if report_id:
            try:
                report = get_object_or_404(Report, pk=report_id)
            except Http404:
                messages.error(
                    request,
                    f"{self.model._meta.verbose_name.title()} not found or no longer exists.",
                )
                return HttpResponse(
                    "<script>$('#reloadButton').click();closeModal();</script>"
                )
            if report.report_owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")


@method_decorator(htmx_required, name="dispatch")
class MoveReportView(LoginRequiredMixin, HorillaSingleFormView):
    """View for moving reports between folders."""

    model = Report
    fields = ["folder"]
    modal_height = False
    full_width_fields = ["folder"]

    @cached_property
    def form_url(self):
        """Return the form URL for moving a report to a folder."""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "horilla_reports:move_report_to_folder", kwargs={"pk": pk}
            )
        return None

    def get(self, request, *args, **kwargs):
        """Allow GET only if user has change/add permission or is the report owner."""
        report_id = self.kwargs.get("pk")
        if request.user.has_perm(
            "horilla_reports.change_report"
        ) or request.user.has_perm("horilla_reports.add_report"):
            return super().get(request, *args, **kwargs)

        if report_id:
            try:
                report = get_object_or_404(Report, pk=report_id)
            except Http404:
                messages.error(
                    request,
                    f"{self.model._meta.verbose_name.title()} not found or no longer exists.",
                )
                return HttpResponse(
                    "<script>$('#reloadButton').click();closeModal();</script>"
                )
            if report.report_owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")

    def get_form(self, form_class=None):
        """Return form with folder widget styling and queryset limited to user's folders for non-superusers."""
        form = super().get_form(form_class)
        user = getattr(self.request, "user", None)
        if user:
            form.fields["folder"].widget.attrs.update(
                {
                    "class": "js-example-basic-single",
                }
            )
            if not user.is_superuser:
                form.fields["folder"].queryset = ReportFolder.objects.filter(
                    report_folder_owner=user
                )
        return form


@method_decorator(htmx_required, name="dispatch")
class MoveFolderView(LoginRequiredMixin, HorillaSingleFormView):
    """View for moving report folders to different parent folders."""

    model = ReportFolder
    fields = ["parent"]
    modal_height = False
    full_width_fields = ["parent"]

    @cached_property
    def form_url(self):
        """Return the form URL for moving a folder to a different parent folder."""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "horilla_reports:move_folder_to_folder", kwargs={"pk": pk}
            )
        return None

    def get(self, request, *args, **kwargs):
        """Allow GET only if user has change/add permission or is the folder owner."""
        folder_id = self.kwargs.get("pk")
        if request.user.has_perm(
            "horilla_reports.change_report"
        ) or request.user.has_perm("horilla_reports.add_report"):
            return super().get(request, *args, **kwargs)

        if folder_id:
            try:
                folder = get_object_or_404(ReportFolder, pk=folder_id)
            except Http404:
                messages.error(
                    request,
                    f"{self.model._meta.verbose_name.title()} not found or no longer exists.",
                )
                return HttpResponse(
                    "<script>$('#reloadButton').click();closeModal();</script>"
                )
            if folder.report_folder_owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")

    def get_form(self, form_class=None):
        """Return form with parent widget styling and queryset limited to user's folders for non-superusers."""
        form = super().get_form(form_class)
        user = getattr(self.request, "user", None)
        if user:
            form.fields["parent"].widget.attrs.update(
                {
                    "class": "js-example-basic-single",
                }
            )
            if not user.is_superuser:
                form.fields["parent"].queryset = ReportFolder.objects.filter(
                    report_folder_owner=user
                )
        return form


@method_decorator(htmx_required, name="dispatch")
class GetModuleColumnsHTMXView(LoginRequiredMixin, View):
    """HTMX view to return updated selected_columns field based on module selection"""

    def get(self, request, *args, **kwargs):
        """Handle GET request to return updated selected_columns widget HTML based on module."""
        module_id = request.GET.get("module")

        widget_html = self.get_columns_widget_html(module_id)

        return HttpResponse(widget_html)

    def get_columns_widget_html(self, module_id):
        """Generate HTML for the select widget with choices based on module"""
        choices = []

        if module_id:
            try:
                content_type = ContentType.objects.get(id=module_id)
                temp_report = Report(module=content_type)
                fields = temp_report.get_available_fields()

                choices = [
                    (field["name"], f"{field['verbose_name']}") for field in fields
                ]
            except ContentType.DoesNotExist:
                choices = []

        widget = forms.SelectMultiple(
            attrs={
                "class": "js-example-basic-multiple headselect w-full",
                "id": "id_columns",
                "name": "selected_columns",
                "tabindex": "-1",
                "aria-hidden": "true",
                "multiple": True,
            }
        )

        field = forms.MultipleChoiceField(
            choices=choices, widget=widget, required=False
        )
        return field.widget.render("selected_columns", None, attrs=widget.attrs)


@method_decorator(
    permission_required_or_denied(["reports.view_report", "reports.view_own_report"]),
    name="dispatch",
)
class ReportUpdateView(LoginRequiredMixin, DetailView):
    """View for updating report configuration in a panel interface."""

    model = Report
    template_name = "partials/report_panel.html"
    context_object_name = "report"

    def dispatch(self, request, *args, **kwargs):
        """Ensure user is authenticated and report exists before dispatching."""
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        try:
            self.object = self.get_object()
        except Exception as e:
            if request.headers.get("HX-Request") == "true":
                messages.error(self.request, e)
                return RefreshResponse(request)
            raise HttpNotFound(e)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Build context with report, preview data, active tab, and available fields for the panel."""
        context = super().get_context_data(**kwargs)
        report = self.object
        model_class = report.model_class

        # Get preview data for panel display
        session_key = f"report_preview_{report.pk}"
        preview_data = self.request.session.get(session_key, {})

        # Get the active tab from request (for maintaining state)
        active_tab = self.request.GET.get("active_tab", "columns")
        context["active_tab"] = active_tab

        temp_report = self.create_temp_report(report, preview_data)
        context["report"] = temp_report
        context["has_unsaved_changes"] = bool(preview_data)
        context["panel_open"] = True

        available_fields = []
        for field in model_class._meta.get_fields():
            if not field.many_to_many and not field.one_to_many:
                if field.name in ("id", "pk"):
                    continue
                if not getattr(field, "editable", True):
                    continue
                available_fields.append(
                    {
                        "name": field.name,
                        "verbose_name": field.verbose_name,
                        "field_type": field.__class__.__name__,
                    }
                )

        context["available_fields"] = available_fields
        return context

    def create_temp_report(self, original_report, preview_data):
        """Create a temporary report object with preview data."""
        return create_temp_report_with_preview(original_report, preview_data)


@method_decorator(
    permission_required_or_denied(["reports.view_report", "reports.view_own_report"]),
    name="dispatch",
)
class DiscardReportChangesView(LoginRequiredMixin, View):
    """View for discarding temporary report configuration changes."""

    @method_decorator(require_POST)
    def dispatch(self, *args, **kwargs):
        """Restrict to POST and delegate to parent dispatch."""
        return super().dispatch(*args, **kwargs)

    def post(self, request, pk):
        """Discard any preview changes for the given report by clearing session data."""
        try:
            report = get_object_or_404(Report, pk=pk)
        except Exception as e:
            messages.error(request, str(e))
            return RefreshResponse(request)

        session_key = f"report_preview_{pk}"

        # Clear the session preview data
        if session_key in request.session:
            del request.session[session_key]

        # Use ReportDetailView to get the full context
        detail_view = ReportDetailView()
        detail_view.request = request
        detail_view.object = report
        context = detail_view.get_context_data()

        # Ensure panel is closed and no unsaved changes
        context["panel_open"] = False
        context["has_unsaved_changes"] = False

        # Render the report_detail.html template with the full context
        return render(request, "report_detail.html", context)


@method_decorator(
    permission_required_or_denied(["reports.view_report", "reports.view_own_report"]),
    name="dispatch",
)
class SaveReportChangesView(LoginRequiredMixin, View):
    """View for saving temporary report configuration changes."""

    @method_decorator(require_POST)
    def dispatch(self, *args, **kwargs):
        """Restrict to POST and delegate to parent dispatch."""
        return super().dispatch(*args, **kwargs)

    def post(self, request, pk):
        """Persist preview changes to the Report model when requested."""
        try:
            report = get_object_or_404(Report, pk=pk)
        except Exception as e:
            messages.error(request, str(e))
            return RefreshResponse(request)

        session_key = f"report_preview_{report.pk}"
        preview_data = request.session.get(session_key, {})

        if preview_data:
            # Apply all changes to the actual model
            for field in TEMP_REPORT_FIELDS:
                if field in preview_data:
                    setattr(report, field, preview_data[field])
            report.save()

            # Clear the session preview data
            if session_key in request.session:
                del request.session[session_key]

        # Use ReportDetailView to get the full context
        detail_view = ReportDetailView()
        detail_view.request = request
        detail_view.object = report
        context = detail_view.get_context_data()

        # Ensure panel is closed and no unsaved changes
        context["panel_open"] = False
        context["has_unsaved_changes"] = False

        # Render the report_detail.html template with the full context
        return render(request, "report_detail.html", context)


@method_decorator(
    permission_required_or_denied(
        ["horilla_reports.view_report", "horilla_reports.view_own_report"]
    ),
    name="dispatch",
)
class CloseReportPanelView(LoginRequiredMixin, View):
    """View for closing the report configuration panel and returning to detail view."""

    def get(self, request, pk):
        """Close the report panel and redirect to detail view"""
        # Clear any session data if needed
        session_key = f"report_preview_{pk}"
        if session_key in request.session:
            pass

        return redirect("horilla_reports:report_detail", pk=pk)
