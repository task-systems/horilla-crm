"""
Shared hooks for process apps (approvals, review, etc.).

Sub-apps register callables here so sibling apps do not import each other directly.
"""

_pre_approval_sync_hooks = []
_suppress_approval_if_hooks = []


def register_pre_approval_sync(fn):
    """Register a callable(record) invoked before approval rules are evaluated."""
    if fn not in _pre_approval_sync_hooks:
        _pre_approval_sync_hooks.append(fn)


def register_suppress_approval_if(fn):
    """
    Register a callable(record) -> bool.

    If any hook returns True after pre-approval sync hooks run, pending approval
    instances are removed and rule matching is skipped.
    """
    if fn not in _suppress_approval_if_hooks:
        _suppress_approval_if_hooks.append(fn)


def run_pre_approval_sync_hooks(record):
    """Run all registered pre-approval hooks (e.g. refresh review jobs)."""
    if not record:
        return
    for fn in _pre_approval_sync_hooks:
        try:
            fn(record)
        except Exception:
            pass


def should_suppress_approval(record):
    """True if any registered hook says approvals must not run for this record."""
    if not record:
        return False
    for fn in _suppress_approval_if_hooks:
        try:
            if fn(record):
                return True
        except Exception:
            pass
    return False
