from django import template
import mistune

from ..models import Project, RoleAssignment, OMICS_CONSTANTS


# Local constants
INDENT_PX = 25


register = template.Library()


@register.simple_tag
def get_project_list(user, parent=None):
    """Return flat project list for displaying in templates"""
    project_list = []

    if user.is_superuser:
        project_list = Project.objects.filter(
            parent=parent,
            submit_status='OK').order_by('title')

    elif not user.is_anonymous():
        project_list = [
            p for p in Project.objects.filter(
                parent=parent,
                submit_status='OK').order_by('title')
            if p.has_role(user, include_children=True)]

    def append_projects(project):
        lst = [project]

        for c in project.get_children():
            if (user.is_superuser or
                    c.has_role(user, include_children=True)):
                lst += append_projects(c)

        return lst

    flat_list = []

    for p in project_list:
        flat_list += append_projects(p)

    return flat_list


@register.simple_tag
def get_project_list_indent(project, list_parent):
    """Return indent in pixels for project list"""
    project_depth = project.get_depth()

    if list_parent:
        project_depth -= (list_parent.get_depth() + 1)

    return project_depth * INDENT_PX


@register.simple_tag
def omics_constant(value):
    """Get value from OMICS_CONSTANTS in settings"""
    return OMICS_CONSTANTS[value] \
        if value in OMICS_CONSTANTS else None


@register.simple_tag
def get_description(project):
    """Return description, truncate if needed"""
    max_len = 128
    ret = project.description[:max_len]

    if len(project.description) > max_len:
        ret += '...'

    return ret


@register.simple_tag
def get_user_role_str(project, user):
    try:
        role_as = RoleAssignment.objects.get(project=project, user=user)
        return role_as.role.name.split(' ')[1]

    except RoleAssignment.DoesNotExist:
        return ''


@register.simple_tag
def render_markdown(raw_markdown):
    return mistune.markdown(raw_markdown)
