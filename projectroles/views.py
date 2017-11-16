from django.conf import settings
from django.contrib import auth
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import localtime
from django.views.generic import TemplateView, DetailView, UpdateView,\
    CreateView, DeleteView, View
from django.views.generic.edit import ModelFormMixin
from django.views.generic.detail import SingleObjectMixin, ContextMixin

from extra_views import ModelFormSetView
from rest_framework.response import Response
from rest_framework.views import APIView
from rules.contrib.views import PermissionRequiredMixin, redirect_to_login

from .email import send_role_change_mail, send_invite_mail, send_accept_note,\
    send_expiry_note, get_invite_subject, get_invite_body, get_invite_message, \
    get_email_footer, get_role_change_body, get_role_change_subject
from .forms import ProjectForm, RoleAssignmentForm, ProjectInviteForm,\
    ProjectSettingForm
from .models import Project, Role, RoleAssignment, ProjectInvite, \
    ProjectSetting, OMICS_CONSTANTS, PROJECT_TAG_STARRED
from .plugins import ProjectAppPluginPoint, get_active_plugins, get_backend_api
from .project_tags import get_tag_state, set_tag_state, remove_tag
from .utils import get_expiry_date
from projectroles.project_settings import save_default_project_settings

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
PROJECT_ROLE_STAFF = OMICS_CONSTANTS['PROJECT_ROLE_STAFF']
SUBMIT_STATUS_OK = OMICS_CONSTANTS['SUBMIT_STATUS_OK']
SUBMIT_STATUS_PENDING = OMICS_CONSTANTS['SUBMIT_STATUS_PENDING']
SUBMIT_STATUS_PENDING_TASKFLOW = OMICS_CONSTANTS['SUBMIT_STATUS_PENDING']

# Local constants
APP_NAME = 'projectroles'


# Mixins -----------------------------------------------------------------


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


class RolePermissionMixin(LoggedInPermissionMixin):
    """Mixin to ensure permissions for RoleAssignment according to user role in
    project"""
    def has_permission(self):
        """Override has_permission to check perms depending on role"""
        try:
            obj = RoleAssignment.objects.get(pk=self.kwargs['pk'])

            if obj.role.name == PROJECT_ROLE_OWNER:
                # Modifying the project owner is not allowed in role views
                return False

            elif obj.role.name == PROJECT_ROLE_DELEGATE:
                return self.request.user.has_perm(
                    'projectroles.update_project_delegate',
                    self.get_permission_object())

            elif obj.role.name == PROJECT_ROLE_STAFF:
                return self.request.user.has_perm(
                    'projectroles.update_project_staff',
                    self.get_permission_object())

            else:
                return self.request.user.has_perm(
                    'projectroles.update_project_members',
                    self.get_permission_object())

        except RoleAssignment.DoesNotExist:
            return False

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        if self.get_object():
            return self.get_object().project

        return None


class ProjectContextMixin(ContextMixin):
    """Mixin for adding context data to Project base view and other views
    extending it"""
    def get_context_data(self, *args, **kwargs):
        context = super(ProjectContextMixin, self).get_context_data(
            *args, **kwargs)

        # Project
        if hasattr(self, 'object') and isinstance(self.object, Project):
            context['project'] = self.get_object()

        elif hasattr(self, 'object') and hasattr(self.object, 'project'):
            context['project'] = self.object.project

        elif 'project' in self.kwargs:
            try:
                context['project'] = Project.objects.get(
                    pk=self.kwargs['project'])

            except Project.DoesNotExist:
                pass

        # Plugins stuff
        plugins = ProjectAppPluginPoint.get_plugins()

        if plugins:
            context['app_plugins'] = sorted([
                p for p in plugins if p.is_active()],
                key=lambda x: x.details_position)

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

        app_plugins = get_active_plugins(plugin_type='app')

        if app_plugins:
            context['app_plugins'] = app_plugins

        return context


# Base Project Views -----------------------------------------------------


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


