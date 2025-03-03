.. _ui_project_timeline:

Project Timeline
^^^^^^^^^^^^^^^^

The *Timeline* application displays a detailed log of activity in the project.
This includes e.g. member role assignments, file transfers from landing zones,
and changes to the sample sheets. The activity is displayed as a list of events.

.. figure:: _static/sodar_ui/timeline.png
    :align: center
    :scale: 50%

    Project timeline

For each event the following details are available:

Timestamp
    Time of the event's creation. This doubles as a link to a modal which
    displays the event status history. This can be useful information e.g. in
    case of asynchronous background events.
User
    User initiating the event.
Description
    Description of the event. The description is preceded by a badge displaying
    the event type. Objects included in the description are linked to the
    respective application. Objects also have a history link displayed as a
    clock icon. Clicking on the icon opens a list of all events related to the
    object within the project. The title of the object also often works as a
    link to the related application. Possible extra JSON data is displayed as a
    link in the right hand side of the field. The link opens a modal displaying
    the JSON data.
Status
    Current status of the event.

For viewing site-wide events not related to any specific project, open the
:ref:`ui_user_dropdown` and click :guilabel:`Site-Wide Events`.
