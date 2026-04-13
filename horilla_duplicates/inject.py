"""Runtime injections for duplicate checking in Horilla generic views."""

# Standard library imports
import logging

# First-party / Horilla apps
from horilla_duplicates.form_integration import (
    create_form_valid_with_duplicate_check,
    create_prepare_tabs_with_duplicate_tab,
    create_update_field_with_duplicate_check,
)
from horilla_generics.views import (
    HorillaDetailTabView,
    HorillaMultiStepFormView,
    HorillaSingleFormView,
)
from horilla_generics.views.helpers.edit_field import UpdateFieldView


def inject_duplicate_checking():
    """
    Inject duplicate checking into HorillaSingleFormView and HorillaMultiStepFormView.
    This should be called from apps.py ready() method.
    """
    try:
        # Store original form_valid methods
        if not hasattr(HorillaSingleFormView, "_original_form_valid"):
            HorillaSingleFormView._original_form_valid = (
                HorillaSingleFormView.form_valid
            )
            HorillaSingleFormView.form_valid = create_form_valid_with_duplicate_check(
                HorillaSingleFormView._original_form_valid, is_multi_step=False
            )

        if not hasattr(HorillaMultiStepFormView, "_original_form_valid"):
            HorillaMultiStepFormView._original_form_valid = (
                HorillaMultiStepFormView.form_valid
            )
            HorillaMultiStepFormView.form_valid = (
                create_form_valid_with_duplicate_check(
                    HorillaMultiStepFormView._original_form_valid, is_multi_step=True
                )
            )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning("Failed to inject duplicate checking: %s", e)


def inject_duplicate_tab():
    """
    Inject Potential Duplicates tab into HorillaDetailTabView.
    This should be called from apps.py ready() method.
    """
    try:
        # Store original _prepare_detail_tabs method
        if not hasattr(HorillaDetailTabView, "_original_prepare_detail_tabs"):
            HorillaDetailTabView._original_prepare_detail_tabs = (
                HorillaDetailTabView._prepare_detail_tabs
            )
            HorillaDetailTabView._prepare_detail_tabs = (
                create_prepare_tabs_with_duplicate_tab(
                    HorillaDetailTabView._original_prepare_detail_tabs
                )
            )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning("Failed to inject duplicate tab: %s", e)


def inject_inline_edit_duplicate_checking():
    """
    Inject duplicate checking into UpdateFieldView.post() for inline field edits.
    After a field is saved via the inline edit UI, check_duplicates() is called on
    the updated object. If duplicates are found, a warning modal and tab refresh are
    triggered via appended HTMX snippets. The save always completes first.
    """
    try:
        if not hasattr(UpdateFieldView, "_original_post"):
            UpdateFieldView._original_post = UpdateFieldView.post
            UpdateFieldView.post = create_update_field_with_duplicate_check(
                UpdateFieldView._original_post
            )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning("Failed to inject inline edit duplicate checking: %s", e)


# Inject duplicate checking into form views
inject_duplicate_checking()

# Inject Potential Duplicates tab into detail views
inject_duplicate_tab()

# Inject duplicate checking into inline field edit view
inject_inline_edit_duplicate_checking()
