from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    if mapping is None:
        return None
    try:
        return mapping.get(key)
    except AttributeError:
        return None


@register.filter
def get_nested(mapping, args):
    if mapping is None:
        return None
    try:
        first, second = args.split(':')
        return mapping.get(int(first), {}).get(int(second))
    except Exception:
        return None


@register.filter
def attr(obj, name):
    return getattr(obj, name, None)
