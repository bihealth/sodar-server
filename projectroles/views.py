import json
import re
import requests

from django.apps import apps
from django.conf import settings
from django.core.urlresolvers import resolve
from django.contrib import auth
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView, DetailView, UpdateView,\
    CreateView, DeleteView, View
from django.views.generic.edit import ModelFormMixin
from django.views.generic.detail import ContextMixin

from rest_framework.response import Response
from rest_framework.views import APIView
from rules.contrib.views import PermissionRequiredMixin, redirect_to_login

from .email import send_role_change_mail, send_invite_mail, send_accept_note,\
    send_expiry_note, get_invite_subject, get_invite_body, get_invite_message, \
    get_email_footer, get_role_change_body, get_role_change_subject
from .forms import ProjectForm, RoleAssignmentForm, ProjectInviteForm
from .models import Project, Role, RoleAssignment, ProjectInvite, \
    OMICS_CONSTANTS, PROJECT_TAG_STARRED
from .plugins import ProjectAppPluginPoint, get_active_plugins, get_backend_api
from .project_settings import set_project_setting, get_project_setting, \
    get_all_settings
from .project_tags import get_tag_state, set_tag_state, remove_tag
from .utils import get_expiry_date

# Access Django user model
User = auth.get_user_model()


# Settings
SEND_EMAIL = settings.PROJECTROLES_SEND_EMAIL

# Omics constants
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_CHOICES = OMICS_CONSTANTS['PROJECT_TYPE_CHOICES']
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
SUBMIT_STATUS_OK = OMICS_CONSTANTS['SUBMIT_STATUS_OK']
SUBMIT_STATUS_PENDING = OMICS_CONSTANTS['SUBMIT_STATUS_PENDING']
SUBMIT_STATUS_PENDING_TASKFLOW = OMICS_CONSTANTS[
    'SUBMIT_STATUS_PENDING_TASKFLOW']

# Local constants
APP_NAME = 'projectroles'
SEARCH_REGEX = re.compile(r'^[a-zA-Z0-9.:\-_\s\t]+$')


# General mixins ---------------------------------------------------------------


class ProjectAccessMixin:
    """Mixin for providing access to a Project object from request kwargs"""

    @classmethod
    def _get_project(cls, request, kwargs):
        # "project" kwarg is a special case
        if 'project' in kwargs:
            try:
                return Project.objects.get(omics_uuid=kwargs['project'])

            except Project.DoesNotExist:
                return None

        # Other object types
        model = None
        uuid_kwarg = None

        for k, v in kwargs.items():
            if re.match(r'[0-9a-f-]+', v):
                try:
                    app_name = resolve(request.path).app_name

                    if app_name.find('.') != -1:
                        app_name = app_name.split('.')[0]

                    model = apps.get_model(app_name, k)
                    uuid_kwarg = k
                    break

                except LookupError:
                    pass

        if not model:
            return None

        try:
            obj = model.objects.get(omics_uuid=kwargs[uuid_kwarg])

            if hasattr(obj, 'project'):
                return obj.project

            # Some objects may have a get_project() func instead of foreignkey
            elif (hasattr(obj, 'get_project') and
                    callable(getattr(obj, 'get_project', None))):
                return obj.get_project()

        except model.DoesNotExist:
            return None


class ProjectPermissionMixin(PermissionRequiredMixin, ProjectAccessMixin):
    """Mixin for providing a Project object for permission checking"""
    def get_permission_object(self):
        return self._get_project(self.request, self.kwargs)


class LoggedInPermissionMixin(PermissionRequiredMixin):
    """Mixin for handling redirection for both unlogged users and authenticated
    users without permissions"""
    def handle_no_permission(self):
        """Override handle_no_permission to redirect user"""
        if self.request.user.is_authenticated():
            messages.error(
                self.request,
                'User not authorized for requested action')
            return redirect(reverse('home'))

        else:
            messages.error(self.request, 'Please sign in')
            return redirect_to_login(self.request.get_full_path())


class RolePermissionMixin(LoggedInPermissionMixin, ProjectAccessMixin):
    """Mixin to ensure permissions for RoleAssignment according to user role in
    project"""
    def has_permission(self):
        """Override has_permission to check perms depending on role"""
        try:
            obj = RoleAssignment.objects.get(
                omics_uuid=self.kwargs['roleassignment'])

            if obj.role.name == PROJECT_ROLE_OWNER:
                # Modifying the project owner is not allowed in role views
                return False

            elif obj.role.name == PROJECT_ROLE_DELEGATE:
                return self.request.user.has_perm(
                    'projectroles.update_project_delegate',
                    self.get_permission_object())

            else:
                return self.request.user.has_perm(
                    'projectroles.update_project_members',
                    self.get_permission_object())

        except RoleAssignment.DoesNotExist:
            return False

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        return self._get_project(self.request, self.kwargs)


class HTTPRefererMixin:
    """Mixin for updating a correct referer url in session cookie regardless of
    page reload"""

    def get(self, request, *args, **kwargs):
        if 'HTTP_REFERER' in request.META:
            referer = request.META['HTTP_REFERER']

            if ('real_referer' not in request.session or
                    referer != request.build_absolute_uri()):
                request.session['real_referer'] = referer

        return super(HTTPRefererMixin, self).get(request, *args, **kwargs)


class ProjectContextMixin(HTTPRefererMixin, ContextMixin, ProjectAccessMixin):
    """Mixin for adding context data to Project base view and other views
    extending it. Includes HTTPRefererMixin for correct referer URL"""
    def get_context_data(self, *args, **kwargs):
        context = super(ProjectContextMixin, self).get_context_data(
            *args, **kwargs)

        # Project
        if hasattr(self, 'object') and isinstance(self.object, Project):
            context['project'] = self.get_object()

        elif hasattr(self, 'object') and hasattr(self.object, 'project'):
            context['project'] = self.object.project

        else:
            context['project'] = self._get_project(self.request, self.kwargs)

        # Plugins stuff
        plugins = ProjectAppPluginPoint.get_plugins()

        if plugins:
            context['app_plugins'] = sorted([
                p for p in plugins if p.is_active()],
                key=lambda x: x.plugin_ordering)

        # Project tagging/starring
        if 'project' in context:
            context['project_starred'] = get_tag_state(
                context['project'], self.request.user, PROJECT_TAG_STARRED)

        return context


