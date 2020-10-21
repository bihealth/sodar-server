"""Ajax API views for the ontologyaccess app"""

from functools import reduce
import logging

from django.conf import settings
from django.db.models import Case, When, Q

from rest_framework.response import Response

# Projectroles dependency
from projectroles.views_ajax import SODARBasePermissionAjaxView

from ontologyaccess.api import OntologyAccessAPI
from ontologyaccess.models import OBOFormatOntologyTerm


logger = logging.getLogger(__name__)


# Base Classes and Mixins ------------------------------------------------------


class OBOOntologyTermMixin:
    """Mixin for OBOFormatOntologyTerm helpers"""

    @classmethod
    def get_term_dict(cls, term):
        """
        Return term dictionary.
        TODO: Replace with a serializer if we ever do standardized API views

        :param term: OBOFormatOntologyTerm object
        :return: dict
        """
        return {
            'ontology_name': term.ontology.name,
            'term_id': term.term_id,
            'name': term.name,
            'definition': term.definition,
            'is_obsolete': term.is_obsolete,
            'replaced_by': term.replaced_by,
            'accession': term.get_url(),
        }


# Ajax Views -------------------------------------------------------------------


# TODO: Remove? Not currently used for anything
class OBOOntologyListAjaxView(SODARBasePermissionAjaxView):
    """View to list available OBO format ontologies"""

    permission_required = 'ontologyaccess.query_ontology'

    def get(self, request, *args, **kwargs):
        ontology_api = OntologyAccessAPI()
        ret_data = {'ontologies': ontology_api.get_obo_dict(key='name')}
        return Response(ret_data, status=200)


class OBOTermQueryAjaxView(OBOOntologyTermMixin, SODARBasePermissionAjaxView):
    """View to query for terms in one or more OBO format ontologies"""

    permission_required = 'ontologyaccess.query_ontology'

    def get(self, request, *args, **kwargs):
        if not request.GET.get('name'):
            return Response({'detail': 'Incorrect query string'}, status=400)

        ret_data = {'terms': []}
        filter_kwargs = {'name__icontains': request.GET['name']}
        query_limit = settings.ONTOLOGYACCESS_QUERY_LIMIT
        o_list = None

        # Filter by specific ontologies
        if request.GET.get('o'):
            o_list = request.GET.getlist('o')
            filter_kwargs['ontology__name__in'] = o_list

        logger.debug('Term query: {}'.format(filter_kwargs))

        # Order by ontology list order if set
        order = []

        if request.GET.get('order') and o_list:
            order.append(
                Case(
                    *[
                        When(ontology__name=name, then=pos)
                        for pos, name in enumerate(o_list)
                    ]
                )
            )
            logger.debug('Order by ontology: {}'.format(', '.join(o_list)))

        order.append('name')
        terms = OBOFormatOntologyTerm.objects.filter(**filter_kwargs).order_by(
            *order
        )
        logger.debug('Term count: {}'.format(terms.count()))

        if terms.count() > query_limit:
            ret_data['detail'] = (
                'Query exceeds {} results. Please refine your search to see '
                'all results.'.format(query_limit)
            )
            ret_data['detail_type'] = 'warning'

        for t in terms[:query_limit]:
            ret_data['terms'].append(self.get_term_dict(t))

        return Response(ret_data, status=200)


class OBOTermListAjaxView(OBOOntologyTermMixin, SODARBasePermissionAjaxView):
    """View to get a list of exact terms with all term data"""

    permission_required = 'ontologyaccess.query_ontology'

    def get(self, request, *args, **kwargs):
        term_names = request.GET.getlist('t')

        if not term_names:
            return Response({'detail': 'Incorrect query string'}, status=400)

        ret_data = {'terms': []}
        q_list = map(lambda n: Q(name__iexact=n), term_names)
        q_list = reduce(lambda a, b: a | b, q_list)
        terms = OBOFormatOntologyTerm.objects.filter(q_list)

        for t in terms:
            ret_data['terms'].append(self.get_term_dict(t))

        return Response(ret_data, status=200)
