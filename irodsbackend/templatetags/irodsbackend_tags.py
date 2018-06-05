from django import template

from ..api import IrodsAPI


irods_backend = IrodsAPI()

register = template.Library()


# TODO: Not needed anymore, can be removed
@register.simple_tag
def get_irods_path(obj):
    return irods_backend.get_path(obj)
