import datetime as dt

from django import forms
from django.conf import settings
from django.contrib import auth
from django.utils import timezone

from pagedown.widgets import PagedownWidget

from .models import Project, Role, RoleAssignment, ProjectInvite, \
    ProjectSetting, OMICS_CONSTANTS, PROJECT_SETTING_VAL_MAXLENGTH
from .plugins import ProjectAppPluginPoint
from .utils import get_user_display_name, build_secret
from projectroles.project_settings import validate_project_setting, \
    get_project_setting, get_default_setting

# Omics constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_TYPE_CHOICES = OMICS_CONSTANTS['PROJECT_TYPE_CHOICES']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
SUBMIT_STATUS_OK = OMICS_CONSTANTS['SUBMIT_STATUS_OK']
SUBMIT_STATUS_PENDING = OMICS_CONSTANTS['SUBMIT_STATUS_PENDING']
SUBMIT_STATUS_PENDING_TASKFLOW = OMICS_CONSTANTS['SUBMIT_STATUS_PENDING']

# Local constants and settings
APP_NAME = 'projectroles'
INVITE_EXPIRY_DAYS = settings.PROJECTROLES_INVITE_EXPIRY_DAYS


User = auth.get_user_model()


# Project form -----------------------------------------------------------


class ProjectForm(forms.ModelForm):
    """Form for Project creation/updating"""
    owner = forms.ModelChoiceField(
        User.objects.all(),
        required=True,
        to_field_name='omics_uuid',
        label='Owner',
        help_text='Project owner')

    class Meta:
        model = Project
        fields = ['title', 'type', 'parent', 'owner', 'description', 'readme']

    def __init__(self, project=None, current_user=None, *args, **kwargs):
        """Override for form initialization"""
        super(ProjectForm, self).__init__(*args, **kwargs)

        # Add settings fields
        self.app_plugins = sorted(
            [p for p in ProjectAppPluginPoint.get_plugins() if
             p.project_settings],
            key=lambda x: x.name)

        for p in self.app_plugins:
            for s_key in sorted(p.project_settings):
                s = p.project_settings[s_key]
                s_field = 'settings.{}.{}'.format(p.name, s_key)
                setting_kwargs = {
                    'required': False,
                    'label': '{}.{}'.format(p.name, s_key),
                    'help_text': s['description']}

                if s['type'] == 'STRING':
                    self.fields[s_field] = forms.CharField(
                        max_length=PROJECT_SETTING_VAL_MAXLENGTH,
                        **setting_kwargs)

                elif s['type'] == 'INTEGER':
                    self.fields[s_field] = forms.IntegerField(
                        **setting_kwargs)

                elif s['type'] == 'BOOLEAN':
                    self.fields[s_field] = forms.BooleanField(
                        **setting_kwargs)

                # Set initial value
                if self.instance.pk:
                    self.initial[s_field] = get_project_setting(
                        project=self.instance,
                        app_name=p.name,
                        setting_name=s_key)

                else:
                    self.initial[s_field] = get_default_setting(
                        app_name=p.name,
                        setting_name=s_key)

        # Access parent project if present
        parent_project = None

        if project:
            try:
                parent_project = Project.objects.get(omics_uuid=project)

            except Project.DoesNotExist:
                pass

        # Get current user for checking permissions for form items
        if current_user:
            self.current_user = current_user

        # Do not allow transfer under another parent
        self.fields['parent'].disabled = True

        ####################
        # Form modifications
        ####################

        # Modify ModelChoiceFields to use omics_uuid
        self.fields['parent'].to_field_name = 'omics_uuid'

        # Set readme widget with preview
        self.fields['readme'].widget = PagedownWidget(show_preview=True)

        # Updating an existing project
        if self.instance.pk:
            # Set readme value as raw markdown
            self.initial['readme'] = self.instance.readme.raw

            # Do not allow change of project type
            force_select_value(
                self.fields['type'],
                (self.instance.type, self.instance.type))

            # Only owner/superuser has rights to modify owner
            if (current_user.has_perm(
                    'projectroles.update_project_owner',
                    self.instance)):
                # Limit owner choices to users without non-owner role in project
                project_users = RoleAssignment.objects.filter(
                    project=self.instance.pk).exclude(
                   role__name=PROJECT_ROLE_OWNER).values_list('user').distinct()

                # Get owner choices
                self.fields['owner'].choices = [
                    (user.omics_uuid, get_user_display_name(user, True)) for
                    user in get_selectable_users(current_user).exclude(
                        pk__in=project_users).order_by('name')]

                # Set current owner as initial value
                owner = self.instance.get_owner().user
                self.initial['owner'] = owner.omics_uuid

            # Else don't allow changing the user
            else:
                owner = self.instance.get_owner().user
                force_select_value(
                    self.fields['owner'],
                    (owner.omics_uuid, get_user_display_name(owner, True)))

            # Set initial value for parent
            if parent_project:
                self.initial['parent'] = parent_project.omics_uuid

            else:
                self.initial['parent'] = None

        # Project creation
        else:
            # Common stuff
            self.fields['owner'].choices = [
                (user.omics_uuid, get_user_display_name(user, True)) for user in
                get_selectable_users(current_user).order_by('username')]

            # Creating a subproject
            if parent_project:
                # Parent must be current parent
                force_select_value(
                    self.fields['parent'],
                    (parent_project.omics_uuid, parent_project.title))

                # Set parent owner as initial value
                parent_owner = parent_project.get_owner().user
                self.initial['owner'] = parent_owner.omics_uuid

                # Set up parent field
                self.initial['parent'] = parent_project.omics_uuid

            # Creating a top level project
            else:
                self.fields['owner'].choices = [
                    (user.omics_uuid, get_user_display_name(user, True)) for
                    user in get_selectable_users(current_user).order_by(
                        'username')]

                # Limit project type choice to category
                force_select_value(
                    self.fields['type'],
                    (PROJECT_TYPE_CATEGORY, 'Category'))

                # Set up parent field
                self.initial['parent'] = None

    def clean(self):
        """Function for custom form validation and cleanup"""

        # Ensure the title is unique within parent
        try:
            existing_project = Project.objects.get(
                parent=self.cleaned_data.get('parent'),
                title=self.cleaned_data.get('title'))
            if not self.instance or existing_project.pk != self.instance.pk:
                self.add_error('title', 'Title must be unique within parent')

        except Project.DoesNotExist:
            pass

        # Ensure title is not equal to parent
        parent = self.cleaned_data.get('parent')

        if parent and parent.title == self.cleaned_data.get('title'):
            self.add_error(
                'title', 'Project and parent titles can not be equal')

        # Ensure owner has been set
        if not self.cleaned_data.get('owner'):
            self.add_error('owner', 'Owner must be set for project')

        # Verify settings fields
        for p in self.app_plugins:
            for s_key in sorted(p.project_settings):
                s = p.project_settings[s_key]
                s_field = 'settings.{}.{}'.format(p.name, s_key)

                if not validate_project_setting(
                        setting_type=s['type'],
                        setting_value=self.cleaned_data.get(s_field)):
                    self.add_error(s_field, 'Invalid value')

        return self.cleaned_data