class PluginContextMixin(ContextMixin):
    """Mixin for adding plugin list to context data"""

    def get_context_data(self, *args, **kwargs):
        context = super(PluginContextMixin, self).get_context_data(
            *args, **kwargs)

        app_plugins = get_active_plugins(plugin_type='project_app')

        if app_plugins:
            context['app_plugins'] = app_plugins

        return context


class APIPermissionMixin(PermissionRequiredMixin):
    """Mixin for handling permission response for API functions"""

    def handle_no_permission(self):
        """Override handle_no_permission to provide 403"""
        return HttpResponseForbidden()


class CurrentUserFormMixin(ModelFormMixin):
    """Mixin for passing current user to form as current_user"""
    def get_form_kwargs(self):
        kwargs = super(CurrentUserFormMixin, self).get_form_kwargs()
        kwargs.update({'current_user': self.request.user})
        return kwargs


# Base Project Views -----------------------------------------------------------


class HomeView(LoginRequiredMixin, PluginContextMixin, TemplateView):
    """Home view"""
    template_name = 'projectroles/home.html'

    def get_context_data(self, *args, **kwargs):
        context = super(HomeView, self).get_context_data(*args, **kwargs)

        context['count_categories'] = Project.objects.filter(
            type=PROJECT_TYPE_CATEGORY).count()
        context['count_projects'] = Project.objects.filter(
            type=PROJECT_TYPE_PROJECT).count()
        context['count_users'] = auth.get_user_model().objects.all().count()
        context['count_assignments'] = RoleAssignment.objects.all().count()

        context['user_projects'] = RoleAssignment.objects.filter(
            user=self.request.user).count()
        context['user_owner'] = RoleAssignment.objects.filter(
            user=self.request.user, role__name=PROJECT_ROLE_OWNER).count()
        context['user_delegate'] = RoleAssignment.objects.filter(
            user=self.request.user, role__name=PROJECT_ROLE_DELEGATE).count()

        backend_plugins = get_active_plugins(plugin_type='backend')

        if backend_plugins:
            context['backend_plugins'] = backend_plugins

        return context


class ProjectDetailView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        DetailView):
    """Project details view"""
    permission_required = 'projectroles.view_project'
    model = Project
    slug_url_kwarg = 'project'
    slug_field = 'omics_uuid'

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectDetailView, self).get_context_data(
            *args, **kwargs)

        if self.request.user.is_superuser:
            context['role'] = None

        else:
            try:
                role_as = RoleAssignment.objects.get(
                    user=self.request.user, project=self.object)

                context['role'] = role_as.role

            except RoleAssignment.DoesNotExist:
                context['role'] = None

        return context


class ProjectSearchView(LoginRequiredMixin, TemplateView):
    """View for displaying results of search within projects"""
    template_name = 'projectroles/search.html'

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectSearchView, self).get_context_data(
            *args, **kwargs)

        plugins = get_active_plugins(plugin_type='project_app')

        search_input = self.request.GET.get('s').strip()
        context['search_input'] = search_input

        search_split = search_input.split(' ')
        search_term = search_split[0].strip()
        search_type = None
        search_keywords = {}

        for i in range(1, len(search_split)):
            s = search_split[i].strip()
            if ':' in s:
                kw = s.split(':')[0].lower().strip()
                val = s.split(':')[1].lower().strip()

                if kw == 'type':
                    search_type = val

                else:
                    search_keywords[kw] = val

            elif s != '':
                search_term += ' ' + s

        context['search_term'] = search_term
        context['search_type'] = search_type
        context['search_keywords'] = search_keywords

        # Get project results
        if not search_type or search_type == 'project':
            context['project_results'] = [
                p for p in Project.objects.find(
                    search_term, project_type='PROJECT') if
                self.request.user.has_perm('projectroles.view_project', p)]

        # Get app results
        if search_type:
            search_apps = sorted([
                p for p in plugins if (
                    p.search_enable and
                    search_type in p.search_types)],
                key=lambda x: x.plugin_ordering)

        else:
            search_apps = sorted(
                [p for p in plugins if p.search_enable],
                key=lambda x: x.plugin_ordering)

        context['app_search_data'] = []

        for plugin in search_apps:
            context['app_search_data'].append({
                'plugin': plugin,
                'results': plugin.search(
                    search_term,
                    self.request.user,
                    search_type,
                    search_keywords)})

        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)

        # Check input, redirect if unwanted characters are found
        if not bool(re.match(SEARCH_REGEX, context['search_input'])):
            messages.error(self.request, 'Please check your search input')
            return redirect('home')

        return super(TemplateView, self).render_to_response(context)


# Project Editing Views --------------------------------------------------------


