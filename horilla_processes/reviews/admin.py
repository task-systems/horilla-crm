"""
Admin registration for the reviews app
"""

# Third-party imports (Django)
from django.contrib import admin

# Local party imports
from .models import (
    ReviewCondition,
    ReviewJob,
    ReviewProcess,
    ReviewRule,
    ReviewRuleCondition,
)

admin.site.register(ReviewProcess)
admin.site.register(ReviewCondition)
admin.site.register(ReviewRule)
admin.site.register(ReviewRuleCondition)
admin.site.register(ReviewJob)