class IrodsInfoView(LoginRequiredMixin, TemplateView):
    """iRODS server info and guide view"""
    template_name = 'projectroles/irods_info.html'

    def get_context_data(self, *args, **kwargs):
        context = super(IrodsInfoView, self).get_context_data(*args, **kwargs)

        # Add iRODS query API
        irods_backend = get_backend_api('omics_irods')

        if irods_backend:
            try:
                context['server_info'] = irods_backend.get_info()

            except irods_backend.IrodsQueryException:
                context['server_info'] = None

        context['irods_backend'] = get_backend_api('omics_irods')

        return context


class ProjectDetailView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        DetailView):
    """Project details view"""
    permission_required = 'projectroles.view_project'
    model = Project

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

        plugins = get_active_plugins(plugin_type='app')

        search_input = self.request.GET.get('s')
        context['search_input'] = search_input

        search_split = search_input.split(' ')
        search_term = search_split[0]
        search_type = None
        search_keywords = {}

        for i in range(1, len(search_split)):
            s = search_split[i]

            if ':' in s:
                kw = s.split(':')[0].lower().strip()
                val = s.split(':')[1].lower().strip()

                if kw == 'type':
                    search_type = val

                else:
                    search_keywords[kw] = val

            else:
                search_term += ' ' + s

        context['search_term'] = search_term
        context['search_type'] = search_type
        context['search_keywords'] = search_keywords

        if search_type:
            context['search_apps'] = [
                p for p in plugins if (
                    p.search_enable and
                    search_type in p.search_types)]

        else:
            context['search_apps'] = [p for p in plugins if p.search_enable]

        return context


# Project Editing Views --------------------------------------------------


class ProjectModifyMixin(ModelFormMixin):
    def form_valid(self, form):
        taskflow = get_backend_api('taskflow')
        timeline = get_backend_api('timeline_backend')
        tl_event = None
        form_action = 'update' if self.object else 'create'

        old_data = {
            'title': None,
            'description': None,
            'readme': None,
            'owner': None}

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
            project.submit_status = SUBMIT_STATUS_PENDING_TASKFLOW if taskflow \
                else SUBMIT_STATUS_PENDING

        else:
            project.submit_status = SUBMIT_STATUS_OK

        project.save()  # Got to save Project in order to refer to it
        owner = form.cleaned_data.get('owner')
        extra_data = {}
        type_str = 'Project' if project.type == PROJECT_TYPE_PROJECT else \
            'Category'

        if timeline:
            if form_action == 'create':
                tl_desc = 'create ' + type_str.lower() + \
                          ' with {owner} as owner'
                extra_data = {
                    'title': project.title,
                    'owner': owner.username,
                    'description': project.description,
                    'readme': project.readme.raw}

            else:
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
        if taskflow:
            if tl_event:
                tl_event.set_status('SUBMIT')

            flow_data = {
                'project_title': project.title,
                'project_description': project.description,
                'parent_pk': project.parent.pk if project.parent else 0,
                'owner_username': owner.username,
                'owner_pk': owner.pk,
                'owner_role_pk': Role.objects.get(
                    name='project owner').pk}

            if form_action == 'update':
                old_owner = project.get_owner().user
                flow_data['old_owner_pk'] = old_owner.pk
                flow_data['old_owner_username'] = old_owner.username

            try:
                taskflow.submit(
                    project_pk=project.pk,
                    flow_name='project_{}'.format(form_action),
                    flow_data=flow_data,
                    request=self.request)

            except taskflow.FlowSubmitException as ex:
                # NOTE: No need to update status as project will be deleted
                if form_action == 'create':
                    project.delete()

                else:
                    if tl_event:
                        tl_event.set_status('FAILED', str(ex))

                messages.error(self.request, str(ex))
                return HttpResponseRedirect(reverse('home'))

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

        # Post submit/save
        if form_action == 'create':
            # Set default settings for project app plugins
            if project.type == PROJECT_TYPE_PROJECT:
                save_default_project_settings(project)

            project.submit_status = SUBMIT_STATUS_OK
            project.save()

        if tl_event:
            tl_event.set_status('OK')

        messages.success(self.request, '{} {}d.'.format(type_str, form_action))
        return HttpResponseRedirect(reverse(
            'project_detail', kwargs={'pk': project.pk}))


