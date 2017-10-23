from django import forms
from django.conf import settings
from django.template.defaultfilters import filesizeformat

from db_file_storage.form_widgets import DBClearableFileInput

# Projectroles dependency
from projectroles.models import Project
from projectroles.utils import build_secret
from projectroles.project_settings import get_project_setting

from .models import File, Folder, HyperLink


# Settings
MAX_UPLOAD_SIZE = settings.FILESFOLDERS_MAX_UPLOAD_SIZE

# Local constants
APP_NAME = 'filesfolders'


class FolderForm(forms.ModelForm):
    """Form for Folder creation/updating"""

    class Meta:
        model = Folder
        fields = ['name', 'folder', 'description']

    def __init__(
            self, current_user=None, project=None, folder=None,
            *args, **kwargs):
        """Override for form initialization"""
        super(FolderForm, self).__init__(*args, **kwargs)

        self.current_user = None
        self.project = None
        self.folder = None

        # Get current user for checking permissions for form items
        if current_user:
            self.current_user = current_user

        if project:
            self.project = Project.objects.get(pk=project)

        if folder:
            self.folder = Folder.objects.get(pk=folder)

        # Creation
        if not self.instance.pk:
            # Don't allow changing folder if we are creating a new object
            self.fields['folder'].choices = [
                (self.folder.pk, self.folder.name)
                if self.folder else (None, 'root')]
            self.fields['folder'].widget.attrs['readonly'] = True

        # Updating
        else:
            # Allow moving folder inside other folders in project
            folder_choices = [(None, 'root')]

            folders = Folder.objects.filter(
                project=self.instance.project.pk).exclude(
                    pk=self.instance.pk)

            # Exclude everything under current folder
            folders = [f for f in folders if not f.has_in_path(self.instance)]

            for f in folders:
                folder_choices.append((f.pk, f.get_path()))

            self.fields['folder'].choices = folder_choices
            self.initial['folder'] =\
                self.instance.folder.pk if self.instance.folder else None

    def clean(self):
        # Creation
        if not self.instance.pk:
            try:
                Folder.objects.get(
                    project=self.project,
                    folder=self.folder,
                    name=self.cleaned_data['name'])

                self.add_error('name', 'Folder already exists')

            except Folder.DoesNotExist:
                pass

        # Updating
        else:
            # Ensure a folder with the same name does not exist in the location
            old_folder = None

            try:
                old_folder = Folder.objects.get(pk=self.instance.pk)

            except Folder.DoesNotExist:
                pass

            if (old_folder and (
                    old_folder.name != self.cleaned_data['name'] or
                    old_folder.folder != self.cleaned_data['folder'])):
                try:
                    Folder.objects.get(
                        project=self.instance.project,
                        folder=self.cleaned_data['folder'],
                        name=self.cleaned_data['name'])

                    self.add_error('name', 'Folder already exists')

                except Folder.DoesNotExist:
                    pass

        return self.cleaned_data

    def save(self, *args, **kwargs):
        """Override of form saving function"""
        obj = super(FolderForm, self).save(commit=False)

        # Updating
        if self.instance.pk:
            obj.owner = self.instance.owner
            obj.project = self.instance.project
            obj.folder = self.instance.folder

        # Creation
        else:
            obj.owner = self.current_user
            obj.project = self.project

            if self.folder:
                obj.folder = self.folder

        obj.save()
        return obj


