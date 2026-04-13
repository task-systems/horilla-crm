"""URLs for Review Process settings."""

# First party imports (Horilla)
from horilla.urls import path

# Local party imports
from . import views

app_name = "reviews"

urlpatterns = [
    path(
        "review-processes/",
        views.ReviewProcessView.as_view(),
        name="reviews_view",
    ),
    path(
        "review-processes-navbar/",
        views.ReviewProcessNavbar.as_view(),
        name="reviews_navbar_view",
    ),
    path(
        "review-processes-list/",
        views.ReviewProcessListView.as_view(),
        name="reviews_list_view",
    ),
    path(
        "review-processes-create/",
        views.ReviewProcessFormView.as_view(),
        name="reviews_create_view",
    ),
    path(
        "review-processes-update/<int:pk>/",
        views.ReviewProcessFormView.as_view(),
        name="reviews_update_view",
    ),
    path(
        "review-processes-model-dependent-fields/",
        views.ReviewProcessModelDependentFieldsView.as_view(),
        name="reviews_model_dependent_fields",
    ),
    path(
        "review-processes-approver-fields-toggle/",
        views.ReviewProcessApproverFieldsToggleView.as_view(),
        name="reviews_approver_fields_toggle",
    ),
    path(
        "review-processes-approver-fields-toggle/<int:pk>/",
        views.ReviewProcessApproverFieldsToggleView.as_view(),
        name="reviews_approver_fields_toggle_with_pk",
    ),
    path(
        "review-processes-delete/<int:pk>/",
        views.ReviewProcessDeleteView.as_view(),
        name="reviews_delete_view",
    ),
    path(
        "review-processes-detail-navbar/",
        views.ReviewProcessDetailNavbar.as_view(),
        name="reviews_detail_navbar_view",
    ),
    path(
        "review-processes/<int:pk>/",
        views.ReviewProcessDetailView.as_view(),
        name="reviews_detail_view",
    ),
    path(
        "review-processes-rule/create/<int:process_pk>/",
        views.ReviewRuleFormView.as_view(),
        name="review_rule_create_view",
    ),
    path(
        "review-processes-rule/update/<int:pk>/",
        views.ReviewRuleFormView.as_view(),
        name="review_rule_update_view",
    ),
    path(
        "review-processes-rule-delete/<int:pk>/",
        views.ReviewRuleDeleteView.as_view(),
        name="review_rule_delete_view",
    ),
    path(
        "review-jobs/",
        views.ReviewJobView.as_view(),
        name="review_job_view",
    ),
    path(
        "review-jobs-navbar/",
        views.ReviewJobNavbar.as_view(),
        name="review_job_navbar_view",
    ),
    path(
        "review-jobs-list/",
        views.ReviewJobListView.as_view(),
        name="review_job_list_view",
    ),
    path(
        "review-jobs-detail-review/<int:pk>/",
        views.ReviewJobDetailView.as_view(),
        name="review_job_detail_view",
    ),
    path(
        "review-jobs-review-field/<int:pk>/",
        views.ReviewJobFieldReviewView.as_view(),
        name="review_job_field_review_view",
    ),
]
