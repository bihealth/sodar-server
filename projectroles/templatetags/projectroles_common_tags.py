"""Template tags provided by projectroles for use in other apps"""

from django import template

from projectroles.plugins import get_backend_api


register = template.Library()


@register.simple_tag
def get_history_dropdown(project, obj):
    """Return link to object timeline events within project"""
    timeline = get_backend_api('timeline_backend')

    if not timeline:
        return ''

    url = timeline.get_object_url(project.pk, obj)
    return '<a class="dropdown-item" href="{}">\n<i class="fa fa-fw ' \
           'fa-clock-o"></i> History</a>\n'.format(url)


@register.simple_tag
def highlight_search_term(item, term):
    """Return string with search term highlighted"""

    def get_highlights(item):
        pos = item.lower().find(term)
        tl = len(term)

        if pos == -1:
            return item     # Nothing to highlight

        ret = item[:pos]
        ret += '<span class="omics-search-highlight">' + \
               item[pos:pos + tl] + '</span>'

        if len(item[pos + tl:]) > 0:
            ret += get_highlights(item[pos + tl:])

        return ret

    return get_highlights(item)


@register.simple_tag
def get_project_title_html(project):
    """Return HTML version of the full project title including parents"""
    ret = ''

    if project.get_parents():
        ret += '<span class="text-muted">{}</span>'.format(
            ' / '.join(project.get_full_title().split(' / ')[:-1]) + ' / ')

    ret += project.title
    return ret