class FileForm(forms.ModelForm):
    """Form for File creation/updating"""

    class Meta:
        model = File
        fields = ['file', 'folder', 'description', 'public_url']
        widgets = {'file': DBClearableFileInput}
        help_texts = {
            'file': 'Uploaded file (maximum size: {})'.format(
                filesizeformat(MAX_UPLOAD_SIZE))}

    def __init__(
            self, current_user=None, project=None, folder=None,
            *args, **kwargs):
        """Override for form initialization"""
        super(FileForm, self).__init__(*args, **kwargs)

        self.current_user = None
        self.project = None
        self.folder = None

        # Get current user for checking permissions for form items
        if current_user:
            self.current_user = current_user

        if project:
            self.project = Project.objects.get(pk=project)

        if folder:
            self.folder = Folder.objects.get(pk=folder)

        # Creation
        if not self.instance.pk:
            # Don't allow changing folder if we are creating a new object
            self.fields['folder'].choices = [
                (self.folder.pk, self.folder.name)
                if self.folder else (None, 'root')]
            self.fields['folder'].widget.attrs['readonly'] = True

            # Disable public URL creation if setting is false
            if not get_project_setting(
                    self.project, APP_NAME, 'allow_public_links'):
                self.fields['public_url'].disabled = True

        # Updating
        else:
            # Allow moving file inside other folders in project
            folder_choices = [(None, 'root')]

            for f in Folder.objects.filter(
                    project=self.instance.project.pk):
                folder_choices.append((f.pk, f.get_path()))

            self.fields['folder'].choices = folder_choices
            self.initial['folder'] =\
                self.instance.folder.pk if self.instance.folder else None

            # Disable public URL creation if setting is false
            if not get_project_setting(
                    self.instance.project, APP_NAME, 'allow_public_links'):
                self.fields['public_url'].disabled = True

    def clean(self):
        if self.cleaned_data.get('file'):
            file = self.cleaned_data.get('file')

            # Ensure max file size is not exceeded
            try:
                size = file.size

            except NotImplementedError:
                size = file.file.size

            if size > MAX_UPLOAD_SIZE:
                self.add_error(
                    'file',
                    'File too large, maximum size is {} bytes '
                    '(file size is {} bytes)'.format(
                        MAX_UPLOAD_SIZE,
                        file.size))

            # Creation
            if not self.instance.pk:
                try:
                    File.objects.get(
                        project=self.project,
                        folder=self.folder,
                        name=file.name)
                    self.add_error('file', 'File already exists')

                except File.DoesNotExist:
                    pass

            # Updating
            else:
                # Ensure file with the same name does not exist in the same
                # folder (unless we update file with the same folder and name)
                old_file = None

                try:
                    old_file = File.objects.get(
                        project=self.instance.project,
                        folder=self.instance.folder,
                        name=self.instance.name)

                except File.DoesNotExist:
                    pass

                if (old_file and
                        str(self.instance.name) != str(
                            self.cleaned_data.get('file'))):
                    try:
                        new_file = File.objects.get(
                            project=self.instance.project,
                            folder=self.cleaned_data.get('folder'),
                            name=self.cleaned_data.get('file'))
                        self.add_error('file', 'File already exists')

                    except File.DoesNotExist:
                        pass

        return self.cleaned_data

    def save(self, *args, **kwargs):
        """Override of form saving function"""
        obj = super(FileForm, self).save(commit=False)

        # Creation
        if not self.instance.pk:
            obj.name = obj.file.name
            obj.owner = self.current_user
            obj.project = self.project

            if self.folder:
                obj.folder = self.folder

            obj.secret = build_secret()    # Secret string created here

        # Updating
        else:
            old_file = File.objects.get(pk=self.instance.pk)

            if old_file.file != self.instance.file:
                obj.file = self.instance.file
                obj.name = obj.file.name.split('/')[-1]

            obj.owner = self.instance.owner
            obj.project = self.instance.project

            if (get_project_setting(
                    self.instance.project, APP_NAME, 'allow_public_links')):
                obj.public_url = self.instance.public_url

            else:
                obj.public_url = False

            obj.secret = self.instance.secret

            if self.instance.folder:
                obj.folder = self.instance.folder

        obj.save()
        return obj


class HyperLinkForm(forms.ModelForm):
    """Form for HyperLink creation/updating"""

    class Meta:
        model = HyperLink
        fields = ['name', 'url', 'folder', 'description']

    def __init__(
            self, current_user=None, project=None, folder=None,
            *args, **kwargs):
        """Override for form initialization"""
        super(HyperLinkForm, self).__init__(*args, **kwargs)

        self.current_user = None
        self.project = None
        self.folder = None

        # Get current user for checking permissions for form items
        if current_user:
            self.current_user = current_user

        if project:
            self.project = Project.objects.get(pk=project)

        if folder:
            self.folder = Folder.objects.get(pk=folder)

        # Creation
        if not self.instance.pk:
            # Don't allow changing folder if we are creating a new object
            self.fields['folder'].choices = [
                (self.folder.pk, self.folder.name)
                if self.folder else (None, 'root')]
            self.fields['folder'].widget.attrs['readonly'] = True

        # Updating
        else:
            # Allow moving file inside other folders in project
            folder_choices = [(None, 'root')]

            for f in Folder.objects.filter(
                    project=self.instance.project.pk):
                folder_choices.append((f.pk, f.get_path()))

            self.fields['folder'].choices = folder_choices
            self.initial['folder'] =\
                self.instance.folder.pk if self.instance.folder else None

    def clean(self):
        # Creation
        if not self.instance.pk:
            try:
                HyperLink.objects.get(
                    project=self.project,
                    folder=self.folder,
                    name=self.cleaned_data['name'])

                self.add_error('name', 'Link already exists')

            except HyperLink.DoesNotExist:
                pass

        # Updating
        else:
            # Ensure a link with the same name does not exist in the location
            old_link = None

            try:
                old_link = HyperLink.objects.get(pk=self.instance.pk)

            except HyperLink.DoesNotExist:
                pass

            if (old_link and (
                    old_link.name != self.cleaned_data['name'] or
                    old_link.folder != self.cleaned_data['folder'])):
                try:
                    HyperLink.objects.get(
                        project=self.instance.project,
                        folder=self.cleaned_data['folder'],
                        name=self.cleaned_data['name'])

                    self.add_error('name', 'Link already exists')

                except HyperLink.DoesNotExist:
                    pass

        return self.cleaned_data

    def save(self, *args, **kwargs):
        """Override of form saving function"""
        obj = super(HyperLinkForm, self).save(commit=False)

        # Updating
        if self.instance.pk:
            obj.owner = self.instance.owner
            obj.project = self.instance.project
            obj.folder = self.instance.folder

        # Creation
        else:
            obj.owner = self.current_user
            obj.project = self.project

            if self.folder:
                obj.folder = self.folder

        obj.save()
        return obj
