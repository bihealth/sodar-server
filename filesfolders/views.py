from wsgiref.util import FileWrapper    # For db files

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, UpdateView,\
    CreateView, DeleteView, View
from django.views.generic.edit import ModelFormMixin, DeletionMixin
from django.views.generic.detail import SingleObjectMixin

from db_file_storage.storage import DatabaseFileStorage

from .forms import FolderForm, FileForm, HyperLinkForm
from .models import Folder, File, FileData, HyperLink
from .utils import build_public_url

# Projectroles dependency
from projectroles.models import Project
from projectroles.plugins import get_backend_api
from projectroles.project_settings import get_project_setting
from projectroles.views import LoggedInPermissionMixin, \
    ProjectContextMixin


# Settings and constants
APP_NAME = 'filesfolders'
TL_OBJ_TYPES = {
    'Folder': 'folder',
    'File': 'file',
    'HyperLink': 'hyperlink'}

LINK_BAD_REQUEST_MSG = settings.FILESFOLDERS_LINK_BAD_REQUEST_MSG
SERVE_AS_ATTACHMENT = settings.FILESFOLDERS_SERVE_AS_ATTACHMENT

storage = DatabaseFileStorage()


# Mixins -----------------------------------------------------------------


class ObjectPermissionMixin(LoggedInPermissionMixin):
    """Mixin to ensure owner permission for different filesfolders objects"""

    def has_permission(self):
        """Override has_permission to check perms depending on owner"""
        try:
            obj = type(self.get_object()).objects.get(pk=self.kwargs['pk'])

            if obj.owner == self.request.user:
                return self.request.user.has_perm(
                    'filesfolders.update_data_own',
                    self.get_permission_object())

            else:
                return self.request.user.has_perm(
                    'filesfolders.update_data_all',
                    self.get_permission_object())

        except type(self.get_object()).DoesNotExist:
            return False

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        if self.get_object():
            return self.get_object().project

        return None


class ViewActionMixin(object):
    """Mixin for retrieving form action type"""

    @property
    def view_action(self):
        raise ImproperlyConfigured('Property "view_action" missing!')

    def get_view_action(self):
        return self.view_action if self.view_action else None


class FormValidMixin(ModelFormMixin):
    """Mixin for overriding form_valid in form views for creation/updating"""

    def form_valid(self, form):
        view_action = self.get_view_action()
        timeline = get_backend_api('timeline_backend')
        old_data = {}

        update_attrs = ['name', 'folder', 'description', 'flag']

        if view_action == 'update':
            old_item = self.get_object()

            if old_item.__class__.__name__ == 'HyperLink':
                update_attrs.append('url')

            elif old_item.__class__.__name__ == 'File':
                update_attrs.append('public_url')

            # Get old fields
            for a in update_attrs:
                old_data[a] = getattr(old_item, a)

        self.object = form.save()

        # Add event in Timeline
        if timeline:
            obj_type = TL_OBJ_TYPES[self.object.__class__.__name__]
            extra_data = {}
            tl_desc = '{} {} {{{}}}'.format(
                view_action, obj_type, obj_type)

            if view_action == 'create':
                for a in update_attrs:
                    extra_data[a] = str(getattr(self.object, a))

            else:   # Update
                for a in update_attrs:
                    if old_data[a] != getattr(self.object, a):
                        extra_data[a] = str(getattr(self.object, a))

                tl_desc += ' (' + ', '.join(a for a in extra_data) + ')'

            tl_event = timeline.add_event(
                project=self.object.project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='{}_{}'.format(obj_type, view_action),
                description=tl_desc,
                extra_data=extra_data,
                status_type='OK')

            tl_event.add_object(
                obj=self.object,
                label=obj_type,
                name=self.object.get_path()
                if isinstance(self.object, Folder) else self.object.name)

        messages.success(
            self.request,
            '{} "{}" successfully {}d.'.format(
                self.object.__class__.__name__,
                self.object.name,
                view_action))

        re_kwargs = {'project': self.object.project.pk}

        if type(self.object) == Folder and self.object.folder:
            re_kwargs['folder'] = self.object.folder.pk

        elif type(self.object) != Folder and self.object.folder:
            re_kwargs['folder'] = self.object.folder.pk

        return redirect(
            reverse('project_files', kwargs=re_kwargs))


