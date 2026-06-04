from django import template

register = template.Library()

@register.filter
def get_item(dic, key):
    if dic:
        return dic.get(key)
    return None
