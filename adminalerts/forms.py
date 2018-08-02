from django import forms
from django.utils import timezone

from pagedown.widgets import PagedownWidget

from .models import AdminAlert


class AdminAlertForm(forms.ModelForm):
    """Form for AdminAlert creation/updating"""

    class Meta:
        model = AdminAlert
        fields = ['message', 'date_expire', 'active', 'description']

    def __init__(self, current_user=None, *args, **kwargs):
        """Override for form initialization"""
        super(AdminAlertForm, self).__init__(*args, **kwargs)

        self.current_user = current_user

        # Set date_expire properties
        # NOTE: "format" works in source but not in widget, any way to fix?
        self.fields['date_expire'].label = 'Expiry date'
        self.fields['date_expire'].widget = forms.widgets.DateInput(
            attrs={'type': 'date'},
            format='%Y-%m-%d')

        # Set description widget with preview
        self.fields['description'].widget = PagedownWidget(show_preview=True)

        # Creation
        if not self.instance.pk:
            self.fields['date_expire'].initial = timezone.now() + \
                timezone.timedelta(days=1)

        # Updating
        else:   # self.instance.pk
            # Set description value as raw markdown
            self.initial['description'] = self.instance.description.raw

    def clean(self):
        """Custom form validation and cleanup"""

        # Don't allow alerts to expire in the past :)
        if self.cleaned_data.get('date_expire') <= timezone.now():
            self.add_error(
                'date_expire', 'Expiry date must be set in the future')

        return self.cleaned_data

    def save(self, *args, **kwargs):
        """Override of form saving function"""
        obj = super(AdminAlertForm, self).save(commit=False)
        obj.user = self.current_user
        obj.save()
        return obj
