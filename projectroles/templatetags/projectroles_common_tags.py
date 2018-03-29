"""Template tags provided by projectroles for use in other apps"""

import mistune

from django import template
from django.urls import reverse

from projectroles.plugins import get_backend_api


register = template.Library()


@register.simple_tag
def render_markdown(raw_markdown):
    return mistune.markdown(raw_markdown)


@register.simple_tag
def get_history_dropdown(project, obj):
    """Return link to object timeline events within project"""
    timeline = get_backend_api('timeline_backend')

    if not timeline:
        return ''

    url = timeline.get_object_url(project.omics_uuid, obj)
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


@register.simple_tag
def get_user_html(user):
    """Return standard HTML representation for a User object"""

    # In case full name has not been added for a user
    full_name = user.name if user.name else user.username

    return '<a title="{}" href="mailto:{}" data-toggle="tooltip" ' \
           'data-placement="top">{}</a>'.format(
                full_name, user.email, user.username)


@register.simple_tag
def get_project_link(project):
    """Return link to project with simple title"""
    return '<a href="{}">{}</a>'.format(
        reverse('projectroles:detail', kwargs={'project': project.omics_uuid}),
        project.title)