class ProjectModifyMixin(ModelFormMixin):
    def form_valid(self, form):
        taskflow = get_backend_api('taskflow')
        timeline = get_backend_api('timeline_backend')

        use_taskflow = True if taskflow and \
            form.cleaned_data.get('type') == PROJECT_TYPE_PROJECT else False

        tl_event = None
        form_action = 'update' if self.object else 'create'
        old_data = {}

        app_plugins = [
            p for p in ProjectAppPluginPoint.get_plugins() if
            p.project_settings]

        if self.object:
            project = self.get_object()

            old_data['title'] = project.title
            old_data['description'] = project.description
            old_data['readme'] = project.readme.raw
            old_data['owner'] = project.get_owner().user

            project.title = form.cleaned_data.get('title')
            project.description = form.cleaned_data.get('description')
            project.type = form.cleaned_data.get('type')
            project.readme = form.cleaned_data.get('readme')

        else:
            project = Project(
                title=form.cleaned_data.get('title'),
                description=form.cleaned_data.get('description'),
                type=form.cleaned_data.get('type'),
                parent=form.cleaned_data.get('parent'),
                readme=form.cleaned_data.get('readme'))

        if form_action == 'create':
            project.submit_status = SUBMIT_STATUS_PENDING_TASKFLOW if \
                use_taskflow else SUBMIT_STATUS_PENDING
            project.save()  # Always save locally if creating (to get uuid)

        else:
            project.submit_status = SUBMIT_STATUS_OK

        # Save project with changes if updating without taskflow
        if form_action == 'update' and not use_taskflow:
            project.save()

        owner = form.cleaned_data.get('owner')
        extra_data = {}
        type_str = 'Project' if project.type == PROJECT_TYPE_PROJECT else \
            'Category'

        # Get settings
        project_settings = {}

        for p in app_plugins:
            for s_key in p.project_settings:
                s_name = 'settings.{}.{}'.format(p.name, s_key)
                project_settings[s_name] = form.cleaned_data.get(s_name)

        if timeline:
            if form_action == 'create':
                tl_desc = 'create ' + type_str.lower() + \
                          ' with {owner} as owner'
                extra_data = {
                    'title': project.title,
                    'owner': owner.username,
                    'description': project.description,
                    'readme': project.readme.raw}

            else:   # Update
                tl_desc = 'update ' + type_str.lower()
                upd_fields = []

                if old_data['title'] != project.title:
                    extra_data['title'] = project.title
                    upd_fields.append('title')

                if old_data['owner'] != owner:
                    extra_data['owner'] = owner.username
                    upd_fields.append('owner')

                if old_data['description'] != project.description:
                    extra_data['description'] = project.description
                    upd_fields.append('description')

                if old_data['readme'] != project.readme.raw:
                    extra_data['readme'] = project.readme.raw
                    upd_fields.append('readme')

                # Settings
                for k, v in project_settings.items():
                    old_v = get_project_setting(
                        project, k.split('.')[1], k.split('.')[2])
                    if old_v != v:
                        extra_data[k] = v
                        upd_fields.append(k)

                if len(upd_fields) > 0:
                    tl_desc += ' (' + ', '.join(x for x in upd_fields) + ')'

            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='project_{}'.format(form_action),
                description=tl_desc,
                extra_data=extra_data)

            if form_action == 'create':
                tl_event.add_object(owner, 'owner', owner.username)

        # Submit with taskflow
        if use_taskflow:
            if tl_event:
                tl_event.set_status('SUBMIT')

            flow_data = {
                'project_title': project.title,
                'project_description': project.description,
                'parent_uuid': str(project.parent.omics_uuid) if
                project.parent else 0,
                'owner_username': owner.username,
                'owner_uuid': str(owner.omics_uuid),
                'owner_role_pk': Role.objects.get(
                    name=PROJECT_ROLE_OWNER).pk,
                'settings': project_settings}

            if form_action == 'update':
                old_owner = project.get_owner().user
                flow_data['old_owner_uuid'] = str(old_owner.omics_uuid)
                flow_data['old_owner_username'] = old_owner.username
                flow_data['project_readme'] = project.readme.raw

            try:
                taskflow.submit(
                    project_uuid=str(project.omics_uuid),
                    flow_name='project_{}'.format(form_action),
                    flow_data=flow_data,
                    request=self.request)

            except (
                    requests.exceptions.ConnectionError,
                    taskflow.FlowSubmitException) as ex:
                # NOTE: No need to update status as project will be deleted
                if form_action == 'create':
                    project.delete()

                else:
                    if tl_event:
                        tl_event.set_status('FAILED', str(ex))

                messages.error(self.request, str(ex))

                if form_action == 'create':
                    if project.parent:
                        redirect_url = reverse(
                            'projectroles:detail',
                            kwargs={'project': project.parent.omics_uuid})

                    else:
                        redirect_url = reverse('home')

                else:   # Update
                    redirect_url = reverse(
                        'projectroles:detail',
                        kwargs={'project': project.omics_uuid})

                return HttpResponseRedirect(redirect_url)

        # Local save without Taskflow
        else:
            # Modify owner role if it does exist
            try:
                assignment = RoleAssignment.objects.get(
                    project=project, role__name=PROJECT_ROLE_OWNER)
                assignment.user = owner
                assignment.save()

            # Else create a new one
            except RoleAssignment.DoesNotExist:
                assignment = RoleAssignment(
                    project=project,
                    user=owner,
                    role=Role.objects.get(name=PROJECT_ROLE_OWNER))
                assignment.save()

            # Modify settings
            for k, v in project_settings.items():
                set_project_setting(
                    project=project,
                    app_name=k.split('.')[1],
                    setting_name=k.split('.')[2],
                    value=v,
                    validate=False)     # Already validated in form

        # Post submit/save
        if form_action == 'create':
            project.submit_status = SUBMIT_STATUS_OK
            project.save()

        if tl_event:
            tl_event.set_status('OK')

        messages.success(self.request, '{} {}d.'.format(type_str, form_action))
        return HttpResponseRedirect(reverse(
            'projectroles:detail', kwargs={'project': project.omics_uuid}))


