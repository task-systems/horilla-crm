"""Signals for review job creation."""

# Standard library imports
import logging

# Third-party imports (Django)
from django.db.models.signals import post_save

# First party imports (Horilla)
from horilla.registry.feature import FEATURE_CONFIG, FEATURE_REGISTRY

# Local party imports
from .utils import sync_jobs_for_record

logger = logging.getLogger(__name__)


def reviews_post_save_handler(sender, instance, **kwargs):
    """Sync review jobs for a record whenever it is saved."""
    try:
        sync_jobs_for_record(instance)
    except Exception:
        logger.exception("Failed to sync review jobs for %s", instance)


def connect_review_signals():
    """Bind post_save for all models registered under review process feature."""
    registry_key = FEATURE_CONFIG.get("reviews", "reviews_models")
    for model in FEATURE_REGISTRY.get(registry_key, []):
        post_save.connect(
            reviews_post_save_handler,
            sender=model,
            dispatch_uid=f"reviews_post_save_{model._meta.app_label}_{model._meta.model_name}",
        )


connect_review_signals()
