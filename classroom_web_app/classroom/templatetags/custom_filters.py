from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """Splits a string by the given argument"""
    try:
        return value.split(arg)
    except (AttributeError, TypeError):
        return []