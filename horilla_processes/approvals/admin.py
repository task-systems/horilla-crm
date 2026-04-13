"""
Admin registration for the approvals app.
"""

# Third-party imports (Django)
from django.contrib import admin

# First-party / Horilla imports
from horilla_processes.approvals.models import (
    ApprovalCondition,
    ApprovalDecision,
    ApprovalInstance,
    ApprovalProcessRule,
    ApprovalRule,
    ApprovalStep,
)


@admin.register(ApprovalRule)
class ApprovalRuleAdmin(admin.ModelAdmin):
    """Admin configuration for ApprovalRule."""

    list_display = (
        "name",
        "model",
        "is_active",
        "trigger_on_create",
        "trigger_on_edit",
        "company",
    )
    list_filter = ("is_active", "trigger_on_create", "trigger_on_edit", "company")
    search_fields = ("name", "description")
    raw_id_fields = ("model", "company", "created_by", "updated_by")


@admin.register(ApprovalProcessRule)
class ApprovalProcessRuleAdmin(admin.ModelAdmin):
    """Admin configuration for ApprovalProcessRule."""

    list_display = ("approval_process", "order", "is_active", "company")
    list_filter = ("is_active", "company")
    search_fields = ("approval_process__name",)
    raw_id_fields = ("approval_process", "company", "created_by", "updated_by")


@admin.register(ApprovalStep)
class ApprovalStepAdmin(admin.ModelAdmin):
    """Admin configuration for ApprovalStep."""

    list_display = (
        "approval_process_rule",
        "order",
        "approver_type",
        "approver_user",
        "is_active",
    )
    list_filter = ("approver_type", "is_active")
    search_fields = ("approval_process_rule__approval_process__name", "role_identifier")
    raw_id_fields = (
        "approval_process_rule",
        "approver_user",
        "company",
        "created_by",
        "updated_by",
    )


@admin.register(ApprovalCondition)
class ApprovalConditionAdmin(admin.ModelAdmin):
    """Admin configuration for ApprovalCondition."""

    list_display = ("approval_process_rule", "field", "operator", "value", "order")
    list_filter = ("operator", "logical_operator")
    search_fields = ("field", "value", "approval_process_rule__approval_process__name")
    raw_id_fields = ("approval_process_rule", "company", "created_by", "updated_by")


@admin.register(ApprovalInstance)
class ApprovalInstanceAdmin(admin.ModelAdmin):
    """Admin configuration for ApprovalInstance."""

    list_display = (
        "rule",
        "status",
        "content_type",
        "object_id",
        "requested_by",
        "current_step",
    )
    list_filter = ("status", "content_type")
    search_fields = ("object_id", "rule__name")
    raw_id_fields = (
        "rule",
        "content_type",
        "requested_by",
        "current_step",
        "company",
        "created_by",
        "updated_by",
    )


@admin.register(ApprovalDecision)
class ApprovalDecisionAdmin(admin.ModelAdmin):
    """Admin configuration for ApprovalDecision."""

    list_display = ("instance", "step", "decision", "decided_by", "decided_at")
    list_filter = ("decision",)
    search_fields = ("comment", "instance__rule__name")
    raw_id_fields = (
        "instance",
        "step",
        "decided_by",
        "company",
        "created_by",
        "updated_by",
    )
