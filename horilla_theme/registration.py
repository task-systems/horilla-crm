"""
Feature registration & HTML Injection to index.html file for Theme Manager app.
"""

# First party imports (Horilla)
from horilla.registry.asset_registry import register_html

register_html(
    "inject_html/tailwind_dynamic_config.html",
    slot="head_end",
    priority=100,
)

register_html(
    "inject_html/tailwind_dynamic_config_login.html",
    slot="head_end",
    priority=50,
    page="login",
)