class DeleteSuccessMixin(DeletionMixin):
    """Mixin for overriding get_success_url in deletion form views"""

    def get_success_url(self):
        timeline = get_backend_api('timeline_backend')

        # Add event in Timeline
        if timeline:
            obj_type = TL_OBJ_TYPES[self.object.__class__.__name__]

            # Add event in Timeline
            tl_event = timeline.add_event(
                project=self.object.project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='{}_delete'.format(obj_type),
                description='delete {} {{{}}}'.format(
                    obj_type, obj_type),
                status_type='OK')

            tl_event.add_object(
                obj=self.object,
                label=obj_type,
                name=self.object.get_path()
                if isinstance(self.object, Folder) else self.object.name)

        messages.success(
            self.request, '{} "{}" deleted.'.format(
                self.object.__class__.__name__,
                self.object.name))

        re_kwargs = {'project': self.object.project.pk}

        if type(self.object) == Folder and self.object.folder:
            re_kwargs['folder'] = self.object.folder.pk

        elif type(self.object) != Folder and self.object.folder:
            re_kwargs['folder'] = self.object.folder.pk

        return reverse('project_files', kwargs=re_kwargs)


class FileServeMixin:
    """Mixin for file download serving"""

    def get(self, *args, **kwargs):
        """GET request to return the file as attachment"""
        timeline = get_backend_api('timeline_backend')

        # Get File object
        try:
            file = File.objects.get(pk=kwargs['pk'])

        except File.DoesNotExist:
            messages.error(self.request, 'File object not found!')

            return redirect(reverse(
                'project_files', kwargs={'project': kwargs['project']}))

        # Get corresponding FileData object with file content
        try:
            file_data = FileData.objects.get(file_name=file.file.name)

        except FileData.DoesNotExist:
            messages.error(self.request, 'File data not found!')

            return redirect(reverse(
                'project_files', kwargs={'project': kwargs['project']}))

        # Open file for serving
        try:
            file_content = storage.open(file_data.file_name)

        except Exception as ex:
            print({}.format(ex))  # DEBUG

            messages.error(self.request, 'Error opening file!')

            return redirect(reverse(
                'project_files', kwargs={'project': kwargs['project']}))

        # Return file as attachment
        response = HttpResponse(
            FileWrapper(file_content),
            content_type=file_data.content_type)

        if SERVE_AS_ATTACHMENT:
            response['Content-Disposition'] = \
                'attachment; filename={}'.format(file.name)

        if not self.request.user.is_anonymous:
            # Add event in Timeline
            if timeline:
                tl_event = timeline.add_event(
                    project=file.project,
                    app_name=APP_NAME,
                    user=self.request.user,
                    event_name='file_serve',
                    description='serve file {file}',
                    classified=True,
                    status_type='INFO')

                tl_event.add_object(
                    obj=file,
                    label='file',
                    name=file.name)

        return response


# Base Views -------------------------------------------------------------


