"""Ajax API views for the ontologyaccess app"""

from rest_framework.response import Response

# Projectroles dependency
from projectroles.views_ajax import SODARBasePermissionAjaxView

from ontologyaccess.models import OBOFormatOntology, OBOFormatOntologyTerm


class OBOOntologyListAjaxView(SODARBasePermissionAjaxView):
    """View to list available OBO format ontologies"""

    permission_required = 'ontologyaccess.query_ontology'

    def get(self, request, *args, **kwargs):
        ret_data = {'ontologies': {}}
        ontologies = OBOFormatOntology.objects.all().order_by('title')

        for o in ontologies:
            ret_data['ontologies'][str(o.sodar_uuid)] = {
                'title': o.title,
                'ontology_id': o.ontology_id,
                'description': o.description,
                'data_version': o.data_version,
                'term_url': o.term_url,
            }

        return Response(ret_data, status=200)


class OBOTermQueryAjaxView(SODARBasePermissionAjaxView):
    """View to query for terms in one or more OBO format ontologies"""

    permission_required = 'ontologyaccess.query_ontology'

    def get(self, request, *args, **kwargs):
        if not request.GET.get('name'):
            return Response({'detail': 'Incorrect query string'}, status=400)

        ret_data = {'terms': []}
        filter_kwargs = {'name__icontains': request.GET['name']}

        if kwargs.get('oboformatontology'):
            filter_kwargs['ontology__sodar_uuid'] = kwargs['oboformatontology']

        terms = OBOFormatOntologyTerm.objects.filter(**filter_kwargs).order_by(
            'name'
        )

        for t in terms:
            ret_data['terms'].append(
                {
                    'ontology': str(t.ontology.sodar_uuid),
                    'term_id': t.term_id,
                    'name': t.name,
                    'definition': t.definition,
                    'is_obsolete': t.is_obsolete,
                    'replaced_by': t.replaced_by,
                }
            )

        return Response(ret_data, status=200)
