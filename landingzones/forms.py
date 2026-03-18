"""Forms for the landingzones app"""

from django import forms

# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import PluginAPI

# Samplesheets dependency
from samplesheets.models import Assay

import landingzones.constants as lc
from landingzones.models import LandingZone
from landingzones.utils import get_zone_title


plugin_api = PluginAPI()


# Local constants
ZONE_COLLS_CREATION_CHOICES = [
    (lc.ZONE_COLLS_NONE, 'NONE: Do not create collections'),
    (
        lc.ZONE_COLLS_CREATE,
        'CREATE: Create collections, allow creation of additional root '
        'collections',
    ),
    (
        lc.ZONE_COLLS_RESTRICT,
        'RESTRICT: Create collections, restrict write access to created '
        'collections (recommended)',
    ),
]


class LandingZoneForm(forms.ModelForm):
    """Form for landing zone creation"""

    #: Title suffix field
    title_suffix = forms.CharField(max_length=64, required=False)

    class Meta:
        model = LandingZone
        fields = [
            'assay',
            'title_suffix',
            'description',
            'user_message',
            'coll_creation',
            'configuration',
        ]

    def __init__(
        self, current_user=None, project=None, assay=None, *args, **kwargs
    ):
        """Override for form initialization"""
        super().__init__(*args, **kwargs)
        irods_backend = plugin_api.get_backend_api('omics_irods')
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
        self.fields['coll_creation'].label = 'Collection creation'
        self.fields['coll_creation'].help_text = (
            'Automatically create landing zone subcollections in iRODS, '
            'optionally restrict write access to created collections'
        )

        # Get options for configuration
        self.fields['configuration'].widget = forms.Select()
        self.fields['configuration'].widget.choices = [(None, '--------------')]
        for plugin in config_plugins:
            self.fields['configuration'].widget.choices.append(
                (plugin.config_name, plugin.config_display_name)
            )  # TODO: Sort

        # Creation
        if not self.instance.pk:
            self.fields['assay'].widget.choices = []
            # Only show choices for assays which are in iRODS
            with irods_backend.get_session() as irods:
                for assay in Assay.objects.filter(
                    study__investigation__project=self.project,
                    study__investigation__active=True,
                ):
                    if irods.collections.exists(irods_backend.get_path(assay)):
                        self.fields['assay'].widget.choices.append(
                            (
                                assay.sodar_uuid,
                                f'{assay.study.get_name()} / '
                                f'{assay.get_display_name()}',
                            )
                        )
            # Set options and initial value for coll_creation
            self.fields['coll_creation'].widget = forms.Select()
            self.fields[
                'coll_creation'
            ].widget.choices = ZONE_COLLS_CREATION_CHOICES
            self.initial['coll_creation'] = lc.ZONE_COLLS_RESTRICT
        # Updating
        else:
            # Set initial values
            self.initial['assay'] = self.instance.assay.sodar_uuid
            self.initial['coll_creation'] = self.instance.coll_creation
            # Don't allow modifying certain fields
            self.fields['title_suffix'].widget = forms.HiddenInput()
            self.fields['assay'].widget = forms.HiddenInput()
            self.fields['configuration'].widget = forms.HiddenInput()
            self.fields['coll_creation'].widget = forms.HiddenInput()

    def clean(self):
        # Creation
        if not self.instance.pk:
            # Set full title
            self.cleaned_data['title'] = get_zone_title(
                self.cleaned_data.get('title_suffix')
            )
        # Updating
        else:
            if (
                self.cleaned_data['coll_creation']
                != self.instance.coll_creation
            ):
                self.add_error(None, 'Updating coll_creation is not allowed')
            self.cleaned_data['title'] = self.instance.title
        return self.cleaned_data

    def save(self, *args, **kwargs):
        """Override of form saving function"""
        obj = super().save(commit=False)
        obj.title = self.cleaned_data['title']
        # Creation
        if not self.instance.pk:
            obj.user = self.current_user
            obj.project = self.project
        # Updating
        else:
            obj.user = self.instance.user
            obj.project = self.instance.project
            obj.coll_creation = self.instance.coll_creation
        obj.save()
        return obj