class ProjectCreateView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        ProjectModifyMixin, ProjectContextMixin, HTTPRefererMixin, CreateView):
    """Project creation view"""
    permission_required = 'projectroles.create_project'
    model = Project
    form_class = ProjectForm

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectCreateView, self).get_context_data(
            *args, **kwargs)

        if 'project' in self.kwargs:
            context['parent'] = Project.objects.get(
                omics_uuid=self.kwargs['project'])

        return context

    def get_form_kwargs(self):
        """Pass URL arguments to form"""
        kwargs = super(ProjectCreateView, self).get_form_kwargs()
        kwargs.update(self.kwargs)
        kwargs.update({'current_user': self.request.user})
        return kwargs

    def get(self, request, *args, **kwargs):
        """Override get() to limit project creation under other projects"""
        if 'project' in self.kwargs:
            project = Project.objects.get(omics_uuid=self.kwargs['project'])

            if project.type != PROJECT_TYPE_CATEGORY:
                messages.error(
                    self.request,
                    'Creating a project within a project is not allowed')
                return HttpResponseRedirect(reverse(
                    'projectroles:detail',
                    kwargs={'project': project.omics_uuid}))

        return super(ProjectCreateView, self).get(request, *args, **kwargs)


class ProjectUpdateView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        ProjectModifyMixin, UpdateView):
    """Project updating view"""
    permission_required = 'projectroles.update_project'
    model = Project
    form_class = ProjectForm
    slug_url_kwarg = 'project'
    slug_field = 'omics_uuid'

    def get_form_kwargs(self):
        kwargs = super(ProjectUpdateView, self).get_form_kwargs()
        kwargs.update({'current_user': self.request.user})
        return kwargs


# RoleAssignment Views ---------------------------------------------------------


class ProjectRoleView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        ProjectContextMixin, TemplateView):
    """View for displaying project roles"""
    permission_required = 'projectroles.view_project_roles'
    template_name = 'projectroles/project_roles.html'
    model = Project

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectRoleView, self).get_context_data(
            *args, **kwargs)
        context['owner'] = context['project'].get_owner()
        context['delegate'] = context['project'].get_delegate()
        context['members'] = context['project'].get_members()
        return context


class RoleAssignmentModifyMixin(ModelFormMixin):
    def get_context_data(self, *args, **kwargs):
        context = super(RoleAssignmentModifyMixin, self).get_context_data(
            *args, **kwargs)

        change_type = self.request.resolver_match.url_name.split('_')[1]
        project = self._get_project(self.request, self.kwargs)

        if change_type != 'delete':
            context['preview_subject'] = get_role_change_subject(
                change_type, project)
            context['preview_body'] = get_role_change_body(
                change_type=change_type,
                project=project,
                user_name='{user_name}',
                issuer=self.request.user,
                role_name='{role_name}',
                project_url=self.request.build_absolute_uri(reverse(
                    'projectroles:detail',
                    kwargs={
                        'project': project.omics_uuid}))).replace('\n', '\\n')

        return context

    def form_valid(self, form):
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')

        form_action = 'update' if self.object else 'create'
        tl_event = None

        project = self.get_context_data()['project']
        user = form.cleaned_data.get('user')
        role = form.cleaned_data.get('role')

        use_taskflow = taskflow.use_taskflow(project) if taskflow else False

        # Init Timeline event
        if timeline:
            tl_desc = '{} role {}"{}" for {{{}}}'.format(
                form_action,
                'to ' if form_action == 'update' else '',
                role.name,
                'user')

            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='role_{}'.format(form_action),
                description=tl_desc)

            tl_event.add_object(
                obj=user,
                label='user',
                name=user.username)

        # Submit with taskflow
        if use_taskflow:
            if tl_event:
                tl_event.set_status('SUBMIT')

            flow_data = {
                'username': user.username,
                'user_uuid': str(user.omics_uuid),
                'role_pk': role.pk}

            try:
                taskflow.submit(
                    project_uuid=project.omics_uuid,
                    flow_name='role_update',
                    flow_data=flow_data,
                    request=self.request)

            except taskflow.FlowSubmitException as ex:
                if tl_event:
                    tl_event.set_status('FAILED', str(ex))

                messages.error(self.request, str(ex))
                return redirect(reverse(
                    'projectroles:roles',
                    kwargs={'project': project.omics_uuid}))

            # Get object
            self.object = RoleAssignment.objects.get(
                project=project, user=user)

        # Local save without Taskflow
        else:
            if form_action == 'create':
                self.object = RoleAssignment(
                    project=project,
                    user=user,
                    role=role)

            else:
                self.object = RoleAssignment.objects.get(
                    project=project, user=user)
                self.object.role = role

            self.object.save()

        if SEND_EMAIL:
            send_role_change_mail(
                form_action, project, user, role, self.request)

        if tl_event:
            tl_event.set_status('OK')

        messages.success(
            self.request,
            'Membership {} for {} with the role of {}.'.format(
                'added' if form_action == 'create' else 'updated',
                self.object.user.username,
                self.object.role.name))
        return redirect(
            reverse(
                'projectroles:roles',
                kwargs={'project': self.object.project.omics_uuid}))


class RoleAssignmentCreateView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        ProjectContextMixin, RoleAssignmentModifyMixin, CreateView):
    """RoleAssignment creation view"""
    permission_required = 'projectroles.update_project_members'
    model = RoleAssignment
    form_class = RoleAssignmentForm

    def get_form_kwargs(self):
        """Pass URL arguments and current user to form"""
        kwargs = super(RoleAssignmentCreateView, self).get_form_kwargs()
        kwargs.update(self.kwargs)
        kwargs.update({'current_user': self.request.user})
        return kwargs


class RoleAssignmentUpdateView(
        LoginRequiredMixin, RolePermissionMixin, ProjectContextMixin,
        RoleAssignmentModifyMixin, UpdateView):
    """RoleAssignment updating view"""
    model = RoleAssignment
    form_class = RoleAssignmentForm
    slug_url_kwarg = 'roleassignment'
    slug_field = 'omics_uuid'

    def get_form_kwargs(self):
        """Pass current user to form"""
        kwargs = super(RoleAssignmentUpdateView, self).get_form_kwargs()
        kwargs.update({'current_user': self.request.user})
        return kwargs


