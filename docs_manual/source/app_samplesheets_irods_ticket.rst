.. _app_samplesheets_irods_ticket:

iRODS Access Tickets
^^^^^^^^^^^^^^^^^^^^

The Sample Sheets application allows you to create iRODS access tickets. The
tickets enable read-only access to specific collections in a project's sample
data repository without the need for a login or project membership. This can be
used to provide URLs for simple links to iRODS collections for e.g. enabling
access to SODAR data from other software.

.. warning::

    Anyone with the URL and network access to your iRODS server can access these
    collections regardless of their project roles. Care should be taken in what
    is shared publicly and to whom tickets are provided.


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
    Collection name and label for the ticket. The name works as a link to the
    collection in Davrods. A button for copying the ticket link with the
    access token included is also included.
Ticket
    The token string of the access ticket.
User
    The user who created the ticket.
Created
    Date and time of ticket creation.
Expires
    Expiry date for the ticket, or *"Never"* if no expiry has been set.


Creating Access Tickets
=======================

With a sufficient role in a project (contributor or above), you can create
access tickets for any collection in the project within the following
constraints:

- The collection must exist.
- The collection must belong to the project in question.
- The collection must be within an assay collection.
- The collection must **not** be an assay root collection.
- There must not be another active ticket for the same collection.

To create a ticket, navigate to the access ticket list of the desired project
and click on :guilabel:`Create Ticket`. This will open the form for ticket
creation.

.. figure:: _static/app_samplesheets/irods_ticket_form.png
    :align: center
    :scale: 60%

    iRODS access ticket creation form

The form contains the following items:

Path
    Full iRODS path for the collection for which the ticket should be created.
    See constraints above.
Label
    Optional text label for the ticket. This will be displayed for the ticket
    to e.g. inform other users of the purpose for which the ticket was created.
Expiry Date
    Optional date for ticket expiry.


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
deletion, the collection the ticket targeted can no longer be accessed with the
token string.


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
