.. _ui_search:

Search Bar
^^^^^^^^^^

If enabled by the administrator, it is possible to search SODAR for projects and
categories, assay sources and samples, files in iRODS, and timeline events. The
search bar can be found at the top of the SODAR UI.

Basic Search
============

Write the search terms in the text box and then press :kbd:`Enter` or click
the :guilabel:`Search` button. You can enter multiple terms separated by white
space, but each term must be at least three characters long. If your search
term contains a space, the term must be enclosed in 'single quotes' or "double
quotes".

Search Keywords
===============

The scope of the search can be further restricted to a specific project or a
specific category and its children. To do so, add ``project:<uuid or title>``
to the search terms, replacing ``<uuid or title>`` with the UUID or title of
the project or category. Note that if the title contains spaces, it must be
quoted. For example, to search for proteomics data under a project identified by
``f30e894e-753f-4bf3-b999-c6e8b3e4d350``, you could write::

    proteomic project:f30e894e-753f-4bf3-b999-c6e8b3e4d350

Furthermore, if you want to restrict the search scope to objects of a particular
type, you can add the ``type:<value>`` keyword. Supported values for the type
keyword include:

- ``source`` for study sources (e.g. patients or donors);
- ``sample`` for samples derived from some study source;
- ``file`` for files in iRODS;
- ``project`` for projects and categories;
- ``timeline`` for timeline events (e.g. file uploads, project updates, and
  so on).

For instance, you can search for files containing "brain" in their name with the
following query:

.. code-block:: text

    brain type:file

Advanced Search
===============

The advanced search page can be reached by clicking on the magnifying glass
button to the left of the search box. There, you can enter multiple search
terms, one for each line, without needing to quote them. You can specify the
search keywords using a dedicated text box.
