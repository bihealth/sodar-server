"""Backend API for the ontologyaccess app"""

from ontologyaccess.models import OBOFormatOntology


class OntologyAccessAPI:
    """Ontology access API"""

    def get_obo_dict(self, key: str = 'name') -> dict:
        """
        Return metadata dictionary of available OBO ontologies imported into
        SODAR.

        :param key: Key used for each ontology, "name" or "sodar_uuid" (string)
        :return: Dict
        :raise: ValueError if key is incorrect
        """
        if key not in ['name', 'sodar_uuid']:
            raise ValueError('Key must be either "name" or "sodar_uuid"')
        ret = {}
        for o in OBOFormatOntology.objects.order_by('name'):
            o_data = {
                'file': o.file,
                'title': o.title,
                'ontology_id': o.ontology_id,
                'description': o.description,
                'data_version': o.data_version,
                'term_url': o.term_url,
            }
            if key == 'name':
                o_data.update({'sodar_uuid': str(o.sodar_uuid)})
                ret[o.name] = o_data
            else:
                o_data.update({'name': o.name})
                ret[str(o.sodar_uuid)] = o_data
        return ret
