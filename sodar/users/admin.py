from django import forms
from django.contrib import admin
from django.contrib.auth.forms import (
    AdminUserCreationForm,
    UserChangeForm,
    UserCreationForm,
)

from projectroles.admin import SODARUserAdmin

from .models import User


class MyUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


class MyUserCreationForm(AdminUserCreationForm):
    error_message = AdminUserCreationForm.error_messages.update(
        {'duplicate_username': 'This username has already been taken.'}
    )

    class Meta(UserCreationForm.Meta):
        model = User

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages['duplicate_username'])


@admin.register(User)
class MyUserAdmin(SODARUserAdmin):
    form = MyUserChangeForm
    add_form = MyUserCreationForm