class RoleAssignmentDeleteView(
        LoginRequiredMixin, RolePermissionMixin, ProjectContextMixin,
        DeleteView):
    """RoleAssignment deletion view"""
    model = RoleAssignment
    slug_url_kwarg = 'roleassignment'
    slug_field = 'omics_uuid'

    def post(self, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        tl_event = None

        self.object = RoleAssignment.objects.get(
            omics_uuid=kwargs['roleassignment'])
        project = self.object.project
        user = self.object.user
        role = self.object.role

        use_taskflow = taskflow.use_taskflow(project) if taskflow else False

        # Init Timeline event
        if timeline:
            tl_event = timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='role_delete',
                description='delete role "{}" from {{{}}}'.format(
                    role.name, 'user'))

            tl_event.add_object(
                obj=user,
                label='user',
                name=user.username)

        # Submit with taskflow
        if use_taskflow:
            if tl_event:
                tl_event.set_status('SUBMIT')

            flow_data = {
                'username': user.username,
                'user_uuid': str(user.omics_uuid),
                'role_pk': role.pk}

            try:
                taskflow.submit(
                    project_uuid=project.omics_uuid,
                    flow_name='role_delete',
                    flow_data=flow_data,
                    request=self.request)
                self.object = None

            except taskflow.FlowSubmitException as ex:
                if tl_event:
                    tl_event.set_status('FAILED', str(ex))

                messages.error(self.request, str(ex))
                return HttpResponseRedirect(redirect(reverse(
                    'projectroles:roles',
                    kwargs={'project': project.omics_uuid})))

        # Local save without Taskflow
        else:
            self.object.delete()

        if SEND_EMAIL:
            send_role_change_mail(
                'delete', project, user, None, self.request)

        # Remove project star from user if it exists
        remove_tag(project=project, user=user)

        if tl_event:
            tl_event.set_status('OK')

        messages.success(
            self.request, 'Membership of {} removed.'.format(
                user.username))

        return HttpResponseRedirect(reverse(
            'projectroles:roles', kwargs={'project': project.omics_uuid}))

    def get_form_kwargs(self):
        """Pass current user to form"""
        kwargs = super(RoleAssignmentDeleteView, self).get_form_kwargs()
        kwargs.update({'current_user': self.request.user})
        return kwargs


class RoleAssignmentImportView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        ProjectContextMixin, TemplateView):
    """View for importing roles from an existing project"""
    # TODO: Add taskflow functionality in v0.3
    http_method_names = ['get', 'post']
    template_name = 'projectroles/roleassignment_import.html'
    permission_required = 'projectroles.import_roles'

    def get(self, request, *args, **kwargs):
        context = super(RoleAssignmentImportView, self).get_context_data(
            *args, **kwargs)

        if request.user.is_superuser:
            projects = Project.objects.filter(
                type=PROJECT_TYPE_PROJECT).exclude(
                omics_uuid=self.kwargs['project'])

            context['owned_projects'] = sorted(
                [p for p in projects],
                key=lambda x: x.get_full_title())

        else:
            assignments = RoleAssignment.objects.filter(
                project__type=PROJECT_TYPE_PROJECT,
                user=self.request.user,
                role__name=PROJECT_ROLE_OWNER).exclude(
                    project__omics_uuid=self.kwargs['project'])

            if assignments.count() > 0:
                context['owned_projects'] = sorted(
                    [a.project for a in assignments],
                    key=lambda x: x.get_full_title())

        context['previous_page'] = reverse(
            'projectroles:roles', kwargs={'project': self.kwargs['project']})

        return super(TemplateView, self).render_to_response(context)

    def post(self, request, **kwargs):
        taskflow = get_backend_api('taskflow')
        timeline = get_backend_api('timeline_backend')
        context = self.get_context_data()
        post_data = request.POST
        confirmed = True if 'import-confirmed' in post_data else False
        import_mode = post_data['import-mode'] if \
            'import-mode' in post_data else None

        dest_project = self.get_permission_object()
        source_project = Project.objects.get(
            omics_uuid=post_data['source-project'])

        use_taskflow = taskflow.use_taskflow(dest_project) if \
            taskflow else False

        ######################
        # Confirmation needed
        ######################

        if not confirmed:
            context['import_mode'] = import_mode

            context['source_project'] = source_project
            dest_users = dest_project.roles.all().values_list(
                'user', flat=True)

            assignments = source_project.roles.exclude(
                role__name=PROJECT_ROLE_OWNER)

            if import_mode == 'append':
                assignments = assignments.exclude(user__in=dest_users)

            context['import_assignments'] = assignments.order_by(
                'user__username')

            if import_mode == 'replace':
                import_users = assignments.values_list(
                    'user', flat=True)

                context['del_assignments'] = dest_project.roles.exclude(
                    role__name=PROJECT_ROLE_OWNER).exclude(
                        user__in=import_users).order_by('user__username')

            context['previous_page'] = reverse(
                'projectroles:role_import',
                kwargs={'project': dest_project.omics_uuid})

            return super(TemplateView, self).render_to_response(context)

        ############
        # Confirmed
        ############

        import_keys = [
            key for key, val in post_data.items()
            if key.startswith('import_field') and val == '1']
        import_count = len(import_keys)

        # Import/update
        import_users = []

        for key in import_keys:
            source_as = RoleAssignment.objects.get(
                omics_uuid=key.split('_')[2])

            try:
                old_as = RoleAssignment.objects.get(
                    project=dest_project, user=source_as.user)

            except RoleAssignment.DoesNotExist:
                old_as = None

            # Save new
            if import_mode == 'append' or not old_as:
                dest_as = RoleAssignment(
                    project=dest_project,
                    role=source_as.role,
                    user=source_as.user)
                dest_as.save()

                if SEND_EMAIL:
                    send_role_change_mail(
                        'create', dest_project, dest_as.user, dest_as.role,
                        self.request)

                import_users.append(dest_as.user)

            # Update role
            elif old_as and source_as.role != old_as.role:
                old_as.role = source_as.role
                old_as.save()

                if SEND_EMAIL:
                    send_role_change_mail(
                        'update', dest_project, old_as.user, old_as.role,
                        self.request)

                import_users.append(old_as.user)

        final_count = len(import_users)

        # Add Timeline event for import
        if timeline:
            tl_users = []

            for i in range(0, final_count):
                tl_users.append('{user' + str(i) + '}')

            tl_desc = 'import {} role{} from {{{}}}{}'.format(
                final_count,
                's' if final_count != 1 else '',
                'project',
                ' ({})'.format(', '.join(tl_users)) if
                final_count > 0 else '')

            tl_event = timeline.add_event(
                project=dest_project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='role_import',
                description=tl_desc,
                status_type='OK')

            tl_event.add_object(
                obj=source_project,
                label='project',
                name=source_project.title)

            for i in range(0, final_count):
                tl_event.add_object(
                    obj=import_users[i],
                    label='user{}'.format(i),
                    name=import_users[i].username)

        msg = 'Imported {} member{} from project "{}"{}.'.format(
                final_count,
                's' if final_count != 1 else '',
                source_project.title,
                ' ({})'.format(
                    ', '.join([u.username for u in import_users])) if
                import_users else '')

        if final_count > 0:
            messages.success(self.request, msg)

        else:
            messages.warning(self.request, msg)

        # Delete
        del_keys = [
            key for key, val in post_data.items()
            if key.startswith('delete_field') and val == '1']
        del_count = len(del_keys)

        if import_mode == 'replace' and del_count > 0:
            del_uuids = [k.split('_')[2] for k in del_keys]
            del_assignments = RoleAssignment.objects.filter(
                omics_uuid__in=del_uuids).order_by('user__username')
            del_users = [a.user for a in del_assignments]

            del_assignments.delete()

            if SEND_EMAIL:
                for u in del_users:
                    send_role_change_mail(
                        'delete', dest_project, u, None, self.request)

            if timeline:
                tl_users = []

                for i in range(0, len(del_users)):
                    tl_users.append('{user' + str(i) + '}')

                tl_desc = 'delete {} role{} ({})'.format(
                    del_count,
                    's' if len(del_users) != 1 else '',
                    ', '.join(tl_users))

                tl_event = timeline.add_event(
                    project=dest_project,
                    app_name=APP_NAME,
                    user=self.request.user,
                    event_name='role_delete',
                    description=tl_desc,
                    status_type='OK')

                for i in range(0, len(del_users)):
                    tl_event.add_object(
                        obj=del_users[i],
                        label='user{}'.format(i),
                        name=del_users[i].username)

            messages.success(
                self.request,
                'Removed {} member{} ({}).'.format(
                    del_count,
                    's' if del_count != 1 else '',
                    ', '.join([u.username for u in del_users])))

        if import_count == 0 and del_count == 0:
            messages.warning(
                self.request,
                'Nothing to {}, no changes made to project members.'.format(
                    import_mode))

        return redirect(reverse(
            'projectroles:roles',
            kwargs={'project': dest_project.omics_uuid}))