# RoleAssignment form ----------------------------------------------------


class RoleAssignmentForm(forms.ModelForm):
    """Form for editing Project role assignments"""

    class Meta:
        model = RoleAssignment
        fields = ['project', 'user', 'role']

    def __init__(self, project=None, current_user=None, *args, **kwargs):
        """Override for form initialization"""
        super(RoleAssignmentForm, self).__init__(*args, **kwargs)

        # Get current user for checking permissions for form items
        if current_user:
            self.current_user = current_user

        # Get the project for which role is being assigned
        self.project = None

        if self.instance.pk:
            self.project = self.instance.project

        else:
            try:
                self.project = Project.objects.get(omics_uuid=project)

            except Project.DoesNotExist:
                pass

        ####################
        # Form modifications
        ####################

        # Modify ModelChoiceFields to use omics_uuid
        self.fields['project'].to_field_name = 'omics_uuid'
        self.fields['user'].to_field_name = 'omics_uuid'

        # Limit role choices
        self.fields['role'].choices = get_role_choices(
            self.project, self.current_user)

        # Updating an existing assignment
        if self.instance.pk:
            # Do not allow switching to another project
            force_select_value(
                self.fields['project'],
                (self.instance.project.omics_uuid,
                 self.instance.project.title))

            # Do not allow switching to a different user
            force_select_value(
                self.fields['user'],
                (self.instance.user.omics_uuid, get_user_display_name(
                    self.instance.user, True)))

            # Set initial role
            self.fields['role'].initial = self.instance.role

        # Creating a new assignment
        elif self.project:
            # Limit project choice to self.project
            force_select_value(
                self.fields['project'],
                (self.project.omics_uuid, self.project.title))

            # Limit user choices to users without roles in current project
            project_users = RoleAssignment.objects.filter(
                project=self.project.pk).values_list('user').distinct()

            self.fields['user'].choices = [
                (user.omics_uuid, get_user_display_name(user, True)) for user in
                get_selectable_users(current_user).exclude(
                    pk__in=project_users).order_by('name')]

    def clean(self):
        """Function for custom form validation and cleanup"""
        role = self.cleaned_data.get('role')
        existing_as = None

        try:
            existing_as = RoleAssignment.objects.get_assignment(
                self.cleaned_data.get('user'),
                self.cleaned_data.get('project'))

        except RoleAssignment.DoesNotExist:
            pass

        # Adding a new RoleAssignment
        if not self.instance.pk:
            # Make sure user doesn't already have role in project
            if existing_as:
                self.add_error(
                    'user',
                    'User {} already assigned as {}'.format(
                        existing_as.role.name,
                        get_user_display_name(self.cleaned_data.get('user'))))

        # Updating a RoleAssignment
        else:
            # Ensure not setting existing role again
            if existing_as and existing_as.role == role:
                self.add_error(
                    'role', 'Role already assigned to user')

        # Delegate checks
        if role.name == PROJECT_ROLE_DELEGATE:
            # Ensure current user has permission to set delegate
            if (not self.current_user.has_perm(
                    'projectroles.update_project_delegate',
                    obj=self.project)):
                self.add_error(
                    'role', 'Insufficient permissions for altering delegate')

            # Ensure user can't attempt to add another delegate
            delegate = self.cleaned_data.get('project').get_delegate()

            if delegate:
                self.add_error(
                    'role',
                    'User {} already assigned as delegate, only one '
                    'delegate allowed per project'.format(
                        delegate.user.username))

        return self.cleaned_data


