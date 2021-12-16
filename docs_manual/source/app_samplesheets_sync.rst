.. _app_samplesheets_sync:

Remote Sheet Synchronization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is possible to set up a project's sample sheets to be synchronized from
another project, which may be on the same SODAR instance or a separate one. This
can be useful if e.g. you want to set up a public demonstration version of a
project without access to sensitive data.

.. note::

    This functionality is intended for special cases only. When in doubt of
    whether it should be use, contact the project owner or the administrators of
    your SODAR instance.

To set up sheet synchronization, you need the following things:

- Owner or delegate access to a project with sample sheets you want to
  synchronize (the *source project*)
- Owner or delegate access to a project without sample sheets, into which the
  other project's sheets will be synchronized (the *target project*)

To set up sheet synchronization, follow these steps:

- Navigate to the :ref:`Project Update <ui_project_update>` view for the
  *source project*
- Generate a token string and enter it in the *Token for sheet synchronization*
  field. Make sure to click the :guilabel:`Update` button to save the changes.
- Navigate to the :ref:`Project Update <ui_project_update>` view for the
  *target project*
- Click the checkbox for *Enable sheet synchronization*
- Enter the :ref:`REST API <api_samplesheets>` URL for sheet synchronization of
  the source site and project into *URL for sheet synchronization*
- Add the same token you generated earlier into
  *Token for sheet synchronization* and save the changes to the target project.

After this, SODAR will periodically update the sample sheets in the target
project. Changes made to the sheets in the source project will be visible in
the target project without the need for further actions.

If you need to synchronize the sheets manually, you can navigate to the Sample
Sheets app, open the :guilabel:`Sheet Operations` dropdown and select
:guilabel:`Sync Sheets`.

.. note::

    :ref:`Sample sheet import and creation <app_samplesheets_create>` are not
    allowed for a project with synchronization enabled.

.. note::

    If the source project is on a different instance of SODAR, it must be
    reachable from the network of the target project for the synchronization
    to function.