# ProjectInvite Views ----------------------------------------------------------


class ProjectInviteMixin:
    """General utilities for mixins"""

    @classmethod
    def _handle_invite(
            cls, invite, request, resend=False):
        """
        Handle invite creation, email sending/resending and logging to timeline
        :param invite: ProjectInvite object
        :param request: Django request object
        :param resend: Send or resend (bool)
        """
        timeline = get_backend_api('timeline_backend')
        send_str = 'resend' if resend else 'send'
        status_type = 'OK'
        status_desc = None

        if SEND_EMAIL:
            sent_mail = send_invite_mail(invite, request)

            if sent_mail == 0:
                status_type = 'FAILED'
                status_desc = 'Email sending failed'

        else:
            status_type = 'FAILED'
            status_desc = 'PROJECTROLES_SEND_EMAIL not True'

        if status_type != 'OK' and not resend:
            status_desc += ', invite not created'

        # Add event in Timeline
        if timeline:
            timeline.add_event(
                project=invite.project,
                app_name=APP_NAME,
                user=request.user,
                event_name='invite_{}'.format(send_str),
                description='{} project invite with role "{}" to {}'.format(
                    send_str,
                    invite.role.name,
                    invite.email),
                status_type=status_type,
                status_desc=status_desc)

        if status_type == 'OK':
            messages.success(
                request,
                'Invite for "{}" role in {} sent to {}, expires on {}'.format(
                    invite.role.name,
                    invite.project.title,
                    invite.email,
                    timezone.localtime(
                        invite.date_expire).strftime('%Y-%m-%d %H:%M')))

        elif not resend:  # NOTE: Delete invite if send fails
            invite.delete()
            messages.error(request, status_desc)


class ProjectInviteView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        TemplateView):
    """View for displaying and modifying project invites"""
    permission_required = 'projectroles.invite_users'
    template_name = 'projectroles/project_invites.html'
    model = ProjectInvite

    # TODO: is this needed?
    def get_object(self):
        """Override get_object to provide a Project object for both template
        and permission checking"""
        try:
            obj = Project.objects.get(omics_uuid=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectInviteView, self).get_context_data(
            *args, **kwargs)

        context['invites'] = ProjectInvite.objects.filter(
            project=context['project'],
            active=True,
            date_expire__gt=timezone.now())

        return context


