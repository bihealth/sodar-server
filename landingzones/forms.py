"""Forms for the landingzones app"""

from django import forms

# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_backend_api

# Samplesheets dependency
from samplesheets.models import Assay

from landingzones.models import LandingZone
from landingzones.utils import get_zone_title


class LandingZoneForm(forms.ModelForm):
    """Form for landing zone creation"""

    #: Title suffix field
    title_suffix = forms.CharField(max_length=64, required=False)

    #: Automated creation of collections
    create_colls = forms.BooleanField(
        initial=True,
        required=False,
        label='Create collections',
        help_text='Create empty collections as defined by assay plugin',
    )

    #: Limit write access to created collectionss
    restrict_colls = forms.BooleanField(
        initial=True,
        required=False,
        label='Restrict collections',
        help_text='Restrict write access to created collections (recommended)',
    )

    class Meta:
        model = LandingZone
        fields = [
            'assay',
            'title_suffix',
            'description',
            'user_message',
            'create_colls',
            'restrict_colls',
            'configuration',
        ]

    def __init__(
        self, current_user=None, project=None, assay=None, *args, **kwargs
    ):
        """Override for form initialization"""
        super().__init__(*args, **kwargs)
        irods_backend = get_backend_api('omics_irods')
        from landingzones.plugins import LandingZoneConfigPluginPoint

        config_plugins = LandingZoneConfigPluginPoint.get_plugins()
        self.current_user = current_user
        if project:
            self.project = Project.objects.filter(sodar_uuid=project).first()
        if assay:
            self.assay = Assay.objects.filter(sodar_uuid=assay).first()

        # Form modifications
        # Modify ModelChoiceFields to use sodar_uuid
        self.fields['assay'].to_field_name = 'sodar_uuid'
        # Set suffix
        self.fields['title_suffix'].label = 'Title suffix'
        self.fields[
            'title_suffix'
        ].help_text = 'Zone title suffix (optional, maximum 64 characters)'
        self.fields['description'].widget.attrs['rows'] = 4

        # Get options for configuration
        self.fields['configuration'].widget = forms.Select()
        self.fields['configuration'].widget.choices = [(None, '--------------')]
        for plugin in config_plugins:
            self.fields['configuration'].widget.choices.append(
                (plugin.config_name, plugin.config_display_name)
            )  # TODO: Sort

        # Creation
        if not self.instance.pk:
            self.fields['assay'].choices = []
            # Only show choices for assays which are in iRODS
            with irods_backend.get_session() as irods:
                for assay in Assay.objects.filter(
                    study__investigation__project=self.project,
                    study__investigation__active=True,
                ):
                    if irods.collections.exists(irods_backend.get_path(assay)):
                        self.fields['assay'].choices.append(
                            (
                                assay.sodar_uuid,
                                '{} / {}'.format(
                                    assay.study.get_display_name(),
                                    assay.get_display_name(),
                                ),
                            )
                        )
        # Updating
        else:
            # Set initial assay value
            self.initial['assay'] = self.instance.assay.sodar_uuid

            # Don't allow modifying certain fields
            self.fields['title_suffix'].disabled = True
            self.fields['create_colls'].disabled = True
            self.fields['restrict_colls'].disabled = True
            self.fields['assay'].disabled = True
            self.fields['configuration'].disabled = True
            self.fields['user_message'].disabled = True

    def clean(self):
        # Creation
        if not self.instance.pk:
            # Set full title
            self.cleaned_data['title'] = get_zone_title(
                self.cleaned_data.get('title_suffix')
            )
        # Updating
        else:
            self.cleaned_data['title'] = self.instance.title
            self.cleaned_data['assay'] = self.instance.assay
            self.cleaned_data['configuration'] = self.instance.configuration
            self.cleaned_data['user_message'] = self.instance.user_message
        return self.cleaned_data

    def save(self, *args, **kwargs):
        """Override of form saving function"""
        obj = super().save(commit=False)
        obj.title = self.cleaned_data['title']
        # Updating
        if self.instance.pk:
            obj.user = self.instance.user
            obj.project = self.instance.project
        # Creation
        else:
            obj.user = self.current_user
            obj.project = self.project
        obj.save()
        return obj
