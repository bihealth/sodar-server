from datetime import datetime as dt

from django import forms
from django.utils.text import slugify

# Projectroles dependency
from projectroles.models import Project

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
        fields = ['title_suffix', 'description']

    def __init__(
            self, current_user=None, project=None, assay=None,
            *args, **kwargs):
        """Override for form initialization"""
        super(LandingZoneForm, self).__init__(*args, **kwargs)

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

        self.fields['title_suffix'].label = 'Title suffix'
        self.fields['title_suffix'].help_text = \
            'Zone title suffix (optional, maximum 64 characters)'

        # Updating
        if self.instance.pk:
            # Don't allow modifying the title
            self.fields['title_suffix'].disabled = True

    def clean(self):
        # Creation
        if not self.instance.pk:
            # Set full title
            title = dt.now().strftime('%Y%m%d-%H%M%S')

            if self.cleaned_data.get('title_suffix') != '':
                title += '-' + slugify(self.cleaned_data.get('title_suffix'))

            self.cleaned_data['title'] = title

        return self.cleaned_data
