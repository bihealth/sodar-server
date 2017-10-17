# import magic

from django import forms
from django.conf import settings
from django.template.defaultfilters import filesizeformat

from db_file_storage.form_widgets import DBClearableFileInput

# Projectroles dependency
from projectroles.models import Project, ProjectSetting
from projectroles.utils import build_secret

from .models import File, Folder, HyperLink


# Settings
MAX_UPLOAD_SIZE = settings.FILESFOLDERS_MAX_UPLOAD_SIZE

# Local constants
APP_NAME = 'files'

# TODO: Clean up, simplify and refactor these forms


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

        # TODO: Simplify/refactor this
        self.current_user = None
        self.project = None
        self.folder = None

        # Get current user for checking permissions for form items
        if current_user:
            self.current_user = current_user

        if project:
            try:
                self.project = Project.objects.get(id=project)

            except Project.DoesNotExist:
                pass

        if folder:
            try:
                self.folder = Folder.objects.get(id=folder)

            except Folder.DoesNotExist:
                pass

        # Form modifications

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
        # Ensure a folder with the same name does not exist in the location
        # TODO: Simplify this
        old_folder = None

        # Updating
        if self.instance.pk:
            try:
                old_folder = Folder.objects.get(id=self.instance.pk)

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

        # Creation
        else:
            try:
                Folder.objects.get(
                    project=self.project,
                    folder=self.folder,
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

        # TODO: Simplify/refactor this
        self.current_user = None
        self.project = None
        self.folder = None

        # Get current user for checking permissions for form items
        if current_user:
            self.current_user = current_user

        if project:
            try:
                self.project = Project.objects.get(id=project)

            except Project.DoesNotExist:
                pass

        if folder:
            try:
                self.folder = Folder.objects.get(id=folder)

            except Folder.DoesNotExist:
                pass

        # Form modifications

        # Creation
        if not self.instance.pk:
            # Don't allow changing folder if we are creating a new object
            self.fields['folder'].choices = [
                (self.folder.pk, self.folder.name)
                if self.folder else (None, 'root')]
            self.fields['folder'].widget.attrs['readonly'] = True

            # Disable public URL creation if setting is false
            if not ProjectSetting.objects.get_setting_value(
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
            if not ProjectSetting.objects.get_setting_value(
                    self.instance.project, APP_NAME, 'allow_public_links'):
                self.fields['public_url'].disabled = True

    def clean(self):
        if self.cleaned_data.get('file'):
            file = self.cleaned_data.get('file')
            size = 0

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

            # Ensure file with the same name does not exist in the same folder
            # (Unless we update file with the same folder and name, that is ok)
            # Updating
            if self.instance.pk:
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

            # Creation
            else:
                try:
                    File.objects.get(
                        project=self.project,
                        folder=self.folder,
                        name=file.name)
                    self.add_error('file', 'File already exists')

                except File.DoesNotExist:
                    pass

        return self.cleaned_data

    def save(self, *args, **kwargs):
        """Override of form saving function"""
        obj = super(FileForm, self).save(commit=False)
        mime = magic.Magic(mime=True)

        # Updating
        if self.instance.pk:
            old_file = File.objects.get(id=self.instance.pk)

            if old_file.file != self.instance.file:
                obj.file = self.instance.file
                obj.name = obj.file.name.split('/')[-1]
                obj.content_type = mime.from_buffer(self.instance.file.read())

            obj.owner = self.instance.owner
            obj.project = self.instance.project

            if (ProjectSetting.objects.get_setting_value(
                    self.instance.project, APP_NAME, 'allow_public_links')):
                obj.public_url = self.instance.public_url

            else:
                obj.public_url = False

            obj.secret = self.instance.secret

            if self.instance.folder:
                obj.folder = self.instance.folder

        # Creation
        else:
            obj.name = obj.file.name
            obj.content_type = mime.from_buffer(obj.file.read())
            obj.owner = self.current_user
            obj.project = self.project

            if self.folder:
                obj.folder = self.folder

            obj.secret = build_secret()    # Secret string created here

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

        # TODO: Simplify/refactor this
        self.current_user = None
        self.project = None
        self.folder = None

        # Get current user for checking permissions for form items
        if current_user:
            self.current_user = current_user

        if project:
            try:
                self.project = Project.objects.get(id=project)

            except Project.DoesNotExist:
                pass

        if folder:
            try:
                self.folder = Folder.objects.get(id=folder)

            except Folder.DoesNotExist:
                pass

        # Form modifications

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
        # Ensure a link with the same name does not exist in the location
        # TODO: Simplify this
        old_link = None

        # Updating
        if self.instance.pk:
            try:
                old_link = HyperLink.objects.get(id=self.instance.pk)

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

        # Creation
        else:
            try:
                HyperLink.objects.get(
                    project=self.project,
                    folder=self.folder,
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
