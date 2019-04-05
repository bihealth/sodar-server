from django.conf import settings
from django.contrib import auth

from samplesheets.plugins import SampleSheetStudyPluginPoint
from samplesheets.models import Investigation, Study, GenericMaterial
from projectroles.plugins import get_backend_api
from ..utils import get_library_file_url

User = auth.get_user_model()


class SampleSheetStudyPlugin(SampleSheetStudyPluginPoint):
    """Plugin for cancer studies in sample sheets"""

    # Properties required by django-plugins ------------------------------

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_study_cancer'

    #: Title (used in templates)
    title = 'Sample Sheets Cancer Study Plugin'

    # Properties defined in SampleSheetStudyPluginPoint ------------------

    #: Configuration name
    config_name = 'bih_cancer'

    #: Description string
    description = 'Sample sheets cancer study app'

    #: Template for study addition (Study object as "study" in context)
    study_template = 'samplesheets_study_cancer/_study.html'

    #: Required permission for accessing the plugin
    permission = None

    def update_cache(self, name=None, project=None):
        """
        Update cached data for this app, limitable to item ID and/or project.

        :param name: Item name to limit update to (string, optional)
        :param project: Project object to limit update to (optional)
        """

        # TODO: Refactor this once sodar_core#204 is done
        try:
            user = User.objects.get(
                username=settings.PROJECTROLES_DEFAULT_ADMIN
            )
        except User.DoesNotExist:
            raise Exception('PROJECTROLES_DEFAULT_ADMIN user not found')

        cache_backend = get_backend_api('sodar_cache')

        if not cache_backend:
            raise Exception('Sodarcache backend not available')

        try:
            investigation = Investigation.objects.get(project=project)
        except Investigation.DoesNotExist:
            return None

        # if a name is given, only update that specific CacheItem
        # TODO: Modify naming scheme
        if name:
            study_uuid = name.split('/')[0]
            studies = Study.objects.filter(sodar_uuid=study_uuid)
        else:
            studies = Study.objects.filter(investigation=investigation)

        for study in studies:
            if study:
                study_uuid = study.sodar_uuid

                bam_urls = {}
                vcf_urls = {}

                libraries = GenericMaterial.objects.filter(study=study)
                for library in libraries:
                    if library.assay:
                        bam_url = get_library_file_url(
                            file_type='bam', library=library
                        )
                        bam_urls[library.name] = bam_url

                        vcf_url = get_library_file_url(
                            file_type='vcf', library=library
                        )
                        vcf_urls[library.name] = vcf_url

                updated_data = {'bam_urls': bam_urls, 'vcf_urls': vcf_urls}

                cache_backend.set_cache_item(
                    name=str(study_uuid) + '/' + self.name,
                    app_name='samplesheets',
                    user=user,
                    data=updated_data,
                    project=project,
                )
