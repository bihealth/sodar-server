from django import template

from ..models import Investigation
from ..rendering import get_assay_table as r_get_assay_table, \
    render_assay_cell as r_render_assay_cell, \
    render_top_header as r_render_top_header


register = template.Library()


@register.simple_tag
def get_investigation(project):
    """Return Investigation for a project"""
    try:
        return Investigation.objects.get(project=project)

    except Investigation.DoesNotExist:
        return None


@register.simple_tag
def get_assay_table(assay):
    """Return data grid for a "simple" HTML assay table"""
    return r_get_assay_table(assay)


@register.simple_tag
def render_assay_cell(cell):
    """Return assay table cell as HTML"""
    return r_render_assay_cell(cell)

@register.simple_tag
def render_top_header(section):
    """Render section of top header"""
    return r_render_top_header(section)
