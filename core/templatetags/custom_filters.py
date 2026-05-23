"""
Custom template filters for GroupSathi.
"""

from django import template

register = template.Library()


@register.filter
def currency(value):
    """Format a number as Indian currency."""
    try:
        value = float(value)
        return f"₹{value:,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"


@register.filter
def truncate_name(value, length=20):
    """Truncate a name to specified length."""
    if len(str(value)) > length:
        return str(value)[:length] + "..."
    return value


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary in template."""
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''


@register.filter
def subtract(value, arg):
    """Subtract arg from value."""
    try:
        val = float(value) - float(arg)
        return round(val, 2)
    except (ValueError, TypeError):
        return 0.0

