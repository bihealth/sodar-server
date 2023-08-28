.. _admin_commands:

Management Commands
^^^^^^^^^^^^^^^^^^^

This section briefly lists the management commands available for SODAR
administrators with shell access, in addition to the built-in commands in Django
and used third party components. For more details on their usage, use the
``-h`` or ``--help`` argument.


SODAR Core Commands
===================

These commands originate in SODAR Core. More information can be found in the
`SODAR Core documentation <https://sodar-core.readthedocs.io/en/latest/>`_.

``addremotesite``
    Add remote site for remote project synchronization.
``batchupdateroles``
    Batch update project roles and send invites.
``cleanappsettings``
    Clean up unused application settings.
``deletecache``
    Delete SODAR Cache entries.
``geticons``
    Download and install the latest versions of iconify icon sets. Must be
    followed by ``collectstatic`` to take effect.
``synccache``
    Synchronize the SODAR Cache.
``syncgroups``
    Synchronize user groups.
``syncmodifyapi``
    Synchronize project metadata and user access in iRODS. Generally should only
    be used in development.
``syncremote``
    Synchronize project and user data from a remote site if remote project sync
    is enabled.


SODAR Commands
==============

These commands originate from the SODAR applications and are specific to
operations regarding sample sheets, landing zones, iRODS data and ontologies.

``busyzones``
    Return list of currently busy landing zones.
``importobo``
    Import OBO format ontology. See :ref:`admin_ontologyaccess`.
``importomimm``
    Import OMIM catalog as an ontology. See :ref:`admin_ontologyaccess`.
``inactivezones``
    Return list of landing zones last modified over two weeks ago.
``irodsorphans``
    Find orphans in iRODS project collections.
``syncnames``
    Synchronize alternative names for sample sheet material search.
``syncstudytables``
    Build study render tables in cache for all study tables. These will be
    automatically built when accessing sample sheets if existing  cache is not
    up-to-date, but this can be used to e.g. regenerate the cache if something
    has been changed in study table rendering.
