from django import template

from samplesheets.utils import get_isa_field_name


register = template.Library()


@register.simple_tag
def find_sequencing_assays(study):
    """Return true if sequencing assays exist under the study"""

    for assay in study.assays.all():
        if (get_isa_field_name(assay.measurement_type) in [
                'genome sequencing', 'exome sequencing']):
            return True

    return False
