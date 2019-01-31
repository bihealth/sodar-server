from django import template

from samplesheets.models import GenericMaterial


register = template.Library()


@register.simple_tag
def get_families(study):
    """
    Return list of families
    :param study: Study object
    :return: List of strings
    """
    sources = GenericMaterial.objects.filter(study=study, item_type='SOURCE')
    ret = sorted(
        list(
            set(
                [
                    s.characteristics['Family']['value']
                    for s in sources
                    if (
                        'Family' in s.characteristics
                        and 'value' in s.characteristics['Family']
                        and s.characteristics['Family']['value']
                    )
                ]
            )
        )
    )

    if not ret or not ret[0]:
        ret = (
            GenericMaterial.objects.filter(study=study, item_type='SOURCE')
            .values_list('name', flat=True)
            .order_by('name')
        )

    return ret


@register.simple_tag
def get_family_sources(study, family_id):
    """
    Return sources for a family in a study
    :param study: Study object
    :param family_id: String
    :return: QuerySet of GenericMaterial objects
    """
    ret = GenericMaterial.objects.filter(
        study=study,
        item_type='SOURCE',
        characteristics__Family__value=family_id,
    )

    if ret.count() == 0:
        ret = GenericMaterial.objects.filter(
            study=study, item_type='SOURCE', name=family_id
        )

    return ret
