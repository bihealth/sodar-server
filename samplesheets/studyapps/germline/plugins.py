from django.conf import settings
from django.contrib import auth

from samplesheets.models import Investigation, Study, GenericMaterial
from samplesheets.plugins import SampleSheetStudyPluginPoint
from samplesheets.rendering import SampleSheetTableBuilder

from projectroles.plugins import get_backend_api
from ..utils import get_pedigree_file_url

User = auth.get_user_model()


class SampleSheetStudyPlugin(SampleSheetStudyPluginPoint):
    """Plugin for germline studies in sample sheets"""

    # Properties required by django-plugins ------------------------------

    #: Name (used in code and as unique idenfitier)
    name = 'samplesheets_study_germline'

    #: Title (used in templates)
    title = 'Sample Sheets Germline Study Plugin'

    # Properties defined in SampleSheetStudyPluginPoint ------------------

    #: Configuration name
    config_name = 'bih_germline'

    #: Description string
    description = 'Sample sheets germline study app'

    #: Template for study addition (Study object as "study" in context)
    study_template = 'samplesheets_study_germline/_study.html'

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
                # Get URLs to all latest bam files for all sources in family
                bam_urls = {}
                vcf_urls = {}

                # Build render table
                tb = SampleSheetTableBuilder()
                study_tables = tb.build_study_tables(study)

                sources = GenericMaterial.objects.filter(
                    study=study, item_type='SOURCE'
                )
                for source in sources:

                    vcf_url = get_pedigree_file_url(
                        file_type='vcf',
                        source=source,
                        study_tables=study_tables,
                    )

                    # Family defined
                    if 'Family' in source.characteristics:
                        fam_id = source.characteristics['Family']['value']

                    else:
                        fam_id = None

                    if fam_id:
                        if source.study:
                            fam_sources = GenericMaterial.objects.filter(
                                study=source.study,
                                item_type='SOURCE',
                                characteristics__Family__value=fam_id,
                            ).order_by('name')

                            for fam_source in fam_sources:
                                bam_url = get_pedigree_file_url(
                                    file_type='bam',
                                    source=fam_source,
                                    study_tables=study_tables,
                                )

                                bam_urls[fam_source.name] = bam_url

                    # If not, just add for the current source
                    else:
                        bam_url = get_pedigree_file_url(
                            file_type='bam',
                            source=source,
                            study_tables=study_tables,
                        )

                        bam_urls[source.name] = bam_url

                    # Use source name if family ID not known
                    if not fam_id:
                        fam_id = source.name

                    vcf_urls[fam_id] = vcf_url

                # update date
                updated_data = {'bam_urls': bam_urls, 'vcf_urls': vcf_urls}

                cache_backend.set_cache_item(
                    name=str(study_uuid) + '/' + self.name,
                    app_name='samplesheets',
                    user=user,
                    data=updated_data,
                    project=project,
                )
