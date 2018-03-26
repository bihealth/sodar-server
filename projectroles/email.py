"""Email creation and sending for the projectroles app"""

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.timezone import localtime

from .utils import build_invite_url


# Settings
SUBJECT_PREFIX = settings.EMAIL_SUBJECT_PREFIX
EMAIL_SENDER = settings.EMAIL_SENDER
DEBUG = settings.DEBUG


# Generic Elements -------------------------------------------------------


MESSAGE_HEADER = r'''
Dear {recipient},

This email has been automatically sent to you by the
CUBI Omics Data Management system.

'''.lstrip()

MESSAGE_HEADER_NO_RECIPIENT = r'''
This email has been automatically sent to you by the
CUBI Omics Data Management system.
'''.lstrip()

MESSAGE_FOOTER = r'''
For support or reporting issues regarding the CUBI Omics Data Management
system, contact Mikko Nieminen (mikko.nieminen@bihealth.de).
'''


# Role Change Template ---------------------------------------------------


SUBJECT_ROLE_CREATE = 'Membership granted for project "{}"'
SUBJECT_ROLE_UPDATE = 'Membership changed in project "{}"'
SUBJECT_ROLE_DELETE = 'Membership removed from project "{}"'

MESSAGE_ROLE_CREATE = r'''
{issuer_name} ({issuer_email}) has granted you the membership
in project "{project}" with the role of "{role}".

To access the project in the CUBI Omics Data Management
system, please click on the following link:
{project_url}
'''.lstrip()

MESSAGE_ROLE_UPDATE = r'''
{issuer_name} ({issuer_email}) has changed your membership
role in project "{project}" into "{role}".

To access the project in the CUBI Omics Data Management system,
please click on the following link:
{project_url}
'''.lstrip()

MESSAGE_ROLE_DELETE = r'''
{issuer_name} ({issuer_email}) has removed your membership
from project "{project}".
'''.lstrip()


# Invite Template --------------------------------------------------------


SUBJECT_INVITE = 'Invitation for project "{}"'

MESSAGE_INVITE_BODY = r'''
You have been invited by {issuer_name} ({issuer_email})
to share data in the project "{project}" with the role of "{role}".

To accept the invitation and access the project in the
Omics Data Management system, please click on the following link:
{invite_url}

This invitation will expire on {date_expire}.
'''
MESSAGE_INVITE_ISSUER = r'''
Message from the sender of this invitation:
----------------------------------------
{}
----------------------------------------
'''


# Invite Acceptance Notification Template --------------------------------


SUBJECT_ACCEPT = 'Invitation accepted by {user_name} for project "{project}"'

MESSAGE_ACCEPT_BODY = r'''
Invitation sent by you for role of "{role}" in project "{project}"
has been accepted by {user_name} ({user_email}).
They have been granted access in the project accordingly.
'''.lstrip()


# Invite Expiry Notification Template ------------------------------------


SUBJECT_EXPIRY = 'Expired invitation used by {user_name} in "{project}"'

MESSAGE_EXPIRY_BODY = r'''
Invitation sent by you for role of "{role}" in project "{project}"
was attempted to be used by {user_name} ({user_email}).

This invitation has expired on {date_expire}. Because of this,
access was not granted to the user.

Please add the role manually with "Add Member", if you still wish
to grant the user access to the project.
'''.lstrip()


# Email composing helpers ------------------------------------------------


def get_invite_body(
        project, issuer, role_name, invite_url, date_expire_str, message=None):
    """
    Return the invite content header.
    :param project: Project object
    :param issuer: User object
    :param role_name: Display name of the Role object
    :param invite_url: Generated URL for the invite
    :param date_expire_str: Expiry date as a pre-formatted string
    :param message: Optional user message as string
    :return: string
    """
    body = MESSAGE_HEADER_NO_RECIPIENT

    body += MESSAGE_INVITE_BODY.format(
        issuer_name=issuer.name,
        issuer_email=issuer.email,
        project=project.title,
        role=role_name,
        invite_url=invite_url,
        date_expire=date_expire_str)

    return body


def get_invite_message(message=None):
    """
    Return the message from invite issuer, of empty string if not set.
    :param message: Optional user message as string
    :return: string
    """
    if message and len(message) > 0:
        return MESSAGE_INVITE_ISSUER.format(message)

    return ''


def get_email_footer():
    """
    Return the invite content footer.
    :return: string
    """
    return MESSAGE_FOOTER


def get_invite_subject(project):
    """
    Return invite email subject
    :param project: Project object
    :return: string
    """
    return SUBJECT_PREFIX + ' ' + SUBJECT_INVITE.format(project.title)