class ProjectInviteCreateView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        ProjectContextMixin, ProjectInviteMixin, CreateView):
    """ProjectInvite creation view"""
    model = ProjectInvite
    form_class = ProjectInviteForm
    permission_required = 'projectroles.invite_users'

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectInviteCreateView, self).get_context_data(
            *args, **kwargs)

        project = self.get_permission_object()

        context['preview_subject'] = get_invite_subject(project)
        context['preview_body'] = get_invite_body(
            project=project,
            issuer=self.request.user,
            role_name='{role_name}',
            invite_url='http://XXXXXXXXXXXXXXXXXXXXXXX',
            date_expire_str='YYYY-MM-DD HH:MM').replace('\n', '\\n')
        context['preview_message'] = get_invite_message(
            '{message}').replace('\n', '\\n')
        context['preview_footer'] = get_email_footer().replace('\n', '\\n')

        return context

    def get_form_kwargs(self):
        """Pass current user to form"""
        kwargs = super(ProjectInviteCreateView, self).get_form_kwargs()
        kwargs.update({'current_user': self.request.user})
        kwargs.update({'project': self.get_permission_object().omics_uuid})
        return kwargs

    def form_valid(self, form):
        self.object = form.save()

        # Send mail and add to timeline
        self._handle_invite(invite=self.object, request=self.request)

        return redirect(reverse(
            'projectroles:invites',
            kwargs={'project': self.object.project.omics_uuid}))


class ProjectInviteAcceptView(
        LoginRequiredMixin, View):
    """View to handle accepting a project invite"""

    def get(self, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        tl_event = None

        def revoke_invite(invite, failed=True, fail_desc=''):
            """Set invite.active to False and save the invite"""
            invite.active = False
            invite.save()

            if failed and timeline:
                # Add event in Timeline
                timeline.add_event(
                    project=invite.project,
                    app_name=APP_NAME,
                    user=self.request.user,
                    event_name='invite_accept',
                    description='accept project invite',
                    status_type='FAILED',
                    status_desc=fail_desc)

        # Get invite and ensure it actually exists
        try:
            invite = ProjectInvite.objects.get(secret=kwargs['secret'])

        except ProjectInvite.DoesNotExist:
            messages.error(
                self.request,
                'Error: Invite does not exist!')
            return redirect(reverse('home'))

        # Check user does not already have a role
        try:
            RoleAssignment.objects.get(
                user=self.request.user,
                project=invite.project)
            messages.warning(
                self.request,
                'You already have roles set in this project.')
            revoke_invite(
                invite,
                failed=True,
                fail_desc='User already has roles in project')
            return redirect(reverse(
                'projectroles:detail',
                kwargs={'project': invite.project.omics_uuid}))

        except RoleAssignment.DoesNotExist:
            pass

        # Check expiration date
        if invite.date_expire < timezone.now():
            messages.error(
                self.request,
                'Error: Your invite has expired! '
                'Please contact the person who invited you: {} ({})'.format(
                    invite.issuer.name,
                    invite.issuer.email))

            # Send notification of expiry to issuer
            if SEND_EMAIL:
                send_expiry_note(invite, self.request)

            revoke_invite(invite, failed=True, fail_desc='Invite expired')
            return redirect(reverse('home'))

        # If we get this far, create RoleAssignment..

        # Add event in Timeline
        if timeline:
            tl_event = timeline.add_event(
                project=invite.project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='invite_accept',
                description='accept project invite with role of "{}"'.format(
                    invite.role.name))

        # Submit with taskflow
        if taskflow:
            if tl_event:
                tl_event.set_status('SUBMIT')

            flow_data = {
                'username': self.request.user.username,
                'user_uuid': str(self.request.user.omics_uuid),
                'role_pk': invite.role.pk}

            try:
                taskflow.submit(
                    project_uuid=str(invite.project.omics_uuid),
                    flow_name='role_update',
                    flow_data=flow_data,
                    request=self.request)

            except taskflow.FlowSubmitException as ex:
                if tl_event:
                    tl_event.set_status('FAILED', str(ex))

                messages.error(self.request, str(ex))
                return redirect(
                    reverse('home'))

            # Get object
            role_as = RoleAssignment.objects.get(
                project=invite.project, user=self.request.user)

            tl_event.set_status('OK')

        # Local save without Taskflow
        else:
            role_as = RoleAssignment(
                user=self.request.user,
                project=invite.project,
                role=invite.role)
            role_as.save()

            if tl_event:
                tl_event.set_status('OK')

        # ..notify the issuer by email..
        if SEND_EMAIL:
            send_accept_note(invite, self.request)

        # ..deactivate the invite..
        revoke_invite(invite, failed=False)

        # ..and finally redirect user to the project front page
        messages.success(
            self.request,
            'Welcome to project "{}"! You have been assigned the role of '
            '{}.'.format(
                invite.project.title,
                invite.role.name))
        return redirect(reverse(
            'projectroles:detail',
            kwargs={'project': invite.project.omics_uuid}))


class ProjectInviteResendView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        ProjectInviteMixin, View):
    """View to handle resending a project invite"""
    permission_required = 'projectroles.invite_users'

    def get(self, *args, **kwargs):
        try:
            invite = ProjectInvite.objects.get(
                omics_uuid=self.kwargs['projectinvite'],
                active=True)

        except ProjectInvite.DoesNotExist:
            messages.error(
                self.request,
                'Error: Invite not found!')
            return redirect(reverse(
                'projectroles:invites',
                kwargs={'project': self._get_project(
                    self.request, self.kwargs)}))

        # Reset invite expiration date
        invite.date_expire = get_expiry_date()
        invite.save()

        # Resend mail and add to timeline
        self._handle_invite(invite=invite, request=self.request, resend=True)

        return redirect(reverse(
            'projectroles:invites',
            kwargs={'project': invite.project.omics_uuid}))