class ProjectCreateView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectModifyMixin,
        ProjectContextMixin, CreateView):
    """Project creation view"""
    permission_required = 'projectroles.create_project'
    model = Project
    form_class = ProjectForm

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission from
        parent"""
        if 'project' in self.kwargs:
            try:
                obj = Project.objects.get(pk=self.kwargs['project'])
                return obj

            except Project.DoesNotExist:
                return None

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectCreateView, self).get_context_data(
            *args, **kwargs)

        if 'project' in self.kwargs:
            context['parent'] = Project.objects.get(pk=self.kwargs['project'])

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
            project = Project.objects.get(pk=self.kwargs['project'])

            if project.type != PROJECT_TYPE_CATEGORY:
                messages.error(
                    self.request,
                    'Creating a project within a project is not allowed')
                return HttpResponseRedirect(
                    reverse(
                        'project_detail', kwargs={'pk': project.pk}))

        return super(ProjectCreateView, self).get(request, *args, **kwargs)


class ProjectUpdateView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        ProjectModifyMixin, UpdateView):
    """Project updating view"""
    permission_required = 'projectroles.update_project'
    model = Project
    form_class = ProjectForm

    def get_form_kwargs(self):
        kwargs = super(ProjectUpdateView, self).get_form_kwargs()
        kwargs.update({'current_user': self.request.user})
        return kwargs


class ProjectStarringView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin, View):
    """View to handle starring and unstarring a project"""
    permission_required = 'projectroles.view_project'

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        try:
            obj = Project.objects.get(pk=self.kwargs['pk'])
            return obj

        except Project.DoesNotExist:
            return None

    def get(self, *args, **kwargs):
        project = self.get_permission_object()
        user = self.request.user
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

        messages.success(
            self.request,
            'Project "{}" {}red.'.format(project.title, action_str))

        return redirect(reverse(
            'project_detail', kwargs={'pk': project.pk}))


# RoleAssignment Views ---------------------------------------------------


class ProjectRoleView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        SingleObjectMixin, TemplateView):
    """View for displaying project roles"""
    permission_required = 'projectroles.view_project_roles'
    template_name = 'projectroles/project_roles.html'
    model = Project

    def get_object(self):
        """Override get_object to provide a Project object for both template
        and permission checking"""
        try:
            obj = Project.objects.get(pk=self.kwargs['pk'])
            return obj

        except Project.DoesNotExist:
            return None

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectRoleView, self).get_context_data(
            *args, **kwargs)

        context['owner'] = self.object.get_owner()
        context['delegate'] = self.object.get_delegate()
        context['staff'] = self.object.get_staff()
        context['members'] = self.object.get_members()
        return context

    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to ensure self.object is provided to template"""
        self.object = self.get_object()

        return super(
            ProjectRoleView, self).dispatch(request, *args, **kwargs)


class RoleAssignmentModifyMixin(ModelFormMixin):
    def get_context_data(self, *args, **kwargs):
        context = super(RoleAssignmentModifyMixin, self).get_context_data(
            *args, **kwargs)

        change_type = self.request.resolver_match.url_name.split('_')[1]
        project = Project.objects.get(pk=self.kwargs['project'])

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
                    'project_detail',
                    kwargs={'pk': project.pk}))).replace('\n', '\\n')

        return context

    def form_valid(self, form):
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        form_action = 'update' if self.object else 'create'
        tl_event = None

        project = self.get_context_data()['project']
        user = form.cleaned_data.get('user')
        role = form.cleaned_data.get('role')

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
        if taskflow:
            if tl_event:
                tl_event.set_status('SUBMIT')

            flow_data = {
                'username': user.username,
                'user_pk': user.pk,
                'role_pk': role.pk}

            try:
                taskflow.submit(
                    project_pk=project.pk,
                    flow_name='role_update',
                    flow_data=flow_data,
                    request=self.request)

            except taskflow.FlowSubmitException as ex:
                if tl_event:
                    tl_event.set_status('FAILED', str(ex))

                messages.error(self.request, str(ex))
                return redirect(
                    reverse('project_roles', kwargs={'pk': project.pk}))

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
            'Membership {} for {} in {} with the role of {}.'.format(
                'added' if form_action == 'create' else 'updated',
                self.object.user.username,
                self.object.project.title,
                self.object.role.name))
        return redirect(
            reverse('project_roles', kwargs={'pk': self.object.project.pk}))


