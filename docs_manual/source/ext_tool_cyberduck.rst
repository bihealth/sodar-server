.. _ext_tool_cyberduck:

Cyberduck File Browser for iRODS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Cyberduck is a libre network storage browser for Mac and Windows.
It can be used to access the iRODS filesystem on SODAR directly.
We cannot give you more support than the content of this document though.

Installation & Setup
====================

1. Download the Cyberduck installer from this website:
https://cyberduck.io/download/

.. note::
    While Cyberduck is generally free to use, it will ask you to
    donate to the project by making a one-time license key purchase.

2. Download the SODAR iRODS connection profile:
   :download:`iRODS (SODAR).cyberduckprofile <_static/ext_tool_cyberduck/iRODS (SODAR).cyberduckprofile>`

3. Install and start Cyberduck. Your screen should look like this:

   .. image:: _static/ext_tool_cyberduck/Cyberduck_home_empty.png

4. Import the downloaded Cyberduck profile by double-clicking or dragging it
   onto the Cyberduck window. A new dialog should appear. Fill in your
   SODAR username and password in the respective fields.

   .. image:: _static/ext_tool_cyberduck/Cyberduck_new_profile.png


Using Cyberduck
===============

1. Connect to SODAR iRODS by double-clicking on the newly saved bookmark.

   .. image:: _static/ext_tool_cyberduck/Cyberduck_home_profile.png

2. The file browser should list collections for all projects you have access
   too. Navigate the directory tree like in any other file browser. The
   directory you're currently in is shown in the top bar.

   .. image:: _static/ext_tool_cyberduck/Cyberduck_irods_home.png

3. You can also jump to a specific folder (i. e. iRODS path copied from SODAR)
   via the “Go” > “Go to folder” menu.

   .. image:: _static/ext_tool_cyberduck/Cyberduck_goto_folder.png

4. Files and collections can be downloaded via the right-click menu. Uploads to
   the current directory can be started via the action button on top or via the
   right-click menu.

   .. image:: _static/ext_tool_cyberduck/Cyberduck_irods_download.png

5. Click “Disconnect” in the top right corner once you are done.
