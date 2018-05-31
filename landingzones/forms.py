from datetime import datetime as dt

from django import forms
from django.utils.text import slugify

# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_backend_api

# Samplesheets dependency
from samplesheets.models import Assay

from .models import LandingZone


class LandingZoneForm(forms.ModelForm):
    """Form for landing zone creation"""

    title_suffix = forms.CharField(
        max_length=64,
        required=False)

    class Meta:
        model = LandingZone
        fields = ['assay', 'title_suffix', 'description']

    def __init__(
            self, current_user=None, project=None, assay=None,
            *args, **kwargs):
        """Override for form initialization"""
        super(LandingZoneForm, self).__init__(*args, **kwargs)
        irods_backend = get_backend_api('omics_irods')

        self.current_user = None
        self.project = None
        self.assay = None

        # Get current user for checking permissions for form items
        if current_user:
            self.current_user = current_user

        if project:
            try:
                self.project = Project.objects.get(omics_uuid=project)

            except Project.DoesNotExist:
                pass    # TODO: Fail

        if assay:
            try:
                self.assay = Assay.objects.get(omics_uuid=assay)

            except Assay.DoesNotExist:
                pass    # TODO: Fail

        # Form modifications

        # Modify ModelChoiceFields to use omics_uuid
        self.fields['assay'].to_field_name = 'omics_uuid'

        # Set suffix
        self.fields['title_suffix'].label = 'Title suffix'
        self.fields['title_suffix'].help_text = \
            'Zone title suffix (optional, maximum 64 characters)'

        # Creation
        if not self.instance.pk:
            self.fields['assay'].choices = []
            # Only show choices for assays which are in iRODS
            for assay in Assay.objects.filter(
                    study__investigation__project=self.project,
                    study__investigation__active=True):

                if not irods_backend or irods_backend.collection_exists(
                        irods_backend.get_path(assay)):
                    self.fields['assay'].choices.append(
                        (assay.omics_uuid, '{} / {}'.format(
                            assay.study.get_display_name(),
                            assay.get_display_name())))

        # Updating
        else:
            # Don't allow modifying the title
            self.fields['title_suffix'].disabled = True

            # TODO: Don't allow modifying the assay

    def clean(self):
        # Creation
        if not self.instance.pk:
            # Set full title
            title = dt.now().strftime('%Y%m%d_%H%M%S')

            if self.cleaned_data.get('title_suffix') != '':
                title += '_' + slugify(
                    self.cleaned_data.get('title_suffix')).replace('-', '_')

            self.cleaned_data['title'] = title

        return self.cleaned_data

    def save(self, *args, **kwargs):
        """Override of form saving function"""
        obj = super(LandingZoneForm, self).save(commit=False)
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
