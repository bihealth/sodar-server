.. _app_landingzones_browse:

Browsing Landing Zones
^^^^^^^^^^^^^^^^^^^^^^

This section describes how to browse your landing zones in the SODAR user
interface.


Landing Zone List
=================

The main view in the Landing Zones application displays a list of your active
landing zones (also referred to as "zones" for brevity).

.. figure:: _static/app_landingzones/zone_list.png
    :align: center
    :scale: 50%

    Landing zone list

The following details are available for each landing zone:

Zone
    The title of the zone along with a tooltip for verifying to which assay the
    zone belongs in. The zone name also acts as its collection name in iRODS.
    If a special configuration is used for the zone, it is displayed here.
Status Info
    Detailed status information on the most recent action performed on the zone.
    Successful actions are described here along with detailed information on
    failures. Also included is a badge displaying the zone's current file count
    and size in iRODS
Status
    A coloured representation of the current zone status. If the zone is
    currently locked for read-only access due to an ongoing operation, a lock
    icon is also displayed.
iRODS Links
    Four buttons with iRODS links for the zone are presented here.
Zone Dropdown
    For each active zone, there is a dropdown menu for zone specific operations.

Project owners and delegates will also be able to see active zones of other
users in the project in a separate list within the same view. They can also
perform the same validation, moving and deletion actions as the zone owner.


Status Types
============

The following status types can appear during the lifetime of a landing zone:

CREATING
    Creation of landing zone in iRODS in process.
NOT CREATED
    Creating landing zone in iRODS failed.
ACTIVE
    Available with write access for the user.
PREPARING
    Preparing transaction for validation and moving.
VALIDATING
    Validation OK, moving files into sample data repository.
MOVED
    Files moved successfully, landing zone removed.
FAILED
    Validation or moving failed.
DELETING
    Deletion of landing zone in process.
DELETED
    Landing zone deleted.


iRODS Links
===========

The buttons for iRODS linking for the landing zone are identical to the ones
seen in the :ref:`Sample Sheets <app_samplesheets>` application:

|btn_assay_list| List Files
    Opens a modal with a flat iRODS file list of the landing zone.
|btn_assay_path| Copy iRODS Path into Clipboard
    Copies the iRODS path of the landing zone, to be used with iRODS iCommands.
|btn_assay_url| Copy WebDAV URL into Clipboard
    Copies the entire WebDAV URL for the landing zone path.
|btn_assay_webdav| Browse Files in WebDAV
    Opens a new browser tab with the Davrods web interface for browsing the
    landing zone collection through WebDAV.


iRODS File List Modal
=====================

The iRODS file list modal is slightly different from the similar modal in the
Sample Sheets app. It displays collections in addition to files to help
visualize which root level collections are expected. Furthermore, a check mark
is displayed on the right hand side column for files, if the expected ``.md5``
checksum file is accompanying the actual data file.


.. figure:: _static/app_landingzones/irods_file_list.png
    :align: center
    :scale: 60%

    iRODS file list modal for a landing zone


.. |btn_assay_list| image:: _static/app_samplesheets/btn_assay_list.png
.. |btn_assay_path| image:: _static/app_samplesheets/btn_assay_path.png
.. |btn_assay_url| image:: _static/app_samplesheets/btn_assay_url.png
.. |btn_assay_webdav| image:: _static/app_samplesheets/btn_assay_webdav.png