class ProjectInviteRevokeView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectPermissionMixin,
        ProjectContextMixin, TemplateView):
    """Batch delete/move confirm view"""
    template_name = 'projectroles/invite_revoke_confirm.html'
    permission_required = 'projectroles.invite_users'

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectInviteRevokeView, self).get_context_data(
            *args, **kwargs)
        context['project'] = self._get_project(self.request, self.kwargs)

        if 'projectinvite' in self.kwargs:
            try:
                context['invite'] = ProjectInvite.objects.get(
                    omics_uuid=self.kwargs['projectinvite'])

            except ProjectInvite.DoesNotExist:
                pass

        return context

    def post(self, request, **kwargs):
        """Override post() to handle POST from confirmation template"""
        timeline = get_backend_api('timeline_backend')
        invite = None
        project = self._get_project(self.request, self.kwargs)

        try:
            invite = ProjectInvite.objects.get(
                omics_uuid=kwargs['projectinvite'])

            invite.active = False
            invite.save()
            messages.success(self.request, 'Invite revoked.')

        except ProjectInvite.DoesNotExist:
            messages.error(self.request, 'Error: Unable to revoke invite!')

        # Add event in Timeline
        if timeline and invite:
            timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='invite_revoke',
                description='revoke invite sent to "{}"'.format(
                    invite.email if invite else 'N/A'),
                status_type='OK' if invite else 'FAILED')

        return redirect(reverse(
            'projectroles:invites',
            kwargs={'project': project.omics_uuid}))


# Javascript API Views ---------------------------------------------------


class ProjectStarringAPIView(
        LoginRequiredMixin, ProjectPermissionMixin, APIPermissionMixin,
        APIView):
    """View to handle starring and unstarring a project via AJAX"""
    permission_required = 'projectroles.view_project'

    def post(self, request, *args, **kwargs):
        project = self.get_permission_object()
        user = request.user
        timeline = get_backend_api('timeline_backend')

        tag_state = get_tag_state(project, user)
        action_str = '{}star'.format('un' if tag_state else '')

        set_tag_state(project, user, PROJECT_TAG_STARRED)

        # Add event in Timeline
        if timeline:
            timeline.add_event(
                project=project,
                app_name=APP_NAME,
                user=user,
                event_name='project_{}'.format(action_str),
                description='{} project'.format(action_str),
                classified=True,
                status_type='INFO')

        return Response(0 if tag_state else 1, status=200)


# Taskflow API Views -----------------------------------------------------


# TODO: Limit access to localhost


# TODO: Use GET instead of POST
class ProjectGetAPIView(APIView):
    """API view for getting a project"""
    def post(self, request):
        try:
            project = Project.objects.get(
                omics_uuid=request.data['project_uuid'],
                submit_status=SUBMIT_STATUS_OK)

        except Project.DoesNotExist as ex:
            return Response(str(ex), status=404)

        ret_data = {
            'project_uuid': str(project.omics_uuid),
            'title': project.title,
            'description': project.description}

        return Response(ret_data, status=200)


class ProjectUpdateAPIView(APIView):
    """API view for updating a project"""
    def post(self, request):
        try:
            project = Project.objects.get(
                omics_uuid=request.data['project_uuid'])
            project.title = request.data['title']
            project.description = request.data['description']
            project.readme.raw = request.data['readme']
            project.save()

        except Project.DoesNotExist as ex:
            return Response(str(ex), status=404)

        return Response('ok', status=200)


# TODO: Use GET instead of POST
class RoleAssignmentGetAPIView(APIView):
    """API view for getting a role assignment for user and project"""
    def post(self, request):
        try:
            project = Project.objects.get(
                omics_uuid=request.data['project_uuid'])
            user = User.objects.get(omics_uuid=request.data['user_uuid'])

        except (Project.DoesNotExist, User.DoesNotExist) as ex:
            return Response(str(ex), status=404)

        try:
            role_as = RoleAssignment.objects.get(
                project=project, user=user)
            ret_data = {
                'assignment_uuid': str(role_as.omics_uuid),
                'project_uuid': str(role_as.project.omics_uuid),
                'user_uuid': str(role_as.user.omics_uuid),
                'role_pk': role_as.role.pk,
                'role_name': role_as.role.name}
            return Response(ret_data, status=200)

        except RoleAssignment.DoesNotExist as ex:
            return Response(str(ex), status=404)


class RoleAssignmentSetAPIView(APIView):
    """View for creating or updating a role assignment based on params"""
    def post(self, request):
        try:
            project = Project.objects.get(
                omics_uuid=request.data['project_uuid'])
            user = User.objects.get(omics_uuid=request.data['user_uuid'])
            role = Role.objects.get(pk=request.data['role_pk'])

        except (Project.DoesNotExist, User.DoesNotExist,
                Role.DoesNotExist) as ex:
            return Response(str(ex), status=404)

        try:
            role_as = RoleAssignment.objects.get(project=project, user=user)
            role_as.role = role
            role_as.save()

        except RoleAssignment.DoesNotExist:
            role_as = RoleAssignment(project=project, user=user, role=role)
            role_as.save()

        return Response('ok', status=200)


class RoleAssignmentDeleteAPIView(APIView):
    def post(self, request):
        try:
            project = Project.objects.get(
                omics_uuid=request.data['project_uuid'])
            user = User.objects.get(omics_uuid=request.data['user_uuid'])

        except (Project.DoesNotExist, User.DoesNotExist) as ex:
            return Response(str(ex), status=404)

        try:
            role_as = RoleAssignment.objects.get(project=project, user=user)
            role_as.delete()

        except RoleAssignment.DoesNotExist as ex:
            return Response(str(ex), status=404)

        return Response('ok', status=200)


# TODO: Use GET instead of POST
class ProjectSettingsGetAPIView(APIView):
    """API view for getting project settings"""
    def post(self, request):
        try:
            project = Project.objects.get(
                omics_uuid=request.data['project_uuid'])

        except Project.DoesNotExist as ex:
            return Response(str(ex), status=404)

        ret_data = {
            'project_uuid': project.omics_uuid,
            'settings': get_all_settings(project)}

        return Response(ret_data, status=200)


class ProjectSettingsSetAPIView(APIView):
    """API view for updating project settings"""
    def post(self, request):
        try:
            project = Project.objects.get(
                omics_uuid=request.data['project_uuid'])

        except Project.DoesNotExist as ex:
            return Response(str(ex), status=404)

        for k, v in json.loads(request.data['settings']).items():
            set_project_setting(project, k.split('.')[1], k.split('.')[2], v)

        return Response('ok', status=200)