# ProjectInvite form -----------------------------------------------------


class ProjectInviteForm(forms.ModelForm):
    """Form for ProjectInvite modification"""

    class Meta:
        model = ProjectInvite
        fields = ['email', 'role', 'message']

    def __init__(self, project=None, current_user=None, *args, **kwargs):
        """Override for form initialization"""
        super(ProjectInviteForm, self).__init__(*args, **kwargs)

        # Get current user for checking permissions and saving issuer
        if current_user:
            self.current_user = current_user

        # Get the project for which invite is being sent
        self.project = None

        try:
            self.project = Project.objects.get(omics_uuid=project)

        except Project.DoesNotExist:
            pass

        # Limit Role choices according to user permissions
        self.fields['role'].choices = get_role_choices(
            self.project,
            self.current_user,
            allow_delegate=False)   # NOTE: Inviting delegate here not allowed

    def clean(self):
        # Check if user email is already in users
        try:
            existing_user = User.objects.get(
                email=self.cleaned_data.get('email'))
            self.add_error(
                'email',
                'User "{}" already exists in the system with this email. '
                'Please use "Add Role" instead.'.format(existing_user.username))

        except User.DoesNotExist:
            pass

        # Check if user already has an invite in the project
        try:
            ProjectInvite.objects.get(
                project=self.project,
                email=self.cleaned_data.get('email'),
                active=True,
                date_expire__gt=timezone.now())

            self.add_error(
                'email',
                'There is already an active invite for email {} in {}'.format(
                    self.cleaned_data.get('email'),
                    self.project.title))

        except ProjectInvite.DoesNotExist:
            pass

        return self.cleaned_data

    def save(self, *args, **kwargs):
        """Override of form saving function"""
        obj = super(ProjectInviteForm, self).save(commit=False)

        obj.project = self.project
        obj.issuer = self.current_user
        obj.date_expire = timezone.now() + timezone.timedelta(
            days=INVITE_EXPIRY_DAYS)
        obj.secret = build_secret()

        obj.save()
        return obj


# Helper functions -------------------------------------------------------


def force_select_value(field, choice):
    """
    Force a pre-selected choice in a select field without disabling the
    field from the form submission
    :param field: Form field to be altered
    :param choice: Selected choice (tuple)
    """

    # NOTE: "Readonly" does not actually work with select-fields, Django
    #           still renders it as it would
    field.choices = [choice]
    field.widget.attrs['readonly'] = True


def get_role_choices(project, current_user, allow_delegate=True):
    """
    Return valid role choices according to permissions of current user
    :param project: Project in which role will be assigned
    :param current_user: User for whom the form is displayed
    :param allow_delegate: Whether delegate setting should be allowed (bool)
    """

    # Owner cannot be changed in role assignment
    role_excludes = [PROJECT_ROLE_OWNER]

    # Exclude delegate if not allowed or current user lacks perms
    if not allow_delegate or not current_user.has_perm(
            'projectroles.update_project_delegate',
            obj=project):
        role_excludes.append(PROJECT_ROLE_DELEGATE)

    return [
        (role.pk, role.name) for role in Role.objects.exclude(
            name__in=role_excludes)]


# TODO: TBD: Needed by other apps than projectroles? Move e.g. to utils?
def get_selectable_users(current_user):
    """
    Return selectable users according to current user level: only show
    non-system users for non-superusers
    :param current_user: User object
    :return: QuerySet
    """
    if not current_user.is_superuser:
        return User.objects.exclude(groups__name='system')

    return User.objects.all()
