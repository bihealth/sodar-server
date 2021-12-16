.. _ui_project_members:

Project Members
^^^^^^^^^^^^^^^

The member view displays the roles currently assigned to users within a
project or a category. These roles control the access to project data and SODAR
functions. Users with sufficient access can also add, update and remove roles
through this view.

.. figure:: _static/sodar_ui/project_members.png
    :align: center
    :scale: 50%

    Project members view


Member Roles
============

In SODAR, a single *role* at a time can be assigned to a user within a project.
The following types of roles are available:

Project Owner
    Full access to project, with the ability to assign roles including delegates
    and transferring ownership to another user.
Project Delegate
    Full access to project with the exception of modifying owner or delegate
    roles. This role is assigned by a project owner.
Project Contributor
    User with access to create and modify data within a project, e.g. uploading
    files and editing sample sheets, with some limitations. For example,
    modifying project meta data or user roles is not allowed.
Project Guest
    Read-only access to project data.

Project owner roles are inherited from parent categories. One owner is allowed
per project, with the exception of inherited owners. The amount of allowed
delegates is set by the server administrators. For contributors and guests,
the amount per project is not limited.


Adding Members
==============

Users with an owner or delegate role are able to add and update project member
roles. To add a SODAR user as a member, open the :guilabel:`Member Operations`
dropdown and select :guilabel:`Add Member`.

.. figure:: _static/sodar_ui/project_members_dropdown.png
    :align: center
    :scale: 80%

    Member operations dropdown

You are presented with a form to select a user and a role for them. The user
field works as a search box, where you can start typing a person's name or email
address and available options will be presented as you type. If the user is not
yet a SODAR user, you can also type an email address and be redirected to the
separate invitation form.

.. figure:: _static/sodar_ui/project_members_add.png
    :align: center
    :scale: 65%

    Member adding form

If email is enabled on the SODAR server, an email notification is sent to the
user being added into the project. You can preview this email by clicking the
:guilabel:`Preview` button. To assign the role, click the :guilabel:`Add`
button.


Updating Members
================

If you want to update the role of an existing member, open the dropdown next to
the user in the member list and click :guilabel:`Update Member`. You will be
presented with a form to change the user role. Similarly, if you want to remove
the membership from a user, you can click :guilabel:`Remove Member`.

.. figure:: _static/sodar_ui/project_members_update.png
    :align: center
    :scale: 80%

    Member update dropdown

Modifying the project owner works slightly differently. In the dropdown next to
the owner in the member list, you will see a :guilabel:`Transfer Ownership`
option. This will present you a form where you can select a new owner from the
current project members as well as select a new role for the current owner. This
functionality is only available for users currently set as the project owner.

.. figure:: _static/sodar_ui/project_members_owner.png
    :align: center
    :scale: 80%

    Owner update dropdown

These dropdowns also contain a :guilabel:`History` link, which will take you to
the :ref:`Timeline <ui_project_timeline>` application to view the history of the
user's membership(s) in this project.


Inviting Members
================

If a user has never before logged in to SODAR, you can send them a project
invitation by email. For this, open the :guilabel:`Member Operations` dropdown
and select :guilabel:`Send Invites`. Alternatively, you can enter an email
address in the add member view as described above.

This presents you a form where you can add the user email, project role and an
optional message displayed in the invitation email. You can preview the email by
clicking the :guilabel:`Preview` and send it by clicking :guilabel:`Send`.

.. figure:: _static/sodar_ui/project_members_invite.png
    :align: center
    :scale: 60%

    Member invite form

You will receive a notification for the user accepting the invitation. To view
your existing invitations, navigate to the member list, open the
:guilabel:`Member Operations` dropdown and select :guilabel:`View Invites`. Note
that invitations will expire after a certain time specified by SODAR
administrators.
