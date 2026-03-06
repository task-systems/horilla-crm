"""Views for displaying interactive report details and pivots."""

import logging
from urllib.parse import urlencode, urlparse

# Third-party imports (Others)
import pandas as pd
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db.models import ForeignKey, Q
from django.views.generic import DetailView

from horilla.http import HttpNotFound, RefreshResponse
from horilla.shortcuts import render
from horilla.urls import reverse_lazy
from horilla.utils.decorators import method_decorator, permission_required_or_denied
from horilla_generics.mixins import RecentlyViewedMixin
from horilla_generics.views import HorillaListView
from horilla_reports.models import Report
from horilla_reports.views.toolkit.report_detail_mixin import ReportDetailDataMixin
from horilla_utils.methods import get_section_info_for_model

logger = logging.getLogger(__name__)


@method_decorator(
    permission_required_or_denied(
        ["horilla_reports.view_report", "horilla_reports.view_own_report"]
    ),
    name="dispatch",
)
class ReportDetailView(ReportDetailDataMixin, RecentlyViewedMixin, DetailView):
    """Detail view for displaying individual report with data and configuration."""

    model = Report
    template_name = "report_detail.html"
    context_object_name = "report"

    def dispatch(self, request, *args, **kwargs):
        """Ensure the user is authenticated and the object exists; handle HTMX errors gracefully."""
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

    def col_attrs(self):
        """Define column attributes for clickable rows in the report list view."""
        query_params = {}
        report = self.object
        model_class = report.model_class
        section = get_section_info_for_model(model_class)
        section_value = section["section"]
        query_params["section"] = section_value
        query_params["session_url"] = False
        query_string = urlencode(query_params)
        attrs = {}

        if self.request.user.has_perm("horilla_reports.view_report"):
            attrs = {
                "hx-get": f"{{get_detail_url}}?{query_string}",
                "hx-target": "#mainContent",
                "hx-swap": "outerHTML",
                "hx-push-url": "true",
                "hx-select-oob": "#sideMenuContainer",
                "hx-select": "#mainContent",
                "style": "cursor:pointer",
                "class": "hover:text-primary-600",
            }

        columns_with_attrs = []

        for col in report.selected_columns_list:
            columns_with_attrs.append({col: {**attrs}})

        return columns_with_attrs

    def get(self, request, *args, **kwargs):
        """Return the report detail if the user has permission to view it; otherwise render 403."""
        self.object = self.get_object()
        if not self.model.objects.filter(
            report_owner_id=self.request.user, pk=self.kwargs["pk"]
        ).first() and not self.request.user.has_perm("horilla_reports.view_report"):
            return render(self.request, "error/403.html")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Build the context data for the report detail view including preview and aggregate info."""
        context = super().get_context_data(**kwargs)
        report = self.object

        session_key = f"report_preview_{report.pk}"
        preview_data = self.request.session.get(session_key, {})

        temp_report = self.create_temp_report(report, preview_data)

        aggregate_columns_dict = temp_report.aggregate_columns_dict
        if not isinstance(aggregate_columns_dict, list):
            aggregate_columns_dict = (
                [aggregate_columns_dict] if aggregate_columns_dict else []
            )

        # Get model data
        model_class = temp_report.model_class

        fields = []
        if temp_report.selected_columns_list:
            fields.extend(temp_report.selected_columns_list)
        if temp_report.row_groups_list:
            fields.extend(temp_report.row_groups_list)
        if temp_report.column_groups_list:
            fields.extend(temp_report.column_groups_list)
        for agg in aggregate_columns_dict:
            if agg.get("field"):
                fields.append(agg["field"])

        # Remove duplicates while preserving order
        fields = list(dict.fromkeys(fields))

        # Optimize: Create base queryset with select_related for foreign keys
        # This reduces N+1 queries significantly
        base_queryset = model_class.objects.all()

        # Optimize: Add select_related/prefetch_related for foreign key fields
        select_related_fields = []
        for field_name in fields:
            try:
                field = model_class._meta.get_field(field_name)
                if isinstance(field, ForeignKey):
                    select_related_fields.append(field_name)
            except Exception:
                pass

        if select_related_fields:
            # Remove duplicates from select_related_fields
            select_related_fields = list(dict.fromkeys(select_related_fields))
            base_queryset = base_queryset.select_related(*select_related_fields)

        # Apply filters
        filters = temp_report.filters_dict
        if filters:
            query = None
            for index, (field_name, filter_data) in enumerate(filters.items()):
                if not filter_data.get("value"):
                    continue  # Skip empty filters
                operator = filter_data.get("operator", "exact")
                value = filter_data.get("value")
                logic = (
                    filter_data.get("logic", "and") if index > 0 else "and"
                )  # Default to AND for first filter

                # Use original_field instead of field_name
                actual_field = filter_data.get("original_field", field_name)

                # Construct filter kwargs
                filter_kwargs = {}
                if operator == "exact":
                    filter_kwargs[f"{actual_field}"] = value
                elif operator == "icontains":
                    filter_kwargs[f"{actual_field}__icontains"] = value
                elif operator == "gt":
                    filter_kwargs[f"{actual_field}__gt"] = value
                elif operator == "lt":
                    filter_kwargs[f"{actual_field}__lt"] = value
                elif operator == "gte":
                    filter_kwargs[f"{actual_field}__gte"] = value
                elif operator == "lte":
                    filter_kwargs[f"{actual_field}__lte"] = value

                # Combine filters with AND or OR
                if not filter_kwargs:
                    continue
                current_query = Q(**filter_kwargs)

                if query is None:
                    query = current_query
                elif logic == "or":
                    query |= current_query
                else:  # logic == 'and'
                    query &= current_query

            if query:
                base_queryset = base_queryset.filter(query)

        if fields:
            data_queryset = base_queryset.values(*fields)
            data = list(data_queryset.iterator(chunk_size=1000))
        else:
            data = []

        if data:
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame(columns=fields if fields else [])

        queryset = base_queryset

        context["panel_open"] = bool(preview_data)
        context["hierarchical_data"] = []
        context["pivot_columns"] = []
        context["pivot_table"] = {}
        context["pivot_index"] = []
        context["aggregate_columns"] = []
        context["has_hierarchical_groups"] = len(temp_report.row_groups_list) > 1
        context["configuration_type"] = self.get_configuration_type(temp_report)
        panel_open = self.request.GET.get("panel_open") == "true" or bool(preview_data)
        context["panel_open"] = panel_open
        context["has_unsaved_changes"] = bool(preview_data)

        # Add verbose names for row and column groups
        context["row_group_verbose_names"] = [
            model_class._meta.get_field(field_name).verbose_name.title()
            for field_name in temp_report.row_groups_list
        ]
        context["column_group_verbose_names"] = [
            model_class._meta.get_field(field_name).verbose_name.title()
            for field_name in temp_report.column_groups_list
        ]

        all_grouping_fields = (
            temp_report.row_groups_list + temp_report.column_groups_list
        )
        fk_cache = (
            self._batch_load_foreign_keys(df, model_class, all_grouping_fields)
            if not df.empty
            else {}
        )

        context["_fk_cache"] = fk_cache

        row_count = len(temp_report.row_groups_list)
        col_count = len(temp_report.column_groups_list)

        if row_count == 0 and col_count == 0:
            self.handle_0_row_0_col(df, temp_report, context)
        elif row_count == 1 and col_count == 0:
            self.handle_1_row_0_col(df, temp_report, context, fk_cache)
        elif row_count == 1 and col_count == 1:
            self.handle_1_row_1_col(df, temp_report, context, fk_cache)
        elif row_count == 1 and col_count == 2:
            self.handle_1_row_2_col(df, temp_report, context, fk_cache)
        elif row_count == 2 and col_count == 0:
            self.handle_2_row_0_col(df, temp_report, context, fk_cache)
        elif row_count == 2 and col_count == 1:
            self.handle_2_row_1_col(df, temp_report, context, fk_cache)
        elif row_count == 3 and col_count == 0:
            self.handle_3_row_0_col(df, temp_report, context, fk_cache)
        else:
            context["error"] = (
                f"Configuration not supported: {row_count} rows, {col_count} columns"
            )

        chart_data = self.generate_chart_data(df, temp_report, fk_cache)
        context["chart_data"] = chart_data
        context["total_count"] = len(data)
        context["total_amount"] = sum(
            [
                float(
                    df[agg["field"]].sum()
                    if agg["field"] in df.columns and agg.get("aggfunc") == "sum"
                    else 0
                )
                for agg in aggregate_columns_dict
            ]
        )

        columns = []
        for col in temp_report.selected_columns_list:
            field = model_class._meta.get_field(col)
            verbose_name = field.verbose_name.title()
            if field.choices:
                columns.append((verbose_name, f"get_{col}_display"))
            else:
                columns.append((verbose_name, col))

        list_view = HorillaListView(
            model=model_class,
            view_id="report-details-sec",
            search_url=reverse_lazy(
                "horilla_reports:report_detail", kwargs={"pk": report.pk}
            ),
            main_url=reverse_lazy(
                "horilla_reports:report_detail", kwargs={"pk": report.pk}
            ),
            table_width=False,
            columns=columns,
        )
        list_view.request = self.request
        list_view.table_width = False
        list_view.bulk_select_option = False
        list_view.list_column_visibility = False
        list_view.paginate_by = 10
        list_view.table_height = False
        list_view.table_height_as_class = "h-[200px]"
        if hasattr(report.model_class, "get_detail_url"):
            list_view.col_attrs = self.col_attrs()
        sort_field = self.request.GET.get("sort")
        sort_direction = self.request.GET.get("direction", "asc")

        # Apply sorting to the queryset for list view
        if sort_field:
            queryset = list_view._apply_sorting(queryset, sort_field, sort_direction)
        else:
            queryset = queryset.order_by("-id")
        list_view.object_list = queryset
        context.update(list_view.get_context_data(object_list=queryset))

        session_referer_key = f"report_detail_referer_{report.pk}"
        current_referer = self.request.META.get("HTTP_REFERER")
        hx_current_url = self.request.headers.get("HX-Current-URL")
        stored_referer = self.request.session.get(session_referer_key)
        report_detail_base = f"/reports/report-detail/{report.pk}/"
        session_url_value = self.request.GET.get("session_url")

        if hx_current_url:
            hx_path = urlparse(hx_current_url).path
            is_from_report_detail = hx_path == report_detail_base
            if not is_from_report_detail and session_url_value != "False":
                self.request.session[session_referer_key] = hx_current_url
                previous_url = hx_current_url
            else:
                previous_url = (
                    stored_referer
                    if stored_referer
                    else reverse_lazy("horilla_reports:reports_list_view")
                )
        elif stored_referer:
            previous_url = stored_referer
        elif current_referer and self.request.get_host() in current_referer:
            referer_path = urlparse(current_referer).path
            if referer_path != report_detail_base:
                previous_url = current_referer
                self.request.session[session_referer_key] = current_referer
            else:
                previous_url = reverse_lazy("horilla_reports:reports_list_view")
        else:
            previous_url = reverse_lazy("horilla_reports:reports_list_view")
        context["previous_url"] = previous_url
        context["total_groups_count"] = len(temp_report.row_groups_list) + len(
            temp_report.column_groups_list
        )
        return context

    def generate_chart_data(self, df, report, fk_cache=None):
        """Generate chart-friendly labels and datasets for the given DataFrame and report configuration."""
        chart_data = {
            "labels": [],
            "data": [],
            "type": report.chart_type,
            "label_field": "Count",
            "stacked_data": {},
            "has_multiple_groups": False,
            "urls": [],
        }

        if df.empty:
            return chart_data

        config_type = self.get_configuration_type(report)
        model_class = report.model_class
        section_info = get_section_info_for_model(model_class)

        total_groups = len(report.row_groups_list) + len(report.column_groups_list)
        chart_data["has_multiple_groups"] = total_groups >= 2

        try:
            if config_type == "0_row_0_col":
                chart_data["labels"] = ["Records"]
                chart_data["data"] = [len(df)]
                chart_data["label_field"] = "Records"
                chart_data["urls"] = [section_info["url"]]

            elif (
                report.chart_type in ["stacked_vertical", "stacked_horizontal"]
                and chart_data["has_multiple_groups"]
            ):
                chart_data.update(
                    self._generate_stacked_chart_data(df, report, model_class, fk_cache)
                )

            else:
                chart_field = None

                if (
                    hasattr(report, "chart_field")
                    and report.chart_field
                    and report.chart_field in df.columns
                ):
                    chart_field = report.chart_field
                elif report.row_groups_list and report.row_groups_list[0] in df.columns:
                    chart_field = report.row_groups_list[0]
                    if not hasattr(report, "_temp_report"):
                        if not report.chart_field:
                            report.chart_field = chart_field
                            report.save(update_fields=["chart_field"])
                elif (
                    report.column_groups_list
                    and report.column_groups_list[0] in df.columns
                ):
                    chart_field = report.column_groups_list[0]
                    if not hasattr(report, "_temp_report"):
                        if not report.chart_field:
                            report.chart_field = chart_field
                            report.save(update_fields=["chart_field"])

                if chart_field:
                    grouped = df.groupby(chart_field).size()

                    display_labels = []
                    display_count = {}

                    for k in grouped.index:
                        display_info = self.get_display_value(
                            k, chart_field, model_class, fk_cache
                        )
                        if isinstance(display_info, dict):
                            base_display = display_info["display"]
                        else:
                            base_display = str(display_info)

                        if base_display in display_count:
                            display_count[base_display] += 1
                            unique_label = (
                                f"{base_display} ({display_count[base_display]})"
                            )
                        else:
                            display_count[base_display] = 1
                            unique_label = base_display

                        display_labels.append(unique_label)

                    chart_data["labels"] = display_labels
                    chart_data["data"] = [float(v) for v in grouped.values]
                    chart_data["label_field"] = self.get_verbose_name(
                        chart_field, model_class
                    )
                    urls = []
                    for value in grouped.index:
                        query = urlencode(
                            {
                                "section": section_info["section"],
                                "apply_filter": "true",
                                "field": chart_field,
                                "operator": "exact",
                                "value": value if value is not None else "",
                            }
                        )
                        urls.append(f"{section_info['url']}?{query}")
                    chart_data["urls"] = urls
                else:
                    chart_data["labels"] = ["Records"]
                    chart_data["data"] = [len(df)]
                    chart_data["label_field"] = "Records"
                    chart_data["urls"] = [section_info["url"]]

        except Exception as e:
            chart_data["error"] = f"Error generating chart data: {str(e)}"

        return chart_data

    def _generate_stacked_chart_data(self, df, report, model_class, fk_cache=None):
        """Generate data for stacked charts when multiple grouping fields are available."""
        try:
            primary_field = None
            secondary_field = None

            if (
                hasattr(report, "chart_field")
                and report.chart_field
                and report.chart_field in df.columns
            ):
                primary_field = report.chart_field

                if (
                    hasattr(report, "chart_field_stacked")
                    and report.chart_field_stacked
                    and report.chart_field_stacked in df.columns
                    and report.chart_field_stacked != primary_field
                ):
                    secondary_field = report.chart_field_stacked

            elif (
                hasattr(report, "chart_field_stacked")
                and report.chart_field_stacked
                and report.chart_field_stacked in df.columns
            ):
                secondary_field = report.chart_field_stacked
                all_fields = report.row_groups_list + report.column_groups_list
                primary_field = next(
                    (f for f in all_fields if f != secondary_field and f in df.columns),
                    None,
                )

            if not primary_field or not secondary_field:
                if report.row_groups_list and report.column_groups_list:
                    if not primary_field:
                        primary_field = report.row_groups_list[0]
                    if not secondary_field:
                        secondary_field = report.column_groups_list[0]
                elif len(report.row_groups_list) >= 2:
                    if not primary_field:
                        primary_field = report.row_groups_list[0]
                    if not secondary_field:
                        secondary_field = report.row_groups_list[1]
                elif len(report.column_groups_list) >= 2:
                    if not primary_field:
                        primary_field = report.column_groups_list[0]
                    if not secondary_field:
                        secondary_field = report.column_groups_list[1]

            if not primary_field or not secondary_field:
                return self._fallback_chart_data(df, report, model_class, fk_cache)

            if primary_field not in df.columns or secondary_field not in df.columns:
                return self._fallback_chart_data(df, report, model_class, fk_cache)

            if not hasattr(report, "_temp_report"):
                fields_to_update = []
                if not report.chart_field:
                    report.chart_field = primary_field
                    fields_to_update.append("chart_field")
                if not report.chart_field_stacked:
                    report.chart_field_stacked = secondary_field
                    fields_to_update.append("chart_field_stacked")
                if fields_to_update:
                    report.save(update_fields=fields_to_update)

            try:
                pivot_table = pd.pivot_table(
                    df,
                    index=[primary_field],
                    columns=[secondary_field],
                    aggfunc="size",
                    fill_value=0,
                )
            except Exception:
                return self._fallback_chart_data(df, report, model_class, fk_cache)

            if pivot_table.empty:
                return self._fallback_chart_data(df, report, model_class, fk_cache)

            categories = []
            category_count = {}

            for idx in pivot_table.index:
                display_info = self.get_display_value(
                    idx, primary_field, model_class, fk_cache
                )
                if isinstance(display_info, dict):
                    base_display = display_info["display"]
                else:
                    base_display = str(display_info)

                if base_display in category_count:
                    category_count[base_display] += 1
                    unique_label = f"{base_display} ({category_count[base_display]})"
                else:
                    category_count[base_display] = 1
                    unique_label = base_display

                categories.append(unique_label)

            series = []
            series_name_count = {}

            for col in pivot_table.columns:
                col_display_info = self.get_display_value(
                    col, secondary_field, model_class, fk_cache
                )
                if isinstance(col_display_info, dict):
                    base_col_display = col_display_info["display"]
                else:
                    base_col_display = str(col_display_info)

                if base_col_display in series_name_count:
                    series_name_count[base_col_display] += 1
                    col_display = (
                        f"{base_col_display} ({series_name_count[base_col_display]})"
                    )
                else:
                    series_name_count[base_col_display] = 1
                    col_display = base_col_display

                series_data = []

                for idx in pivot_table.index:
                    try:
                        value = pivot_table.loc[idx, col]
                        series_data.append(int(value) if pd.notna(value) else 0)
                    except Exception as val_error:
                        logger.error(
                            "Value extraction error for %s, %s: %s",
                            idx,
                            col,
                            str(val_error),
                        )
                        series_data.append(0)

                series.append({"name": col_display, "data": series_data})

            totals = []
            for i in range(len(categories)):
                total = sum(s["data"][i] for s in series if i < len(s["data"]))
                totals.append(total)

            section_info = get_section_info_for_model(model_class)
            urls = []
            for idx in pivot_table.index:
                query = urlencode(
                    {
                        "section": section_info["section"],
                        "apply_filter": "true",
                        "field": primary_field,
                        "operator": "exact",
                        "value": idx if idx is not None else "",
                    }
                )
                urls.append(f"{section_info['url']}?{query}")

            stacked_data = {"categories": categories, "series": series}

            primary_verbose = self.get_verbose_name(primary_field, model_class)
            secondary_verbose = self.get_verbose_name(secondary_field, model_class)

            return {
                "labels": categories,
                "data": totals,
                "urls": urls,
                "stacked_data": stacked_data,
                "label_field": f"{primary_verbose} by {secondary_verbose}",
                "has_stacked_data": True,
                "primary_field": primary_field,
                "secondary_field": secondary_field,
            }

        except Exception as e:
            logger.error("Error in stacked chart generation: %s", str(e))
            return self._fallback_chart_data(df, report, model_class)

    def _fallback_chart_data(self, df, report, model_class, fk_cache=None):
        """Fallback to simple chart when stacking fails."""
        fallback_field = None
        if (
            hasattr(report, "chart_field")
            and report.chart_field
            and report.chart_field in df.columns
        ):
            fallback_field = report.chart_field
        elif report.row_groups_list and report.row_groups_list[0] in df.columns:
            fallback_field = report.row_groups_list[0]
        elif report.column_groups_list and report.column_groups_list[0] in df.columns:
            fallback_field = report.column_groups_list[0]

        section_info = get_section_info_for_model(model_class)

        if fallback_field:
            try:
                grouped = df.groupby(fallback_field).size()

                display_labels = []
                display_count = {}

                for k in grouped.index:
                    display_info = self.get_display_value(
                        k, fallback_field, model_class, fk_cache
                    )
                    if isinstance(display_info, dict):
                        base_display = display_info["display"]
                    else:
                        base_display = str(display_info)

                    if base_display in display_count:
                        display_count[base_display] += 1
                        unique_label = f"{base_display} ({display_count[base_display]})"
                    else:
                        display_count[base_display] = 1
                        unique_label = base_display

                    display_labels.append(unique_label)

                urls = []
                for value in grouped.index:
                    query = urlencode(
                        {
                            "section": section_info["section"],
                            "apply_filter": "true",
                            "field": fallback_field,
                            "operator": "exact",
                            "value": value if value is not None else "",
                        }
                    )
                    urls.append(f"{section_info['url']}?{query}")

                return {
                    "labels": display_labels,
                    "data": [float(v) for v in grouped.values],
                    "urls": urls,
                    "stacked_data": {},
                    "label_field": self.get_verbose_name(fallback_field, model_class),
                    "has_stacked_data": False,
                }
            except Exception as e:
                logger.error("Fallback chart error: %s", str(e))

        return {
            "labels": ["Records"],
            "data": [len(df)],
            "urls": [section_info["url"]],
            "stacked_data": {},
            "label_field": "Records",
            "has_stacked_data": False,
        }