def get_role_change_subject(change_type, project):
    """
    Return role change email subject
    :param change_type: Change type ('create', 'update', 'delete')
    :param project: Project object
    :return: String
    """
    subject = SUBJECT_PREFIX + ' '

    if change_type == 'create':
        subject += SUBJECT_ROLE_CREATE.format(project.title)

    elif change_type == 'update':
        subject += SUBJECT_ROLE_UPDATE.format(project.title)

    elif change_type == 'delete':
        subject += SUBJECT_ROLE_DELETE.format(project.title)

    return subject


def get_role_change_body(
        change_type, project, user_name, role_name, issuer, project_url):
    """
    Return role change email body
    :param change_type: Change type ('create', 'update', 'delete')
    :param project: Project object
    :param user_name: Name of target user
    :param role_name: Name of role as string
    :param issuer: User object for issuing user
    :param project_url: URL for the project
    :return: String
    """
    body = MESSAGE_HEADER.format(recipient=user_name)

    if change_type == 'create':
        body += MESSAGE_ROLE_CREATE.format(
            issuer_name=issuer.name,
            issuer_email=issuer.email,
            role=role_name,
            project=project.title,
            project_url=project_url)

    elif change_type == 'update':
        body += MESSAGE_ROLE_UPDATE.format(
            issuer_name=issuer.name,
            issuer_email=issuer.email,
            role=role_name,
            project=project.title,
            project_url=project_url)

    elif change_type == 'delete':
        body += MESSAGE_ROLE_DELETE.format(
            issuer_name=issuer.name,
            issuer_email=issuer.email,
            project=project.title)

    body += MESSAGE_FOOTER
    return body


# Sending functions ------------------------------------------------------


def send_role_change_mail(change_type, project, user, role, request):
    """
    Send email to user when their role in a project has been changed.
    :param change_type: Change type ('create', 'update', 'delete')
    :param project: Project object
    :param user: User object
    :param role: Role object (can be None for deletion)
    :param request: HTTP request
    :return: 1 or 0 depending on email sending success
    """
    project_url = request.build_absolute_uri(reverse(
        'projectroles:detail',
        kwargs={'project': project.omics_uuid}))

    subject = get_role_change_subject(change_type, project)
    body = get_role_change_body(
        change_type=change_type,
        project=project,
        user_name=user.name,
        role_name=role.name if role else '',
        issuer=request.user,
        project_url=project_url)

    return send_mail(
        subject,
        body,
        EMAIL_SENDER,
        [user.email],
        fail_silently=not DEBUG)


def send_invite_mail(invite, request):
    """
    Send an email invitation to user not yet registered in the system.
    :param invite: ProjectInvite object
    :param request: HTTP request
    :return: 1 or 0 depending on email sending success
    """
    invite_url = build_invite_url(invite, request)

    body = get_invite_body(
        project=invite.project,
        issuer=invite.issuer,
        role_name=invite.role.name,
        invite_url=invite_url,
        date_expire_str=localtime(
            invite.date_expire).strftime('%Y-%m-%d %H:%M'))
    body += get_invite_message(invite.message)
    body += get_email_footer()

    subject = get_invite_subject(invite.project)

    return send_mail(
        subject,
        body,
        EMAIL_SENDER,
        [invite.email],
        fail_silently=not DEBUG)


def send_accept_note(invite, request):
    """
    Send a notification email to the issuer of an invitation when a user
    accepts the invitation.
    :param invite: ProjectInvite object
    :param request: HTTP request
    :return: 1 or 0 depending on email sending success
    """
    subject = SUBJECT_PREFIX + ' ' + SUBJECT_ACCEPT.format(
        user_name=request.user.name,
        project=invite.project.title)

    message = MESSAGE_HEADER.format(
        recipient=invite.issuer.name)

    message += MESSAGE_ACCEPT_BODY.format(
        role=invite.role.name,
        project=invite.project.title,
        user_name=request.user.name,
        user_email=request.user.email)

    message += MESSAGE_FOOTER

    return send_mail(
        subject,
        message,
        EMAIL_SENDER,
        [invite.issuer.email],
        fail_silently=not DEBUG)


def send_expiry_note(invite, request):
    """
    Send a notification email to the issuer of an invitation when a user
    attempts to accept an expired invitation.
    :param invite: ProjectInvite object
    :param request: HTTP request
    :return: 1 or 0 depending on email sending success
    """
    subject = SUBJECT_PREFIX + ' ' + SUBJECT_EXPIRY.format(
        user_name=request.user.name,
        project=invite.project.title)

    body = MESSAGE_HEADER.format(
        recipient=invite.issuer.name)

    body += MESSAGE_EXPIRY_BODY.format(
        role=invite.role.name,
        project=invite.project.title,
        user_name=request.user.name,
        user_email=request.user.email,
        date_expire=localtime(invite.date_expire).strftime('%Y-%m-%d %H:%M'))

    body += MESSAGE_FOOTER

    return send_mail(
        subject,
        body,
        EMAIL_SENDER,
        [invite.issuer.email],
        fail_silently=not DEBUG)
