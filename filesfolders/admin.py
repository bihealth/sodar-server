from django import forms
from django.contrib import admin

from db_file_storage.form_widgets import DBAdminClearableFileInput
from .models import File, Folder, HyperLink


class FileForm(forms.ModelForm):
    class Meta:
        model = File
        exclude = []
        widgets = {'file': DBAdminClearableFileInput}


class FileAdmin(admin.ModelAdmin):
    form = FileForm


admin.site.register(File)
admin.site.register(Folder)
admin.site.register(HyperLink)
