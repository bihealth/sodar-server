.. _app_samplesheets_irods_ticket:

iRODS Access Tickets
^^^^^^^^^^^^^^^^^^^^

The Sample Sheets application allows you to create iRODS access tickets. The
tickets enable read-only access to specific collections or data objects in a
project's sample data repository without the need for a login or project
membership. This can be used to provide URLs for simple links to iRODS
files for e.g. enabling access to SODAR data from other software.

.. warning::

    Anyone with the URL and network access to your iRODS server can access these
    files regardless of their project roles. Care should be taken in what is
    shared publicly and to whom tickets are provided.

.. hint::

    From SODAR v1.1 onwards it is possible to restrict ticket access to users
    from certain hosts. Read further for instructions on how to do this.


Browsing Access Tickets
=======================

To browse access tickets in a project, open the :guilabel:`Sheet Operations`
dropdown and select :guilabel:`iRODS Access Tickets`. The view displays a list
of tickets created in the project.

.. figure:: _static/app_samplesheets/irods_ticket_list.png
    :align: center
    :scale: 60%

    iRODS access ticket list

For each ticket, the list displays the following information:

Name
    Collection or data object name and label for the ticket. The name works as
    a link to the collection or data object in Davrods. A button for copying the
    ticket link with the access token included is also included. If access to
    the ticket is restricted to specific hosts, those will be displayed here as
    badges.
Ticket
    The token string of the access ticket.
User
    The user who created the ticket.
Created
    Date and time of ticket creation.
Expires
    Expiry date for the ticket, or *"Never"* if no expiry has been set.


.. _app_samplesheets_irods_ticket_create:

Creating Access Tickets
=======================

With a sufficient role in a project (contributor or above), you can create
access tickets for any collection or data object in the project within the
following constraints:

- The target (collection or data object) must exist.
- The target must belong to the project in question.
- The target must be within an assay collection.
- The path must **not** be equal an assay root collection.
- There must not be another active ticket for the same target.

To create a ticket, navigate to the access ticket list of the desired project
and click on :guilabel:`Create Ticket`. This will open the form for ticket
creation.

.. figure:: _static/app_samplesheets/irods_ticket_form.png
    :align: center
    :scale: 60%

    iRODS access ticket creation form

The form contains the following items:

Path
    Full iRODS path for the collection or data object for which the ticket
    should be created. See constraints above.
Label
    Optional text label for the ticket. This will be displayed for the ticket
    to e.g. inform other users of the purpose for which the ticket was created.
Expiry date
    Optional date for ticket expiry.
Allowed hosts
    Optional comma-separated list of hosts from which access to the ticket URL
    is allowed. Hosts can be given as DNS host names like ``site.example.com``
    or IP addresses such as ``127.0.0.1``. A project-specific default value for
    allowed hosts can be set by a project owner or delegate in the
    :ref:`project update view <ui_project_update>`. This can be overridden for
    each ticket if needed. If no hosts are listed for a ticket, access is
    allowed from any host for those who know the ticket URL.


Updating Access Tickets
=======================

To update an existing access ticket, open the dropdown menu on the right hand
side of the ticket list and select :guilabel:`Update Ticket`. In the form, you
can edit the label and the expiry date for the ticket. The path can not be
edited. To enable ticket access to another iRODS collection, you need to create
another ticket.


Deleting Access Tickets
=======================

To delete an access ticket, open the dropdown menu associated with a ticket in
the ticket list and select :guilabel:`Delete Ticket`. After confirming the
deletion, the collection or data object the ticket targeted can no longer be
accessed with the token string.


Managing Tickets for UCSC Track Hubs
====================================

Tickets for
`track hubs <https://genome.ucsc.edu/goldenpath/help/hgTrackHubHelp.html>`_ for
`UCSC Genome Browser <https://genome.ucsc.edu/>`_ integration are a special
case, as they are also visible in the sample sheets GUI.

If you upload a collection with files under an assay collection called
``TrackHubs`` using Landing Zones, the track hub collection will be visible in
the assay shortcuts. E.g. if you want to create a track hub named
``YourTrackHub``, files should go under the collection
``TrackHubs/YourTrackHub``. Once files are uploaded, validated and moved from
the landing zone, the collection will be displayed in the GUI.

.. figure:: _static/app_samplesheets/irods_ticket_hub.png
    :align: center

    Track hub in assay shortcuts

Once you create an access ticket for the track hub collection, a button for
accessing the collection with the ticket link is automatically added to the
assay shortcut. The URL can also be copied into the clipboard from this link.


.. figure:: _static/app_samplesheets/irods_ticket_hub_link.png
    :align: center

    Track hub in assay shortcuts with ticket link

.. note::

    GUI links for access tickets for collections other than track hubs will be
    introduced in a later SODAR release. For now, the tickets can be viewed in
    the access ticket list.
