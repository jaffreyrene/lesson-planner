import os
from django import template

register = template.Library()

@register.filter
def basename(value):
    return os.path.basename(value)

# touched on 2025-06-13T18:49:51.142824Z