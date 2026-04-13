"""
helper view for review job
"""

# Third-party imports (Django)
from django.utils import timezone

# First-party / Horilla apps
from horilla_processes.reviews.models import ReviewJob


def _is_record_owned_by_user(record, user):
    """Check ownership using model OWNER_FIELDS, then fallback to created_by."""
    if not record or not user:
        return False

    user_id = getattr(user, "id", None)
    if not user_id:
        return False

    owner_fields = list(getattr(record, "OWNER_FIELDS", []) or [])
    for field_name in owner_fields:
        if not hasattr(record, field_name):
            continue

        # Fast path for FK-like owner fields.
        owner_id_attr = f"{field_name}_id"
        if getattr(record, owner_id_attr, None) == user_id:
            return True

        owner_value = getattr(record, field_name, None)
        if owner_value is None:
            continue

        # Handle M2M owners (e.g. specific_users).
        if hasattr(owner_value, "filter") and hasattr(owner_value, "exists"):
            try:
                if owner_value.filter(pk=user_id).exists():
                    return True
            except Exception:
                pass
            continue

        # Handle direct user object owners.
        if getattr(owner_value, "pk", None) == user_id:
            return True

    # Generic fallback for models without OWNER_FIELDS.
    return getattr(record, "created_by_id", None) == user_id


def _get_record_owner_users(record):
    """Resolve owner users from OWNER_FIELDS (or created_by fallback)."""
    owners = []
    if not record:
        return owners

    owner_fields = list(getattr(record, "OWNER_FIELDS", []) or [])
    for field_name in owner_fields:
        if not hasattr(record, field_name):
            continue
        owner_value = getattr(record, field_name, None)
        if owner_value is None:
            continue
        if hasattr(owner_value, "all"):
            try:
                owners.extend(list(owner_value.all()))
            except Exception:
                pass
            continue
        if getattr(owner_value, "pk", None):
            owners.append(owner_value)

    if not owners and getattr(record, "created_by", None):
        owners.append(record.created_by)

    uniq = {}
    for user in owners:
        if getattr(user, "pk", None):
            uniq[user.pk] = user
    return list(uniq.values())


def _get_sibling_jobs(job):
    """
    Return all ReviewJob rows for the same record + process + rule,
    INCLUDING the current job itself.
    These are all the parallel approver jobs for one review assignment.
    """
    return list(
        ReviewJob.all_objects.filter(
            reviews_id=job.reviews_id,
            review_rule_id=job.review_rule_id,
            content_type_id=job.content_type_id,
            object_id=job.object_id,
            is_active=True,
        )
    )


def _aggregate_field_status(field_key, sibling_jobs):
    """
    Compute the aggregate review status for a single field across all sibling jobs.

    Rules:
    - "approved"  → every approver has approved this field
    - "rejected"  → at least one approver has rejected this field
    - "pending"   → otherwise (some have not reviewed yet, or none have)
    """
    statuses = []
    for sibling in sibling_jobs:
        field_reviews = (sibling.additional_info or {}).get("field_reviews") or {}
        meta = field_reviews.get(field_key) or {}
        statuses.append(meta.get("status", ""))

    if not statuses:
        return "pending"
    if any(s == ReviewJob.STATUS_REJECTED for s in statuses):
        return ReviewJob.STATUS_REJECTED
    sample_job = sibling_jobs[0] if sibling_jobs else None
    review_rule = getattr(sample_job, "review_rule", None)
    if review_rule and getattr(review_rule, "approver_type", "") == "role":
        required_role_ids = set(review_rule.approver_roles.values_list("id", flat=True))
        if not required_role_ids:
            return "pending"

        approved_role_ids = set()
        for sibling in sibling_jobs:
            field_reviews = (sibling.additional_info or {}).get("field_reviews") or {}
            meta = field_reviews.get(field_key) or {}
            if meta.get("status") != ReviewJob.STATUS_APPROVED:
                continue
            role_id = getattr(getattr(sibling, "assigned_to", None), "role_id", None)
            if role_id in required_role_ids:
                approved_role_ids.add(role_id)

        if approved_role_ids == required_role_ids:
            return ReviewJob.STATUS_APPROVED
        return "pending"

    if all(s == ReviewJob.STATUS_APPROVED for s in statuses):
        return ReviewJob.STATUS_APPROVED
    return "pending"


def _aggregate_field_comment(field_key, sibling_jobs):
    """
    Collect all reviewer comments for a field and combine them for display.
    Format: "ApproverName: <comment>" per sibling that has a non-empty comment.
    """
    parts = []
    for sibling in sibling_jobs:
        field_reviews = (sibling.additional_info or {}).get("field_reviews") or {}
        meta = field_reviews.get(field_key) or {}
        comment = (meta.get("comment") or "").strip()
        if comment:
            reviewer_name = (
                str(sibling.assigned_to) if sibling.assigned_to_id else "Reviewer"
            )
            parts.append(f"{reviewer_name}: {comment}")
    return " | ".join(parts)


def _check_and_complete_all_jobs(job, acting_user, request=None):
    """
    After an approver saves their field decision, check whether ALL sibling jobs
    now have every field approved.  If so, mark every pending sibling as approved
    and return True.  Otherwise return False.

    """
    siblings = _get_sibling_jobs(job)
    snapshot_keys = list((job.review_fields_snapshot or {}).keys())

    if not snapshot_keys:
        return False

    # Verify each field is globally approved per aggregation rule:
    # - user approvers: all approvers approved
    # - role approvers: at least one approver per selected role approved
    for key in snapshot_keys:
        if _aggregate_field_status(key, siblings) != ReviewJob.STATUS_APPROVED:
            return False

    # All approvers have approved all fields → complete all pending sibling jobs.
    now = timezone.now()
    for sibling in siblings:
        if sibling.status == ReviewJob.STATUS_PENDING:
            sibling.status = ReviewJob.STATUS_APPROVED
            sibling.reviewed_by = acting_user
            sibling.reviewed_at = now
            sibling.save(
                update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"]
            )

    # Record post_save does not run when only ReviewJob rows change; start approval flow here.
    record = job.content_object
    if record:
        try:
            from ..utils import sync_approval_for_record_if_available

            sync_approval_for_record_if_available(record)
        except Exception:
            pass

    return True