class RoleAssignmentCreateView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        RoleAssignmentModifyMixin, CreateView):
    """RoleAssignment creation view"""
    permission_required = 'projectroles.update_project_members'
    model = RoleAssignment
    form_class = RoleAssignmentForm

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        try:
            obj = Project.objects.get(pk=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None

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

    def post(self, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')
        taskflow = get_backend_api('taskflow')
        tl_event = None

        self.object = RoleAssignment.objects.get(pk=kwargs['pk'])
        project = self.object.project
        user = self.object.user
        role = self.object.role

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
        if taskflow:
            if tl_event:
                tl_event.set_status('SUBMIT')

            flow_data = {
                'username': user.username,
                'user_pk': user.pk,
                'role_pk': role.pk}

            try:
                taskflow.submit(
                    project_pk=project.pk,
                    flow_name='role_delete',
                    flow_data=flow_data,
                    request=self.request)
                self.object = None

            except taskflow.FlowSubmitException as ex:
                if tl_event:
                    tl_event.set_status('FAILED', str(ex))

                messages.error(self.request, str(ex))
                return HttpResponseRedirect(redirect(
                    reverse('project_roles', kwargs={'pk': project.pk})))

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
            self.request, 'Membership of {} removed from {}.'.format(
                user.username,
                project.title))

        return HttpResponseRedirect(reverse(
            'project_roles', kwargs={'pk': project.pk}))

    def get_form_kwargs(self):
        """Pass current user to form"""
        kwargs = super(RoleAssignmentDeleteView, self).get_form_kwargs()
        kwargs.update({'current_user': self.request.user})
        return kwargs


# ProjectInvite Views ----------------------------------------------------


class ProjectInviteView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        SingleObjectMixin, TemplateView):
    """View for displaying and modifying project invites"""
    permission_required = 'projectroles.invite_users'
    template_name = 'projectroles/project_invites.html'
    model = ProjectInvite

    def get_object(self):
        """Override get_object to provide a Project object for both template
        and permission checking"""
        try:
            obj = Project.objects.get(pk=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectInviteView, self).get_context_data(
            *args, **kwargs)

        context['invites'] = ProjectInvite.objects.filter(
            project=self.kwargs['project'],
            active=True,
            date_expire__gt=timezone.now())

        return context

    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to ensure self.object is provided to template"""
        self.object = self.get_object()

        return super(
            ProjectInviteView, self).dispatch(request, *args, **kwargs)


class ProjectInviteCreateView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        CreateView):
    """ProjectInvite creation view"""
    model = ProjectInvite
    form_class = ProjectInviteForm
    permission_required = 'projectroles.invite_users'

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        try:
            obj = Project.objects.get(pk=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None

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
        kwargs.update({'project': self.get_permission_object().pk})
        return kwargs

    def form_valid(self, form):
        timeline = get_backend_api('timeline_backend')
        self.object = form.save()

        if SEND_EMAIL:
            send_invite_mail(self.object, self.request)

        # Add event in Timeline
        if timeline:
            timeline.add_event(
                project=self.object.project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='invite_send',
                description='send project invite with role "{}" to {}'.format(
                    self.object.role.name,
                    self.object.email),
                status_type='OK')

        messages.success(
            self.request,
            'Invite for "{}" role in {} sent to {}, expires on {}'.format(
                self.object.role.name,
                self.object.project.title,
                self.object.email,
                timezone.localtime(
                    self.object.date_expire).strftime('%Y-%m-%d %H:%M')))

        return redirect(
            reverse(
                'role_invites',
                kwargs={'project': self.object.project.pk}))


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
                'project_detail', kwargs={'pk': invite.project.pk}))

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
                'user_pk': self.request.user.pk,
                'role_pk': invite.role.pk}

            try:
                taskflow.submit(
                    project_pk=invite.project.pk,
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
            'project_detail', kwargs={'pk': invite.project.pk}))


class ProjectInviteResendView(
        LoginRequiredMixin, LoggedInPermissionMixin, View):
    """View to handle resending a project invite"""
    permission_required = 'projectroles.invite_users'

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        try:
            obj = Project.objects.get(pk=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None

    def get(self, *args, **kwargs):
        timeline = get_backend_api('timeline_backend')

        try:
            invite = ProjectInvite.objects.get(
                pk=self.kwargs['pk'],
                active=True)

        except ProjectInvite.DoesNotExist:
            messages.error(
                self.request,
                'Error: Invite not found!')
            return redirect(reverse(
                'project_invites',
                kwargs={'project': kwargs['project']}))

        # Reset invite expiration date
        invite.date_expire = get_expiry_date()
        invite.save()

        # Resend mail
        if SEND_EMAIL:
            send_invite_mail(invite, self.request)

        # Add event in Timeline
        if timeline:
            timeline.add_event(
                project=invite.project,
                app_name=APP_NAME,
                user=self.request.user,
                event_name='invite_resend',
                description='resend invite to "{}"'.format(
                    invite.email),
                status_type='OK')

        messages.success(
            self.request,
            'Invitation resent to {}, expires on {}.'.format(
                invite.email,
                localtime(invite.date_expire).strftime('%Y-%m-%d %H:%M')))

        return redirect(reverse(
            'role_invites', kwargs={'project': invite.project.pk}))


class ProjectInviteRevokeView(
        LoginRequiredMixin, LoggedInPermissionMixin, ProjectContextMixin,
        TemplateView):
    """Batch delete/move confirm view"""
    template_name = 'projectroles/invite_revoke_confirm.html'
    permission_required = 'projectroles.invite_users'

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        try:
            obj = Project.objects.get(pk=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectInviteRevokeView, self).get_context_data(
            *args, **kwargs)

        if 'project' in self.kwargs:
            try:
                context['project'] = Project.objects.get(
                    pk=self.kwargs['project'])

            except Project.DoesNotExist:
                pass

        if 'pk' in self.kwargs:
            try:
                context['invite'] = ProjectInvite.objects.get(
                    pk=self.kwargs['pk'])

            except ProjectInvite.DoesNotExist:
                pass

        return context

    def post(self, request, **kwargs):
        """Override post() to handle POST from confirmation template"""
        timeline = get_backend_api('timeline_backend')
        invite = None

        try:
            invite = ProjectInvite.objects.get(
                pk=kwargs['pk'])

            invite.active = False
            invite.save()
            messages.success(self.request, 'Invite revoked.')

        except ProjectInvite.DoesNotExist:
            messages.error(self.request, 'Error: Unable to revoke invite!')

        # Add event in Timeline
        if timeline:
            timeline.add_event(
                project=Project.objects.get(pk=self.kwargs['project']),
                app_name=APP_NAME,
                user=self.request.user,
                event_name='invite_revoke',
                description='revoke invite sent to "{}"'.format(
                    invite.email if invite else 'N/A'),
                status_type='OK' if invite else 'FAILED')

        return redirect(reverse(
            'role_invites',
            kwargs={'project': kwargs['project']}))


# Settings Views ---------------------------------------------------------


class ProjectSettingUpdateView(
        LoginRequiredMixin, LoggedInPermissionMixin,
        ProjectContextMixin, ModelFormSetView):
    permission_required = 'projectroles.update_project_settings'
    template_name = 'projectroles/projectsettings_formset.html'
    model = ProjectSetting
    fields = ['value']
    can_delete = False
    extra = 0
    form_class = ProjectSettingForm

    def get_permission_object(self):
        """Override get_permission_object for checking Project permission"""
        try:
            obj = Project.objects.get(pk=self.kwargs['project'])
            return obj

        except Project.DoesNotExist:
            return None

    def get_queryset(self):
        project = self.kwargs['project']

        return super(
            ProjectSettingUpdateView, self).get_queryset().filter(
                project=project)

    def get_success_url(self):
        timeline = get_backend_api('timeline_backend')

        # Add event in Timeline
        if timeline:
            timeline.add_event(
                project=Project.objects.get(pk=self.kwargs['project']),
                app_name=APP_NAME,
                user=self.request.user,
                event_name='settings_update',
                description='update settings',
                status_type='OK')

        messages.success(
            self.request, 'Settings updated.')

        return reverse(
            'project_detail', kwargs={'pk': self.kwargs['project']})


# Taskflow API Views -----------------------------------------------------


class ProjectGetAPIView(APIView):
    """API view for getting a project"""
    def post(self, request):
        try:
            project = Project.objects.get(
                pk=request.data['project_pk'],
                submit_status=SUBMIT_STATUS_OK)

        except Project.DoesNotExist as ex:
            return Response(str(ex), status=404)

        # Could also use a generic serializer
        # Add more fields from Project here if needed..
        ret_data = {
            'project_pk': project.pk,    # Always define what object pk is for
            'title': project.title,
            'description': project.description}

        return Response(ret_data, status=200)


class ProjectUpdateAPIView(APIView):
    """API view for updating a project"""
    def post(self, request):
        try:
            project = Project.objects.get(pk=request.data['project_pk'])
            project.title = request.data['title']
            project.description = request.data['description']
            project.save()

        except Project.DoesNotExist as ex:
            return Response(str(ex), status=404)

        return Response('ok', status=200)


class RoleAssignmentGetAPIView(APIView):
    """API view for getting a role assignment for user and project"""
    def post(self, request):
        try:
            project = Project.objects.get(pk=request.data['project_pk'])
            user = User.objects.get(pk=request.data['user_pk'])

        except (Project.DoesNotExist, User.DoesNotExist) as ex:
            return Response(str(ex), status=404)

        try:
            role_as = RoleAssignment.objects.get(
                project=project, user=user)
            ret_data = {
                'assignment_pk': role_as.pk,
                'project_pk': role_as.project.pk,
                'user_pk': role_as.user.pk,
                'role_pk': role_as.role.pk,
                'role_name': role_as.role.name}
            return Response(ret_data, status=200)

        except RoleAssignment.DoesNotExist as ex:
            return Response(str(ex), status=404)


class RoleAssignmentSetAPIView(APIView):
    """View for creating or updating a role assignment based on params"""
    def post(self, request):
        try:
            project = Project.objects.get(pk=request.data['project_pk'])
            user = User.objects.get(pk=request.data['user_pk'])
            role = Role.objects.get(pk=request.data['role_pk'])

        except (Project.DoesNotExist, User.DoesNotExist,
                Role.DoesNotExist) as ex:
            return Response(str(ex), status=404)

        try:
            role_as = RoleAssignment.objects.get(
                project=project, user=user)
            role_as.role = role
            role_as.save()

        except RoleAssignment.DoesNotExist:
            role_as = RoleAssignment(project=project, user=user, role=role)
            role_as.save()

        return Response('ok', status=200)


class RoleAssignmentDeleteAPIView(APIView):
    def post(self, request):
        try:
            project = Project.objects.get(pk=request.data['project_pk'])
            user = User.objects.get(pk=request.data['user_pk'])

        except (Project.DoesNotExist, User.DoesNotExist) as ex:
            return Response(str(ex), status=404)

        try:
            role_as = RoleAssignment.objects.get(
                project=project, user=user)
            role_as.delete()

        except RoleAssignment.DoesNotExist as ex:
            return Response(str(ex), status=404)

        return Response('ok', status=200)
