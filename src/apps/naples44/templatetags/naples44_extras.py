"""Template helpers for the Naples '44 site."""

import markdown as _md

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Content is authored only through the Django admin (single trusted author), so
# the rendered HTML is not sanitised. Don't expose these fields to public input.
_MD = _md.Markdown(extensions=["extra", "sane_lists", "smarty"], output_format="html")


@register.filter(name="markdownify")
def markdownify(text):
    if not text:
        return ""
    _MD.reset()
    return mark_safe(_MD.convert(text))
