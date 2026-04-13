"""
Feature registration for Approvals app.

This declares the "approvals" feature and its registry key ("approval_models"),
so other apps can opt-in their models without modifying their model code.
"""

# First-party / Horilla imports
from horilla.registry.feature import register_feature

register_feature(
    "approvals",
    "approval_models",
    include_models=[
        ("leads", "Lead"),
        ("opportunities", "Opportunity"),
        ("accounts", "Account"),
        ("contacts", "Contact"),
    ],
)
