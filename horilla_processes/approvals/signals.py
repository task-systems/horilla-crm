"""Signals for approvals job syncing and edit guards."""

# Third-party imports (Django)
from django.contrib import messages
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save

from horilla.apps import apps as horilla_apps
from horilla.http import HttpResponse

# First-party / Horilla imports
from horilla.registry.feature import FEATURE_REGISTRY
from horilla.utils.translation import gettext_lazy as _
from horilla_core.models.base import HorillaContentType
from horilla_generics.views.helpers.edit_field import UpdateFieldView
from horilla_generics.views.list import HorillaListView
from horilla_processes.approvals.models import ApprovalInstance
from horilla_utils.middlewares import _thread_local

# Local imports
from .utils import enforce_pending_edit_policy, sync_approval_instances_for_record


def _approval_models():
    return FEATURE_REGISTRY.get("approval_models", [])


def _is_approval_internal_model(model):
    return model._meta.app_label == "approvals"


def _on_registered_model_saved(sender, instance, created, **kwargs):
    """
    Run approval matching after the DB transaction commits.

    This lets the review-process post_save (and any other listeners) finish in the
    same transaction first, so pending ReviewJob rows exist when we evaluate
    """
    if getattr(_thread_local, "skip_approval_sync", False):
        return
    pk = getattr(instance, "pk", None)
    if pk is None:
        return

    def _sync():
        try:
            obj = sender.objects.get(pk=pk)
        except sender.DoesNotExist:
            return
        sync_approval_instances_for_record(obj, created=created)

    transaction.on_commit(_sync)


def _on_registered_model_pre_save(sender, instance, **kwargs):
    enforce_pending_edit_policy(instance)


def _on_registered_model_deleted(sender, instance, **kwargs):
    from horilla_core.models import HorillaContentType

    from .models import ApprovalInstance

    try:
        content_type = HorillaContentType.objects.get_for_model(sender)
        ApprovalInstance.objects.filter(
            content_type=content_type,
            object_id=str(instance.pk),
        ).delete()
    except Exception:
        pass


def _connect_registered_models():
    for model in _approval_models():
        if _is_approval_internal_model(model):
            continue
        post_save.connect(
            _on_registered_model_saved,
            sender=model,
            dispatch_uid=f"approvals_post_save_{model._meta.label_lower}",
        )
        pre_save.connect(
            _on_registered_model_pre_save,
            sender=model,
            dispatch_uid=f"approvals_pre_save_{model._meta.label_lower}",
        )
        post_delete.connect(
            _on_registered_model_deleted,
            sender=model,
            dispatch_uid=f"approvals_post_delete_{model._meta.label_lower}",
        )


def _patch_horilla_list_view():
    """Patch list querysets at runtime without editing generics code."""

    if getattr(HorillaListView, "_approval_list_patch_applied", False):
        return

    original_get_queryset = HorillaListView.get_queryset

    def patched_get_queryset(self):
        queryset = original_get_queryset(self)
        model = getattr(self, "model", None)
        if not model or model._meta.app_label == "approvals":
            return queryset
        try:
            content_type = HorillaContentType.objects.get_for_model(model)
            pending_object_ids = ApprovalInstance.objects.filter(
                content_type=content_type,
                status__in=["pending", "rejected"],
                is_active=True,
            ).values_list("object_id", flat=True)
            return queryset.exclude(pk__in=pending_object_ids)
        except Exception:
            return queryset

    HorillaListView.get_queryset = patched_get_queryset
    HorillaListView._approval_list_patch_applied = True


def _patch_update_field_view():
    """
    Ensure UpdateFieldView.post() properly handles inline edits within the approval workflow by redirecting back to the current page when updates are blocked due to pending or rejected approval, and also redirecting after a successful update that creates a pending approval so the view reflects the updated state.
    """
    if getattr(UpdateFieldView, "_approval_patch_applied", False):
        return

    original_post = UpdateFieldView.post

    def _get_list_redirect_url(request, model_name, pk):
        """
        Return the list/parent URL to redirect to after an approval event.
        Tries (in order):
          1. The stored detail-referer session key set by HorillaDetailView
             when the user navigated from the list to this detail view.
          2. HTTP_REFERER header.
          3. "/" as a last resort.
        """
        session_key = f"detail_referer_{model_name}_{pk}"
        url = request.session.get(session_key)
        if url:
            return url
        return request.META.get("HTTP_REFERER") or "/"

    def patched_post(self, request, pk, field_name, app_label, model_name):
        response = original_post(self, request, pk, field_name, app_label, model_name)

        # ── Case 1: save blocked by approval edit-guard ──────────────────────
        if response.status_code == 400:
            content = response.content.decode("utf-8", errors="ignore")
            approval_phrases = (
                "pending approval",
                "rejected state",
            )
            if any(phrase in content.lower() for phrase in approval_phrases):
                messages.warning(
                    request,
                    str(_("This record is pending approval and cannot be edited.")),
                )
                resp = HttpResponse()
                resp["HX-Redirect"] = _get_list_redirect_url(request, model_name, pk)
                return resp
            return response

        # ── Case 2: save succeeded — check if it created a pending approval ──
        if response.status_code == 200:
            try:
                model = horilla_apps.get_model(app_label, model_name)
                ct = HorillaContentType.objects.get_for_model(model)
                is_pending = ApprovalInstance.objects.filter(
                    content_type=ct,
                    object_id=str(pk),
                    status="pending",
                    is_active=True,
                ).exists()

                if is_pending:
                    messages.success(
                        request,
                        str(_("Record has been submitted for approval.")),
                    )
                    resp = HttpResponse()
                    resp["HX-Redirect"] = _get_list_redirect_url(
                        request, model_name, pk
                    )
                    return resp
            except Exception:
                pass

        return response

    UpdateFieldView.post = patched_post
    UpdateFieldView._approval_patch_applied = True


_connect_registered_models()
_patch_horilla_list_view()
_patch_update_field_view()
