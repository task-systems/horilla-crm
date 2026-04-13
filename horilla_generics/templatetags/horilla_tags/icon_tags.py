"""Template tags for themed SVG mask icons."""

from django.templatetags.static import static
from django.utils.html import format_html

from ._registry import register


@register.simple_tag
def themed_icon(icon_path, classes="", style=""):
    """
    Render a themed SVG icon span using CSS mask-image.

    Usage:
        {% themed_icon menu.icon "w-4 h-4 shrink-0" %}
    """
    if not icon_path:
        return ""

    icon_url = static(icon_path)
    class_name = f"svg-themed {classes}".strip()
    style_attr = f"--icon: url('{icon_url}'); {style}".strip()
    return format_html(
        '<span class="{}" style="{}" aria-hidden="true"></span>',
        class_name,
        style_attr,
    )
