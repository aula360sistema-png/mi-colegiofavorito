from django import template
from collections import defaultdict

register = template.Library()

@register.filter
def get_item(dic, key):
    if dic is None:
        return ''
    if isinstance(dic, (dict, defaultdict)):
        val = dic.get(key)
        if val is None:
            return ''
        return val
    return ''