class BaseCreateView(
        LoginRequiredMixin, LoggedInPermissionMixin, FormValidMixin,
        ProjectContextMixin, CreateView):
    """Base File/Folder/HyperLink creation view"""

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        try:
            obj = Project.objects.get(pk=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None

    def get_context_data(self, *args, **kwargs):
        context = super(BaseCreateView, self).get_context_data(
            *args, **kwargs)

        if 'folder' in self.kwargs:
            try:
                context['folder'] = Folder.objects.get(
                    pk=self.kwargs['folder'])

            except Folder.DoesNotExist:
                pass

        return context

    def get_form_kwargs(self):
        """Pass current user and URL kwargs to form"""
        kwargs = super(BaseCreateView, self).get_form_kwargs()
        kwargs.update({'current_user': self.request.user})

        if 'project' in self.kwargs:
            kwargs.update({'project': self.kwargs['project']})

        if 'folder' in self.kwargs:
            kwargs.update({'folder': self.kwargs['folder']})

        return kwargs


# File List View ---------------------------------------------------------


class ProjectFileView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        SingleObjectMixin, TemplateView):
    """View for displaying files and folders for a project"""

    # Projectroles dependency
    permission_required = 'filesfolders.view_data'
    template_name = 'filesfolders/project_files.html'
    model = Project

    def get_object(self):
        """Override get_object to provide a Project object for both template
        and permission checking"""
        try:
            obj = Project.objects.get(pk=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectFileView, self).get_context_data(
            *args, **kwargs)

        # Get folder and file data
        root_folder = None

        if 'folder' in self.kwargs:
            try:
                root_folder = Folder.objects.get(
                    pk=self.kwargs['folder'])

                context['folder'] = root_folder

                # Build breadcrumb
                f = root_folder
                breadcrumb = [f]

                while f.folder:
                    breadcrumb.insert(0, f.folder)
                    f = f.folder

                context['folder_breadcrumb'] = breadcrumb

            except Folder.DoesNotExist:
                pass

        context['folders'] = Folder.objects.filter(
            project=self.get_object(), folder=root_folder)

        context['files'] = File.objects.filter(
            project=self.get_object(), folder=root_folder)

        context['links'] = HyperLink.objects.filter(
            project=self.get_object(), folder=root_folder)

        # Get folder ReadMe
        readme_file = File.objects.get_folder_readme(
            self.get_object().pk, self.kwargs['folder'] if
            'folder' in self.kwargs else None)

        if readme_file:
            context['readme_name'] = readme_file.name
            context['readme_data'] = readme_file.file.read().decode('utf-8')
            context['readme_mime'] = readme_file.file.file.mimetype

        return context

    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to ensure self.object is provided to template"""
        self.object = self.get_object()

        return super(
            ProjectFileView, self).dispatch(request, *args, **kwargs)


# Folder Views -----------------------------------------------------------


class FolderCreateView(ViewActionMixin, BaseCreateView):
    """Folder creation view"""
    permission_required = 'filesfolders.add_data'
    model = Folder
    form_class = FolderForm
    view_action = 'create'


class FolderUpdateView(
        LoginRequiredMixin, ObjectPermissionMixin, FormValidMixin,
        ViewActionMixin, ProjectContextMixin, UpdateView):
    """Folder updating view"""
    model = Folder
    form_class = FolderForm
    view_action = 'update'


class FolderDeleteView(
        LoginRequiredMixin, ObjectPermissionMixin, DeleteSuccessMixin,
        ProjectContextMixin, DeleteView):
    """Folder deletion view"""
    model = Folder


# File Views -------------------------------------------------------------


class FileCreateView(ViewActionMixin, BaseCreateView):
    """File creation view"""
    permission_required = 'filesfolders.add_data'
    model = File
    form_class = FileForm
    view_action = 'create'


class FileUpdateView(
        LoginRequiredMixin, ObjectPermissionMixin, FormValidMixin,
        ViewActionMixin, ProjectContextMixin, UpdateView):
    """File updating view"""
    model = File
    form_class = FileForm
    view_action = 'update'


class FileDeleteView(
        LoginRequiredMixin, ObjectPermissionMixin, DeleteSuccessMixin,
        ProjectContextMixin, DeleteView):
    """File deletion view"""
    model = File


# NOTE: This should only be used for prototype use with the development server
class FileServeView(
        LoginRequiredMixin, LoggedInPermissionMixin, FileServeMixin, View):
    """View for serving file to a logged in user with permissions"""
    permission_required = 'filesfolders.view_data'

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        try:
            obj = Project.objects.get(pk=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None


class FileServePublicView(FileServeMixin, View):
    """View for serving file to a public user with secure link"""

    def get(self, *args, **kwargs):
        """Override of GET for checking request URL"""

        try:
            file = File.objects.get(secret=kwargs['secret'])

            # Check if sharing public files is not allowed in project settings
            if not get_project_setting(
                    file.project, APP_NAME, 'allow_public_links'):
                return HttpResponseBadRequest(LINK_BAD_REQUEST_MSG)

        except File.DoesNotExist:
            return HttpResponseBadRequest(LINK_BAD_REQUEST_MSG)

        # If public URL serving is disabled, don't serve file
        if not file.public_url:
            return HttpResponseBadRequest(LINK_BAD_REQUEST_MSG)

        # Update kwargs with file and project keys
        kwargs.update({'pk': file.pk, 'project': file.project.pk})

        # If successful, return get() from FileServeMixin
        return super(FileServePublicView, self).get(*args, **kwargs)


class FilePublicLinkView(
        LoginRequiredMixin, LoggedInPermissionMixin, SingleObjectMixin,
        ProjectContextMixin, TemplateView):
    """View for generating a public secure link to a file"""
    permission_required = 'filesfolders.share_public_link'
    template_name = 'filesfolders/public_link.html'

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        try:
            obj = Project.objects.get(pk=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None

    def get_object(self):
        """Override get_object to provide a File object for perm checking
        and template"""
        try:
            obj = File.objects.get(pk=self.kwargs['pk'])
            return obj

        except File.DoesNotExist:
            return None

    def get(self, *args, **kwargs):
        """Override of GET for checking project settings"""
        file = self.get_object()

        if not file:
            messages.error(self.request, 'File not found!')

            return redirect(reverse(
                'project_files', kwargs={'project': kwargs['project']}))

        if not get_project_setting(
                file.project, APP_NAME, 'allow_public_links'):
            messages.error(
                self.request,
                'Sharing public links not allowed for this project')

            return redirect(reverse(
                'project_files', kwargs={'project': file.project.pk}))

        return super(FilePublicLinkView, self).get(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to ensure self.object is provided to template"""
        self.object = self.get_object()

        return super(
            FilePublicLinkView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        """Provide URL to context"""
        context = super(FilePublicLinkView, self).get_context_data(
            *args, **kwargs)

        try:
            file = self.get_object()

        except File.DoesNotExist:
            messages.error(self.request, 'File not found!')

            return redirect(reverse(
                'project_files', kwargs={'project': kwargs['project']}))

        if not file.public_url:
            messages.error(self.request, 'Public URL for file not enabled!')

            return redirect(reverse(
                'project_files', kwargs={'project': kwargs['project']}))

        # Build URL
        context['public_url'] = build_public_url(
            file, self.request)

        return context


# HyperLink Views --------------------------------------------------------


class HyperLinkCreateView(ViewActionMixin, BaseCreateView):
    """HyperLink creation view"""
    permission_required = 'filesfolders.add_data'
    model = HyperLink
    form_class = HyperLinkForm
    view_action = 'create'


class HyperLinkUpdateView(
        LoginRequiredMixin, ObjectPermissionMixin, FormValidMixin,
        ViewActionMixin, ProjectContextMixin, UpdateView):
    """HyperLink updating view"""
    model = HyperLink
    form_class = HyperLinkForm
    view_action = 'update'


class HyperLinkDeleteView(
        LoginRequiredMixin, ObjectPermissionMixin, DeleteSuccessMixin,
        ProjectContextMixin, DeleteView):
    """HyperLink deletion view"""
    model = HyperLink


# Batch Edit Views --------------------------------------------------------


# TODO: Refactor this completely for the final version.
class BatchEditView(
        LoginRequiredMixin, LoggedInPermissionMixin, TemplateView):
    """Batch delete/move confirm view"""
    http_method_names = ['post']
    template_name = 'filesfolders/batch_edit_confirm.html'
    # NOTE: minimum perm, all checked files will be tested in post()
    permission_required = 'filesfolders.update_data_own'

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        try:
            obj = Project.objects.get(pk=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None

    def post(self, request, **kwargs):
        timeline = get_backend_api('timeline_backend')
        post_data = request.POST

        #: Items we will delete
        items = []

        #: Item IDs to be deleted (so we don't have to create them again)
        item_names = []

        #: Items which we can't delete
        failed = []

        can_update_all = request.user.has_perm(
            'filesfolders.update_data_all', self.get_permission_object())

        user_confirmed = bool(int(post_data['user_confirmed']))
        batch_action = post_data['batch_action']
        target_folder = None

        if batch_action == 'move' and 'target_folder' in post_data:
            try:
                target_folder = Folder.objects.get(
                    pk=int(post_data['target_folder']))

            except Folder.DoesNotExist:
                pass

        edit_count = 0

        for key in [
                key for key, val in post_data.items()
                if key.startswith('batch_item') and val == '1']:
            cls = eval(key.split('_')[2])

            try:
                item = cls.objects.get(pk=int(key.split('_')[3]))

            except cls.DoesNotExist:
                pass

            #: Item permission
            perm_ok = can_update_all | (item.owner == request.user)

            #########
            # Checks
            #########

            # Perm check
            if not perm_ok:
                failed.append(item)

            # Moving checks (after user has selected target folder)
            elif batch_action == 'move' and user_confirmed:

                # Can't move if item with same name in target
                get_kwargs = {
                    'project': kwargs['project'],
                    'folder': target_folder.pk if target_folder else None,
                    'name': item.name}

                try:
                    cls.objects.get(**get_kwargs)
                    failed.append(item)

                except cls.DoesNotExist:
                    pass

            # Deletion checks
            elif batch_action == 'delete':

                # Can't delete a non-empty folder
                if type(item) == Folder and not item.is_empty():
                    failed.append(item)

            ##############
            # Modify item
            ##############

            if perm_ok and item not in failed:
                if user_confirmed and batch_action == 'move':
                    item.folder = target_folder

                    item.save()
                    edit_count += 1

                elif user_confirmed and batch_action == 'delete':
                    item.delete()
                    edit_count += 1

                elif not user_confirmed:
                    items.append(item)
                    item_names.append(key)

        ##################
        # Render/redirect
        ##################

        # User confirmed, batch operation done
        if user_confirmed:
            if len(failed) > 0:
                messages.warning(
                    self.request,
                    'Unable to edit {} items, check '
                    'permissions and target folder! Failed: {}'.format(
                        len(failed),
                        ', '.join(f.name for f in failed)))

            if edit_count > 0:
                messages.success(self.request, 'Batch {} {} items.'.format(
                    'deleted' if batch_action == 'delete' else 'moved',
                    edit_count))

            # Add event in Timeline
            # TODO: Add extra info regarding modified files
            if timeline:
                tl_event = timeline.add_event(
                    project=Project.objects.get(pk=kwargs['project']),
                    app_name=APP_NAME,
                    user=self.request.user,
                    event_name='batch_{}'.format(batch_action),
                    description='batch {} {} items {} {}'.format(
                        batch_action,
                        edit_count,
                        '({} failed)'.format(len(failed))
                        if len(failed) > 0 else '',
                        'to {target_folder}'
                        if batch_action == 'move' and target_folder else ''),
                    status_type='OK' if edit_count > 0 else 'FAILED')

                if batch_action == 'move' and target_folder:
                    tl_event.add_object(
                        obj=target_folder,
                        label='target_folder',
                        name=target_folder.get_path())

            re_kwargs = {'project': kwargs['project']}

            if 'folder' in kwargs:
                re_kwargs['folder'] = kwargs['folder']

            return redirect(
                reverse('project_files', kwargs=re_kwargs))

        # Confirmation needed
        else:
            context = {
                'batch_action': batch_action,
                'items': items,
                'item_names': item_names,
                'failed': failed,
                'project': Project.objects.get(pk=kwargs['project'])}

            if 'folder' in kwargs:
                context['folder'] = kwargs['folder']

            if batch_action == 'move':
                # Exclude folders to be moved
                exclude_list = [x.pk for x in items if type(x) == Folder]

                # Exclude folders under folders to be moved
                for i in items:
                    exclude_list += [x.pk for x in Folder.objects.filter(
                        project=kwargs['project']) if x.has_in_path(i)]

                # Exclude current folder
                if 'folder' in kwargs:
                    exclude_list.append(kwargs['folder'])

                folder_choices = Folder.objects.filter(
                    project=kwargs['project']).exclude(pk__in=exclude_list)

                context['folder_choices'] = folder_choices

                # HACK: Quick fix for root folder option not showing
                if 'folder' in kwargs or folder_choices.count() > 0:
                    context['folder_check'] = True

                else:
                    context['folder_check'] = False

            else:   # Delete
                context['folder_check'] = True

            return super(TemplateView, self).render_to_response(context)
